#!/usr/bin/env python3
"""Call Qwen3 to segment lyrics-timing JSON into sections (verse / chorus / …).

Expects JSON from parse_lyrics.py (`schema_version` 1.1). Validates a fixed reply
shape; `--merged-parsed` is optional (legacy tooling) and **not** part of the
mv-production SKILL Stage 1 path.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_MV_SCRIPTS = Path(__file__).resolve().parent
_AIGC_ROOT = _MV_SCRIPTS.parents[2]
_QWEN_DIR = _AIGC_ROOT / "generation" / "qwen3-chat-gitee"
if str(_QWEN_DIR) not in sys.path:
    sys.path.insert(0, str(_QWEN_DIR))

from client import (  # noqa: E402
    extract_assistant_text,
    load_aigc_dotenv,
    post_messages,
)

VALID_SECTION_TYPES = frozenset({
    "intro", "verse", "pre_chorus", "chorus", "post_chorus",
    "bridge", "breakdown", "instrumental", "outro", "interlude",
})

SYSTEM_PROMPT = """你是音乐分析专家。你收到一份歌词 timing JSON（逐行 lyrics-timing），需要将整首歌划分为若干段落 section。

对 **每个 section**，你必须回答以下 5 个问题：

1) 时间范围：从哪句开始、到哪句结束（给出 line_refs[]，脚本会自动注入精确 start_time / end_time / duration_seconds）。
2) 在全曲中起什么作用：这一段对整首歌结构有何贡献（开场、情绪堆叠、高潮释放、过渡、收束……）。
3) 核心情绪：这一段的核心情绪或表达的是什么（用中文描述氛围、情感温度、心理状态）。
4) 视觉 segment 划分：这一段应该切成几个视觉 segment？每个 visual segment 的 line_refs、起始时间（秒）、歌词内容文本。注意：visual segment 是对该 section 内部的进一步细分，用于指导后续导演确定 keyframe 数量。每个 section 至少 1 个 visual segment。
5) 与重复段落之间的变奏关系：如果这首歌有重复的段落（如 verse_1 和 verse_2、chorus_1 和 chorus_2），你这段的 counterpart 是谁？在情绪、思想、视角上有何不同？唯一出现的段落（intro / outro / bridge）填 related_section: null。

硬性规则：
- 只输出「一个合法 JSON 对象」，不要 Markdown、不要前后说明文字。
- schema_version 必须为 "2.0"。
- section_id 使用 snake_case，不得重复。
- 将所有 section 的 line_refs 串联后，必须与输入歌词的 line_id 顺序完全一致，每条 line_id 恰好出现一次，包括 is_instrumental=true 的空行。
- 每个 visual_segments 的 start_time / end_time 从该 segment 对应的第一句和最后一句歌词的时间码中提取。可以查看输入中的 start_time 字段。

