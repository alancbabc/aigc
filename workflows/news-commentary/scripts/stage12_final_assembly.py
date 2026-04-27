#!/usr/bin/env python3
"""Assemble Stage 12 final video from rendered Stage 11 segments."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_FFMPEG_BIN = "ffmpeg"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def project_root_from_render_plan(render_plan_path: Path) -> Path:
    if render_plan_path.parent.name == "video":
        return render_plan_path.parent.parent
    return render_plan_path.parent


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def resolve_project_path(project_root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (project_root / candidate).resolve()


def write_segments_list(list_path: Path, segment_paths: list[Path]) -> None:
    ensure_parent(list_path)
    lines = [f"file '{segment_path.as_posix()}'" for segment_path in segment_paths]
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_command(command: list[str], log_path: Path) -> None:
    ensure_parent(log_path)
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    log_path.write_text(
        "COMMAND:\n"
        + " ".join(command)
        + "\n\nSTDOUT:\n"
        + completed.stdout
        + "\nSTDERR:\n"
        + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble Stage 12 final video from rendered segments")
    parser.add_argument("--render-plan", required=True, help="Path to video/render-plan.json")
    parser.add_argument("--output", help="Final output path; defaults to <project>/video/final/output.mp4")
    parser.add_argument("--segments-list", help="Optional explicit path for generated concat list")
    parser.add_argument("--log-path", help="Optional log path; defaults to <project>/logs/stage12_assembly.log")
    parser.add_argument("--ffmpeg-bin", default=DEFAULT_FFMPEG_BIN, help="ffmpeg executable name or path")
    parser.add_argument("--reencode", choices=["yes", "no"], default="yes", help="Default is yes to avoid concat noise from non-identical segment streams")
    args = parser.parse_args()

    render_plan_path = Path(args.render_plan).resolve()
    render_plan = load_json(render_plan_path)
    project_root = project_root_from_render_plan(render_plan_path)
    output_path = Path(args.output).resolve() if args.output else (project_root / "video" / "final" / "output.mp4").resolve()
    list_path = Path(args.segments_list).resolve() if args.segments_list else (output_path.parent / "segments.txt").resolve()
    log_path = Path(args.log_path).resolve() if args.log_path else (project_root / "logs" / "stage12_assembly.log").resolve()

    segment_paths = [resolve_project_path(project_root, item["output_path"]) for item in render_plan.get("render_items", [])]
    missing_paths = [str(path) for path in segment_paths if not path.exists()]
    if missing_paths:
        raise FileNotFoundError(f"Missing rendered segment files for Stage 12: {missing_paths}")

    write_segments_list(list_path, segment_paths)
    ensure_parent(output_path)

    command = [args.ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path)]
    if args.reencode == "yes":
        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
            ]
        )
    else:
        command.extend(["-c", "copy"])
    command.append(str(output_path))

    run_command(command, log_path)

    summary_path = log_path.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(
            {
                "render_plan": str(render_plan_path),
                "segments_list": str(list_path),
                "output": str(output_path),
                "segment_count": len(segment_paths),
                "reencode": args.reencode,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
