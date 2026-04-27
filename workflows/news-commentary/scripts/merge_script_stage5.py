#!/usr/bin/env python3
"""Merge Stage 5 skeleton + segment drafts into final script.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def ensure_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def ensure_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON array")
    return value


def build_skeleton_lookup(skeleton: dict[str, Any]) -> dict[int, dict[str, Any]]:
    mapping: dict[int, dict[str, Any]] = {}
    for raw_segment in ensure_list(skeleton.get("segments", []), "skeleton.segments"):
        segment = ensure_object(raw_segment, "skeleton segment")
        segment_no = int(segment.get("segment_no"))
        if segment_no in mapping:
            raise ValueError(f"Duplicate segment_no {segment_no} in script-skeleton.json")
        mapping[segment_no] = segment
    if not mapping:
        raise ValueError("script-skeleton.json must contain at least one segment")
    return mapping


def load_segment_drafts(segments_dir: Path) -> dict[int, dict[str, Any]]:
    if not segments_dir.exists() or not segments_dir.is_dir():
        raise ValueError(f"Segment directory does not exist: {segments_dir}")

    mapping: dict[int, dict[str, Any]] = {}
    for path in sorted(segments_dir.glob("*.json")):
        segment = ensure_object(load_json(path), f"segment draft {path.name}")
        segment_no = int(segment.get("segment_no"))
        if segment_no in mapping:
            raise ValueError(f"Duplicate segment_no {segment_no} across segment drafts")
        mapping[segment_no] = segment

    if not mapping:
        raise ValueError(f"No segment draft JSON files found in: {segments_dir}")
    return mapping


def preferred_value(primary: dict[str, Any], fallback: dict[str, Any], key: str) -> Any:
    value = primary.get(key)
    if value is None:
        return fallback.get(key)
    if isinstance(value, str) and not normalize_text(value):
        return fallback.get(key)
    if isinstance(value, list) and len(value) == 0:
        return fallback.get(key)
    return value


def build_line_id(segment_no: int, line_no: int) -> str:
    return f"seg{segment_no:02d}_line{line_no:02d}"


def merge_lines(segment_no: int, raw_lines: Any) -> list[dict[str, Any]]:
    lines = ensure_list(raw_lines, f"segment {segment_no} lines")
    if not lines:
        raise ValueError(f"Segment {segment_no} must contain at least one line")

    merged_lines: list[dict[str, Any]] = []
    seen_line_ids: set[str] = set()

    for index, raw_line in enumerate(lines, start=1):
        line = ensure_object(raw_line, f"segment {segment_no} line")
        line_no = int(line.get("line_no") or index)
        speaker = normalize_text(line.get("speaker"))
        text = normalize_text(line.get("text"))

        if speaker not in {"host", "guest"}:
            raise ValueError(f"Segment {segment_no} line {line_no} has invalid speaker: {speaker!r}")
        if not text:
            raise ValueError(f"Segment {segment_no} line {line_no} must have non-empty text")

        line_id = normalize_text(line.get("line_id")) or build_line_id(segment_no, line_no)
        if line_id in seen_line_ids:
            raise ValueError(f"Duplicate line_id {line_id!r} in segment {segment_no}")
        seen_line_ids.add(line_id)

        merged_line: dict[str, Any] = {
            "line_id": line_id,
            "line_no": line_no,
            "speaker": speaker,
            "text": text,
        }

        if line.get("estimated_duration_seconds") is not None:
            merged_line["estimated_duration_seconds"] = float(line["estimated_duration_seconds"])
        if normalize_text(line.get("split_group_id")):
            merged_line["split_group_id"] = normalize_text(line["split_group_id"])
        if normalize_text(line.get("emotion")):
            merged_line["emotion"] = normalize_text(line["emotion"])
        if line.get("pause_before") is not None:
            merged_line["pause_before"] = float(line["pause_before"])
        if line.get("pause_after") is not None:
            merged_line["pause_after"] = float(line["pause_after"])

        merged_lines.append(merged_line)

    merged_lines.sort(key=lambda item: int(item["line_no"]))
    return merged_lines


def merge_segment(skeleton_segment: dict[str, Any], drafted_segment: dict[str, Any]) -> dict[str, Any]:
    segment_no = int(skeleton_segment["segment_no"])
    drafted_segment_no = int(drafted_segment.get("segment_no"))
    if drafted_segment_no != segment_no:
        raise ValueError(f"Segment draft mismatch: skeleton has {segment_no}, draft has {drafted_segment_no}")

    skeleton_type = normalize_text(skeleton_segment.get("type"))
    drafted_type = normalize_text(drafted_segment.get("type"))
    if drafted_type and drafted_type != skeleton_type:
        raise ValueError(f"Segment {segment_no} type mismatch: skeleton={skeleton_type}, draft={drafted_type}")

    merged_segment: dict[str, Any] = {
        "segment_no": segment_no,
        "type": skeleton_type,
        "segment_goal": preferred_value(drafted_segment, skeleton_segment, "segment_goal"),
        "takeaway": preferred_value(drafted_segment, skeleton_segment, "takeaway"),
        "source_refs": preferred_value(drafted_segment, skeleton_segment, "source_refs") or [],
        "visual_hint": preferred_value(drafted_segment, skeleton_segment, "visual_hint"),
        "lines": merge_lines(segment_no, drafted_segment.get("lines", [])),
    }

    for optional_key in [
        "duration",
        "scripting_rules",
        "repetition_risk",
        "key_point_id",
        "fact_layer",
        "explanation_layer",
        "meaning_layer",
        "source_ref",
        "ltx2_prompt",
    ]:
        value = drafted_segment.get(optional_key)
        if value is not None:
            merged_segment[optional_key] = value

    return merged_segment


def merge_script(skeleton: dict[str, Any], segment_drafts: dict[int, dict[str, Any]]) -> dict[str, Any]:
    skeleton_lookup = build_skeleton_lookup(skeleton)

    missing_segments = sorted(set(skeleton_lookup) - set(segment_drafts))
    extra_segments = sorted(set(segment_drafts) - set(skeleton_lookup))
    if missing_segments:
        raise ValueError(f"Missing segment drafts for segment_no: {missing_segments}")
    if extra_segments:
        raise ValueError(f"Found segment drafts not declared in skeleton: {extra_segments}")

    payload: dict[str, Any] = {
        "title": skeleton.get("title"),
        "duration_estimate": skeleton.get("duration_estimate"),
        "series_mode": skeleton.get("series_mode"),
        "anchors": skeleton.get("anchors", {}),
        "segments": [],
    }

    for segment_no in sorted(skeleton_lookup):
        payload["segments"].append(merge_segment(skeleton_lookup[segment_no], segment_drafts[segment_no]))

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge Stage 5 script skeleton and segment drafts into final script.json")
    parser.add_argument("--skeleton", required=True, help="Path to script-skeleton.json")
    parser.add_argument("--segments-dir", required=True, help="Directory containing script-segments/*.json")
    parser.add_argument("--output", required=True, help="Output path for final script.json")
    args = parser.parse_args()

    skeleton_path = Path(args.skeleton).resolve()
    segments_dir = Path(args.segments_dir).resolve()
    output_path = Path(args.output).resolve()

    skeleton = ensure_object(load_json(skeleton_path), "script-skeleton.json")
    segment_drafts = load_segment_drafts(segments_dir)
    script_payload = merge_script(skeleton, segment_drafts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{json.dumps(script_payload, ensure_ascii=False, indent=2)}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
