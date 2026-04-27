#!/usr/bin/env python3
"""Parse LRC or plain-text lyrics into a structured JSON for MV production."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


LRC_TIMESTAMP_PATTERN = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")

METADATA_PATTERNS = re.compile(
    r"^("
    r"written\s*by|composer|lyricist|arranger|artist|album|title|editor"
    r"|作[词曲编]|编曲|专辑|歌手|演唱"
    r")\s*[：:：]",
    re.IGNORECASE,
)


def is_metadata_line(text: str, timestamp: float) -> bool:
    """Detect LRC metadata lines that should not be treated as lyrics."""
    if timestamp != 0.0:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    if METADATA_PATTERNS.search(stripped):
        return True
    if " - " in stripped and ("(" in stripped or "（" in stripped):
        return True
    return False


def parse_lrc_timestamp(match: re.Match) -> float:
    minutes = int(match.group(1))
    seconds = int(match.group(2))
    centiseconds = match.group(3)
    if centiseconds is not None:
        frac = int(centiseconds.ljust(3, "0")) / 1000.0
    else:
        frac = 0.0
    return minutes * 60 + seconds + frac


def round3(value: float) -> float:
    return round(float(value), 3)


def parse_lrc(text: str) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    line_counter = 0

    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        timestamps: list[float] = []
        remaining = raw_line

        while True:
            match = LRC_TIMESTAMP_PATTERN.match(remaining)
            if not match:
                break
            timestamps.append(parse_lrc_timestamp(match))
            remaining = remaining[match.end():]

        content = remaining.strip()
        if not timestamps:
            continue

        for ts in timestamps:
            if is_metadata_line(content, ts):
                continue
            line_counter += 1
            entry: dict[str, Any] = {
                "line_id": f"line_{line_counter:02d}",
                "start_time": round3(ts),
                "text": content,
            }
            if content:
                entry["is_instrumental"] = False
            else:
                entry["is_instrumental"] = True
                entry["text"] = ""
            lines.append(entry)

    lines.sort(key=lambda item: item["start_time"])

    lines = _merge_bilingual_lines(lines)

    for i in range(len(lines) - 1):
        lines[i]["end_time"] = round3(lines[i + 1]["start_time"])
        lines[i]["duration_seconds"] = round3(
            lines[i]["end_time"] - lines[i]["start_time"]
        )

    if lines:
        last = lines[-1]
        if "end_time" not in last:
            last["end_time"] = None
            last["duration_seconds"] = None

    return lines


def _merge_bilingual_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge consecutive lines that share the same timestamp.

    Bilingual LRC files put the original and translation on the same
    timestamp.  We keep the first line as primary and attach the second
    as ``translation``, so downstream section inference sees one entry
    per musical moment instead of two.
    """
    if not lines:
        return lines
    merged: list[dict[str, Any]] = []
    i = 0
    line_counter = 0
    while i < len(lines):
        group = [lines[i]]
        j = i + 1
        while j < len(lines) and lines[j]["start_time"] == lines[i]["start_time"]:
            group.append(lines[j])
            j += 1

        primary = group[0]
        line_counter += 1
        primary["line_id"] = f"line_{line_counter:02d}"

        if len(group) > 1:
            translations = [g["text"] for g in group[1:] if g["text"]]
            if translations:
                primary["translation"] = " / ".join(translations)

        merged.append(primary)
        i = j
    return merged


def parse_plain_text(text: str) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    line_counter = 0

    for raw_line in text.splitlines():
        content = raw_line.strip()
        if not content:
            continue

        line_counter += 1
        lines.append({
            "line_id": f"line_{line_counter:02d}",
            "text": content,
            "start_time": None,
            "end_time": None,
            "duration_seconds": None,
            "is_instrumental": False,
        })

    return lines


def detect_format(text: str) -> str:
    lrc_count = len(LRC_TIMESTAMP_PATTERN.findall(text))
    non_empty_lines = sum(1 for line in text.splitlines() if line.strip())
    if non_empty_lines > 0 and lrc_count / max(non_empty_lines, 1) > 0.3:
        return "lrc"
    return "plain_text"


def infer_sections_from_lyrics(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attempt to detect repeated patterns to infer verse/chorus structure."""
    if not lines:
        return []

    text_lines = [line["text"] for line in lines if line["text"]]
    if len(text_lines) < 4:
        return [{
            "section_id": "full_song",
            "section_type": "verse",
            "line_refs": [line["line_id"] for line in lines],
            "start_time": lines[0].get("start_time"),
            "end_time": lines[-1].get("end_time"),
        }]

    text_counts: dict[str, int] = {}
    for t in text_lines:
        normalized = t.strip().lower()
        text_counts[normalized] = text_counts.get(normalized, 0) + 1

    repeated_lines = {t for t, count in text_counts.items() if count >= 2}

    sections: list[dict[str, Any]] = []
    current_lines: list[dict[str, Any]] = []
    current_type = "verse"
    section_counter = 0
    verse_counter = 0
    chorus_counter = 0

    for line in lines:
        normalized = line["text"].strip().lower()
        is_chorus_line = normalized in repeated_lines and len(normalized) > 5

        if current_lines and is_chorus_line != (current_type == "chorus"):
            section_counter += 1
            if current_type == "verse":
                verse_counter += 1
                label = f"verse_{verse_counter}"
            else:
                chorus_counter += 1
                label = f"chorus_{chorus_counter}"

            sections.append({
                "section_id": label,
                "section_type": current_type,
                "line_refs": [cl["line_id"] for cl in current_lines],
                "start_time": current_lines[0].get("start_time"),
                "end_time": current_lines[-1].get("end_time"),
            })
            current_lines = []

        current_type = "chorus" if is_chorus_line else "verse"
        current_lines.append(line)

    if current_lines:
        if current_type == "verse":
            verse_counter += 1
            label = f"verse_{verse_counter}"
        else:
            chorus_counter += 1
            label = f"chorus_{chorus_counter}"
        sections.append({
            "section_id": label,
            "section_type": current_type,
            "line_refs": [cl["line_id"] for cl in current_lines],
            "start_time": current_lines[0].get("start_time"),
            "end_time": current_lines[-1].get("end_time"),
        })

    return sections


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse LRC or plain-text lyrics into structured JSON"
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to lyrics file (.lrc or .txt)"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output path for parsed lyrics JSON"
    )
    parser.add_argument(
        "--format", choices=["lrc", "plain_text", "auto"], default="auto",
        help="Input format (default: auto-detect)"
    )
    parser.add_argument(
        "--infer-sections", action="store_true",
        help="Attempt to infer song sections from lyric repetition patterns"
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    text = input_path.read_text(encoding="utf-8")

    fmt = args.format
    if fmt == "auto":
        fmt = detect_format(text)

    if fmt == "lrc":
        lines = parse_lrc(text)
    else:
        lines = parse_plain_text(text)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "source_file": str(input_path.name),
        "detected_format": fmt,
        "total_lines": len(lines),
        "has_timestamps": fmt == "lrc",
        "lines": lines,
    }

    if args.infer_sections:
        payload["inferred_sections"] = infer_sections_from_lyrics(lines)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