JSON 输出格式（必须严格遵守；所有 section 必须包含这些字段）：
{
  "schema_version": "2.0",
  "sections": [
    {
      "section_id": "verse_1",
      "section_type": "verse",
      "line_refs": ["line_01", "line_02"],
      "time_range": {
        "start_time": 0.0,
        "end_time": 25.0,
        "duration_seconds": 25.0
      },
      "role_in_song_zh": "开场主歌，建立…的基调，引入…",
      "core_emotion_zh": "沉静、朦胧、…",
      "visual_segments": [
        {
          "segment_id": "seg_v1_01",
          "start_time": 0.0,
          "end_time": 12.0,
          "line_refs": ["line_01"],
          "lyrics_text": "歌词第一句 / 歌词第二句"
        }
      ],
      "variation": {
        "related_section": "verse_2",
        "relationship_zh": "verse_1 是初次进入的朦胧感，verse_2 是经历离别后的回望与宿命感"
      }
    }
  ]
}
"""


def load_timing(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    ver = data.get("schema_version")
    if ver not in ("1.0", "1.1"):
        raise SystemExit(
            "Unsupported lyrics JSON schema_version "
            f"(expected 1.0 or 1.1, got {ver!r}); re-run parse_lyrics.py"
        )
    if "lines" not in data or not isinstance(data["lines"], list):
        raise SystemExit("Missing or invalid 'lines' array")
    return data


def slim_lines_for_prompt(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ln in lines:
        item = {
            "line_id": ln["line_id"],
            "text": ln.get("text") or "",
        }
        for key in ("start_time", "end_time", "duration_seconds", "is_instrumental", "translation"):
            if key in ln and ln[key] is not None:
                item[key] = ln[key]
        out.append(item)
    return out


def unwrap_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        stripped = []
        lines = text.splitlines()
        for i, row in enumerate(lines):
            if i == 0 and row.strip().startswith("```"):
                continue
            if row.strip() == "```":
                break
            stripped.append(row)
        text = "\n".join(stripped).strip()
    return text


def parse_model_json(raw_text: str) -> dict[str, Any]:
    text = unwrap_json_fence(raw_text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Assistant did not return valid JSON: {e}\n{text[:1200]}") from e


def validate_sections_structure(data: dict[str, Any]) -> list[dict[str, Any]]:
    top_keys = set(data.keys())
    if top_keys != {"schema_version", "sections"}:
        extras = top_keys - {"schema_version", "sections"}
        missing = {"schema_version", "sections"} - top_keys
        raise SystemExit(f"Unexpected top-level keys; extra={extras!r} missing={missing!r}")
    if data.get("schema_version") != "2.0":
        raise SystemExit('Reply schema_version must be "2.0".')
    secs = data.get("sections")
    if not isinstance(secs, list) or not secs:
        raise SystemExit("'sections' must be a non-empty array.")
    ids: list[str] = []
    allowed_section_keys = {
        "section_id", "section_type", "line_refs",
        "time_range", "role_in_song_zh", "core_emotion_zh",
        "visual_segments", "variation",
    }
    req_section_keys = {
        "section_id", "section_type", "line_refs",
        "time_range", "role_in_song_zh", "core_emotion_zh",
        "visual_segments", "variation",
    }
    for i, sec in enumerate(secs):
        if not isinstance(sec, dict):
            raise SystemExit(f"sections[{i}] is not an object.")
        keys = set(sec.keys())
        if not keys.issubset(allowed_section_keys):
            raise SystemExit(f"sections[{i}] has forbidden keys: {keys - allowed_section_keys!r}")
        missing = req_section_keys - keys
        if missing:
            raise SystemExit(f"sections[{i}] missing required keys: {sorted(missing)!r}")
        sid = sec["section_id"]
        st = sec["section_type"]
        refs = sec["line_refs"]
        if not isinstance(sid, str) or not re.match(r"^[a-z][a-z0-9_]*$", sid):
            raise SystemExit(f"Invalid section_id at index {i}: {sid!r}")
        if st not in VALID_SECTION_TYPES:
            raise SystemExit(f"Invalid section_type at {sid!r}: {st!r}")
        if not isinstance(refs, list) or not all(isinstance(x, str) for x in refs):
            raise SystemExit(f"line_refs must be string array at {sid!r}")
        # Validate time_range
        tr = sec["time_range"]
        if not isinstance(tr, dict):
            raise SystemExit(f"time_range must be object at {sid!r}")
        for fld in ("start_time", "end_time", "duration_seconds"):
            if not isinstance(tr.get(fld), (int, float)):
                raise SystemExit(f"time_range.{fld} must be number at {sid!r}")
        # Validate role_in_song_zh
        for fld in ("role_in_song_zh", "core_emotion_zh"):
            val = sec.get(fld)
            if not isinstance(val, str) or len(val.strip()) < 4:
                raise SystemExit(f"{fld} too short at {sid!r}")
        # Validate visual_segments
        vs = sec["visual_segments"]
        if not isinstance(vs, list) or len(vs) < 1:
            raise SystemExit(f"visual_segments must be non-empty array at {sid!r}")
        for j, seg in enumerate(vs):
            if not isinstance(seg, dict):
                raise SystemExit(f"visual_segments[{j}] not an object at {sid!r}")
            for fld in ("segment_id", "line_refs", "lyrics_text"):
                if fld not in seg:
                    raise SystemExit(f"visual_segments[{j}] missing {fld} at {sid!r}")
            if not isinstance(seg.get("start_time"), (int, float)):
                raise SystemExit(f"visual_segments[{j}].start_time must be number at {sid!r}")
            if not isinstance(seg.get("end_time"), (int, float)):
                raise SystemExit(f"visual_segments[{j}].end_time must be number at {sid!r}")
        # Validate variation
        var = sec["variation"]
        if not isinstance(var, dict):
            raise SystemExit(f"variation must be object at {sid!r}")
        if "related_section" not in var or "relationship_zh" not in var:
            raise SystemExit(f"variation missing related_section or relationship_zh at {sid!r}")
        if not isinstance(var.get("relationship_zh"), str) or len(str(var["relationship_zh"]).strip()) < 2:
            raise SystemExit(f"variation.relationship_zh too short (min 2 chars) at {sid!r}")
        ids.append(sid)
    if len(ids) != len(set(ids)):
        raise SystemExit("Duplicate section_id in model reply.")
    return secs


def validate_line_coverage(
    lines: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> None:
    expected = [ln["line_id"] for ln in lines]
    got: list[str] = []
    for sec in sections:
        got.extend(sec["line_refs"])
    if got != expected:
        raise SystemExit(
            "line_refs do not match input line order / count.\n"
            f"expected ({len(expected)}): {expected}\n"
            f"got      ({len(got)}): {got}"
        )


def merge_inferred_sections(
    lines: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {ln["line_id"]: ln for ln in lines}
    inferred: list[dict[str, Any]] = []
    for sec in sections:
        refs = sec["line_refs"]
        first = by_id[refs[0]]
        last = by_id[refs[-1]]
        inferred.append({
            "section_id": sec["section_id"],
            "section_type": sec["section_type"],
            "line_refs": list(refs),
            "start_time": first.get("start_time"),
            "end_time": last.get("end_time"),
        })
    return inferred


def inject_timing(
    lines: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> None:
    """Inject accurate time_range from lyrics-timing.json into each section and visual_segment."""
    by_id = {ln["line_id"]: ln for ln in lines}
    for sec in sections:
        refs = sec["line_refs"]
        first_ln = by_id[refs[0]]
        last_ln = by_id[refs[-1]]
        start = first_ln.get("start_time")
        end = last_ln.get("end_time")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            dur = round(float(end) - float(start), 3)
        else:
            dur = 0.0
        sec["time_range"] = {
            "start_time": float(start) if isinstance(start, (int, float)) else 0.0,
            "end_time": float(end) if isinstance(end, (int, float)) else 0.0,
            "duration_seconds": dur,
        }
        # Also inject accurate timing into visual_segments
        for seg in sec.get("visual_segments", []):
            seg_refs = seg.get("line_refs", [])
            if not seg_refs:
                continue
            seg_first = by_id.get(seg_refs[0])
            seg_last = by_id.get(seg_refs[-1])
            if seg_first and seg_last:
                s_st = seg_first.get("start_time")
                s_et = seg_last.get("end_time")
                if isinstance(s_st, (int, float)):
                    seg["start_time"] = float(s_st)
                if isinstance(s_et, (int, float)):
                    seg["end_time"] = float(s_et)


def main() -> None:
    load_aigc_dotenv()
    if not os.getenv("AIGC_GITEE_API_KEY") and os.getenv("GITEE_API_TOKEN"):
        os.environ["AIGC_GITEE_API_KEY"] = os.getenv("GITEE_API_TOKEN", "")

    import config as qwen_cfg  # noqa: E402

    ap = argparse.ArgumentParser(
        description="Qwen3 lyric structure from lyrics-timing JSON"
    )
    ap.add_argument(
        "--lyrics-timing", required=True, type=Path,
        help="JSON from parse_lyrics.py",
    )
    ap.add_argument(
        "--out", required=True, type=Path,
        help="Write validated model JSON (schema song-sections-llm 1.0)",
    )
    ap.add_argument(
        "--merged-parsed", type=Path, default=None,
        help="Optional: timing JSON + inferred_sections + section_analysis_source",
    )
    ap.add_argument(
        "--temperature", type=float, default=0.2,
        help="Sampling temperature (default 0.2 for stable structure)",
    )
    ap.add_argument(
        "--max-tokens", type=int, default=16384,
        help="max_tokens for the chat request",
    )
    ap.add_argument(
        "--timeout", type=int, default=300,
        help="HTTP timeout seconds",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print user payload only, do not call API",
    )
    args = ap.parse_args()

    timing_path = args.lyrics_timing.resolve()
    timing = load_timing(timing_path)
    lines = timing["lines"]
    if not lines:
        raise SystemExit("No lines in lyrics JSON.")

    user_blob = {
        "task": "segment_song_structure",
        "lyrics_timing": {
            "source_file": timing.get("source_file"),
            "detected_format": timing.get("detected_format"),
            "lines": slim_lines_for_prompt(lines),
        },
    }
    user_text = (
        "输入如下。请严格按系统说明只输出 JSON。\n"
        + json.dumps(user_blob, ensure_ascii=False)
    )

    payload = {
        "model": qwen_cfg.DEFAULT_MODEL,
        "stream": False,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "enable_thinking": False,
        "top_p": 0.9,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
    }

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if not qwen_cfg.API_KEY:
        raise SystemExit(
            "Missing AIGC_GITEE_API_KEY (or GITEE_API_TOKEN). Set in env or aigc/.env"
        )

    response = post_messages(
        qwen_cfg.API_URL, qwen_cfg.API_KEY, payload, timeout=args.timeout
    )
    assistant_text = extract_assistant_text(response)
    model_obj = parse_model_json(assistant_text)
    secs = validate_sections_structure(model_obj)
    validate_line_coverage(lines, secs)
    inject_timing(lines, secs)

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(model_obj, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.merged_parsed:
        merged = dict(timing)
        merged["inferred_sections"] = merge_inferred_sections(lines, secs)
        merged["section_analysis_source"] = "qwen3"
        mp = args.merged_parsed.resolve()
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
