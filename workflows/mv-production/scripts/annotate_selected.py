#!/usr/bin/env python3
"""Annotate selected images with shot_id, time range, and lyrics text.

Reads image-video-prompts.json for per-shot metadata, opens each selected
image, adds a semi-transparent overlay with annotation text at the bottom.
Saves to assets/images/labeled/ directory.
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
    return f"{m}:{s:05.2f}"


def wrap_text(text: str, max_chars: int) -> list[str]:
    """Wrap text at max_chars, Chinese-friendly."""
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
    literal_meaning: str,
    width: int,
) -> None:
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size

    # Build annotation text
    lines = [
        f"{shot_id}  |  {fmt_time(start_time)} - {fmt_time(end_time)}  |  {end_time - start_time:.1f}s",
    ]
    if literal_meaning:
        wrapped = wrap_text(literal_meaning, max(30, w // 12))
        lines.extend(wrapped)

    # Draw semi-transparent bar at bottom
    bar_h = max(80, 20 * len(lines) + 30)
    bar = Image.new("RGBA", (w, bar_h), (0, 0, 0, 180))

    # Expand canvas
    new_img = Image.new("RGBA", (w, h + bar_h))
    new_img.paste(img, (0, 0))
    new_img.paste(bar, (0, h))

    draw = ImageDraw.Draw(new_img)
    try:
        font = ImageFont.truetype("arial.ttf", max(13, min(18, w // 55)))
    except OSError:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", max(13, min(18, w // 55)))
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
    ap.add_argument("--project-root", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = load_json(args.image_video_prompts.resolve())
    project_root = args.project_root.resolve()
    selected_dir = project_root / "assets" / "images" / "selected"
    labeled_dir = project_root / "assets" / "images" / "labeled"
    labeled_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for p in data["prompts"]:
        sid = p["shot_id"]
        tr = p["time_range"]
        lm = p.get("literal_meaning_zh", "")

        img_path = selected_dir / f"{sid}.png"
        if not img_path.exists():
            print(f"  [skip] {sid}: image not found")
            continue

        out_path = labeled_dir / f"{sid}.png"
        if args.dry_run:
            print(f"  [dry-run] {sid}: {fmt_time(tr['start_time'])}-{fmt_time(tr['end_time'])} | {lm[:40]}...")
        else:
            annotate_image(img_path, out_path, sid, tr["start_time"], tr["end_time"], lm, 1024)
        count += 1

    print(f"Annotated {count} images → {labeled_dir}")


if __name__ == "__main__":
    main()
