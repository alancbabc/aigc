#!/usr/bin/env python3
"""Build song-structure.json from parse_lyrics.py output and optional metadata.

Typical usage:

    # Step 1 — parse lyrics
    python parse_lyrics.py --input song.lrc --output parsed-lyrics.json --infer-sections

    # Step 2 — build song-structure scaffold
    python build_song_structure.py \
        --parsed-lyrics parsed-lyrics.json \
        --song-title "夜曲" \
        --artist "周杰伦" \
        --total-duration 245 \
        --bpm 72 \
        --output song-structure.json

    # Step 3 (optional) — merge LLM-enriched fields
    python build_song_structure.py \
        --parsed-lyrics parsed-lyrics.json \
        --enrich enrichment.json \
        --output song-structure.json

The --enrich file is a partial JSON whose keys are section_id values.
Each value is an object with optional fields: mood, energy_level,
visual_suggestion, transition_to_next, lyrics_summary.
Fields present in the enrichment file overwrite scaffold defaults.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SECTION_TYPE_ORDER = [
    "intro", "verse", "pre_chorus", "chorus", "post_chorus",
    "bridge", "breakdown", "instrumental", "outro", "interlude",
]

VALID_ENERGY_LEVELS = [
    "low", "medium_low", "medium", "medium_high", "high", "peak",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def round3(value: float) -> float:
    return round(float(value), 3)


def time_to_beat(time_seconds: float, bpm: float) -> int:
    """Convert a timestamp to the nearest beat number (1-based)."""
    beats_per_second = bpm / 60.0
    return max(1, int(math.ceil(time_seconds * beats_per_second)))


def normalize_section_type(raw_type: str) -> str:
    """Map inferred section labels to valid schema enum values."""
    raw = raw_type.strip().lower()
    if raw in SECTION_TYPE_ORDER:
        return raw
    if raw.startswith("verse"):
        return "verse"
    if raw.startswith("chorus"):
        return "chorus"
    if raw.startswith("pre_chorus") or raw.startswith("prechorus"):
        return "pre_chorus"
    if raw.startswith("post_chorus") or raw.startswith("postchorus"):
        return "post_chorus"
    if raw in ("break", "breakdown"):
        return "breakdown"
    if raw in ("inter", "interlude"):
        return "interlude"
    if raw in ("intro", "opening"):
        return "intro"
    if raw in ("outro", "ending", "coda"):
        return "outro"
    if raw in ("bridge", "solo", "instrumental"):
        return raw
    return "verse"


def build_section_label(section_type: str, counter: dict[str, int]) -> str:
    """Generate a human-readable section label like 'Verse 1', 'Chorus 2'."""
    counter[section_type] = counter.get(section_type, 0) + 1
    count = counter[section_type]
    pretty = section_type.replace("_", " ").title()
    if section_type in ("intro", "outro", "bridge", "breakdown"):
        return pretty if count == 1 else f"{pretty} {count}"
    return f"{pretty} {count}"


def build_sections(
    parsed: dict[str, Any],
    total_duration: float | None,
    bpm: float | None,
) -> list[dict[str, Any]]:
    """Transform parsed lyrics sections into song-structure sections."""
    inferred = parsed.get("inferred_sections", [])
    lines = parsed.get("lines", [])

    if not inferred:
        section = {
            "section_id": "full_song",
            "section_type": "verse",
            "section_label": "Full Song",
            "start_time": lines[0].get("start_time", 0.0) if lines else 0.0,
            "end_time": total_duration or (lines[-1].get("end_time") if lines else None),
            "lyrics_line_refs": [ln["line_id"] for ln in lines],
            "lyrics_summary": None,
            "mood": None,
            "energy_level": None,
            "visual_suggestion": None,
            "transition_to_next": None,
        }
        dur_start = section["start_time"] or 0.0
        dur_end = section["end_time"] or 0.0
        section["duration_seconds"] = round3(dur_end - dur_start) if dur_end else 0.0
        if bpm:
            section["start_beat"] = time_to_beat(dur_start, bpm)
            section["end_beat"] = time_to_beat(dur_end, bpm) if dur_end else None
        return [section]

    label_counter: dict[str, int] = {}
    sections: list[dict[str, Any]] = []

    for raw_sec in inferred:
        sec_id = raw_sec.get("section_id", f"section_{len(sections) + 1}")
        sec_type = normalize_section_type(raw_sec.get("section_type", "verse"))
        label = build_section_label(sec_type, label_counter)

        start = raw_sec.get("start_time")
        end = raw_sec.get("end_time")
        line_refs = raw_sec.get("line_refs", [])

        if start is None and line_refs:
            matched = [ln for ln in lines if ln["line_id"] in line_refs]
            if matched:
                first_start = matched[0].get("start_time")
                if first_start is not None:
                    start = first_start

        if end is None and line_refs:
            matched = [ln for ln in lines if ln["line_id"] in line_refs]
            if matched:
                last_end = matched[-1].get("end_time")
                if last_end is not None:
                    end = last_end

        duration = round3(end - start) if (start is not None and end is not None) else None

        entry: dict[str, Any] = {
            "section_id": sec_id,
            "section_type": sec_type,
            "section_label": label,
            "start_time": round3(start) if start is not None else None,
            "end_time": round3(end) if end is not None else None,
            "duration_seconds": duration,
            "lyrics_line_refs": line_refs,
            "lyrics_summary": None,
            "mood": None,
            "energy_level": None,
            "visual_suggestion": None,
            "transition_to_next": None,
        }

        if bpm and start is not None:
            entry["start_beat"] = time_to_beat(start, bpm)
            if end is not None:
                entry["end_beat"] = time_to_beat(end, bpm)

        sections.append(entry)

    if total_duration and sections:
        last = sections[-1]
        if last["end_time"] is None or last["end_time"] < total_duration:
            last["end_time"] = round3(total_duration)
            if last["start_time"] is not None:
                last["duration_seconds"] = round3(total_duration - last["start_time"])
            if bpm:
                last["end_beat"] = time_to_beat(total_duration, bpm)

    sections = [
        s for s in sections
        if s.get("duration_seconds") is None or s["duration_seconds"] > 0.5
    ]

    return sections


def apply_enrichment(
    sections: list[dict[str, Any]],
    enrichment: dict[str, Any],
) -> None:
    """Merge LLM-enriched fields into existing sections in-place."""
    enrichable_keys = {
        "mood", "energy_level", "visual_suggestion",
        "transition_to_next", "lyrics_summary",
    }
    for sec in sections:
        sid = sec["section_id"]
        if sid in enrichment:
            patch = enrichment[sid]
            for key in enrichable_keys:
                if key in patch:
                    sec[key] = patch[key]


def compute_arcs(sections: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Derive mood_arc and energy_arc from per-section values."""
    mood_arc = [sec.get("mood") or "unknown" for sec in sections]
    energy_arc = [sec.get("energy_level") or "medium" for sec in sections]
    return mood_arc, energy_arc


