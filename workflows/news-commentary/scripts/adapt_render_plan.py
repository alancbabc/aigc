#!/usr/bin/env python3
"""Adapt render-plan.json to stage11 expected structure with ltx_request nesting."""

from __future__ import annotations
import json
import sys
from pathlib import Path


def adapt_render_plan(input_path: Path, output_path: Path) -> None:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    ltx_config = data.get("ltx_config", {})
    render_items = data.get("render_items", [])
    adapted = []
    for item in render_items:
        if item.get("render_mode") != "ltx":
            adapted.append(item)
            continue
        audio_paths = item.get("audio_paths", [])
        ltx_item = {
            "clip_id": item.get("clip_id", ""),
            "render_id": item.get("render_id", ""),
            "render_mode": "ltx",
            "optimized_prompt": item.get("prompt", ""),
            "ltx_request": {
                "audio_paths": audio_paths,
                "audio": audio_paths[0] if audio_paths else "",
                "save_path": item.get("save_path", ""),
                "duration_seconds": item.get("duration_seconds", 5.0),
                "images": item.get("reference_images", []),
                "a2v_audio_start_time": ltx_config.get("a2v_audio_start_time", 0.0),
                "a2v_audio_insert_video_time": ltx_config.get("a2v_audio_insert_video_time", 0.0),
                "negative_prompt": ltx_config.get("default_negative_prompt", ""),
            },
        }
        adapted.append(ltx_item)
    result = {
        "render_items": adapted,
        "_adapted_from": str(input_path),
    }
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Adapted {len(adapted)} items -> {output_path}", file=sys.stderr)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    adapt_render_plan(Path(args.input), Path(args.output))