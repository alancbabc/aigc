#!/usr/bin/env python3
"""Extract source images from doc/docx/markdown-like inputs for news-commentary."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent

WORDPROCESSING_SHAPE_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
DRAWINGML_MAIN_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
OFFICE_DOCUMENT_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
WORD_MAIN_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

NS = {
    "a": DRAWINGML_MAIN_NS,
    "r": OFFICE_DOCUMENT_REL_NS,
    "rel": PACKAGE_REL_NS,
    "w": WORD_MAIN_NS,
    "wp": WORDPROCESSING_SHAPE_NS,
}


def slugify_stem(path: Path) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in path.stem)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "source"


def detect_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".doc":
        return "doc"
    if suffix == ".docx":
        return "docx"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".pdf":
        return "pdf"
    return "other"


def normalize_filename_key(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_image_size(path: Path) -> tuple[int | None, int | None]:
    suffix = path.suffix.lower()
    try:
        with open(path, "rb") as image_file:
            if suffix == ".png":
                header = image_file.read(24)
                if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
                    width, height = struct.unpack(">II", header[16:24])
                    return int(width), int(height)
            elif suffix in {".jpg", ".jpeg"}:
                image_file.read(2)
                while True:
                    marker_prefix = image_file.read(1)
                    if marker_prefix != b"\xff":
                        return None, None
                    marker = image_file.read(1)
                    while marker == b"\xff":
                        marker = image_file.read(1)
                    if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3", b"\xc5", b"\xc6", b"\xc7", b"\xc9", b"\xca", b"\xcb", b"\xcd", b"\xce", b"\xcf"}:
                        segment_length = struct.unpack(">H", image_file.read(2))[0]
                        if segment_length < 7:
                            return None, None
                        image_file.read(1)
                        height, width = struct.unpack(">HH", image_file.read(4))
                        return int(width), int(height)
                    if marker in {b"\xd8", b"\xd9"}:
                        continue
                    segment_length_data = image_file.read(2)
                    if len(segment_length_data) != 2:
                        return None, None
                    segment_length = struct.unpack(">H", segment_length_data)[0]
                    image_file.seek(max(segment_length - 2, 0), 1)
    except OSError:
        return None, None

    return None, None


def normalize_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "")
    return value.strip()


def paragraph_text(paragraph: ET.Element) -> str:
    texts: list[str] = []
    for text_node in paragraph.findall(".//w:t", NS):
        if text_node.text:
            texts.append(text_node.text)
    return normalize_text("".join(texts))


def paragraph_image_rel_ids(paragraph: ET.Element) -> list[str]:
    rel_ids: list[str] = []
    for blip in paragraph.findall(".//a:blip", NS):
        rel_id = blip.attrib.get(f"{{{OFFICE_DOCUMENT_REL_NS}}}embed")
        if rel_id:
            rel_ids.append(rel_id)
    return rel_ids


def paragraph_docpr_metadata(paragraph: ET.Element) -> dict[str, str]:
    title_parts: list[str] = []
    descr_parts: list[str] = []
    for docpr in paragraph.findall(".//wp:docPr", NS):
        title = normalize_text(docpr.attrib.get("title", ""))
        descr = normalize_text(docpr.attrib.get("descr", ""))
        if title:
            title_parts.append(title)
        if descr:
            descr_parts.append(descr)
    return {
        "title": normalize_text(" | ".join(title_parts)),
        "descr": normalize_text(" | ".join(descr_parts)),
    }


def is_caption_like(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False
    if len(normalized) > 120:
        return False
    caption_prefixes = (
        "图",
        "图表",
        "图示",
        "图像",
        "图片",
        "附图",
        "表",
        "figure",
        "fig.",
        "fig ",
        "image",
        "chart",
        "diagram",
        "screenshot",
    )
    lowered = normalized.lower()
    if lowered.startswith(caption_prefixes):
        return True
    return bool(re.match(r"^(图|表|figure|fig\.?|image|chart|diagram)\s*[0-9a-zA-Z一二三四五六七八九十:：.-]", normalized, re.IGNORECASE))


def choose_caption(current_text: str, previous_text: str, next_text: str, docpr_title: str, docpr_descr: str) -> str:
    candidates = [docpr_title, docpr_descr]
    if current_text and is_caption_like(current_text):
        candidates.append(current_text)
    if next_text and is_caption_like(next_text):
        candidates.append(next_text)
    if previous_text and is_caption_like(previous_text):
        candidates.append(previous_text)
    for candidate in candidates:
        normalized = normalize_text(candidate)
        if normalized:
            return normalized
    for fallback in [current_text, next_text, previous_text]:
        normalized = normalize_text(fallback)
        if normalized and len(normalized) <= 80:
            return normalized
    return ""


def choose_context(current_text: str, previous_text: str, next_text: str, caption: str) -> str:
    context_parts: list[str] = []
    for candidate in [previous_text, current_text, next_text]:
        normalized = normalize_text(candidate)
        if not normalized:
            continue
        if normalized == caption:
            continue
        if is_caption_like(normalized) and normalized != current_text:
            continue
        context_parts.append(normalized)
    merged = normalize_text(" ".join(context_parts))
    if len(merged) > 240:
        return merged[:237].rstrip() + "..."
    return merged


def extract_docx_paragraph_context(archive: zipfile.ZipFile) -> dict[str, dict[str, str]]:
    try:
        document_xml = archive.read("word/document.xml")
        rels_xml = archive.read("word/_rels/document.xml.rels")
    except KeyError:
        return {}

    document_root = ET.fromstring(document_xml)
    rels_root = ET.fromstring(rels_xml)

    rel_id_to_target: dict[str, str] = {}
    for relationship in rels_root.findall(".//rel:Relationship", NS):
        rel_id = relationship.attrib.get("Id")
        target = relationship.attrib.get("Target")
        if rel_id and target:
            rel_id_to_target[rel_id] = target.replace("\\", "/")

    paragraphs = document_root.findall(".//w:body//w:p", NS)
    paragraph_blocks: list[dict[str, Any]] = []
    for paragraph in paragraphs:
        text = paragraph_text(paragraph)
        rel_ids = paragraph_image_rel_ids(paragraph)
        docpr = paragraph_docpr_metadata(paragraph)
        paragraph_blocks.append({
            "text": text,
            "rel_ids": rel_ids,
            "title": docpr["title"],
            "descr": docpr["descr"],
        })

    media_context: dict[str, dict[str, str]] = {}
    for index, block in enumerate(paragraph_blocks):
        if not block["rel_ids"]:
            continue
        previous_text = ""
        next_text = ""

        for candidate_index in range(index - 1, -1, -1):
            candidate_text = normalize_text(paragraph_blocks[candidate_index]["text"])
            if candidate_text:
                previous_text = candidate_text
                break

        for candidate_index in range(index + 1, len(paragraph_blocks)):
            candidate_text = normalize_text(paragraph_blocks[candidate_index]["text"])
            if candidate_text:
                next_text = candidate_text
                break

        current_text = normalize_text(block["text"])
        caption = choose_caption(current_text, previous_text, next_text, block["title"], block["descr"])
        context_hint = choose_context(current_text, previous_text, next_text, caption)

        for rel_id in block["rel_ids"]:
            target = rel_id_to_target.get(rel_id)
            if not target:
                continue
            normalized_target = target.removeprefix("../").replace("\\", "/")
            if not normalized_target.startswith("word/"):
                normalized_target = f"word/{normalized_target}"
            media_context.setdefault(
                normalized_target,
                {
                    "caption": caption,
                    "context_hint": context_hint,
                    "docpr_title": block["title"],
                    "docpr_descr": block["descr"],
                },
            )

    return media_context


def infer_video_usability(asset_type: str, width: int | None, height: int | None) -> tuple[bool, str]:
    if width is None or height is None:
        return False, "Image dimensions unavailable; require manual review before video use."
    if width < 160 or height < 120:
        return False, "Image is too small for stable video usage."
    if width < 640 or height < 360:
        return True, "Image is usable for source-image clips, but low resolution may soften after scale-plus-pad rendering."
    if asset_type in {"chart", "figure", "cover_image", "embedded_image", "screenshot"}:
        return True, "Image is large enough and suitable for source-image video clips."
    return True, "Image is usable for source-image video clips with scale-plus-pad handling if needed."


def infer_asset_type_from_texts(*values: str) -> str:
    combined = normalize_text(" ".join(values)).lower()
    if not combined:
        return "embedded_image"
    if any(token in combined for token in ["图表", "chart", "plot", "曲线", "数据图"]):
        return "chart"
    if any(token in combined for token in ["示意", "架构", "流程", "模型", "框架", "figure", "diagram", "workflow"]):
        return "figure"
    if any(token in combined for token in ["截图", "screenshot", "界面"]):
        return "screenshot"
    if any(token in combined for token in ["封面", "cover"]):
        return "cover_image"
    return "embedded_image"


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def resolve_markdown_image_path(markdown_path: Path, raw_reference: str) -> Path | None:
    cleaned = normalize_text(raw_reference).strip('"\'')
    if not cleaned:
        return None

    direct_candidate = (markdown_path.parent / cleaned).resolve()
    if direct_candidate.exists() and direct_candidate.is_file():
        return direct_candidate

    reference_name = Path(cleaned).name
    reference_key = normalize_filename_key(reference_name)
    reference_suffix = Path(reference_name).suffix.lower()

    for candidate in markdown_path.parent.iterdir():
        if not candidate.is_file():
            continue
        if reference_suffix and candidate.suffix.lower() != reference_suffix:
            continue
        if normalize_filename_key(candidate.name) == reference_key:
            return candidate.resolve()

    return None


def parse_markdown_image_manifest(markdown_path: Path) -> list[dict[str, str]]:
    text = read_text_file(markdown_path)
    lines = text.splitlines()

    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_manifest = False

    heading_pattern = re.compile(r"^#{1,6}\s*(.+?)\s*$")
    filename_pattern = re.compile(r"^(?:\d+[.)、．]?\s*)?(?:文件名|图片名|图像名|文件)\s*[:：]\s*(.+)$")
    title_pattern = re.compile(r"^(?:\d+[.)、．]?\s*)?标题\s*[:：]\s*(.+)$")
    hint_pattern = re.compile(r"^(?:\d+[.)、．]?\s*)?说明\s*[:：。．]?\s*(.+)$")
    markdown_image_pattern = re.compile(r"!\[(.*?)\]\((.+?)\)")

    def flush_current() -> None:
        nonlocal current
        if current and current.get("raw_reference"):
            entries.append(current)
        current = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        heading_match = heading_pattern.match(line)
        if heading_match:
            heading_text = normalize_text(heading_match.group(1))
            if "图片清单" in heading_text or "图像清单" in heading_text:
                flush_current()
                in_manifest = True
                continue
            if in_manifest and heading_text:
                break

        if not in_manifest:
            continue

        markdown_image_match = markdown_image_pattern.search(line)
        if markdown_image_match:
            flush_current()
            alt_text = normalize_text(markdown_image_match.group(1))
            raw_reference = normalize_text(markdown_image_match.group(2))
            current = {
                "raw_reference": raw_reference,
                "caption": alt_text,
                "context_hint": "",
            }
            continue

        filename_match = filename_pattern.match(line)
        if filename_match:
            flush_current()
            current = {
                "raw_reference": normalize_text(filename_match.group(1)),
                "caption": "",
                "context_hint": "",
            }
            continue

        if current is None:
            continue

        title_match = title_pattern.match(line)
        if title_match:
            current["caption"] = normalize_text(title_match.group(1))
            continue

        hint_match = hint_pattern.match(line)
        if hint_match:
            current["context_hint"] = normalize_text(hint_match.group(1))
            continue

        if not current.get("caption"):
            current["caption"] = normalize_text(line)
        elif not current.get("context_hint"):
            current["context_hint"] = normalize_text(line)

    flush_current()
    return entries


def extract_from_markdown(markdown_path: Path, images_dir: Path, source_id: str) -> tuple[list[dict[str, Any]], str | None, str | None]:
    manifest_entries = parse_markdown_image_manifest(markdown_path)
    extracted: list[dict[str, Any]] = []
    missing_references: list[str] = []

    for index, entry in enumerate(manifest_entries, start=1):
        raw_reference = entry.get("raw_reference", "")
        resolved_path = resolve_markdown_image_path(markdown_path, raw_reference)
        if resolved_path is None:
            missing_references.append(raw_reference)
            continue

        ext = resolved_path.suffix.lower() or ".bin"
        image_id = f"{source_id}_img{index:02d}"
        output_path = images_dir / f"{image_id}{ext}"
        shutil.copy2(resolved_path, output_path)

        caption = normalize_text(entry.get("caption", ""))
        context_hint = normalize_text(entry.get("context_hint", ""))
        width, height = read_image_size(output_path)
        asset_type = infer_asset_type_from_texts(resolved_path.name, caption, context_hint)
        is_usable_for_video, video_usage_reason = infer_video_usability(asset_type, width, height)
        if not context_hint:
            context_hint = "Declared in markdown image manifest."

        extracted.append(
            {
                "image_id": image_id,
                "source_id": source_id,
                "path": str(output_path).replace("\\", "/"),
                "asset_type": asset_type,
                "width": width,
                "height": height,
                "is_usable_for_video": is_usable_for_video,
                "video_usage_reason": video_usage_reason,
                "caption": caption,
                "context_hint": context_hint,
                "preferred_segment_types": ["opening", "headline", "discussion", "summary", "closing"],
            }
        )

    if missing_references:
        note = f"Parsed markdown image manifest, but could not match {len(missing_references)} referenced file(s): {', '.join(missing_references)}"
        return extracted, "missing_markdown_image_files", note

    if manifest_entries and not extracted:
        return extracted, "no_images_found", "Markdown image manifest was found, but no referenced image files could be resolved."

    return extracted, None, None


def extract_from_docx(docx_path: Path, images_dir: Path, source_id: str) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    with zipfile.ZipFile(docx_path) as archive:
        media_context = extract_docx_paragraph_context(archive)
        media_names = [name for name in archive.namelist() if name.startswith("word/media/") and not name.endswith("/")]
        media_names.sort()
        for index, media_name in enumerate(media_names, start=1):
            ext = Path(media_name).suffix.lower() or ".bin"
            image_id = f"{source_id}_img{index:02d}"
            output_path = images_dir / f"{image_id}{ext}"
            with archive.open(media_name) as src, open(output_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

            asset_type = "embedded_image"
            lower_name = media_name.lower()
            if "chart" in lower_name:
                asset_type = "chart"
            elif "figure" in lower_name or "fig" in lower_name:
                asset_type = "figure"

            width, height = read_image_size(output_path)
            is_usable_for_video, video_usage_reason = infer_video_usability(asset_type, width, height)
            context_meta = media_context.get(media_name, {})
            caption = normalize_text(context_meta.get("caption", ""))
            context_hint = normalize_text(context_meta.get("context_hint", ""))
            if not context_hint:
                title_bits = [
                    normalize_text(context_meta.get("docpr_title", "")),
                    normalize_text(context_meta.get("docpr_descr", "")),
                ]
                fallback_context = " | ".join(bit for bit in title_bits if bit)
                context_hint = fallback_context or "Extracted from document media bundle."

            extracted.append(
                {
                    "image_id": image_id,
                    "source_id": source_id,
                    "path": str(output_path).replace("\\", "/"),
                    "asset_type": asset_type,
                    "width": width,
                    "height": height,
                    "is_usable_for_video": is_usable_for_video,
                    "video_usage_reason": video_usage_reason,
                    "caption": caption,
                    "context_hint": context_hint,
                    "preferred_segment_types": ["headline", "discussion"],
                }
            )
    return extracted


def try_convert_with_soffice(input_path: Path, temp_dir: Path) -> Path | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None

    subprocess.run(
        [soffice, "--headless", "--convert-to", "docx", "--outdir", str(temp_dir), str(input_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    candidate = temp_dir / f"{input_path.stem}.docx"
    return candidate if candidate.exists() else None


def try_convert_with_word_com(input_path: Path, temp_dir: Path) -> Path | None:
    try:
        import win32com.client  # type: ignore
    except Exception:
        return None

    output_path = temp_dir / f"{input_path.stem}.docx"
    word = None
    document = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        document = word.Documents.Open(str(input_path))
        document.SaveAs(str(output_path), FileFormat=16)
        document.Close(False)
        word.Quit()
        return output_path if output_path.exists() else None
    except Exception:
        if document is not None:
            try:
                document.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        return None


def build_source_document(
    path: Path,
    source_id: str,
    extraction_status: str,
    note: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "source_id": source_id,
        "path": str(path).replace("\\", "/"),
        "kind": detect_kind(path),
        "extraction_status": extraction_status,
    }
    if note:
        data["note"] = note
    if error_code:
        data["error_code"] = error_code
    if error_message:
        data["error_message"] = error_message
    return data


def extract_single_source(input_path: Path, output_root: Path, temp_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_id = slugify_stem(input_path)
    images_dir = output_root / "images"
    ensure_dir(images_dir)

    kind = detect_kind(input_path)
    if kind == "docx":
        try:
            images = extract_from_docx(input_path, images_dir, source_id)
        except zipfile.BadZipFile:
            return (
                build_source_document(
                    input_path,
                    source_id,
                    "failed",
                    error_code="invalid_docx_archive",
                    error_message="File is not a valid .docx zip archive.",
                ),
                [],
            )
        status = "success" if images else "partial"
        note = None if images else "Document opened, but no embedded images were found."
        error_code = None if images else "no_images_found"
        error_message = None if images else "The document contains no extractable embedded images."
        return build_source_document(input_path, source_id, status, note, error_code, error_message), images

    if kind == "doc":
        converted = try_convert_with_word_com(input_path, temp_dir)
        if converted is None:
            converted = try_convert_with_soffice(input_path, temp_dir)
        if converted is None:
            return (
                build_source_document(
                    input_path,
                    source_id,
                    "failed",
                    error_code="conversion_tool_missing_or_failed",
                    error_message="Could not convert .doc to .docx. Install Word COM automation or LibreOffice/soffice for extraction.",
                ),
                [],
            )
        try:
            images = extract_from_docx(converted, images_dir, source_id)
        except zipfile.BadZipFile:
            return (
                build_source_document(
                    input_path,
                    source_id,
                    "failed",
                    note=f"Converted via {converted.name} before extraction.",
                    error_code="converted_docx_invalid",
                    error_message="Converted docx file is not a valid zip archive.",
                ),
                [],
            )
        status = "success" if images else "partial"
        note = f"Converted via {converted.name} before extraction."
        if not images:
            note = f"Converted via {converted.name}, but no embedded images were found."
        error_code = None if images else "no_images_found"
        error_message = None if images else "The converted document contains no extractable embedded images."
        return build_source_document(input_path, source_id, status, note, error_code, error_message), images

    if kind == "markdown":
        images, error_code, detail_note = extract_from_markdown(input_path, images_dir, source_id)
        status = "success" if images and error_code is None else "partial" if images or error_code else "failed"
        note = "Parsed markdown image manifest and sibling image files."
        if detail_note:
            note = f"{note} {detail_note}"
        error_message = None
        if error_code == "no_images_found":
            error_message = "Markdown image manifest did not resolve to any usable image file."
        elif error_code == "missing_markdown_image_files":
            error_message = "Some markdown-declared image files were not found next to the markdown source."
        return build_source_document(input_path, source_id, status, note, error_code, error_message), images

    return (
        build_source_document(
            input_path,
            source_id,
            "failed",
            error_code="unsupported_input",
            error_message=f"Unsupported source kind: {kind}",
        ),
        [],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract source visual assets for news-commentary workflow")
    parser.add_argument("--inputs", nargs="+", required=True, help="Source document paths (.doc/.docx/.md)")
    parser.add_argument("--output-dir", required=True, help="Output directory for source-assets")
    args = parser.parse_args()

    output_root = Path(args.output_dir).resolve()
    ensure_dir(output_root)
    temp_dir = output_root / ".tmp_conversion"
    ensure_dir(temp_dir)

    source_documents: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []

    for raw_input in args.inputs:
        input_path = Path(raw_input).resolve()
        if not input_path.exists():
            source_documents.append(
                {
                    "source_id": slugify_stem(input_path),
                    "path": str(input_path).replace("\\", "/"),
                    "kind": detect_kind(input_path),
                    "extraction_status": "failed",
                    "error_code": "source_not_found",
                    "error_message": "Source file does not exist.",
                }
            )
            continue

        source_document, extracted_images = extract_single_source(input_path, output_root, temp_dir)
        source_documents.append(source_document)
        images.extend(extracted_images)

    payload = {
        "schema_version": "1.0",
        "source_documents": source_documents,
        "images": images,
    }

    output_json = output_root / "source-visual-assets.json"
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
