#!/usr/bin/env python3
"""Build image-generation-queue.json from image-prompts.json.

Pure programmatic: reads image-prompts.json, creates generation tasks
for each generate_new_image=true entry, and reuse tasks for ambient_holds.
Critical shots (based on shot_role) get extra candidates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CRITICAL_ROLES = {"establishing_image", "emotional_peak", "climax_image", "resolution_image"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Build image generation queue from image-prompts.json")
    ap.add_argument("--image-prompts", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--candidates-dir", default="assets/images/candidates")
    args = ap.parse_args()

    data = load_json(args.image_prompts.resolve())
    generation_queue: list[dict[str, Any]] = []
    reuse_tasks: list[dict[str, Any]] = []

    for p in data["image_prompts"]:
        sid = p["shot_id"]
        gen = p["render_strategy"]["generate_new_image"]

        if gen:
            n = 3 if p.get("shot_role") in CRITICAL_ROLES else p["generation_parameters"].get("num_candidates", 2)
            candidates = [f"{args.candidates_dir}/{sid}_c{i+1}.png" for i in range(n)]
            generation_queue.append({
                "task_id": f"gen_img_{sid}",
                "shot_id": sid,
                "prompt_id": p["prompt_id"],
                "generate_new_image": True,
                "image_prompt": p["image_prompt"],
                "negative_prompt": p["negative_prompt"],
                "generation_parameters": {
                    "aspect_ratio": p["generation_parameters"]["aspect_ratio"],
                    "resolution": p["generation_parameters"]["resolution"],
                    "seed": None,
                    "num_candidates": n,
                },
                "output_candidates": candidates,
                "status": "pending",
            })
        else:
            reuse_tasks.append({
                "shot_id": sid,
                "reuse_from_shot_id": p["render_strategy"].get("reuse_from_shot_id"),
                "status": "reuse_after_selection",
            })

    out = {
        "schema_version": "1.0",
        "song_title": data.get("song_title", ""),
        "source_prompt_file": args.image_prompts.name,
        "generation_queue": generation_queue,
        "reuse_tasks": reuse_tasks,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(generation_queue)} generation tasks, {len(reuse_tasks)} reuse tasks)")


if __name__ == "__main__":
    main()
