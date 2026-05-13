#!/usr/bin/env python3
"""Build timeline.json from video-prompts.json + selected-asset-manifest.json.

Assembles a sequential timeline of video segments for final MV production.
Aligns with lyrics-timing for subtitle synchronization.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Build MV timeline from video prompts and assets")
    ap.add_argument("--shot-plan", required=True, type=Path)
    ap.add_argument("--video-prompts", required=True, type=Path)
    ap.add_argument("--selected-manifest", required=True, type=Path)
    ap.add_argument("--lyrics-timing", required=True, type=Path)
    ap.add_argument("--song-audio", type=Path, default=None, help="Original song audio for final assembly reference")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    shot_data = load_json(args.shot_plan.resolve())
    video_data = load_json(args.video_prompts.resolve())
    sel_data = load_json(args.selected_manifest.resolve())
    lyrics_data = load_json(args.lyrics_timing.resolve())

    # Lookup tables
    vid_lookup = {v["shot_id"]: v for v in video_data.get("video_prompts", [])}
    sel_lookup = {a["shot_id"]: a for a in sel_data.get("assets", [])}

    segments: list[dict[str, Any]] = []
    for shot in shot_data.get("shots", []):
        sid = shot["shot_id"]
        tr = shot["time_range"]
        vid = vid_lookup.get(sid, {})
        sel = sel_lookup.get(sid, {})
        lyrics_text = ""
        for rid in shot.get("lyric_refs", []):
            for line in lyrics_data.get("lines", []):
                if line.get("line_id") == rid:
                    lt = line.get("text", "")
                    if lt:
                        lyrics_text += lt + "\n"
                    break

        segments.append({
            "shot_id": sid,
            "start_time": tr["start_time"],
            "end_time": tr["end_time"],
            "duration_seconds": tr["duration_seconds"],
            "input_image": sel.get("selected_image", vid.get("input_image", "")),
            "video_prompt": vid.get("video_prompt", ""),
            "camera_motion": vid.get("camera_motion", ""),
            "motion_intensity": vid.get("motion_intensity", ""),
            "transition_out": vid.get("transition_out", ""),
            "shot_role": shot.get("shot_role", ""),
            "lyrics_text": lyrics_text.strip(),
        })

    segments.sort(key=lambda s: s["start_time"])

    # Build FFmpeg concat list
    concat_files: list[str] = []
    for i, seg in enumerate(segments):
        concat_files.append(f"file '../segments/segment_{i:03d}_{seg['shot_id']}.mp4'")

    total_duration = max(s["end_time"] for s in segments) if segments else 0

    out = {
        "schema_version": "1.0",
        "song_title": shot_data.get("song_title", ""),
        "song_audio_path": str(args.song_audio.resolve()) if args.song_audio else None,
        "total_duration_seconds": total_duration,
        "segments": segments,
        "concat_list": concat_files,
        "assembly_notes": {
            "audio_track": "Replace all segment audio with original song.",
            "encode_mode": "re-encode (H.264 + AAC) for mixed-resolution safety.",
            "subtitles_source": str(args.lyrics_timing.resolve()) if args.lyrics_timing else None,
        },
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(segments)} segments, {total_duration:.1f}s total)")


if __name__ == "__main__":
    main()
