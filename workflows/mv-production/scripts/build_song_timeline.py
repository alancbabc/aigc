#!/usr/bin/env python3
"""Build a song timeline by extracting audio segments for each video-plan entry."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_FFMPEG_BIN = "ffmpeg"
DEFAULT_FFPROBE_BIN = "ffprobe"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def round3(value: float) -> float:
    return round(float(value), 3)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_audio_duration(audio_path: Path, ffprobe_bin: str = DEFAULT_FFPROBE_BIN) -> float:
    command = [
        ffprobe_bin, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(audio_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def extract_audio_segment(
    song_path: Path,
    start_time: float,
    duration: float,
    output_path: Path,
    ffmpeg_bin: str = DEFAULT_FFMPEG_BIN,
) -> None:
    ensure_parent(output_path)
    command = [
        ffmpeg_bin, "-y",
        "-i", str(song_path),
        "-ss", str(round3(start_time)),
        "-t", str(round3(duration)),
        "-c:a", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_path),
    ]
    subprocess.run(command, capture_output=True, text=True, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract audio segments from a song file based on video-plan time windows"
    )
    parser.add_argument(
        "--song", required=True,
        help="Path to the original song audio file"
    )
    parser.add_argument(
        "--video-plan", required=True,
        help="Path to mv-video-plan.json"
    )
    parser.add_argument(
        "--output-dir", required=True,
        help="Directory to write extracted audio segments"
    )
    parser.add_argument(
        "--output-manifest", required=True,
        help="Path to write the timeline manifest JSON"
    )
    parser.add_argument(
        "--ffmpeg-bin", default=DEFAULT_FFMPEG_BIN,
        help="ffmpeg executable"
    )
    parser.add_argument(
        "--ffprobe-bin", default=DEFAULT_FFPROBE_BIN,
        help="ffprobe executable"
    )
    args = parser.parse_args()

    song_path = Path(args.song).resolve()
    video_plan_path = Path(args.video_plan).resolve()
    output_dir = Path(args.output_dir).resolve()
    manifest_path = Path(args.output_manifest).resolve()

    if not song_path.exists():
        raise FileNotFoundError(f"Song file not found: {song_path}")

    song_duration = get_audio_duration(song_path, args.ffprobe_bin)
    video_plan = load_json(video_plan_path)
    entries = video_plan.get("entries", [])

    segments: list[dict[str, Any]] = []

    for entry in entries:
        entry_id = entry["entry_id"]
        time_window = entry["time_window"]
        start_time = float(time_window["start_time"])
        end_time = float(time_window["end_time"])
        duration = round3(end_time - start_time)
        render_mode = entry.get("render_mode", "")

        segment_filename = f"{entry_id}.wav"
        segment_path = output_dir / segment_filename

        extract_audio_segment(
            song_path, start_time, duration, segment_path, args.ffmpeg_bin
        )

        segment_info: dict[str, Any] = {
            "entry_id": entry_id,
            "start_time": round3(start_time),
            "end_time": round3(end_time),
            "duration_seconds": duration,
            "audio_segment_path": str(segment_path.relative_to(manifest_path.parent)),
            "render_mode": render_mode,
            "extraction_status": "success",
        }

        if render_mode == "audio_to_video":
            segment_info["use_for_ltx"] = True
        else:
            segment_info["use_for_ltx"] = False

        segments.append(segment_info)

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "song_title": video_plan.get("song_title", ""),
        "song_file": str(song_path.name),
        "song_duration_seconds": round3(song_duration),
        "total_segments": len(segments),
        "segments": segments,
    }

    ensure_parent(manifest_path)
    manifest_path.write_text(
        f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
