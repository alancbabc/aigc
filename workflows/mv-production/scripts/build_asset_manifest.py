#!/usr/bin/env python3
"""Build asset-manifest.json + selected-asset-manifest.json from generation-queue.json + disk.

Reads the generation queue, scans candidates on disk, copies each candidate
to selected/ (removing _cN suffix), and writes both manifests.
Also creates reuse entries for ambient_hold shots.
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
    ap = argparse.ArgumentParser(description="Build asset manifests from generation queue")
    ap.add_argument("--generation-queue", required=True, type=Path)
    ap.add_argument("--project-root", required=True, type=Path, help="Project root for resolving file paths")
    ap.add_argument("--out", required=True, type=Path, help="Output path for asset-manifest.json")
    args = ap.parse_args()

    queue_data = load_json(args.generation_queue.resolve())
    project_root = args.project_root.resolve()

    selected_dir = project_root / "assets" / "images" / "selected"
    selected_dir.mkdir(parents=True, exist_ok=True)

    assets: list[dict[str, Any]] = []
    selected_assets: list[dict[str, Any]] = []
    selected_lookup: dict[str, str] = {}  # shot_id → selected_image path

    # ── Process generation tasks ──
    for task in queue_data.get("generation_queue", []):
        sid = task["shot_id"]
        expected = task.get("output_candidates", [])
        # Scan which files actually exist on disk
        actual = [c for c in expected if (project_root / c).exists()]

        # Copy candidate to selected/ (remove _cN suffix)
        sel_path = None
        if actual:
            src = project_root / actual[0]
            name = re.sub(r"_c[1-9]$", "", Path(actual[0]).stem)
            sel_name = f"{name}.png"
            dest = selected_dir / sel_name
            shutil.copy(str(src), str(dest))
            sel_path = f"assets/images/selected/{sel_name}"
            selected_lookup[sid] = sel_path

        assets.append({
            "shot_id": sid,
            "sequence_index": task.get("sequence_index", 0),
            "prompt_id": task.get("prompt_id", ""),
            "render_strategy": {"generate_new_image": True, "reuse_from_shot_id": None},
            "candidate_images": actual,
            "selected_image": sel_path,
            "selection_status": "generated" if actual else "generation_pending",
            "selection_reason": None,
        })
        selected_assets.append({
            "shot_id": sid,
            "selected_image": sel_path,
            "selection_status": "selected" if sel_path else "pending_review",
            "selection_reason": "Auto-selected (single candidate)." if sel_path else "No candidate available.",
            "overall_score": None,
            "scores": {},
            "needs_regeneration": not actual,
        })

    # ── Process reuse tasks (ambient_holds) ──
    for task in queue_data.get("reuse_tasks", []):
        sid = task["shot_id"]
        reuse_id = task.get("reuse_from_shot_id", "")
        reused_image = selected_lookup.get(reuse_id)
        # Copy the reused image into selected/{sid}.png (remove _cN from reused name)
        if reused_image:
            src = project_root / reused_image
            name = re.sub(r"_c[1-9]$", "", Path(reused_image).name)
            dest = selected_dir / name
            if src.exists():
                shutil.copy(str(src), str(dest))
        assets.append({
            "shot_id": sid,
            "sequence_index": task.get("sequence_index", 0),
            "prompt_id": "",
            "render_strategy": {"generate_new_image": False, "reuse_from_shot_id": reuse_id},
            "candidate_images": [],
            "selected_image": reused_image,
            "selection_status": "reuse_pending",
            "selection_reason": f"Ambient hold reuses selected image from {reuse_id}." if reuse_id else "Ambient hold with no source shot.",
        })
        selected_assets.append({
            "shot_id": sid,
            "selected_image": reused_image,
            "selection_status": "reused" if reused_image else "reuse_pending",
            "selection_reason": f"Reuses image from {reuse_id}." if reused_image else (
                f"Waiting for {reuse_id} selection." if reuse_id else "No source shot for reuse."),
            "overall_score": None,
            "scores": {},
            "needs_regeneration": False,
        })

    # Sort for consistent ordering
    assets.sort(key=lambda a: a.get("sequence_index", 0))
    selected_assets.sort(key=lambda a: a["shot_id"])

    # ── Write asset-manifest.json ──
    asset_out = {
        "schema_version": "1.0",
        "song_title": queue_data.get("song_title", ""),
        "source_queue_file": args.generation_queue.name,
        "assets": assets,
    }
    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(asset_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gen_ok = sum(1 for a in assets if a["selection_status"] == "generated")
    pending = sum(1 for a in assets if a["selection_status"] == "generation_pending")
    reuse = sum(1 for a in assets if a["selection_status"] == "reuse_pending")
    print(f"Wrote {out_path} ({gen_ok} generated, {pending} pending, {reuse} reuse)")

    # ── Write selected-asset-manifest.json ──
    sel_out_path = out_path.parent / "selected-asset-manifest.json"
    sel_out = {
        "schema_version": "1.0",
        "song_title": queue_data.get("song_title", ""),
        "source_manifest_ref": out_path.name,
        "selection_mode": "auto",
        "assets": selected_assets,
    }
    sel_out_path.write_text(json.dumps(sel_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sel_count = sum(1 for a in selected_assets if a["selection_status"] in ("selected", "reused"))
    pend_count = sum(1 for a in selected_assets if a["selection_status"] not in ("selected", "reused"))
    print(f"Wrote {sel_out_path} ({sel_count} selected/reused, {pend_count} pending)")


if __name__ == "__main__":
    main()
