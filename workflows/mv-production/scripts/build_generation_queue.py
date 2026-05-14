#!/usr/bin/env python3
"""Build image-generation-queue.json from image-video-prompts.json.

Pure programmatic: reads image-video-prompts.json, creates generation tasks
for each generate_new_image=true shot. Ambient holds get reuse tasks.
Defaults to 1 candidate per shot.
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
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--candidates-dir", default="assets/images/candidates")
    ap.add_argument("--num-candidates", type=int, default=1, help="Candidates per shot (default 1)")
    args = ap.parse_args()

    data = load_json(args.image_video_prompts.resolve())
    generation_queue: list[dict[str, Any]] = []
    reuse_tasks: list[dict[str, Any]] = []

    fixed_negative = (
        "text, subtitles, watermark, logo, low quality, blurry, "
        "plain documentary photography, tourist photo, casual snapshot, "
        "cartoon, anime, plastic texture, oversaturated colors, "
        "cluttered composition, harsh daylight"
    )

    for p in data["prompts"]:
        sid = p["shot_id"]
        gen = p.get("generate_new_image", True)

        if gen:
            n = args.num_candidates
            candidates = [f"{args.candidates_dir}/{sid}_c{i+1}.png" for i in range(n)]
            generation_queue.append({
                "task_id": f"gen_img_{sid}",
                "shot_id": sid,
                "prompt_id": f"img_{sid}",
                "generate_new_image": True,
                "image_prompt": p.get("image_prompt", ""),
                "negative_prompt": fixed_negative,
                "generation_parameters": {
                    "aspect_ratio": "16:9",
                    "resolution": "1024x576",
                    "seed": None,
                    "num_candidates": n,
                },
                "output_candidates": candidates,
                "status": "pending",
            })
        else:
            reuse_tasks.append({
                "shot_id": sid,
                "reuse_from_shot_id": p.get("render_strategy", {}).get("reuse_from_shot_id"),
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
