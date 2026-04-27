#!/usr/bin/env python3
"""Assemble final MV from rendered video segments and original song audio."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_FFMPEG_BIN = "ffmpeg"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def resolve_project_path(project_root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (project_root / candidate).resolve()


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


def trim_segment(
    input_path: Path,
    output_path: Path,
    duration_seconds: float,
    ffmpeg_bin: str,
    log_path: Path,
) -> None:
    """Trim a video segment to exact duration, stripping its audio track."""
    ensure_parent(output_path)
    command = [
        ffmpeg_bin, "-y",
        "-i", str(input_path),
        "-t", str(round(duration_seconds, 3)),
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    run_command(command, log_path)


def concatenate_segments(
    segment_paths: list[Path],
    concat_list_path: Path,
    output_path: Path,
    ffmpeg_bin: str,
    log_path: Path,
) -> None:
    """Concatenate trimmed video segments into a single video without audio."""
    ensure_parent(concat_list_path)
    lines = [f"file '{p.as_posix()}'" for p in segment_paths]
    concat_list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ensure_parent(output_path)
    command = [
        ffmpeg_bin, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list_path),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    run_command(command, log_path)


def overlay_song_audio(
    video_path: Path,
    song_path: Path,
    output_path: Path,
    ffmpeg_bin: str,
    log_path: Path,
    fade_out_seconds: float = 2.0,
) -> None:
    """Replace video audio with the original song file."""
    ensure_parent(output_path)
    command = [
        ffmpeg_bin, "-y",
        "-i", str(video_path),
        "-i", str(song_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    run_command(command, log_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble final MV from rendered segments + original song audio"
    )
    parser.add_argument(
        "--video-plan", required=True,
        help="Path to mv-video-plan.json"
    )
    parser.add_argument(
        "--song", required=True,
        help="Path to the original song audio file"
    )
    parser.add_argument(
        "--output",
        help="Final output path (default: <project>/video/final/output.mp4)"
    )
    parser.add_argument(
        "--ffmpeg-bin", default=DEFAULT_FFMPEG_BIN,
        help="ffmpeg executable"
    )
    args = parser.parse_args()

    video_plan_path = Path(args.video_plan).resolve()
    song_path = Path(args.song).resolve()
    video_plan = load_json(video_plan_path)

    if video_plan_path.parent.name == "video":
        project_root = video_plan_path.parent.parent
    else:
        project_root = video_plan_path.parent

    output_path = (
        Path(args.output).resolve()
        if args.output
        else (project_root / "video" / "final" / "output.mp4").resolve()
    )
    work_dir = project_root / "video" / "final" / "_work"
    logs_dir = project_root / "logs"

    entries = video_plan.get("entries", [])
    entries_sorted = sorted(entries, key=lambda e: e["time_window"]["start_time"])

    trimmed_paths: list[Path] = []

    for i, entry in enumerate(entries_sorted):
        entry_id = entry["entry_id"]
        source_path = resolve_project_path(project_root, entry.get("output_path", ""))

        if not source_path.exists():
            raise FileNotFoundError(
                f"Missing rendered segment for {entry_id}: {source_path}"
            )

        duration = entry["time_window"]["duration_seconds"]
        trimmed_path = work_dir / f"{i:03d}_{entry_id}_trimmed.mp4"

        trim_segment(
            source_path, trimmed_path, duration,
            args.ffmpeg_bin,
            logs_dir / f"trim_{entry_id}.log",
        )
        trimmed_paths.append(trimmed_path)

    concat_video_path = work_dir / "concat_video_only.mp4"
    concat_list_path = work_dir / "segments.txt"

    concatenate_segments(
        trimmed_paths, concat_list_path, concat_video_path,
        args.ffmpeg_bin,
        logs_dir / "concat_segments.log",
    )

    overlay_song_audio(
        concat_video_path, song_path, output_path,
        args.ffmpeg_bin,
        logs_dir / "overlay_audio.log",
    )

    summary_path = logs_dir / "assembly_summary.json"
    ensure_parent(summary_path)
    summary_path.write_text(
        json.dumps(
            {
                "video_plan": str(video_plan_path),
                "song_file": str(song_path),
                "output": str(output_path),
                "segment_count": len(entries_sorted),
                "trimmed_segments": [str(p) for p in trimmed_paths],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
