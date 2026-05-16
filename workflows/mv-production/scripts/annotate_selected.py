#!/usr/bin/env python3
"""Annotate selected images with shot_id, time range, lyrics text, and section info.

Reads image-video-prompts.json + segment-interpretation.json for per-shot metadata,
opens each selected image, adds a semi-transparent overlay with annotation text
at the bottom. Saves to assets/images/labeled/ directory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:05.2f}"


def wrap_text(text: str, max_chars: int) -> list[str]:
    lines = []
    current = ""
    for ch in text:
        current += ch
        if len(current) >= max_chars:
            lines.append(current.strip())
            current = ""
    if current.strip():
        lines.append(current.strip())
    return lines if lines else [text]


def annotate_image(
    img_path: Path,
    out_path: Path,
    shot_id: str,
    start_time: float,
    end_time: float,
    lyrics_text: str,
    section_type: str,
) -> None:
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size

    # Build annotation lines
    fsize = max(13, min(18, w // 55))
    lines = [
        f"{shot_id}  |  {fmt_time(start_time)} - {fmt_time(end_time)}  |  {end_time - start_time:.1f}s  |  {section_type}",
    ]
    # Compute max characters per line based on font size and image width
    # Available width = image width - padding (24px), average char width ≈ font_size * 0.6
    avg_char_w = max(fsize * 0.6, 6)
    max_chars = max(30, int((w - 24) / avg_char_w))
    if lyrics_text:
        wrapped = wrap_text(lyrics_text, max_chars)
        lines.extend(wrapped)

    bar_h = max(80, 20 * len(lines) + 30)
    bar = Image.new("RGBA", (w, bar_h), (0, 0, 0, 180))

    new_img = Image.new("RGBA", (w, h + bar_h))
    new_img.paste(img, (0, 0))
    new_img.paste(bar, (0, h))

    draw = ImageDraw.Draw(new_img)
    try:
        font = ImageFont.truetype("arial.ttf", fsize)
    except OSError:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", fsize)
        except OSError:
            font = ImageFont.load_default()

    y = h + 10
    for line in lines:
        draw.text((12, y), line, fill=(255, 255, 255, 255), font=font)
        try:
            bbox = draw.textbbox((12, y), line, font=font)
            y = bbox[3] + 4
        except AttributeError:
            y += 18

    new_img.convert("RGB").save(out_path, format="PNG")


def main() -> None:
    ap = argparse.ArgumentParser(description="Annotate selected images with shot metadata")
    ap.add_argument("--image-video-prompts", required=True, type=Path)
    ap.add_argument("--segment-interpretation", required=True, type=Path)
    ap.add_argument("--project-root", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ivp_data = load_json(args.image_video_prompts.resolve())
    seg_data = load_json(args.segment_interpretation.resolve())
    project_root = args.project_root.resolve()
    selected_dir = project_root / "assets" / "images" / "selected"
    labeled_dir = project_root / "assets" / "images" / "labeled"
    labeled_dir.mkdir(parents=True, exist_ok=True)

    # Build segment_id → section_type lookup
    section_lookup: dict[str, str] = {}
    for seg in seg_data.get("segments", []):
        sid = seg.get("segment_id", "")
        st = seg.get("section_type", "")
        if sid:
            section_lookup[sid] = st

    # Build shot_id → sequence index from prompt order
    seq_lookup: dict[str, int] = {}
    for i, p in enumerate(ivp_data.get("prompts", []), start=1):
        seq_lookup[p["shot_id"]] = i

    count = 0
    for p in ivp_data.get("prompts", []):
        sid = p["shot_id"]
        tr = p["time_range"]
        lyrics_text = p.get("lyrics_text", "")
        literal_m = p.get("literal_meaning_zh", "")
        parent_seg = p.get("parent_segment_id", "")
        section_type = section_lookup.get(parent_seg, "")
        seq = seq_lookup.get(sid, 0)

        filename = f"{seq:03d}_{sid}.png" if seq else f"{sid}.png"
        img_path = selected_dir / filename
        if not img_path.exists():
            # Fall back to old naming without sequence prefix
            img_path = selected_dir / f"{sid}.png"
        if not img_path.exists():
            print(f"  [skip] {sid}: image not found")
            continue

        out_path = labeled_dir / filename
        if args.dry_run:
            print(f"  [dry-run] {sid}: {fmt_time(tr['start_time'])}-{fmt_time(tr['end_time'])} | {section_type} | {lyrics_text[:40]}...")
        else:
            annotate_image(
                img_path, out_path, sid,
                tr["start_time"], tr["end_time"],
                lyrics_text, section_type,
            )
        count += 1

    print(f"Annotated {count} images -> {labeled_dir}")


if __name__ == "__main__":
    main()
