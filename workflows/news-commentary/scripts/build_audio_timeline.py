#!/usr/bin/env python3
"""Build audio/timeline.json from actual generated audio files."""

from __future__ import annotations

import argparse
import json
import subprocess
import wave
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def round3(value: float) -> float:
    return round(float(value), 3)


def infer_audio_filename(entry: dict[str, Any], audio_format: str) -> str:
    line_no = int(entry["line_no"])
    split_total = int(entry.get("split_part_total", 1) or 1)
    split_part_no = int(entry.get("split_part_no", 1) or 1)
    base_name = f"line_{line_no:03d}"
    if split_total > 1:
      base_name = f"{base_name}_part{split_part_no:02d}"
    return f"{base_name}.{audio_format}"


def resolve_audio_path(entry: dict[str, Any], audio_root: Path, audio_format: str) -> tuple[Path, str]:
    explicit_path = entry.get("planned_audio_path")
    if isinstance(explicit_path, str) and explicit_path:
        relative_path = Path(explicit_path)
        absolute_path = (audio_root.parent / relative_path).resolve()
        return absolute_path, relative_path.as_posix()
    speaker = str(entry["speaker"])
    relative_path = Path("audio") / speaker / infer_audio_filename(entry, audio_format)
    absolute_path = audio_root / speaker / infer_audio_filename(entry, audio_format)
    return absolute_path, relative_path.as_posix()


def duration_from_wav(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
        if frame_rate <= 0:
            raise ValueError(f"Invalid WAV frame rate for {path}")
        return frame_count / frame_rate


def duration_from_ffprobe(path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise RuntimeError(f"ffprobe failed for {path}: {stderr or 'unknown error'}")

    output = completed.stdout.strip()
    if not output:
        raise RuntimeError(f"ffprobe returned no duration for {path}")
    return float(output)


def detect_duration_seconds(path: Path) -> float:
    suffix = path.suffix.lower()
    if suffix == ".wav":
        return round3(duration_from_wav(path))
    if suffix == ".mp3":
        return round3(duration_from_ffprobe(path))
    raise ValueError(f"Unsupported audio format for duration detection: {path.suffix}")


def build_voice_source_by_speaker(series_profile: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    defaults = (series_profile or {}).get("anchor_defaults", {})
    result: dict[str, dict[str, Any]] = {}
    for speaker in ("host", "guest"):
        tts_voice_id = defaults.get(f"{speaker}_tts_voice_id")
        voice_reference_audio = defaults.get(f"{speaker}_voice_reference_audio")
        if not tts_voice_id and not voice_reference_audio:
            continue

        mode = "mixed"
        if tts_voice_id and not voice_reference_audio:
            mode = "tts_voice_id"
        if voice_reference_audio and not tts_voice_id:
            mode = "voice_reference_audio"

        result[speaker] = {
            "mode": mode,
            **({"tts_voice_id": tts_voice_id} if tts_voice_id else {}),
            **({"voice_reference_audio": voice_reference_audio} if voice_reference_audio else {}),
        }
    return result


def resolve_voice_source(entry: dict[str, Any], voice_source_by_speaker: dict[str, dict[str, Any]]) -> dict[str, Any]:
    voice_source = entry.get("voice_source")
    if isinstance(voice_source, dict) and voice_source.get("mode"):
        return voice_source

    speaker = str(entry["speaker"])
    fallback = voice_source_by_speaker.get(speaker)
    if fallback:
        return fallback

    raise ValueError(
        f"TTS entry {entry.get('entry_id', '<unknown>')} is missing voice_source and no series-profile fallback was provided"
    )


def build_timeline_entry(entry: dict[str, Any], audio_root: Path, audio_format: str, voice_source_by_speaker: dict[str, dict[str, Any]]) -> dict[str, Any]:
    audio_file_path, relative_audio_path = resolve_audio_path(entry, audio_root, audio_format)
    if not audio_file_path.exists():
        raise FileNotFoundError(f"Generated audio file not found for {entry['entry_id']}: {audio_file_path}")

    duration_seconds = detect_duration_seconds(audio_file_path)
    return {
        "entry_id": entry["entry_id"],
        "script_line_id": entry["script_line_id"],
        "segment_no": entry["segment_no"],
        "segment_type": entry["segment_type"],
        "line_no": entry["line_no"],
        "speaker": entry["speaker"],
        "text": entry["text"],
        **({"emotion": entry["emotion"]} if entry.get("emotion") else {}),
        "audio_path": relative_audio_path,
        "duration_seconds": duration_seconds,
        "pause_before": float(entry.get("pause_before", 0)),
        "pause_after": float(entry.get("pause_after", 0)),
        "split_part_no": int(entry.get("split_part_no", 1)),
        "split_part_total": int(entry.get("split_part_total", 1)),
        **({"split_group_id": entry["split_group_id"]} if entry.get("split_group_id") else {}),
        "source_line_text": entry["source_line_text"],
        "resynthesis_round": int(entry.get("resynthesis_round", 0)),
        "needs_resynthesis": duration_seconds > 15.0,
        **({"resynthesis_reason": "actual generated audio exceeds 15 seconds"} if duration_seconds > 15.0 else {}),
        "voice_source": resolve_voice_source(entry, voice_source_by_speaker),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build audio/timeline.json from actual generated audio files")
    parser.add_argument("--tts-plan", required=True, help="Path to audio/tts-plan.json")
    parser.add_argument("--audio-dir", required=True, help="Directory containing generated host/guest audio subdirectories")
    parser.add_argument("--output", required=True, help="Output path for audio/timeline.json")
    parser.add_argument("--audio-format", default="mp3", choices=["mp3", "wav"], help="Generated audio file format")
    parser.add_argument("--series-profile", help="Optional path to series-profile.json for voice_source fallback")
    args = parser.parse_args()

    tts_plan = load_json(Path(args.tts_plan).resolve())
    series_profile = load_json(Path(args.series_profile).resolve()) if args.series_profile else None
    audio_root = Path(args.audio_dir).resolve()
    output_path = Path(args.output).resolve()
    voice_source_by_speaker = build_voice_source_by_speaker(series_profile)

    entries = [
        build_timeline_entry(entry, audio_root, args.audio_format, voice_source_by_speaker)
        for entry in tts_plan.get("entries", [])
    ]

    payload = {
        "schema_version": "1.0",
        "title": tts_plan.get("title", "news-commentary-audio-timeline"),
        "audio_format": args.audio_format,
        "entries": entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
