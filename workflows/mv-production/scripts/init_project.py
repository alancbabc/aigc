#!/usr/bin/env python3
"""Stage 0 intake: read an mv-production document and produce project_meta.json + user_requirements.json.

Usage:
    python workflows/mv-production/scripts/init_project.py \\
        --doc <path-to-intake-document.json> \\
        --project-root <project-directory>

The intake document must contain:
    song_audio_path     (str)  Path to the song audio file
    lyrics_lrc_path     (str)  Path to the LRC lyrics file
    song_background     (str)  Background knowledge about the song
    visual_style        (str)  Non-realistic style: "anime" / "cartoon" / etc.
    reference_images    (list) Paths to user-provided artist/singer reference images
    resolution          (dict) {"width": int, "height": int} -- defaults to 1280x720

Outputs (under --project-root):
    project_meta.json
    user_requirements.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_RESOLUTION = {"width": 1024, "height": 576}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_doc(doc: dict[str, Any]) -> None:
    required = ["song_audio_path", "lyrics_lrc_path"]
    missing = [k for k in required if k not in doc]
    if missing:
        raise SystemExit(f"Intake document missing required fields: {missing}")

    audio = Path(doc["song_audio_path"])
    if not audio.exists():
        raise SystemExit(f"Audio file not found: {audio}")

    lrc = Path(doc["lyrics_lrc_path"])
    if not lrc.exists():
        raise SystemExit(f"LRC file not found: {lrc}")

    style = doc.get("visual_style", "")
    if style and style not in ("anime", "cartoon"):
        print(f"[warn] visual_style '{style}' is not standard (expected anime/cartoon)", file=sys.stderr)

    refs = doc.get("reference_images") or []
    for r in refs:
        p = Path(r)
        if not p.exists():
            print(f"[warn] reference image not found: {p}", file=sys.stderr)

    res = doc.get("resolution")
    if res and (not isinstance(res, dict) or "width" not in res or "height" not in res):
        raise SystemExit("resolution must be dict with width and height")


def derive_song_title(lrc_path: Path, audio_path: Path) -> str:
    stem = lrc_path.stem
    if stem.lower().endswith(".lrc"):
        stem = stem[:-4]
    import re
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    parts = [p for p in stem.split(" ") if p]
    if not parts:
        stem = audio_path.stem
        stem = re.sub(r"[_\-]+", " ", stem).strip()
        parts = [p for p in stem.split(" ") if p]
    return " ".join(parts) if parts else "Untitled"


def derive_style_prefix(visual_style: str) -> str:
    mapping = {
        "anime": "anime style, cel-shaded, vibrant palette, clean lines",
        "cartoon": "cartoon style, bold outlines, saturated colors, illustrated look",
    }
    return mapping.get(visual_style, f"{visual_style} style, illustrated, non-photorealistic")


def main() -> None:
    ap = argparse.ArgumentParser(description="mv-production Stage 0 intake")
    ap.add_argument("--doc", required=True, type=Path, help="Path to intake document JSON")
    ap.add_argument("--project-root", required=True, type=Path, help="Project output directory")
    args = ap.parse_args()

    doc_path = args.doc.resolve()
    project_root = args.project_root.resolve()

    if not doc_path.is_file():
        raise SystemExit(f"Intake document not found: {doc_path}")

    doc = load_json(doc_path)
    validate_doc(doc)

    project_root.mkdir(parents=True, exist_ok=True)

    song_title = derive_song_title(Path(doc["lyrics_lrc_path"]), Path(doc["song_audio_path"]))
    visual_style = doc.get("visual_style", "anime")
    resolution = doc.get("resolution") or DEFAULT_RESOLUTION
    reference_images = doc.get("reference_images") or []
    song_background = doc.get("song_background", "")
    notes = doc.get("notes", "")

    project_meta: dict[str, Any] = {
        "schema_version": "1.0",
        "song_title": song_title,
        "song_file_path": str(Path(doc["song_audio_path"]).resolve()),
        "lyrics_file_path": str(Path(doc["lyrics_lrc_path"]).resolve()),
        "lyrics_source": "lrc",
        "song_background": song_background,
        "mv_type": "concept",
        "visual_style": visual_style,
        "reference_images": [str(Path(r).resolve()) for r in reference_images],
        "resolution": resolution,
    }
    if notes:
        project_meta["notes"] = notes

    style_prefix = derive_style_prefix(visual_style)

    user_requirements: dict[str, Any] = {
        "schema_version": "2.0",
        "song_title": song_title,
        "mv_type": "concept",
        "visual_style": visual_style,
        "reference_images": [str(Path(r).resolve()) for r in reference_images],
        "resolution": resolution,
        "keyframe_style_prefix": style_prefix,
        "output_goal": "keyframes",
        "confirmation_mode": "auto",
        "song_background": song_background,
    }
    if notes:
        user_requirements["notes"] = notes

    meta_path = project_root / "project_meta.json"
    meta_path.write_text(json.dumps(project_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[init] wrote {meta_path}")

    req_path = project_root / "user_requirements.json"
    req_path.write_text(json.dumps(user_requirements, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[init] wrote {req_path}")

    print(f"\nProject initialized at: {project_root}")
    print(f"  Song    : {song_title}")
    print(f"  Style   : {visual_style}")
    print(f"  MV type : concept")
    print(f"  Size    : {resolution['width']}x{resolution['height']}")
    print(f"  Refs    : {len(reference_images)} reference image(s)")
    print("\nReady for Stage 1: python scripts/parse_lyrics.py ...")


if __name__ == "__main__":
    main()
