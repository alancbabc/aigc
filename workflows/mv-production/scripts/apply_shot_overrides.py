#!/usr/bin/env python3
"""Apply shot overrides from user_requirements.json.

For each entry in shot_overrides, replaces the selected image for the
specified shot_id with the user-provided singer reference image.
The shot's time_range, lyrics, and other metadata remain unchanged —
only the visual content is substituted.

This is a formal workflow step. User declares overrides in the intake
document; this script executes them deterministically.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply shot image overrides from user_requirements")
    ap.add_argument("--user-requirements", required=True, type=Path)
    ap.add_argument("--project-root", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    req = load_json(args.user_requirements.resolve())
    project_root = args.project_root.resolve()
    overrides = req.get("shot_overrides", {})
    if not isinstance(overrides, dict) or not overrides:
        print("No shot_overrides found in user_requirements.json")
        return

    selected_dir = project_root / "assets" / "images" / "selected"
    selected_dir.mkdir(parents=True, exist_ok=True)

    applied = 0
    for shot_id, singer_path_rel in overrides.items():
        singer_path = project_root / singer_path_rel
        if not singer_path.exists():
            print(f"  [warn] {shot_id}: singer image not found: {singer_path}")
            continue

        dest = selected_dir / f"{shot_id}.png"
        if args.dry_run:
            print(f"  [dry-run] {shot_id}: {singer_path.name} → {dest.name}")
        else:
            shutil.copy(str(singer_path), str(dest))
            print(f"  [applied] {shot_id}: {singer_path.name} → {dest.name}")
        applied += 1

    print(f"Applied {applied} overrides. {len(overrides) - applied} failed.")


if __name__ == "__main__":
    main()
