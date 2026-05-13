#!/usr/bin/env python3
"""Build selected-asset-manifest.json from selection-review.json.

Selects the highest-scoring candidate per shot. For reuse tasks,
copies the selected_image from the reused shot.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Build selected asset manifest from review")
    ap.add_argument("--asset-manifest", required=True, type=Path)
    ap.add_argument("--selection-review", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    manifest = load_json(args.asset_manifest.resolve())
    review = load_json(args.selection_review.resolve())

    # Build review lookup by shot_id
    review_lookup: dict[str, dict[str, Any]] = {}
    for r in review.get("reviews", []):
        review_lookup[r["shot_id"]] = r

    assets: list[dict[str, Any]] = []
    selected_lookup: dict[str, str] = {}  # shot_id → selected_image path

    # Process generation shots
    for asset in manifest.get("assets", []):
        sid = asset["shot_id"]
        if asset["render_strategy"]["generate_new_image"]:
            rv = review_lookup.get(sid, {})
            best = None
            best_score = -1.0
            for c in rv.get("candidates", []):
                if c.get("overall_score") is None:
                    continue
                score = float(c["overall_score"])
                if score > best_score:
                    best_score = score
                    best = c
            if best:
                # Replace candidate path with selected path
                sel_path = best["candidate_image"].replace("candidates", "selected").replace("_c1.", ".").replace("_c2.", ".").replace("_c3.", ".").replace("_c4.", ".")
                selected_lookup[sid] = sel_path
                assets.append({
                    "shot_id": sid,
                    "selected_image": sel_path,
                    "selection_status": "selected",
                    "selection_reason": best.get("recommendation", ""),
                    "overall_score": best_score,
                    "scores": best.get("score", {}),
                    "needs_regeneration": False,
                    "candidates_reviewed": len(rv.get("candidates", [])),
                })
            else:
                assets.append({
                    "shot_id": sid,
                    "selected_image": None,
                    "selection_status": "pending_review",
                    "selection_reason": "No scored candidates available.",
                    "overall_score": None,
                    "scores": {},
                    "needs_regeneration": True,
                    "candidates_reviewed": 0,
                })
            continue

    # Process reuse shots — resolve after generation shots are done
    for asset in manifest.get("assets", []):
        sid = asset["shot_id"]
        if not asset["render_strategy"]["generate_new_image"]:
            reuse_id = asset["render_strategy"].get("reuse_from_shot_id", "")
            reused_image = selected_lookup.get(reuse_id)
            assets.append({
                "shot_id": sid,
                "selected_image": reused_image,
                "selection_status": "reused" if reused_image else "reuse_pending",
                "selection_reason": f"Reuses selected image from {reuse_id}." if reused_image else f"Waiting for {reuse_id} selection.",
                "overall_score": None,
                "scores": {},
                "needs_regeneration": False,
            })

    # Sort by shot_id for consistent ordering
    assets.sort(key=lambda a: a["shot_id"])

    out = {
        "schema_version": "1.0",
        "song_title": manifest.get("song_title", ""),
        "source_manifest_ref": args.asset_manifest.name,
        "source_review_ref": args.selection_review.name,
        "assets": assets,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selected = sum(1 for a in assets if a["selection_status"] in ("selected", "reused"))
    pending = sum(1 for a in assets if a["selection_status"] not in ("selected", "reused"))
    print(f"Wrote {out_path} ({selected} selected/reused, {pending} pending)")


if __name__ == "__main__":
    main()