def determine_analysis_method(parsed: dict[str, Any]) -> str:
    fmt = parsed.get("detected_format", "")
    if fmt == "lrc":
        return "lrc_parse"
    if parsed.get("inferred_sections"):
        return "lyrics_pattern"
    return "manual"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build song-structure.json from parsed lyrics output",
    )
    parser.add_argument(
        "--parsed-lyrics", required=True,
        help="Path to JSON output from parse_lyrics.py",
    )
    parser.add_argument("--output", required=True, help="Output path for song-structure.json")
    parser.add_argument("--song-title", default=None, help="Song title")
    parser.add_argument("--artist", default=None, help="Artist name")
    parser.add_argument("--total-duration", type=float, default=None, help="Total song duration in seconds")
    parser.add_argument("--bpm", type=float, default=None, help="Beats per minute")
    parser.add_argument("--time-signature", default=None, help="Time signature, e.g. 4/4")
    parser.add_argument("--key", default=None, help="Musical key, e.g. F minor")
    parser.add_argument(
        "--enrich", default=None,
        help="Optional JSON file with per-section enrichment (mood, energy_level, visual_suggestion, etc.)",
    )
    args = parser.parse_args()

    parsed_path = Path(args.parsed_lyrics).resolve()
    output_path = Path(args.output).resolve()
    parsed = load_json(parsed_path)

    sections = build_sections(parsed, args.total_duration, args.bpm)

    if args.enrich:
        enrichment = load_json(Path(args.enrich).resolve())
        apply_enrichment(sections, enrichment)

    mood_arc, energy_arc = compute_arcs(sections)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "song_title": args.song_title or parsed.get("source_file", "Untitled"),
        "total_duration_seconds": args.total_duration or 0,
        "sections": sections,
    }

    if args.artist:
        payload["artist"] = args.artist
    if args.bpm:
        payload["bpm"] = args.bpm
    if args.time_signature:
        payload["time_signature"] = args.time_signature
    if args.key:
        payload["key"] = args.key

    payload["mood_arc"] = mood_arc
    payload["energy_arc"] = energy_arc
    payload["analysis_method"] = determine_analysis_method(parsed)
    payload["analysis_notes"] = (
        f"Scaffold generated from {parsed.get('detected_format', 'unknown')} lyrics "
        f"with {len(sections)} section(s). "
        "Fields marked null require LLM enrichment."
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
