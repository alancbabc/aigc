#!/usr/bin/env python3
"""Build image-selection-review.json template from asset-manifest.json.

Creates a review template with five scoring dimensions per candidate
image. Scores default to null — filled in during manual/VLM review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCORE_DIMS = [
    "prompt_alignment",
    "style_consistency",
    "composition_quality",
    "symbolic_strength",
    "video_readiness",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Build image selection review template")
    ap.add_argument("--asset-manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    data = load_json(args.asset_manifest.resolve())

    reviews: list[dict[str, Any]] = []
    for asset in data.get("assets", []):
        if not asset["render_strategy"]["generate_new_image"]:
            continue
        sid = asset["shot_id"]
        review: dict[str, Any] = {
            "shot_id": sid,
            "selected_image": None,
            "selection_reason": "",
            "candidates": [],
        }
        for img_path in asset.get("candidate_images", []):
            review["candidates"].append({
                "candidate_image": img_path,
                "score": {d: None for d in SCORE_DIMS},
                "overall_score": None,
                "issues": [],
                "recommendation": None,
            })
        reviews.append(review)

    out_obj = {
        "schema_version": "1.0",
        "source_manifest_ref": args.asset_manifest.name,
        "scoring_dimensions": {
            "prompt_alignment": "Does the image match prompt and must_include? Scale 0-1",
            "style_consistency": "Does it match the global visual style? Scale 0-1",
            "composition_quality": "Is composition clear with defined depth? Scale 0-1",
            "symbolic_strength": "Is the imagery powerful and evocative? Scale 0-1",
            "video_readiness": "Is it suitable for image-to-video generation? Scale 0-1",
        },
        "reviews": reviews,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total_candidates = sum(len(r["candidates"]) for r in reviews)
    print(f"Wrote {out_path} ({len(reviews)} shots, {total_candidates} candidate reviews pending)")


if __name__ == "__main__":
    main()
