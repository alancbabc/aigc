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

SYSTEM_PROMPT = """你是一个音乐制作人助理。你只根据用户给出的歌词 timing JSON，
划分歌曲结构段落。必须输出「仅一个合法 JSON 对象」，不要 Markdown、不要前后说明文字。
JSON schema:
{
  "schema_version": "1.0",
  "sections": [
    {
      "section_id": "唯一小写下划线英文名，如 verse_1",
      "section_type": "必须是 intro|verse|pre_chorus|chorus|post_chorus|bridge|breakdown|instrumental|outro|interlude 之一",
      "line_refs": ["line_01", "line_02"],
      "notes": "可选，一句话说明你为何如此划分（中文亦可）"
    }
  ]
}
硬性规则：
1) 每一段 line_refs 非空。
2) 将所有 line_refs 串联后，必须与输入 JSON 里的 lines 按顺序一一对应，每条 line_id 恰好出现一次，顺序与歌词先后一致。
3) section_id 在同一个 JSON 内不得重复。
4) 不要使用 schema 以外的顶层键或段落键。
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
    if set(data.keys()) != {"schema_version", "sections"}:
        extras = set(data.keys()) - {"schema_version", "sections"}
        missing = {"schema_version", "sections"} - set(data.keys())
        raise SystemExit(f"Unexpected top-level keys; extra={extras!r} missing={missing!r}")
    if data.get("schema_version") != "1.0":
        raise SystemExit("Reply schema_version must be \"1.0\".")
    secs = data.get("sections")
    if not isinstance(secs, list) or not secs:
        raise SystemExit("'sections' must be a non-empty array.")
    ids: list[str] = []
    for i, sec in enumerate(secs):
        if not isinstance(sec, dict):
            raise SystemExit(f"sections[{i}] is not an object.")
        keys = set(sec.keys())
        allowed = {"section_id", "section_type", "line_refs", "notes"}
        if not keys.issubset(allowed):
            raise SystemExit(f"sections[{i}] has forbidden keys: {keys - allowed!r}")
        for req in ("section_id", "section_type", "line_refs"):
            if req not in sec:
                raise SystemExit(f"sections[{i}] missing {req}.")
        sid = sec["section_id"]
        st = sec["section_type"]
        refs = sec["line_refs"]
        if not isinstance(sid, str) or not re.match(r"^[a-z][a-z0-9_]*$", sid):
            raise SystemExit(f"Invalid section_id at index {i}: {sid!r}")
        if st not in VALID_SECTION_TYPES:
            raise SystemExit(f"Invalid section_type at {sid!r}: {st!r}")
        if not isinstance(refs, list) or not all(isinstance(x, str) for x in refs):
            raise SystemExit(f"line_refs must be string array at {sid!r}")
        if "notes" in sec and sec["notes"] is not None and not isinstance(sec["notes"], str):
            raise SystemExit(f"notes must be string or absent at {sid!r}")
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
        "--max-tokens", type=int, default=8192,
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
