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
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def check_ffmpeg(ffmpeg_bin: str = "ffmpeg") -> None:
    try:
        subprocess.run([ffmpeg_bin, "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise SystemExit(f"FFmpeg not found: '{ffmpeg_bin}' is not installed or not in PATH.")


def probe_duration(video_path: Path, ffmpeg_bin: str = "ffmpeg") -> float | None:
    """Probe video duration in seconds using ffprobe."""
    try:
        cmd = [ffmpeg_bin.replace("ffmpeg", "ffprobe"), "-v", "error",
               "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1",
               str(video_path)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return float(r.stdout.strip())
    except Exception:
        pass
    return None


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


def clean_work_dir(work_dir: Path) -> None:
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
        print(f"Cleaned up {work_dir}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Assemble final MV")
    ap.add_argument("--timeline", required=True, type=Path)
    ap.add_argument("--song-audio", required=True, type=Path, help="Original song audio file")
    ap.add_argument("--output", type=Path, default=None, help="Output MP4 path (default: <project>/assets/videos/final/output.mp4)")
    ap.add_argument("--project-root", type=Path, default=None)
    ap.add_argument("--target-width", type=int, default=1920, help="Uniform output width (16:9)")
    ap.add_argument("--target-height", type=int, default=1080, help="Uniform output height (16:9)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    timeline_data = load_json(args.timeline.resolve())
    project_root = args.project_root.resolve() if args.project_root else args.timeline.resolve().parent
    song_path = args.song_audio.resolve()
    if not song_path.is_file():
        raise SystemExit(f"Song audio file not found: {song_path}")
    output_path = args.output.resolve() if args.output else (project_root / "assets" / "videos" / "final" / "output.mp4")
    work_dir = output_path.parent / "_work"

    # Build selected_image lookup for still-image fallback
    sel_manifest_path = project_root / "selected-asset-manifest.json"
    sel_lookup: dict[str, str] = {}
    if sel_manifest_path.exists():
        sel_data = load_json(sel_manifest_path)
        for a in sel_data.get("assets", []):
            sel_image = a.get("selected_image")
            if sel_image:
                sel_lookup[a["shot_id"]] = sel_image

    check_ffmpeg()

    if args.dry_run:
        segments = timeline_data.get("segments", [])
        print(f"[dry-run] Would assemble {len(segments)} segments to {output_path}")
        print(f"[dry-run] target: {args.target_width}x{args.target_height}, audio: {song_path}")
        return

    segments = timeline_data.get("segments", [])
    segments.sort(key=lambda s: s["start_time"])

    # Build shot_id → sequence index from segment order
    seq_lookup: dict[str, int] = {}
    for idx, seg in enumerate(segments, start=1):
        seq_lookup[seg["shot_id"]] = idx

    trimmed_paths: list[Path] = []
    missing_videos = 0
    for i, seg in enumerate(segments):
        dur = seg["duration_seconds"]
        vid_path_str = seg.get("video_path", "")
        if not vid_path_str:
            sid = seg["shot_id"]
            seq = seq_lookup.get(sid, 0)
            vid_path_str = f"assets/videos/candidates/{seq:03d}_{sid}.mp4" if seq else f"assets/videos/candidates/{sid}.mp4"
        input_path = project_root / vid_path_str

        if not input_path.exists() or input_path.suffix.lower() not in (".mp4", ".mov", ".avi"):
            # Try still-image fallback for ambient holds / missing videos
            still_path = project_root / sel_lookup.get(seg["shot_id"], {}).get("selected_image", "")
            if still_path and still_path.exists():
                trimmed_path = work_dir / f"{i:03d}_{seg['shot_id']}_still.mp4"
                cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1", "-r", "24", "-i", str(still_path),
                    "-t", str(round(dur, 3)),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-an",
                    str(trimmed_path),
                ]
                try:
                    subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
                    trimmed_paths.append(trimmed_path)
                    print(f"  [still] {seg['shot_id']}: generated still-frame video")
                    continue
                except subprocess.CalledProcessError:
                    pass
            missing_videos += 1
            print(f"  [skip] {seg['shot_id']}: video not found: {input_path}")
            continue

        trimmed_path = work_dir / f"{i:03d}_{seg['shot_id']}.mp4"
        # Validate actual duration before trimming
        actual_dur = probe_duration(input_path)
        if actual_dur is not None and actual_dur < dur - 0.1:
            gap = round(dur - actual_dur, 2)
            print(f"  [warn] {seg['shot_id']}: video {actual_dur:.3f}s < target {dur:.3f}s, padding {gap:.1f}s")
            padded_path = work_dir / f"{i:03d}_{seg['shot_id']}_padded.mp4"
            pad_cmd = [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-vf", f"tpad=stop_mode=clone:stop_duration={gap}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an",
                str(padded_path),
            ]
            try:
                subprocess.run(pad_cmd, capture_output=True, text=True, check=True, timeout=120)
                input_path = padded_path
            except subprocess.CalledProcessError:
                print(f"    [warn] padding failed, using original")
        try:
            trim_segment(input_path, trimmed_path, dur)
            trimmed_paths.append(trimmed_path)
        except RuntimeError:
            print(f"  [error] Failed to trim {seg['shot_id']}, skipping")

    if missing_videos:
        print(f"\n  [warn] {missing_videos}/{len(segments)} video files missing")
    if not trimmed_paths:
        raise SystemExit("No video segments to assemble. Generate videos first with stage generate_videos.")

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
    try:
        concat_segments(normalized_paths, concat_path)
    except RuntimeError as e:
        clean_work_dir(work_dir)
        raise SystemExit(f"Concat failed: {e}")

    # Overlay audio
    try:
        overlay_audio(concat_path, song_path, output_path)
    except RuntimeError as e:
        clean_work_dir(work_dir)
        raise SystemExit(f"Audio overlay failed: {e}")

    print(f"\nFinal MV: {output_path} ({output_path.stat().st_size / 1024:.0f} KB)")

    # Clean up work directory
    clean_work_dir(work_dir)


if __name__ == "__main__":
    main()
