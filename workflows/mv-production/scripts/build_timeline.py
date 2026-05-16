#!/usr/bin/env python3
"""Build timeline.json from shot-plan.json + selected-asset-manifest.json.

Assembles a sequential timeline of video segments for final MV production.
Aligns with lyrics-timing for lyric text synchronization.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Build MV timeline from shot plan, prompts, and assets")
    ap.add_argument("--shot-plan", required=True, type=Path)
    ap.add_argument("--image-video-prompts", required=True, type=Path)
    ap.add_argument("--selected-manifest", required=True, type=Path)
    ap.add_argument("--lyrics-timing", required=True, type=Path)
    ap.add_argument("--song-audio", type=Path, default=None, help="Original song audio for final assembly reference")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    shot_data = load_json(args.shot_plan.resolve())
    sel_data = load_json(args.selected_manifest.resolve())
    lyrics_data = load_json(args.lyrics_timing.resolve())

    # Lookup tables
    sel_lookup = {a["shot_id"]: a for a in sel_data.get("assets", [])}

    # Build line_id → text lookup from lyrics-timing
    line_text: dict[str, str] = {}
    for ln in lyrics_data.get("lines", []):
        lid = ln.get("line_id", "")
        text = ln.get("text", "")
        if lid and text:
            line_text[lid] = text

    # Build shot_id → sequence index from shot-plan order
    seq_lookup: dict[str, int] = {}
    for i, s in enumerate(shot_data.get("shots", []), start=1):
        seq_lookup[s["shot_id"]] = i

    segments: list[dict[str, Any]] = []
    for shot in shot_data.get("shots", []):
        sid = shot["shot_id"]
        tr = shot["time_range"]
        sel = sel_lookup.get(sid, {})
        seq = seq_lookup.get(sid, 0)

        # Collect lyrics text from lyric_refs
        lyrics_lines: list[str] = []
        for rid in shot.get("lyric_refs", []):
            lt = line_text.get(rid)
            if lt:
                lyrics_lines.append(lt)

        fallback_img = f"assets/images/selected/{seq:03d}_{sid}.png" if seq else f"assets/images/selected/{sid}.png"
        fallback_vid = f"assets/videos/candidates/{seq:03d}_{sid}.mp4" if seq else f"assets/videos/candidates/{sid}.mp4"
        segments.append({
            "shot_id": sid,
            "start_time": tr["start_time"],
            "end_time": tr["end_time"],
            "duration_seconds": tr["duration_seconds"],
            "input_image": sel.get("selected_image", fallback_img),
            "video_path": fallback_vid,
            "lyrics_text": " / ".join(lyrics_lines) if lyrics_lines else "",
        })

    segments.sort(key=lambda s: s["start_time"])

    total_duration = max(s["end_time"] for s in segments) if segments else 0

    out = {
        "schema_version": "1.0",
        "song_title": shot_data.get("song_title", ""),
        "song_audio_path": str(args.song_audio.resolve()) if args.song_audio else None,
        "total_duration_seconds": total_duration,
        "segments": segments,
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
