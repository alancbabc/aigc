#!/usr/bin/env python3
"""Build clip-plan.json for news-commentary with optional automatic source-image routing."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_ANCHOR_IMAGE_BY_SPEAKER = {
    "host": "builtin-anchor-templates/default-news-duo-v1/visuals/anchors/female_solo.png",
    "guest": "builtin-anchor-templates/default-news-duo-v1/visuals/anchors/male_solo.png",
}
DEFAULT_DUO_REFERENCE_IMAGE = "builtin-anchor-templates/default-news-duo-v1/visuals/anchors/duo_close.png"
DEFAULT_TARGET_DIMENSIONS = {"width": 1536, "height": 1024}
SOLO_CONTINUOUS_SECONDS_THRESHOLD = 15.0
LTX_MERGE_MAX_DURATION_SECONDS = 16.0
DOCUMENT_BLOCK_CONTINUE_SCORE_THRESHOLD = 5
DOCUMENT_BLOCK_MAX_DURATION_SECONDS = 6.0

DATA_HEAVY_HINTS = [
    "数据", "图", "图表", "流程", "模型", "集群", "gpu", "训练", "部署", "闭环", "算力", "性能", "架构", "框架", "发布", "现场", "签约", "仪式",
]
VISUAL_PREFERRED_SEGMENTS = {"opening", "closing", "headline", "discussion", "summary", "intro", "technical", "capability", "outlook", "background"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "")
    return value.strip()


def tokenize_for_match(value: str) -> list[str]:
    normalized = normalize_text(value).lower()
    if not normalized:
        return []
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", normalized)
    return [token for token in tokens if len(token) >= 2]


def segment_lookup(script: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {segment["segment_no"]: segment for segment in script.get("segments", [])}


def line_lookup(script: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for segment in script.get("segments", []):
        for line in segment.get("lines", []):
            mapping[line["line_id"]] = line
    return mapping


def pick_duration_source(audio_payload: dict[str, Any], source_name: str) -> str:
    if source_name == "audio_timeline":
        return "audio_timeline"
    return "tts_plan"


def resolve_audio_path(entry: dict[str, Any]) -> str:
    explicit_path = entry.get("audio_path")
    if isinstance(explicit_path, str) and explicit_path:
        return explicit_path
    speaker = entry.get("speaker")
    entry_id = entry.get("entry_id")
    if speaker in {"host", "guest"} and isinstance(entry_id, str) and entry_id:
        return f"audio/{speaker}/{entry_id}.mp3"
    raise ValueError(f"Audio entry {entry.get('entry_id', '<unknown>')} is missing audio_path and cannot infer fallback path")


def validate_audio_entries(entries: list[dict[str, Any]]) -> None:
    _ = entries


def image_keywords(image: dict[str, Any]) -> list[str]:
    return tokenize_for_match(" ".join([
        str(image.get("caption", "")),
        str(image.get("context_hint", "")),
        str(image.get("asset_type", "")),
        Path(str(image.get("path", ""))).stem,
    ]))


def normalize_source_image(image: dict[str, Any], index: int) -> dict[str, Any]:
    image_id = str(image.get("image_id") or image.get("filename") or f"legacy_img_{index:02d}")
    source_id = str(image.get("source_id") or "source")
    path = str(image.get("path") or image.get("source_path") or image.get("filename") or "")
    asset_type = str(image.get("asset_type") or "embedded_image")
    width = image.get("width")
    height = image.get("height")
    if not isinstance(width, int):
        width = None
    if not isinstance(height, int):
        height = None
    is_usable_for_video = image.get("is_usable_for_video")
    if not isinstance(is_usable_for_video, bool):
        is_usable_for_video = bool(path)
    preferred_segment_types = image.get("preferred_segment_types")
    if not isinstance(preferred_segment_types, list) or not preferred_segment_types:
        preferred_segment_types = sorted(VISUAL_PREFERRED_SEGMENTS)
    caption = str(image.get("caption") or image.get("filename") or image_id)
    context_hint = str(image.get("context_hint") or image.get("video_usage_reason") or image.get("source_path") or "")
    return {
        "image_id": image_id,
        "source_id": source_id,
        "path": path.replace("\\", "/"),
        "asset_type": asset_type,
        "width": width,
        "height": height,
        "is_usable_for_video": is_usable_for_video,
        "video_usage_reason": str(image.get("video_usage_reason") or ""),
        "caption": caption,
        "context_hint": context_hint,
        "preferred_segment_types": preferred_segment_types,
    }


def normalize_source_images(source_visual_assets: dict[str, Any] | None) -> list[dict[str, Any]]:
    raw_images = (source_visual_assets or {}).get("images", [])
    if not isinstance(raw_images, list):
        return []
    return [normalize_source_image(image, index + 1) for index, image in enumerate(raw_images) if isinstance(image, dict)]


def entry_match_text(entry: dict[str, Any], segment: dict[str, Any], line: dict[str, Any]) -> str:
    return " ".join([
        str(entry.get("text", "")),
        str(line.get("text", "")),
        str(segment.get("segment_goal", "")),
        str(segment.get("takeaway", "")),
        str(segment.get("visual_hint", "")),
    ])


def score_image_for_entry(image: dict[str, Any], entry: dict[str, Any], segment: dict[str, Any], line: dict[str, Any]) -> int:
    if not image.get("is_usable_for_video", True):
        return -999

    text_blob = entry_match_text(entry, segment, line).lower()
    score = 0

    for token in image_keywords(image):
        if token and token in text_blob:
            score += 4 if len(token) >= 4 else 2
        elif token and text_blob in token:
            score += 1

    preferred_segments = set(image.get("preferred_segment_types", []))
    if segment.get("type") in preferred_segments:
        score += 2

    if segment.get("type") in VISUAL_PREFERRED_SEGMENTS and line.get("speaker") == "guest":
        score += 2

    if any(hint in text_blob for hint in DATA_HEAVY_HINTS):
        score += 2

    caption = str(image.get("caption", ""))
    context_hint = str(image.get("context_hint", ""))
    if any(word in caption + context_hint for word in ["发布", "现场"]) and any(word in text_blob for word in ["发布", "联合", "新闻"]):
        score += 4
    if any(word in caption + context_hint for word in ["模型", "流程", "集群", "gpu", "训练", "算力"]) and any(word in text_blob for word in ["模型", "流程", "集群", "gpu", "训练", "算力", "性能", "数据"]):
        score += 5

    return score


def choose_visual_assignment(
    entry: dict[str, Any],
    segment: dict[str, Any],
    line: dict[str, Any],
    source_images: list[dict[str, Any]],
    blocked_image_ids: set[str],
) -> tuple[str, dict[str, Any] | None, str, str]:
    segment_type = str(segment.get("type") or "")
    if segment_type not in VISUAL_PREFERRED_SEGMENTS:
        return "ltx", None, "Opening/closing defaults to anchor-led delivery.", f"Use {line['speaker']} anchor shot for on-camera delivery."

    scored: list[tuple[int, dict[str, Any]]] = []
    for image in source_images:
        if image["image_id"] in blocked_image_ids:
            continue
        score = score_image_for_entry(image, entry, segment, line)
        score += 1
        scored.append((score, image))

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_image = scored[0] if scored else (-999, None)

    if best_image is not None and best_score >= 7:
        return (
            "image_audio_ffmpeg",
            best_image,
            "Source image carries the informational payload better than a talking-head shot for this line.",
            f"Matched source image '{best_image.get('caption') or best_image['image_id']}' to this line based on caption/context overlap.",
        )

    if best_image is not None and best_score >= 5 and line.get("speaker") == "guest":
        return (
            "image_audio_ffmpeg",
            best_image,
            "Guest explanation is data/process-heavy, so a source image is preferred over repeated anchor footage.",
            f"Selected source image '{best_image.get('caption') or best_image['image_id']}' for a technical explanation beat.",
        )

    return "ltx", None, "Anchor shot keeps persona continuity for this beat.", f"Use {line['speaker']} anchor shot because no source image strongly matches this line."


def should_continue_document_block(
    entry: dict[str, Any],
    segment: dict[str, Any],
    line: dict[str, Any],
    active_image: dict[str, Any],
    current_block_duration: float,
) -> bool:
    if segment.get("type") in {"opening", "closing"}:
        return False
    continuation_score = score_image_for_entry(active_image, entry, segment, line)
    # Determine if adding this entry would exceed the 6-second maximum for a single
    # document-led block using one news image. If so, stop continuing the block.
    next_duration = float(entry.get("_computed_duration") or entry.get("duration_seconds") or 0.0)
    projected_duration = current_block_duration + next_duration
    return (continuation_score >= DOCUMENT_BLOCK_CONTINUE_SCORE_THRESHOLD) and (
        projected_duration <= DOCUMENT_BLOCK_MAX_DURATION_SECONDS
    )


def ltx_reference_key(entry: dict[str, Any], anchor_binding: str) -> str:
    if anchor_binding == "duo":
        return DEFAULT_DUO_REFERENCE_IMAGE
    speaker = str(entry.get("speaker") or "")
    return DEFAULT_ANCHOR_IMAGE_BY_SPEAKER.get(speaker, "")


def can_merge_ltx_entries(current_entries: list[dict[str, Any]], candidate: dict[str, Any]) -> bool:
    if not current_entries:
        return True

    first_entry = current_entries[0]
    first_binding = str(first_entry.get("_anchor_binding") or "duo")
    candidate_binding = str(candidate.get("_anchor_binding") or "duo")
    if first_binding != candidate_binding:
        return False

    if ltx_reference_key(first_entry, first_binding) != ltx_reference_key(candidate, candidate_binding):
        return False

    current_duration = sum(float(entry["_computed_duration"]) for entry in current_entries)
    return current_duration + float(candidate["_computed_duration"]) <= LTX_MERGE_MAX_DURATION_SECONDS


def force_minimum_document_clip(
    evaluated_entries: list[dict[str, Any]],
    script_segments: dict[int, dict[str, Any]],
    script_lines: dict[str, dict[str, Any]],
    source_images: list[dict[str, Any]],
    consumed_image_ids: set[str],
) -> None:
    has_document_entry = any(entry.get("_render_mode") == "image_audio_ffmpeg" and entry.get("_chosen_image") is not None for entry in evaluated_entries)
    if has_document_entry or not source_images:
        return

    candidates: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for entry in evaluated_entries:
        segment = script_segments[entry["segment_no"]]
        line = script_lines[entry["script_line_id"]]
        if segment.get("type") in {"opening", "closing"}:
            continue
        if float(entry.get("_computed_duration") or 0.0) > DOCUMENT_BLOCK_MAX_DURATION_SECONDS:
            continue
        best_score = -999
        best_image: dict[str, Any] | None = None
        for image in source_images:
            if image["image_id"] in consumed_image_ids:
                continue
            score = score_image_for_entry(image, entry, segment, line)
            if score > best_score:
                best_score = score
                best_image = image
        if best_image is not None:
            candidates.append((best_score, entry, best_image))

    if not candidates:
        raise ValueError("Usable source images exist, but no entry could be matched to a document clip.")

    candidates.sort(key=lambda item: item[0], reverse=True)
    best_score, chosen_entry, chosen_image = candidates[0]
    consumed_image_ids.add(chosen_image["image_id"])
    chosen_entry["_render_mode"] = "image_audio_ffmpeg"
    chosen_entry["_chosen_image"] = chosen_image
    chosen_entry["_render_reason"] = "Usable source images exist, so at least one document-led clip is mandatory for the program."
    chosen_entry["_image_selection_reason"] = f"Forced source-image binding to satisfy minimum document-clip requirement using '{chosen_image.get('caption') or chosen_image['image_id']}'."


def force_all_source_images_used(
    evaluated_entries: list[dict[str, Any]],
    script_segments: dict[int, dict[str, Any]],
    script_lines: dict[str, dict[str, Any]],
    source_images: list[dict[str, Any]],
) -> None:
    if not source_images:
        return

    assigned_image_ids = {
        str(entry.get("_chosen_image", {}).get("image_id") or "")
        for entry in evaluated_entries
        if isinstance(entry.get("_chosen_image"), dict)
    }
    reserved_entry_ids = {
        str(entry.get("entry_id") or "")
        for entry in evaluated_entries
        if entry.get("_render_mode") == "image_audio_ffmpeg"
    }

    for image in source_images:
        image_id = image["image_id"]
        if image_id in assigned_image_ids:
            continue

        candidates: list[tuple[int, dict[str, Any]]] = []
        for entry in evaluated_entries:
            if entry.get("entry_id") in reserved_entry_ids:
                continue
            if float(entry.get("_computed_duration") or 0.0) > DOCUMENT_BLOCK_MAX_DURATION_SECONDS:
                continue
            segment = script_segments[entry["segment_no"]]
            if segment.get("type") in {"opening", "closing"}:
                continue
            line = script_lines[entry["script_line_id"]]
            score = score_image_for_entry(image, entry, segment, line)
            candidates.append((score, entry))

        if not candidates:
            raise ValueError(
                f"Source image {image_id} could not be assigned within the {DOCUMENT_BLOCK_MAX_DURATION_SECONDS:.0f}s document-image limit."
            )

        candidates.sort(key=lambda item: item[0], reverse=True)
        _score, chosen_entry = candidates[0]
        chosen_entry["_render_mode"] = "image_audio_ffmpeg"
        chosen_entry["_chosen_image"] = image
        chosen_entry["_render_reason"] = f"Forced source-image binding so image '{image.get('caption') or image_id}' is used exactly once in the program."
        chosen_entry["_image_selection_reason"] = (
            f"Assigned source image '{image.get('caption') or image_id}' to the best available <= {DOCUMENT_BLOCK_MAX_DURATION_SECONDS:.0f}s anchor-led entry because every source image must appear once."
        )
        assigned_image_ids.add(image_id)
        reserved_entry_ids.add(chosen_entry["entry_id"])


def entry_duration(entry: dict[str, Any]) -> float:
    return round(float(entry.get("duration_seconds") or entry.get("estimated_duration_seconds") or 0) + float(entry.get("pause_before", 0)) + float(entry.get("pause_after", 0)), 3)


def compute_anchor_binding_plan(anchor_entries: list[dict[str, Any]]) -> dict[str, str]:
    binding_by_entry_id: dict[str, str] = {}
    run_start = 0

    while run_start < len(anchor_entries):
        run_end = run_start + 1
        run_speaker = anchor_entries[run_start]["speaker"]
        run_duration = anchor_entries[run_start]["_computed_duration"]

        while run_end < len(anchor_entries) and anchor_entries[run_end]["speaker"] == run_speaker:
            run_duration += anchor_entries[run_end]["_computed_duration"]
            run_end += 1

        binding = "solo" if run_duration > SOLO_CONTINUOUS_SECONDS_THRESHOLD else "duo"
        for index in range(run_start, run_end):
            binding_by_entry_id[anchor_entries[index]["entry_id"]] = binding

        run_start = run_end

    return binding_by_entry_id


def build_ltx_clip(
    entries: list[dict[str, Any]],
    segment: dict[str, Any],
    line: dict[str, Any],
    anchor_binding: str,
    render_reason: str,
    image_selection_reason: str,
    duration_source: str,
) -> dict[str, Any]:
    first_entry = entries[0]
    speaker = first_entry["speaker"]
    clip_id = first_entry["entry_id"].replace("line", "clip") if "line" in first_entry["entry_id"] else f"{first_entry['entry_id']}_clip"
    duration = round(sum(float(entry["_computed_duration"]) for entry in entries), 3)
    audio_paths = [resolve_audio_path(entry) for entry in entries]
    audio_entry_ids = [entry["entry_id"] for entry in entries]
    line_refs = [entry["line_no"] for entry in entries]
    unique_speakers = {str(entry.get("speaker") or "") for entry in entries}
    speaker_focus = speaker if len(unique_speakers) == 1 else "duo"
    grouping_reason = (
        "Consecutive spoken units share one anchor reference image, so they stay inside one continuous anchor-led clip."
        if len(entries) > 1
        else "Keep one spoken unit per clip for stable lip-sync and simple review."
    )

    if anchor_binding == "duo":
        return {
            "clip_id": clip_id,
            "segment_no": segment["segment_no"],
            "segment_type": segment["type"],
            "render_mode": "ltx",
            "anchor_binding": "duo",
            "character_bindings": ["host", "guest"],
            "visual_asset_paths": [
                DEFAULT_ANCHOR_IMAGE_BY_SPEAKER["host"],
                DEFAULT_ANCHOR_IMAGE_BY_SPEAKER["guest"],
            ],
            "composite_visual_asset_path": DEFAULT_DUO_REFERENCE_IMAGE,
            "speaker_focus": speaker_focus,
            "image_mode": "duo_frame",
            "audio_entry_ids": audio_entry_ids,
            "audio_paths": audio_paths,
            "line_refs": line_refs,
            "computed_duration_seconds": duration,
            "duration_source": duration_source,
            "grouping_reason": grouping_reason,
            "render_reason": render_reason,
            "image_selection_reason": image_selection_reason,
            "target_dimensions": DEFAULT_TARGET_DIMENSIONS,
            "image_fit_mode": "match_image",
            "transition_in": "cold_open" if segment.get("type") == "opening" and line.get("line_no") == 1 else "cut",
            "transition_out": "cut",
        }

    image_mode = "female_solo" if speaker == "host" else "male_solo"
    return {
        "clip_id": clip_id,
        "segment_no": segment["segment_no"],
        "segment_type": segment["type"],
        "render_mode": "ltx",
        "anchor_binding": "solo",
        "character_bindings": [speaker],
        "visual_asset_paths": [DEFAULT_ANCHOR_IMAGE_BY_SPEAKER[speaker]],
        "speaker_focus": speaker_focus,
        "image_mode": image_mode,
        "audio_entry_ids": audio_entry_ids,
        "audio_paths": audio_paths,
        "line_refs": line_refs,
        "computed_duration_seconds": duration,
        "duration_source": duration_source,
        "grouping_reason": grouping_reason,
        "render_reason": render_reason,
        "image_selection_reason": image_selection_reason,
        "target_dimensions": DEFAULT_TARGET_DIMENSIONS,
        "image_fit_mode": "match_image",
        "transition_in": "cut",
        "transition_out": "cut",
    }


def build_document_clip(
    entries: list[dict[str, Any]],
    segment: dict[str, Any],
    chosen_image: dict[str, Any],
    duration_source: str,
) -> dict[str, Any]:
    first_entry = entries[0]
    clip_id = first_entry["entry_id"].replace("line", "clip") if "line" in first_entry["entry_id"] else f"{first_entry['entry_id']}_clip"
    duration = round(sum(float(entry["_computed_duration"]) for entry in entries), 3)
    audio_paths = [resolve_audio_path(entry) for entry in entries]
    line_refs = [entry["line_no"] for entry in entries]
    audio_entry_ids = [entry["entry_id"] for entry in entries]
    width = chosen_image.get("width") if isinstance(chosen_image.get("width"), int) else DEFAULT_TARGET_DIMENSIONS["width"]
    height = chosen_image.get("height") if isinstance(chosen_image.get("height"), int) else DEFAULT_TARGET_DIMENSIONS["height"]
    grouping_reason = (
        "Consecutive spoken units share one source image, so they stay inside one continuous document-led visual block."
        if len(entries) > 1
        else "Single audio entry remains one clip, but visual payload is carried by source imagery."
    )
    render_reason = entries[0]["_render_reason"] if len(entries) == 1 else "One source image is used once as a continuous visual block across consecutive matching audio units."
    image_selection_reason = entries[0]["_image_selection_reason"] if len(entries) == 1 else f"Reused source image '{chosen_image['image_id']}' only inside one continuous block, then retire it for the rest of the program."
    return {
        "clip_id": clip_id,
        "segment_no": segment["segment_no"],
        "segment_type": segment["type"],
        "render_mode": "image_audio_ffmpeg",
        "anchor_binding": "document",
        "character_bindings": [],
        "visual_asset_paths": [],
        "speaker_focus": first_entry["speaker"],
        "image_mode": "document_image",
        "audio_entry_ids": audio_entry_ids,
        "audio_paths": audio_paths,
        "line_refs": line_refs,
        "computed_duration_seconds": duration,
        "duration_source": duration_source,
        "grouping_reason": grouping_reason,
        "render_reason": render_reason,
        "image_selection_reason": image_selection_reason,
        "source_image_ids": [chosen_image["image_id"]],
        "source_image_paths": [chosen_image["path"]],
        "target_dimensions": {"width": width, "height": height},
        "image_fit_mode": "scale_pad",
        "transition_in": "cut",
        "transition_out": "cut",
    }


def build_clip_plan(
    script: dict[str, Any],
    audio_payload: dict[str, Any],
    audio_source_name: str,
    source_visual_assets: dict[str, Any] | None,
) -> dict[str, Any]:
    entries = audio_payload.get("entries", [])
    validate_audio_entries(entries)
    script_segments = segment_lookup(script)
    script_lines = line_lookup(script)
    source_images = [image for image in normalize_source_images(source_visual_assets) if image.get("is_usable_for_video", True)]
    consumed_image_ids: set[str] = set()
    duration_source = pick_duration_source(audio_payload, audio_source_name)

    evaluated_entries: list[dict[str, Any]] = []
    anchor_entries: list[dict[str, Any]] = []
    active_document_image: dict[str, Any] | None = None
    active_document_duration = 0.0

    for entry in entries:
        segment = script_segments[entry["segment_no"]]
        line = script_lines[entry["script_line_id"]]
        computed_duration = entry_duration(entry)
        render_mode = "ltx"
        chosen_image = None
        render_reason = "Anchor shot keeps persona continuity for this beat."
        image_selection_reason = f"Use {line['speaker']} anchor shot because no source image strongly matches this line."

        if segment.get("type") in {"opening", "closing"}:
            active_document_image = None
            active_document_duration = 0.0
        elif active_document_image is not None and should_continue_document_block(
            {**entry, "_computed_duration": computed_duration},
            segment,
            line,
            active_document_image,
            active_document_duration,
        ):
            render_mode = "image_audio_ffmpeg"
            chosen_image = active_document_image
            render_reason = "Continue the same source image block so one news image appears only once in one uninterrupted visual run."
            image_selection_reason = f"Continue source image '{active_document_image['image_id']}' across consecutive matching audio units instead of cutting away and later reusing it."
            active_document_duration = round(active_document_duration + computed_duration, 3)
        else:
            active_document_image = None
            active_document_duration = 0.0
            render_mode, chosen_image, render_reason, image_selection_reason = choose_visual_assignment(entry, segment, line, source_images, consumed_image_ids)
            if render_mode == "image_audio_ffmpeg" and computed_duration > DOCUMENT_BLOCK_MAX_DURATION_SECONDS:
                render_mode = "ltx"
                chosen_image = None
                render_reason = (
                    f"Anchor shot keeps persona continuity because a source image may stay on screen for at most {DOCUMENT_BLOCK_MAX_DURATION_SECONDS:.0f} seconds continuously."
                )
                image_selection_reason = (
                    f"Do not start source image usage on this entry because its audio duration already exceeds the {DOCUMENT_BLOCK_MAX_DURATION_SECONDS:.0f}s document-image limit."
                )
            if render_mode == "image_audio_ffmpeg" and chosen_image is not None:
                consumed_image_ids.add(chosen_image["image_id"])
                active_document_image = chosen_image
                active_document_duration = computed_duration

        evaluated_entry = {
            **entry,
            "_computed_duration": computed_duration,
            "_render_mode": render_mode,
            "_chosen_image": chosen_image,
            "_render_reason": render_reason,
            "_image_selection_reason": image_selection_reason,
        }

        if segment.get("type") in {"opening", "closing"}:
            evaluated_entry["_anchor_binding"] = "duo"
            if segment.get("type") == "opening":
                evaluated_entry["_render_reason"] = "Opening beats must stay in duo frame to establish the show before moving into explanation clips."
                evaluated_entry["_image_selection_reason"] = "Opening beats should prioritize program identity over source visuals."
            else:
                evaluated_entry["_render_reason"] = "Closing beats must stay in duo frame so the program signs off with both anchors on screen."
                evaluated_entry["_image_selection_reason"] = "Closing beats should preserve the duo-anchor sign-off instead of switching to source visuals."
            evaluated_entry["_render_mode"] = "ltx"
            evaluated_entry["_chosen_image"] = None
            active_document_image = None
            active_document_duration = 0.0

        if evaluated_entry["_render_mode"] == "ltx":
            anchor_entries.append(evaluated_entry)

        evaluated_entries.append(evaluated_entry)

    force_minimum_document_clip(evaluated_entries, script_segments, script_lines, source_images, consumed_image_ids)
    force_all_source_images_used(evaluated_entries, script_segments, script_lines, source_images)

    anchor_binding_by_entry_id = compute_anchor_binding_plan(anchor_entries)
    for entry in evaluated_entries:
        if entry["_render_mode"] == "ltx" and "_anchor_binding" not in entry:
            entry["_anchor_binding"] = anchor_binding_by_entry_id.get(entry["entry_id"], "duo")

    clips: list[dict[str, Any]] = []
    index = 0
    while index < len(evaluated_entries):
        entry = evaluated_entries[index]
        if entry["_render_mode"] == "image_audio_ffmpeg" and entry["_chosen_image"] is not None:
            document_entries = [entry]
            image_id = entry["_chosen_image"]["image_id"]
            next_index = index + 1
            while next_index < len(evaluated_entries):
                candidate = evaluated_entries[next_index]
                candidate_image = candidate.get("_chosen_image")
                if (
                    candidate["_render_mode"] == "image_audio_ffmpeg"
                    and candidate_image is not None
                    and candidate_image["image_id"] == image_id
                ):
                    document_entries.append(candidate)
                    next_index += 1
                    continue
                break

            clips.append(
                build_document_clip(
                    document_entries,
                    script_segments[entry["segment_no"]],
                    entry["_chosen_image"],
                    duration_source,
                )
            )
            index = next_index
            continue

        ltx_entries = [entry]
        next_index = index + 1
        while next_index < len(evaluated_entries):
            candidate = evaluated_entries[next_index]
            if candidate["_render_mode"] != "ltx":
                break
            if not can_merge_ltx_entries(ltx_entries, candidate):
                break
            ltx_entries.append(candidate)
            next_index += 1

        clips.append(
            build_ltx_clip(
                ltx_entries,
                script_segments[entry["segment_no"]],
                script_lines[entry["script_line_id"]],
                entry["_anchor_binding"],
                entry["_render_reason"],
                entry["_image_selection_reason"],
                duration_source,
            )
        )
        index = next_index

    if source_images and not any(clip.get("anchor_binding") == "document" for clip in clips):
        raise ValueError("Usable source images exist, but clip planning produced no document-led clip.")

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "title": script.get("title", audio_payload.get("title", "news-commentary-clip-plan")),
        "aggregation_rules": {
            "default_grouping_policy": "Prefer one spoken unit per clip for stable lip-sync and easier render routing.",
            "duo_frame_policy": "Merge consecutive anchor-led units when they keep the same anchor reference image and total duration stays within the LTX limit; otherwise split conservatively.",
            "max_lines_per_clip": max((len(clip.get("line_refs", [])) for clip in clips), default=1),
            "split_on_speaker_change": False,
            "split_on_long_duration_seconds": 15.0,
            "short_dialogue_duo_max_seconds": 15.0,
            "long_single_speaker_solo_min_seconds": 15.0,
            "ltx_max_duration_seconds": LTX_MERGE_MAX_DURATION_SECONDS,
            "source_image_reuse_policy": f"Each source image must appear exactly once in the program, only as one continuous document-led visual block, and that block must stay within {DOCUMENT_BLOCK_MAX_DURATION_SECONDS:.0f} seconds before cutting back to anchor-led shots.",
            "duration_source": duration_source,
        },
        "clips": clips,
    }
    if source_visual_assets is not None:
        payload["source_visual_assets_ref"] = "source-assets/source-visual-assets.json"
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build clip-plan.json for news-commentary workflow")
    parser.add_argument("--script", required=True, help="Path to script.json")
    parser.add_argument("--audio-timeline", help="Path to audio/timeline.json")
    parser.add_argument("--tts-plan", help="Fallback path to audio/tts-plan.json when audio timeline is unavailable")
    parser.add_argument("--source-visual-assets", help="Optional path to source-assets/source-visual-assets.json")
    parser.add_argument("--output", required=True, help="Output path for video/clip-plan.json")
    args = parser.parse_args()

    if not args.audio_timeline and not args.tts_plan:
        raise ValueError("Provide either --audio-timeline or --tts-plan")

    script = load_json(Path(args.script).resolve())
    audio_source_name = "audio_timeline" if args.audio_timeline else "tts_plan"
    audio_payload = load_json(Path(args.audio_timeline or args.tts_plan).resolve())
    source_visual_assets = load_json(Path(args.source_visual_assets).resolve()) if args.source_visual_assets else None

    payload = build_clip_plan(script, audio_payload, audio_source_name, source_visual_assets)
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
