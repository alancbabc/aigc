#!/usr/bin/env python3
"""Assemble final MV from generated video segments and original song audio.

Reads timeline.json for segment ordering and timing. Trims each segment
to its precise time window, concatenates all segments, overlays the original
song audio track, and produces the final output.mp4.

Uses FFmpeg for all video operations. Handles mixed-resolution segments
by padding to a uniform resolution.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_ffmpeg(cmd: list[str], description: str = "") -> None:
    label = f" [{description}]" if description else ""
    print(f"  ffmpeg{label}...", end=" ", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAIL")
        print(f"  stderr: {result.stderr.strip()[-500:]}")
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}")
    print("OK")


def trim_segment(input_path: Path, output_path: Path, duration_seconds: float, ffmpeg_bin: str = "ffmpeg") -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(input_path),
        "-t", str(round(duration_seconds, 3)),
        "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    run_ffmpeg(cmd, f"trim {output_path.name}")


def normalize_video(input_path: Path, output_path: Path, target_w: int, target_h: int, ffmpeg_bin: str = "ffmpeg") -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scale_filter = f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black"
    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(input_path),
        "-vf", scale_filter,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]
    run_ffmpeg(cmd, f"normalize {output_path.name}")


def concat_segments(segment_paths: list[Path], output_path: Path, ffmpeg_bin: str = "ffmpeg") -> None:
    list_file = output_path.parent / "_concat_list.txt"
    list_file.write_text("\n".join(f"file '{p.as_posix()}'" for p in segment_paths) + "\n", encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    run_ffmpeg(cmd, f"concat {len(segment_paths)} segments")


def overlay_audio(video_path: Path, song_path: Path, output_path: Path, ffmpeg_bin: str = "ffmpeg") -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
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
    run_ffmpeg(cmd, f"overlay audio -> {output_path.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Assemble final MV")
    ap.add_argument("--timeline", required=True, type=Path)
    ap.add_argument("--song-audio", required=True, type=Path, help="Original song audio file")
    ap.add_argument("--output", type=Path, default=None, help="Output MP4 path (default: <project>/assets/videos/final/output.mp4)")
    ap.add_argument("--project-root", type=Path, default=None)
    ap.add_argument("--target-width", type=int, default=1024, help="Uniform output width")
    ap.add_argument("--target-height", type=int, default=576, help="Uniform output height")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    timeline_data = load_json(args.timeline.resolve())
    project_root = args.project_root.resolve() if args.project_root else args.timeline.resolve().parent
    song_path = args.song_audio.resolve()
    output_path = args.output.resolve() if args.output else (project_root / "assets" / "videos" / "final" / "output.mp4")
    work_dir = output_path.parent / "_work"

    segments = timeline_data.get("segments", [])
    segments.sort(key=lambda s: s["start_time"])

    trimmed_paths: list[Path] = []
    for i, seg in enumerate(segments):
        dur = seg["duration_seconds"]
        vid_path_str = seg.get("video_path", seg.get("input_image", ""))
        if not vid_path_str:
            # Check assets/videos/candidates/{shot_id}.mp4
            vid_path_str = f"assets/videos/candidates/{seg['shot_id']}.mp4"
        input_path = project_root / vid_path_str

        if not input_path.exists():
            print(f"  [warn] {seg['shot_id']}: video not found: {input_path}")
            continue

        trimmed_path = work_dir / f"{i:03d}_{seg['shot_id']}.mp4"
        try:
            trim_segment(input_path, trimmed_path, dur)
            trimmed_paths.append(trimmed_path)
        except RuntimeError:
            print(f"  [error] Failed to trim {seg['shot_id']}, skipping")

    if not trimmed_paths:
        raise SystemExit("No video segments to assemble.")

    # Normalize all to uniform resolution
    normalized_paths: list[Path] = []
    for tp in trimmed_paths:
        np = work_dir / f"{tp.stem}_norm.mp4"
        try:
            normalize_video(tp, np, args.target_width, args.target_height)
            normalized_paths.append(np)
        except RuntimeError:
            print(f"  [error] Failed to normalize {tp.name}, using original")
            normalized_paths.append(tp)

    # Concat
    concat_path = work_dir / "concat_video_only.mp4"
    concat_segments(normalized_paths, concat_path)

    # Overlay audio
    overlay_audio(concat_path, song_path, output_path)

    print(f"\nFinal MV: {output_path} ({output_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
