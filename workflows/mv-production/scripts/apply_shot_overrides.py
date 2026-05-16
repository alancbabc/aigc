#!/usr/bin/env python3
"""Apply shot overrides from user_requirements.json.

For each entry in shot_overrides, replaces the selected image for the
specified shot_id with the user-provided singer reference image.
The shot's time_range, lyrics, and other metadata remain unchanged —
only the visual content is substituted.

Also updates selected-asset-manifest.json to reflect the override.

This stage must run AFTER select_manifest so the override overwrites
the auto-selected candidate image.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply shot image overrides from user_requirements")
    ap.add_argument("--user-requirements", required=True, type=Path)
    ap.add_argument("--shot-plan", type=Path, default=None, help="shot-plan.json for sequence index lookup")
    ap.add_argument("--project-root", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    req = load_json(args.user_requirements.resolve())
    project_root = args.project_root.resolve()
    overrides = req.get("shot_overrides", {})
    if not isinstance(overrides, dict) or not overrides:
        print("No shot_overrides found in user_requirements.json")
        return

    # Build shot_id → sequence_index lookup from shot-plan
    seq_lookup: dict[str, int] = {}
    if args.shot_plan:
        sp = load_json(args.shot_plan.resolve())
        for i, s in enumerate(sp.get("shots", []), start=1):
            seq_lookup[s["shot_id"]] = i

    selected_dir = project_root / "assets" / "images" / "selected"
    selected_dir.mkdir(parents=True, exist_ok=True)

    # Load the selected-asset-manifest to update (preserve order)
    manifest_path = project_root / "selected-asset-manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {"assets": []}
    manifest_modified = False

    applied = 0
    for shot_id, singer_path_rel in overrides.items():
        singer_path = project_root / singer_path_rel
        if not singer_path.exists():
            print(f"  [warn] {shot_id}: singer image not found: {singer_path}")
            continue

        seq = seq_lookup.get(shot_id, 0)
        filename = f"{seq:03d}_{shot_id}.png" if seq else f"{shot_id}.png"
        dest = selected_dir / filename
        if args.dry_run:
            print(f"  [dry-run] {shot_id}: {singer_path.name} → {dest.name}")
        else:
            shutil.copy(str(singer_path), str(dest))
            print(f"  [applied] {shot_id}: {singer_path.name} → {dest.name}")
            # Update manifest entry in-place to preserve order
            for entry in manifest.get("assets", []):
                if entry.get("shot_id") == shot_id:
                    entry["selected_image"] = f"assets/images/selected/{filename}"
                    entry["selection_status"] = "overridden"
                    entry["selection_reason"] = f"Overridden with singer reference: {singer_path_rel}"
                    manifest_modified = True
                    break
        applied += 1

    if manifest_modified:
        write_json(manifest_path, manifest)
        print(f"Updated {manifest_path.name} with {applied} override(s)")

    print(f"Applied {applied} overrides. {len(overrides) - applied} failed.")


if __name__ == "__main__":
    main()
