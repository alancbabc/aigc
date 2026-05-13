#!/usr/bin/env python3
"""Build asset-manifest.json from generation-queue.json + actual files on disk.

Reads the generation queue, scans the candidates directory for actual
generated image files, and records per-shot assets with selection status.
Also creates reuse entries for ambient_hold shots.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Build asset manifest from generation queue")
    ap.add_argument("--generation-queue", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    queue_data = load_json(args.generation_queue.resolve())
    base_dir = Path(args.out.resolve()).parent

    assets: list[dict[str, Any]] = []

    # Track which shots have been processed (for reuse lookup)
    shot_to_candidates: dict[str, list[str]] = {}

    for task in queue_data.get("generation_queue", []):
        sid = task["shot_id"]
        expected = task.get("output_candidates", [])
        # Scan which files actually exist on disk
        actual = [c for c in expected if (base_dir / c).exists()]
        shot_to_candidates[sid] = actual

        assets.append({
            "shot_id": sid,
            "prompt_id": task.get("prompt_id", ""),
            "render_strategy": {
                "generate_new_image": True,
                "reuse_from_shot_id": None,
            },
            "candidate_images": actual,
            "expected_candidates": len(expected),
            "selected_image": None,
            "selection_status": "pending_review" if actual else "generation_pending",
            "selection_reason": None,
            "needs_regeneration": len(actual) == 0,
        })

    for task in queue_data.get("reuse_tasks", []):
        sid = task["shot_id"]
        reuse_id = task.get("reuse_from_shot_id", "")
        assets.append({
            "shot_id": sid,
            "prompt_id": "",
            "render_strategy": {
                "generate_new_image": False,
                "reuse_from_shot_id": reuse_id,
            },
            "candidate_images": [],
            "expected_candidates": 0,
            "selected_image": None,
            "selection_status": "reuse_pending",
            "selection_reason": f"Ambient hold reuses selected image from {reuse_id}.",
            "needs_regeneration": False,
        })

    out = {
        "schema_version": "1.0",
        "song_title": queue_data.get("song_title", ""),
        "source_queue_file": args.generation_queue.name,
        "assets": assets,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gen_ok = sum(1 for a in assets if a["selection_status"] == "pending_review")
    pending = sum(1 for a in assets if a["selection_status"] == "generation_pending")
    reuse = sum(1 for a in assets if a["selection_status"] == "reuse_pending")
    print(f"Wrote {out_path} ({gen_ok} ready for review, {pending} pending generation, {reuse} reuse)")


if __name__ == "__main__":
    main()
