#!/usr/bin/env python3
"""Single source of truth: build keyframe-prompts.json from mv-keyframe-director.json.

Merges per-keyframe English prompt with mv-global-visual-style texture/lighting extras
(the same composition as generate_keyframe_images_from_director.build_positive_prompt).

Use this instead of hand-maintaining keyframe-prompts.json alongside the director file.

Output matches the shape expected by workflows/mv-production/scripts/generate_keyframes.py
(shots[].frame_config.frames[] with type first, change_focus, prompt).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_positive_prompt(kf: dict[str, Any], global_style: dict[str, Any]) -> str:
    base = (kf.get("keyframe_image_prompt_en") or "").strip()
    extras: list[str] = []
    tex = global_style.get("texture_material_en")
    if tex:
        extras.append(str(tex))
    mood = global_style.get("lighting_mood_en")
    if mood:
        extras.append(str(mood))
    if extras:
        base = f"{base}, {', '.join(extras)}"
    return base


def style_prefix_from_requirements(req: dict[str, Any] | None) -> str:
    if not req:
        return ""
    return str(
        req.get("keyframe_style_prefix")
        or req.get("visual_style_notes")
        or ""
    ).strip()


def default_style_prefix(style: dict[str, Any]) -> str:
    """When user_requirements has no keyframe_style_prefix, derive a bilingual prefix from Stage 2."""
    zh = str(style.get("global_style_suffix_zh") or "").strip()
    en = str(style.get("global_style_suffix") or "").strip()
    if zh and en:
        return f"{zh}；{en}"
    return zh or en


def main() -> None:
    ap = argparse.ArgumentParser(description="Export keyframe-prompts.json from mv-keyframe-director.json")
    ap.add_argument("--director", type=Path, required=True)
    ap.add_argument("--global-style", type=Path, required=True)
    ap.add_argument("--user-requirements", type=Path, default=None, help="optional user_requirements.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--generation-aspect-ratio",
        default="16:9",
        help="Written to generation_aspect_ratio (generate_keyframes.py reads this)",
    )
    args = ap.parse_args()

    director = load_json(Path(args.director).resolve())
    style = load_json(Path(args.global_style).resolve())
    reqs = load_json(Path(args.user_requirements).resolve()) if args.user_requirements else None

    song_title = director.get("song_title") or style.get("song_title") or ""
    prefix = style_prefix_from_requirements(reqs) or default_style_prefix(style)
    shots: list[dict[str, Any]] = []

    events: list[tuple[str, dict[str, Any]]] = []
    for kf in director.get("keyframes") or []:
        events.append(("lyric", kf))
    for seg in director.get("instrumental_bookends") or []:
        events.append(("instrumental", seg))
    events.sort(key=lambda x: float(x[1]["start_time"]))

    for i, (kind, block) in enumerate(events, start=1):
        st = float(block["start_time"])
        if kind == "lyric":
            change_focus = f"{str(block.get('primary_section_ref') or '')} {st:.2f}".strip()
        else:
            change_focus = f"{str(block.get('role') or 'instrumental')} {st:.2f}".strip()
        prompt = build_positive_prompt(block, style)
        shots.append(
            {
                "shot_no": i,
                "reference_images": {"characters": [], "scene": ""},
                "frame_config": {
                    "frames": [
                        {
                            "type": "first",
                            "intent": "keyframe still",
                            "change_focus": change_focus,
                            "prompt": prompt,
                        }
                    ]
                },
            }
        )

    out_obj: dict[str, Any] = {
        "generation_aspect_ratio": args.generation_aspect_ratio,
        "keyframe_style_prefix": prefix,
        "stage": 2,
        "project_title": song_title,
        "style": str(style.get("animation_art_style_en") or style.get("global_style_suffix") or "").strip(),
        "scene_no": 1,
        "shots": shots,
        "_exported_from": {
            "mv_keyframe_director": str(Path(args.director).resolve()),
            "mv_global_visual_style": str(Path(args.global_style).resolve()),
            "timeline_merge": "lyric keyframes + instrumental_bookends sorted by start_time",
        },
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(shots)} shots)")


if __name__ == "__main__":
    main()
