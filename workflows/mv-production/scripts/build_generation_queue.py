#!/usr/bin/env python3
"""Build image-generation-queue.json from image-video-prompts.json.

Pure programmatic: reads image-video-prompts.json, creates a generation task
for each generate_new_image=true shot. Ambient holds get reuse tasks.
Each shot generates exactly 1 candidate image.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Build image generation queue from image-video-prompts.json")
    ap.add_argument("--image-video-prompts", required=True, type=Path)
    ap.add_argument("--user-requirements", type=Path, default=None, help="user_requirements.json for resolution")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--candidates-dir", default="assets/images/candidates")
    args = ap.parse_args()

    data = load_json(args.image_video_prompts.resolve())

    # Read resolution from user_requirements.json or default to 1024x576
    resolution = "1024x576"
    if args.user_requirements:
        req = load_json(args.user_requirements.resolve())
        res = req.get("resolution", {})
        w = res.get("width")
        h = res.get("height")
        if w and h:
            resolution = f"{w}x{h}"
    generation_queue: list[dict[str, Any]] = []
    reuse_tasks: list[dict[str, Any]] = []

    fixed_negative = (
        "text, subtitles, watermark, logo, low quality, blurry, "
        "plain documentary photography, tourist photo, casual snapshot, "
        "cartoon, anime, plastic texture, oversaturated colors, "
        "cluttered composition, harsh daylight"
    )

    for seq_idx, p in enumerate(data["prompts"], start=1):
        sid = p["shot_id"]
        gen = p.get("generate_new_image", True)
        ext_strategy = p.get("extension_strategy", "none")
        reuse_id = p.get("reuse_from_shot_id") or p.get("render_strategy", {}).get("reuse_from_shot_id")

        if gen:
            candidates = [f"{args.candidates_dir}/{seq_idx:03d}_{sid}_c1.png"]
            task: dict[str, Any] = {
                "task_id": f"gen_img_{sid}",
                "shot_id": sid,
                "sequence_index": seq_idx,
                "prompt_id": f"img_{sid}",
                "generate_new_image": True,
                "image_prompt": p.get("image_prompt", ""),
                "negative_prompt": fixed_negative,
                "generation_parameters": {
                    "aspect_ratio": "16:9",
                    "resolution": resolution,
                    "seed": None,
                },
                "output_candidates": candidates,
                "status": "pending",
            }
            if ext_strategy and ext_strategy != "none":
                task["extension_strategy"] = ext_strategy
            generation_queue.append(task)
        else:
            reuse_tasks.append({
                "shot_id": sid,
                "sequence_index": seq_idx,
                "reuse_from_shot_id": reuse_id,
                "extension_strategy": ext_strategy if ext_strategy != "none" else None,
                "status": "reuse_after_selection",
            })

    out = {
        "schema_version": "1.0",
        "song_title": data.get("song_title", ""),
        "source_prompt_file": args.image_video_prompts.name,
        "generation_queue": generation_queue,
        "reuse_tasks": reuse_tasks,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(generation_queue)} generation tasks, {len(reuse_tasks)} reuse tasks)")


if __name__ == "__main__":
    main()
