#!/usr/bin/env python3
"""Build selected-asset-manifest.json from asset-manifest.json.

Auto-selects the single candidate image per shot, copies it to selected/
(with _cN suffix stripped), and writes the manifest.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Build selected asset manifest")
    ap.add_argument("--asset-manifest", required=True, type=Path)
    ap.add_argument("--project-root", required=True, type=Path,
                    help="Project root for resolving/copying image files")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    manifest = load_json(args.asset_manifest.resolve())
    project_root = args.project_root.resolve()

    assets: list[dict[str, Any]] = []
    selected_lookup: dict[str, str] = {}  # shot_id → selected_image path

    selected_dir = project_root / "assets" / "images" / "selected"
    selected_dir.mkdir(parents=True, exist_ok=True)

    # ── Process generation shots ──
    for asset in manifest.get("assets", []):
        sid = asset["shot_id"]
        if not asset["render_strategy"]["generate_new_image"]:
            continue  # handled in reuse pass below

        candidates = asset.get("candidate_images", [])
        seq = asset.get("sequence_index", 0)

        if candidates:
            src = project_root / candidates[0]
            name = re.sub(r"_c[1-9]$", "", Path(candidates[0]).stem)
            dest = selected_dir / f"{name}.png"
            if src.exists():
                shutil.copy(str(src), str(dest))
                sel_path = f"assets/images/selected/{name}.png"
                selected_lookup[sid] = sel_path
                assets.append({
                    "shot_id": sid,
                    "selected_image": sel_path,
                    "selection_status": "selected",
                    "selection_reason": "Auto-selected (single candidate).",
                    "overall_score": None,
                    "scores": {},
                    "needs_regeneration": False,
                })
                continue

        # No candidate available
        assets.append({
            "shot_id": sid,
            "selected_image": None,
            "selection_status": "pending_review",
            "selection_reason": "No candidate image available.",
            "overall_score": None,
            "scores": {},
            "needs_regeneration": True,
        })

    # ── Process reuse shots (ambient_holds) ──
    for asset in manifest.get("assets", []):
        sid = asset["shot_id"]
        if asset["render_strategy"]["generate_new_image"]:
            continue
        reuse_id = asset["render_strategy"].get("reuse_from_shot_id", "")
        reused_image = selected_lookup.get(reuse_id)
        # Also copy the reused image into selected/{sid}.png for timeline accessibility
        if reused_image:
            src = project_root / reused_image
            seq = asset.get("sequence_index", 0)
            dest_name = re.sub(r"_c[1-9]$", "", Path(reused_image).name)
            dest = selected_dir / dest_name
            if src.exists():
                shutil.copy(str(src), str(dest))
        assets.append({
            "shot_id": sid,
            "selected_image": reused_image,
            "selection_status": "reused" if reused_image else "reuse_pending",
            "selection_reason": f"Reuses image from {reuse_id}." if reused_image else (
                f"Waiting for {reuse_id} selection." if reuse_id else "No source shot for reuse."),
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
        "selection_mode": "auto",
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
