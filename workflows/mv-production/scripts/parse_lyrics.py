#!/usr/bin/env python3
"""Parse LRC or plain-text lyrics into timing JSON only (timestamps per line).

Output is intentionally limited to line-level timestamps and durations; song
sections (verse/chorus/etc.) belong in a separate Qwen step (infer_sections_qwen3).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from media_duration import probe_audio_duration_seconds


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
    # Only filter if the line is very short and matches metadata patterns
    if len(stripped) > 30:
        return False
    if METADATA_PATTERNS.search(stripped):
        return True
    # Artist - Title (parenthetical info) at t=0:00 is usually metadata
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


def split_lrc_body_and_preamble(text: str) -> tuple[list[dict[str, Any]], str]:
    """Leading JSON preamble lines (ignored in output); then `[mm:ss.xxx]` body."""
    raw_lines = text.splitlines()
    preamble: list[dict[str, Any]] = []
    i = 0
    while i < len(raw_lines):
        stripped = raw_lines[i].strip()
        if not stripped:
            i += 1
            continue
        entry = _parse_enriched_lrc_json_line(stripped)
        if entry is None:
            break
        preamble.append(entry)
        i += 1
    body = "\n".join(raw_lines[i:])
    return preamble, body


def _parse_enriched_lrc_json_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped.startswith("{"):
        return None
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    chunks = data.get("c")
    if not isinstance(chunks, list):
        return None
    texts: list[str] = []
    for item in chunks:
        if isinstance(item, dict) and "tx" in item:
            texts.append(str(item["tx"]))
        elif isinstance(item, str):
            texts.append(item)
    if not texts:
        return None
    t_raw = data.get("t")
    offset_ms: int | None
    if isinstance(t_raw, (int, float)):
        offset_ms = int(t_raw)
    else:
        offset_ms = None
    return {"offset_ms": offset_ms, "text": "".join(texts)}


def _parse_lrc_timed_lines(text: str) -> list[dict[str, Any]]:
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
            # Will be filled later if --audio provides audio_duration_seconds
            last["end_time"] = None
            last["duration_seconds"] = None

    return lines


def parse_lrc(text: str) -> list[dict[str, Any]]:
    """Parse LRC body; preamble (credits) is skipped and not written to output."""
    _preamble, body = split_lrc_body_and_preamble(text)
    return _parse_lrc_timed_lines(body)


def _merge_bilingual_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge same-timestamp bilingual lines into one logical line."""

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


def parse_plain_text(text: str, audio_duration: float | None = None) -> list[dict[str, Any]]:
    if not text.strip():
        return []
    lines: list[dict[str, Any]] = []
    line_counter = 0
    # Distribute duration evenly across lines if audio duration known
    duration_per_line = None
    if audio_duration:
        non_empty = sum(1 for raw_line in text.splitlines() if raw_line.strip())
        if non_empty:
            duration_per_line = audio_duration / non_empty

    for raw_line in text.splitlines():
        content = raw_line.strip()
        if not content:
            continue

        line_counter += 1
        start_time = round((line_counter - 1) * duration_per_line, 3) if duration_per_line else 0.0
        end_time = round(line_counter * duration_per_line, 3) if duration_per_line else None
        lines.append({
            "line_id": f"line_{line_counter:02d}",
            "text": content,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": round(end_time - start_time, 3) if (end_time is not None and duration_per_line) else None,
            "is_instrumental": False,
        })

    return lines


def detect_format(text: str) -> str:
    lrc_count = len(LRC_TIMESTAMP_PATTERN.findall(text))
    non_empty_lines = sum(1 for line in text.splitlines() if line.strip())
    if non_empty_lines > 0 and lrc_count / max(non_empty_lines, 1) > 0.3:
        return "lrc"
    return "plain_text"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse LRC/plain lyrics to JSON (line timings only)"
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to lyrics file (.lrc or .txt)"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output path for lyrics-timing JSON"
    )
    parser.add_argument(
        "--format", choices=["lrc", "plain_text", "auto"], default="auto",
        help="Input format (default: auto-detect)"
    )
    parser.add_argument(
        "--audio",
        default=None,
        help="Optional audio file; duration is stored as audio_duration_seconds for timeline length",
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
        "schema_version": "1.1",
        "source_file": str(input_path.name),
        "detected_format": fmt,
        "total_lines": len(lines),
        "has_timestamps": fmt == "lrc",
        "lines": lines,
    }

    if args.audio:
        probed = probe_audio_duration_seconds(Path(args.audio))
        if probed is not None:
            payload["audio_duration_seconds"] = probed
            # For plain text, re-parse with known duration to assign timestamps
            if fmt == "plain_text":
                lines = parse_plain_text(text, probed)
                payload["total_lines"] = len(lines)
                payload["lines"] = lines
                payload["has_timestamps"] = True
            # Fill last line's end_time from audio duration
            if payload.get("lines") and payload["lines"][-1].get("end_time") is None:
                last = payload["lines"][-1]
                last["end_time"] = round3(probed)
                last["duration_seconds"] = round3(probed - last["start_time"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
