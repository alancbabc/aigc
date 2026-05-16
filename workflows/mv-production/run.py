#!/usr/bin/env python3
"""MV Production workflow orchestrator.

Single entry point to run the complete mv-production pipeline stage by stage.
Automatically resolves artifact paths, tracks stage completion in state file,
and supports resume from failed/completed stages.

Usage:
    python workflows/mv-production/run.py \\
        --intake <intake.json> \\
        --project-root <project-dir> \\
        [--from <stage-name>] \\
        [--to <stage-name>] \\
        [--force] [--dry-run] [--continue-on-error] [--no-annotate]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
STATE_FILE = ".mv_workflow_state.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cmd(cmd: list[str], label: str, dry_run: bool) -> int:
    print(f"\n{'='*60}")
    print(f"[{label}] {' '.join(str(c) for c in cmd)}")
    print(f"{'='*60}")
    if dry_run:
        print("  (dry-run, skipped)")
        return 0
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def load_resolution(project_root: Path) -> tuple[int, int]:
    """Read target resolution from user_requirements.json, fallback to 1280x720."""
    req_path = project_root / "user_requirements.json"
    if req_path.exists():
        req = load_json(req_path)
        res = req.get("resolution", {})
        w = res.get("width", 1280)
        h = res.get("height", 720)
        return w, h
    return 1280, 720


def load_song_audio(project_root: Path) -> str | None:
    """Read song audio path from project_meta.json."""
    meta_path = project_root / "project_meta.json"
    if meta_path.exists():
        meta = load_json(meta_path)
        return meta.get("song_file_path")
    return None


def load_song_meta(project_root: Path) -> dict[str, Any] | None:
    """Read project_meta.json."""
    meta_path = project_root / "project_meta.json"
    if meta_path.exists():
        return load_json(meta_path)
    return None


# ── Stage definitions ──────────────────────────────────────────────────────

def stage_init(project_root: Path, intake_path: Path) -> list[str]:
    return [
        sys.executable, str(SCRIPTS_DIR / "init_project.py"),
        "--doc", str(intake_path),
        "--project-root", str(project_root),
    ]


def stage_parse_lyrics(project_root: Path, intake_path: Path) -> list[str]:
    intake = load_json(intake_path)
    lrc = Path(intake["lyrics_lrc_path"]).resolve()
    audio = Path(intake["song_audio_path"]).resolve()
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "parse_lyrics.py"),
        "--input", str(lrc),
        "--output", str(project_root / "lyrics-timing.json"),
        "--audio", str(audio),
    ]
    return cmd


def stage_infer_sections(project_root: Path) -> list[str]:
    return [
        sys.executable, str(SCRIPTS_DIR / "infer_sections_qwen3.py"),
        "--lyrics-timing", str(project_root / "lyrics-timing.json"),
        "--out", str(project_root / "song-sections-llm.json"),
    ]


def stage_interpret_segments(project_root: Path) -> list[str]:
    # Read song title from project_meta.json for proper propagation
    meta = load_song_meta(project_root)
    song_title = meta.get("song_title", "") if meta else ""
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "infer_segment_interpretation_qwen3.py"),
        "--song-sections-llm", str(project_root / "song-sections-llm.json"),
        "--lyrics-timing", str(project_root / "lyrics-timing.json"),
        "--out", str(project_root / "segment-interpretation.json"),
    ]
    if song_title:
        cmd.extend(["--song-title", song_title])
    return cmd


def stage_shot_plan(project_root: Path) -> list[str]:
    return [
        sys.executable, str(SCRIPTS_DIR / "infer_shot_plan_qwen3.py"),
        "--segment-interpretation", str(project_root / "segment-interpretation.json"),
        "--out", str(project_root / "shot-plan.json"),
    ]


def stage_build_prompts(project_root: Path) -> list[str]:
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "build_image_video_prompts.py"),
        "--shot-plan", str(project_root / "shot-plan.json"),
        "--user-requirements", str(project_root / "user_requirements.json"),
        "--out", str(project_root / "image-video-prompts.json"),
    ]
    return cmd


def stage_build_queue(project_root: Path) -> list[str]:
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "build_generation_queue.py"),
        "--image-video-prompts", str(project_root / "image-video-prompts.json"),
        "--user-requirements", str(project_root / "user_requirements.json"),
        "--out", str(project_root / "image-generation-queue.json"),
    ]
    return cmd


def stage_generate_images(project_root: Path) -> list[str]:
    return [
        sys.executable, str(SCRIPTS_DIR / "generate_images.py"),
        "--queue", str(project_root / "image-generation-queue.json"),
        "--image-video-prompts", str(project_root / "image-video-prompts.json"),
        "--segment-interpretation", str(project_root / "segment-interpretation.json"),
        "--out", str(project_root / "image-generation-results.json"),
        "--project-root", str(project_root),
        "--model", "FLUX.2-klein-9B",
    ]


def stage_asset_manifest(project_root: Path) -> list[str]:
    return [
        sys.executable, str(SCRIPTS_DIR / "build_asset_manifest.py"),
        "--generation-queue", str(project_root / "image-generation-queue.json"),
        "--project-root", str(project_root),
        "--out", str(project_root / "asset-manifest.json"),
    ]


def stage_generate_videos(project_root: Path) -> list[str]:
    w, h = load_resolution(project_root)
    return [
        sys.executable, str(SCRIPTS_DIR / "generate_videos.py"),
        "--image-video-prompts", str(project_root / "image-video-prompts.json"),
        "--selected-manifest", str(project_root / "selected-asset-manifest.json"),
        "--out", str(project_root / "video-generation-results.json"),
        "--project-root", str(project_root),
        "--width", str(w),
        "--height", str(h),
        "--model", "Wan2_2-I2V-A14B",
    ]


def stage_build_timeline(project_root: Path) -> list[str]:
    audio = load_song_audio(project_root)
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "build_timeline.py"),
        "--shot-plan", str(project_root / "shot-plan.json"),
        "--image-video-prompts", str(project_root / "image-video-prompts.json"),
        "--selected-manifest", str(project_root / "selected-asset-manifest.json"),
        "--lyrics-timing", str(project_root / "lyrics-timing.json"),
        "--out", str(project_root / "timeline.json"),
    ]
    if audio:
        cmd.extend(["--song-audio", audio])
    return cmd


def stage_assemble(project_root: Path) -> list[str]:
    """Detect whether to use assemble_final (videos exist) or assemble_still_mv (images only)."""
    audio = load_song_audio(project_root)
    if not audio:
        print("  [warn] No song audio path found in project_meta.json, skipping assemble")
        return []

    # Check if actual mp4 video candidates exist
    video_dir = project_root / "assets" / "videos" / "candidates"
    has_videos = False
    if video_dir.exists():
        has_videos = any(f.suffix == ".mp4" for f in video_dir.iterdir())

    w, h = load_resolution(project_root)

    if has_videos:
        return [
            sys.executable, str(SCRIPTS_DIR / "assemble_final.py"),
            "--timeline", str(project_root / "timeline.json"),
            "--song-audio", audio,
            "--project-root", str(project_root),
            "--target-width", str(w),
            "--target-height", str(h),
        ]
    else:
        return [
            sys.executable, str(SCRIPTS_DIR / "assemble_still_mv.py"),
            "--timeline", str(project_root / "timeline.json"),
            "--song-audio", audio,
            "--project-root", str(project_root),
            "--width", str(w),
            "--height", str(h),
        ]


def stage_annotate(project_root: Path) -> list[str]:
    return [
        sys.executable, str(SCRIPTS_DIR / "annotate_selected.py"),
        "--image-video-prompts", str(project_root / "image-video-prompts.json"),
        "--segment-interpretation", str(project_root / "segment-interpretation.json"),
        "--project-root", str(project_root),
    ]


# ── Stage registry ─────────────────────────────────────────────────────────

STAGE_REGISTRY: list[dict[str, Any]] = [
    {"name": "init",               "builder": stage_init,               "artifacts": ["project_meta.json", "user_requirements.json"]},
    {"name": "parse_lyrics",       "builder": stage_parse_lyrics,       "artifacts": ["lyrics-timing.json"]},
    {"name": "infer_sections",     "builder": stage_infer_sections,     "artifacts": ["song-sections-llm.json"]},
    {"name": "interpret_segments", "builder": stage_interpret_segments, "artifacts": ["segment-interpretation.json"]},
    {"name": "shot_plan",          "builder": stage_shot_plan,          "artifacts": ["shot-plan.json"]},
    {"name": "build_prompts",      "builder": stage_build_prompts,      "artifacts": ["image-video-prompts.json"]},
    {"name": "build_queue",        "builder": stage_build_queue,        "artifacts": ["image-generation-queue.json"]},
    {"name": "generate_images",    "builder": stage_generate_images,    "artifacts": ["image-generation-results.json"]},
    {"name": "asset_manifest",     "builder": stage_asset_manifest,     "artifacts": ["asset-manifest.json", "selected-asset-manifest.json"]},
    {"name": "generate_videos",    "builder": stage_generate_videos,    "artifacts": ["video-generation-results.json"]},
    {"name": "build_timeline",     "builder": stage_build_timeline,     "artifacts": ["timeline.json"]},
    {"name": "assemble",           "builder": stage_assemble,           "artifacts": ["assets/videos/final/output.mp4"]},
    {"name": "annotate",           "builder": stage_annotate,           "artifacts": []},
]

STAGE_NAMES = [s["name"] for s in STAGE_REGISTRY]


# ── State management ───────────────────────────────────────────────────────

def load_state(project_root: Path) -> dict[str, Any]:
    path = project_root / STATE_FILE
    if path.exists():
        return load_json(path)
    return {
        "schema_version": "1.0",
        "project_root": str(project_root.resolve()),
        "started_at": None,
        "stages": {},
    }


def save_state(project_root: Path, state: dict[str, Any]) -> None:
    write_json(project_root / STATE_FILE, state)


def is_stage_complete(stage_name: str, artifacts: list[str], project_root: Path, state: dict[str, Any]) -> bool:
    """Check both state file AND actual artifact files on disk."""
    stage_state = state.get("stages", {}).get(stage_name, {})
    if stage_state.get("status") != "completed":
        return False
    for art in artifacts:
        if not (project_root / art).exists():
            return False
    return True


def mark_stage_started(state: dict[str, Any], stage_name: str) -> None:
    state.setdefault("stages", {})[stage_name] = {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def mark_stage_completed(state: dict[str, Any], stage_name: str) -> None:
    state["stages"][stage_name]["status"] = "completed"
    state["stages"][stage_name]["completed_at"] = datetime.now(timezone.utc).isoformat()


def mark_stage_failed(state: dict[str, Any], stage_name: str) -> None:
    state["stages"][stage_name]["status"] = "failed"
    state["stages"][stage_name]["failed_at"] = datetime.now(timezone.utc).isoformat()


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="MV Production workflow orchestrator")
    ap.add_argument("--intake", required=True, type=Path, help="Intake document JSON (required)")
    ap.add_argument("--project-root", required=True, type=Path, help="Project output directory")
    ap.add_argument("--from", dest="from_stage", default=None, help=f"Start stage name ({', '.join(STAGE_NAMES)})")
    ap.add_argument("--to", dest="to_stage", default=None, help=f"End stage name ({', '.join(STAGE_NAMES)})")
    ap.add_argument("--force", action="store_true", help="Re-run all stages even if already completed")
    ap.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    ap.add_argument("--continue-on-error", action="store_true", help="Continue to next stage if current stage fails")
    ap.add_argument("--no-annotate", action="store_true", help="Skip the final annotate stage")
    args = ap.parse_args()

    project_root = args.project_root.resolve()
    intake_path = args.intake.resolve()

    if not intake_path.is_file():
        raise SystemExit(f"Intake document not found: {intake_path}")

    project_root.mkdir(parents=True, exist_ok=True)
    state = load_state(project_root)

    # Determine stage slice
    from_idx = 0
    to_idx = len(STAGE_REGISTRY)

    if args.from_stage:
        if args.from_stage not in STAGE_NAMES:
            raise SystemExit(f"Unknown stage '{args.from_stage}'. Valid: {', '.join(STAGE_NAMES)}")
        from_idx = STAGE_NAMES.index(args.from_stage)

    if args.to_stage:
        if args.to_stage not in STAGE_NAMES:
            raise SystemExit(f"Unknown stage '{args.to_stage}'. Valid: {', '.join(STAGE_NAMES)}")
        to_idx = STAGE_NAMES.index(args.to_stage) + 1

    if from_idx >= to_idx:
        raise SystemExit(f"--from '{args.from_stage}' is after --to '{args.to_stage}', no stages to run.")

    selected = STAGE_REGISTRY[from_idx:to_idx]

    if args.no_annotate:
        selected = [s for s in selected if s["name"] != "annotate"]

    # Print plan
    print(f"\n{'='*60}")
    print(f"MV Production Orchestrator")
    print(f"{'='*60}")
    print(f"  Project : {project_root}")
    print(f"  Intake  : {intake_path}")
    if not selected:
        print("  Stages  : (none selected)")
        print()
        return
    print(f"  Stages  : {selected[0]['name']} → {selected[-1]['name']} ({len(selected)} stages)")
    if args.force:
        print(f"  Force   : re-run all selected stages")
    if args.dry_run:
        print(f"  Dry-run : print commands only")
    print()

    if not state.get("started_at"):
        state["started_at"] = datetime.now(timezone.utc).isoformat()

    overall_start = time.time()
    exit_code = 0

    for stage_def in selected:
        stage_name = stage_def["name"]
        artifacts = stage_def["artifacts"]

        # Check if already completed
        if not args.force and is_stage_complete(stage_name, artifacts, project_root, state):
            print(f"[skip] {stage_name} — already completed")
            continue

        # Build command
        builder = stage_def["builder"]
        if stage_name == "init":
            cmd = builder(project_root, intake_path)
        elif stage_name == "parse_lyrics":
            cmd = builder(project_root, intake_path)
        elif stage_name == "assemble":
            cmd = builder(project_root)
            if not cmd:
                print(f"[skip] {stage_name} — missing audio path, cannot assemble")
                continue
        else:
            try:
                cmd = builder(project_root)
            except Exception as e:
                print(f"[error] {stage_name}: failed to build command: {e}")
                continue

        mark_stage_started(state, stage_name)
        save_state(project_root, state)

        stage_start = time.time()
        rc = run_cmd(cmd, stage_name, args.dry_run)
        elapsed = time.time() - stage_start

        if rc == 0:
            mark_stage_completed(state, stage_name)
            print(f"[ok] {stage_name} completed in {elapsed:.1f}s")
        else:
            mark_stage_failed(state, stage_name)
            print(f"[fail] {stage_name} exited with code {rc} after {elapsed:.1f}s")
            if not args.continue_on_error:
                exit_code = rc
                break
            exit_code = rc

        save_state(project_root, state)

    total_elapsed = time.time() - overall_start
    print(f"\n{'='*60}")
    if exit_code == 0:
        print(f"Pipeline completed successfully in {total_elapsed:.1f}s")
    else:
        print(f"Pipeline finished with errors in {total_elapsed:.1f}s (exit code {exit_code})")
    print(f"{'='*60}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
