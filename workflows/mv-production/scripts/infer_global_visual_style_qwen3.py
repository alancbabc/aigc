#!/usr/bin/env python3
"""Stage 2: call Qwen3 with lyrics-timing lines + song section context → mv-global-visual-style.json.

Line-level lyrics always come from **`lyrics-timing.json`** (`parse_lyrics.py`). Section context is either:

- **`song-structure.json`** (legacy), or
- **`song-sections-llm.json`** paired with the same **`lyrics-timing.json`** (workflow default — no merged file).

Validates the assistant reply against
``contracts/mv-global-visual-style/mv-global-visual-style.schema.json`` (conceptually).

Requires Gitee Qwen3 (same env as infer_sections_qwen3.py).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
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

ALLOWED_TOP_KEYS = frozenset({
    "schema_version",
    "song_title",
    "artist",
    "parsed_lyrics_ref",
    "song_structure_ref",
    "global_style_suffix",
    "global_style_suffix_zh",
    "structural_visual_rules",
    "core_visual_motifs",
    "animation_art_style_en",
    "color_palette_en",
    "lighting_mood_en",
    "texture_material_en",
    "motion_camera_en",
    "negative_style_hints_en",
    "art_direction_summary_zh",
})

REQUIRED_KEYS = frozenset({
    "schema_version",
    "song_title",
    "parsed_lyrics_ref",
    "song_structure_ref",
    "global_style_suffix",
    "structural_visual_rules",
    "core_visual_motifs",
    "animation_art_style_en",
    "color_palette_en",
    "lighting_mood_en",
    "texture_material_en",
    "motion_camera_en",
    "negative_style_hints_en",
    "art_direction_summary_zh",
})

VALID_SECTION_ROLE = frozenset({
    "intro", "verse", "pre_chorus", "chorus", "post_chorus", "bridge",
    "breakdown", "instrumental", "outro", "interlude", "other",
})

STRUCT_RULE_KEYS = frozenset({
    "section_roles",
    "visual_tension_en",
    "visual_tension_zh",
    "camera_framing_en",
    "cut_motion_tempo_en",
    "contrast_vs_other_sections_en",
    # optional enrichment fields (added by Qwen3 or post-processing)
    "shot_ratio",
    "lens_emotion_en",
    "color_temperature",
})

MOTIF_KEYS = frozenset({
    "motif_id",
    "name_en",
    "name_zh",
    "kind",
    "recurrence",
    "prompt_anchor_en",
    "motif_notes_zh",
    "lyrics_line_refs",
    "meaning_evolution",
})

MOTIF_KIND = frozenset({"entity", "environment", "symbol", "prop", "figure"})
MOTIF_RECURRENCE = frozenset({
    "persistent",
    "verse_emphasis",
    "chorus_emphasis",
    "bridge_shift",
    "bookend_only",
    "through_hook_refrain",
})

MOTIF_KIND_ALIASES = {
    "location": "environment",
    "scene": "environment",
    "landscape": "environment",
    "setting": "environment",
    "world": "environment",
    "character": "figure",
    "person": "figure",
    "human": "figure",
    "people": "figure",
    "portrait": "figure",
    "object": "prop",
    "item": "prop",
    "metaphor": "symbol",
    "concept": "symbol",
}

SYSTEM_PROMPT = """你是音乐 MV 的美术指导（Art Director）。用户会提供两份 JSON：
（1）歌词时间轴（逐行文本与时间，来自 parse_lyrics 的 lyrics-timing）；
（2）歌曲结构（分段、能量、情绪与每段的视觉建议摘要）。

你的任务：综合歌词内容与音乐结构，为整首 MV 锁定统一的画面视觉基调，并输出两类「可执行」约束：
A) structural_visual_rules：按段落角色（至少区分 Verse 与 Chorus；若歌曲结构里存在 bridge / pre_chorus 等也可增加条目）定义画面张力、景别剪辑节奏与相互对比策略；
B) core_visual_motifs：从歌词中抽取 3–10 个必须在时间线上反复出现的核心实体/环境/符号，并给出英文 prompt_anchor_en 作为一致性锚点。

硬性输出规则：
1) 只输出「一个合法 JSON 对象」，不要使用 Markdown 代码块，不要输出任何前后说明文字。
2) 键名与层级必须严格符合下列 schema；不得增加额外顶层键；可选键仅有 artist、global_style_suffix_zh、以及 motif 内的 lyrics_line_refs。
3) schema_version 必须为字符串 \"1.1\"。
4) structural_visual_rules：2–8 条；每条包含 section_roles（数组，取值限定为 intro|verse|pre_chorus|chorus|post_chorus|bridge|breakdown|instrumental|outro|interlude|other）。必须覆盖输入歌曲结构中出现的 verse 与 chorus（若结构中确实存在这些 section_type）；二者在 visual_tension_* / camera_framing_en / cut_motion_tempo_en / contrast_vs_other_sections_en 上要有清晰对立（例如主歌克制凝视 vs 副歌抬升爆发）。
5) core_visual_motifs：3–10 条；motif_id 为小写下划线英文；kind 限定 entity|environment|symbol|prop|figure；recurrence 限定 persistent|verse_emphasis|chorus_emphasis|bridge_shift|bookend_only|through_hook_refrain；每条给出英文 prompt_anchor_en 与中文 motif_notes_zh（解释为何不可省略）。
6) global_style_suffix、animation_art_style_en、color_palette_en、lighting_mood_en、texture_material_en、motion_camera_en、negative_style_hints_en 的内容条目必须使用英文。
7) art_direction_summary_zh 中文摘要必须点名：主歌/副歌张力差异 + 若干核心母题的回归策略。
8) color_palette_en 为 3–12 个英文色词或短语；negative_style_hints_en 为 1–24 条英文负面片段。

JSON schema（你必须遵守键名；示例占位符需替换为实质内容）：
{
  \"schema_version\": \"1.1\",
  \"song_title\": \"…\",
  \"artist\": \"可选\",
  \"parsed_lyrics_ref\": \"占位由脚本覆盖\",
  \"song_structure_ref\": \"占位由脚本覆盖\",
  \"global_style_suffix\": \"英文全局 prompt 后缀\",
  \"global_style_suffix_zh\": \"可选\",
  \"structural_visual_rules\": [
    {
      \"section_roles\": [\"verse\"],
      \"visual_tension_en\": \"…\",
      \"visual_tension_zh\": \"…\",
      \"camera_framing_en\": \"…\",
      \"cut_motion_tempo_en\": \"…\",
      \"contrast_vs_other_sections_en\": \"…\"
    },
    {
      \"section_roles\": [\"chorus\"],
      \"visual_tension_en\": \"…\",
      \"visual_tension_zh\": \"…\",
      \"camera_framing_en\": \"…\",
      \"cut_motion_tempo_en\": \"…\",
      \"contrast_vs_other_sections_en\": \"…\"
    }
  ],
  \"core_visual_motifs\": [
    {
      \"motif_id\": \"snake_case_id\",
      \"name_en\": \"…\",
      \"name_zh\": \"…\",
      \"kind\": \"environment\",
      \"recurrence\": \"chorus_emphasis\",
      \"prompt_anchor_en\": \"English continuity phrase for prompts\",
      \"motif_notes_zh\": \"中文理由\",
      \"lyrics_line_refs\": [\"line_01\"]
    }
  ],
  \"animation_art_style_en\": \"…\",
  \"color_palette_en\": [\"…\", \"…\", \"…\"],
  \"lighting_mood_en\": \"…\",
  \"texture_material_en\": \"…\",
  \"motion_camera_en\": \"…\",
  \"negative_style_hints_en\": [\"…\"],
  \"art_direction_summary_zh\": \"…\"
}
"""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slim_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ln in lines:
        item: dict[str, Any] = {
            "line_id": ln["line_id"],
            "text": ln.get("text") or "",
        }
        for key in ("start_time", "end_time", "duration_seconds", "is_instrumental", "translation"):
            if key in ln and ln[key] is not None:
                item[key] = ln[key]
        out.append(item)
    return out


def load_song_structure(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema_version") not in ("1.0", "1.1"):
        raise SystemExit(
            "Unsupported song-structure schema_version "
            f"(expected 1.0 or 1.1, got {data.get('schema_version')!r})."
        )
    secs = data.get("sections")
    if not isinstance(secs, list) or not secs:
        raise SystemExit("song-structure missing non-empty 'sections'.")
    return data


def round3(value: float) -> float:
    return round(float(value), 3)


def load_lyrics_timing_strict(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema_version") not in ("1.0", "1.1"):
        raise SystemExit(
            "Unsupported lyrics-timing schema_version "
            f"(expected 1.0 or 1.1, got {data.get('schema_version')!r})."
        )
    if "lines" not in data or not isinstance(data["lines"], list):
        raise SystemExit("lyrics-timing missing 'lines' array.")
    return data


def load_song_sections_llm_strict(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema_version") not in ("1.0", "2.0"):
        raise SystemExit(
            "Unsupported song-sections-llm schema_version "
            f"(expected \"1.0\" or \"2.0\", got {data.get('schema_version')!r})."
        )
    secs = data.get("sections")
    if not isinstance(secs, list) or not secs:
        raise SystemExit("song-sections-llm missing non-empty 'sections'.")
    return data


def estimate_tail_duration_seconds(lines: list[dict[str, Any]]) -> float:
    durs = [
        float(ln["duration_seconds"])
        for ln in lines
        if isinstance(ln.get("duration_seconds"), (int, float))
    ]
    tail = durs[-10:] if len(durs) >= 3 else durs
    return float(statistics.median(tail)) if tail else 10.0


def resolve_total_duration_seconds(timing: dict[str, Any]) -> float:
    for key in ("audio_duration_seconds", "estimated_total_duration_seconds"):
        val = timing.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return round3(float(val))
    lines = timing.get("lines")
    if not isinstance(lines, list) or not lines:
        raise SystemExit("Cannot derive total duration: no lines and no audio duration.")
    last = lines[-1]
    start = last.get("start_time")
    if not isinstance(start, (int, float)):
        raise SystemExit("Cannot derive total duration: last line has no start_time.")
    pad = estimate_tail_duration_seconds(lines)
    return round3(float(start) + max(pad, 2.0))


def effective_line_end_time(
    line: dict[str, Any],
    timing: dict[str, Any],
    lines_seq: list[dict[str, Any]],
) -> float:
    """Resolve end_time for LRC tail lines where end_time/duration may be null."""
    et = line.get("end_time")
    if isinstance(et, (int, float)):
        return float(et)
    st = line.get("start_time")
    if not isinstance(st, (int, float)):
        raise SystemExit(f"Line {line.get('line_id')!r} missing start_time and end_time.")
    ds = line.get("duration_seconds")
    if isinstance(ds, (int, float)) and ds > 0:
        return round3(float(st) + float(ds))
    audio = timing.get("audio_duration_seconds")
    if isinstance(audio, (int, float)) and float(audio) > float(st):
        return round3(float(audio))
    try:
        idx = lines_seq.index(line)
    except ValueError:
        idx = -1
    nxt = lines_seq[idx + 1] if idx >= 0 and idx + 1 < len(lines_seq) else None
    if nxt and isinstance(nxt.get("start_time"), (int, float)):
        return round3(float(nxt["start_time"]))
    pad = estimate_tail_duration_seconds(lines_seq)
    return round3(float(st) + max(pad, 2.0))


def structure_from_timing_and_sections_llm(
    timing: dict[str, Any],
    llm_blob: dict[str, Any],
    song_title_override: str | None,
    artist_override: str | None,
) -> dict[str, Any]:
    """Minimal song-structure-shaped dict for prompts + validation (no file written)."""
    lines = timing["lines"]
    if not isinstance(lines, list):
        raise SystemExit("lyrics-timing 'lines' invalid.")
    by_id = {ln["line_id"]: ln for ln in lines if isinstance(ln, dict) and "line_id" in ln}

    sections_out: list[dict[str, Any]] = []
    for raw in llm_blob.get("sections", []):
        if not isinstance(raw, dict):
            continue
        refs = raw.get("line_refs")
        if not isinstance(refs, list) or not refs:
            raise SystemExit("song-sections-llm section has empty line_refs.")
        first_id, last_id = refs[0], refs[-1]
        if first_id not in by_id or last_id not in by_id:
            raise SystemExit(
                f"line_refs ({first_id!r} … {last_id!r}) not found in lyrics-timing lines."
            )
        first_ln, last_ln = by_id[first_id], by_id[last_id]
        st = first_ln.get("start_time")
        if not isinstance(st, (int, float)):
            raise SystemExit(
                f"Missing start_time for section {raw.get('section_id')!r} (from lyrics-timing)."
            )
        et = effective_line_end_time(last_ln, timing, lines)
        dur = round3(float(et) - float(st))
        sections_out.append({
            "section_id": raw["section_id"],
            "section_type": raw["section_type"],
            "start_time": round3(float(st)),
            "end_time": round3(float(et)),
            "duration_seconds": dur,
            "lyrics_line_refs": list(refs),
        })

    total = resolve_total_duration_seconds(timing)
    title_src = song_title_override
    if not title_src:
        sf = timing.get("source_file")
        if isinstance(sf, str) and sf.strip():
            title_src = sf.rsplit(".", 1)[0] if "." in sf else sf
        else:
            title_src = "Untitled"

    return {
        "schema_version": "1.0",
        "song_title": title_src,
        "artist": artist_override,
        "total_duration_seconds": total,
        "sections": sections_out,
        "mood_arc": [],
    }


def slim_structure_for_prompt(full: dict[str, Any]) -> dict[str, Any]:
    slim_sections: list[dict[str, Any]] = []
    for sec in full["sections"]:
        if not isinstance(sec, dict):
            continue
        row: dict[str, Any] = {}
        for key in (
            "section_id",
            "section_type",
            "section_label",
            "start_time",
            "end_time",
            "duration_seconds",
            "mood",
            "energy_level",
            "visual_suggestion",
            "lyrics_summary",
            "transition_to_next",
            "lyrics_line_refs",
        ):
            if key in sec and sec[key] is not None:
                row[key] = sec[key]
        slim_sections.append(row)
    return {
        "song_title": full.get("song_title"),
        "artist": full.get("artist"),
        "total_duration_seconds": full.get("total_duration_seconds"),
        "bpm": full.get("bpm"),
        "mood_arc": full.get("mood_arc"),
        "sections": slim_sections,
    }


def unwrap_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        stripped: list[str] = []
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
        raise SystemExit(f"Assistant did not return valid JSON: {e}\n{text[:1600]}") from e


def normalize_palette_and_negatives(obj: dict[str, Any]) -> None:
    """Coerce common model mistakes so validation can pass without losing intent."""

    cp = obj.get("color_palette_en")
    if isinstance(cp, list):
        cleaned = [str(x).strip() for x in cp if str(x).strip()]
        cleaned = [x for x in cleaned if len(x) >= 2]
    else:
        cleaned = []
    palette_fallbacks = [
        "balanced midtone neutrals",
        "controlled saturation",
        "cohesive grade",
    ]
    while len(cleaned) < 3:
        cleaned.append(palette_fallbacks[len(cleaned) % len(palette_fallbacks)])
    obj["color_palette_en"] = cleaned[:12]

    neg = obj.get("negative_style_hints_en")
    if isinstance(neg, str) and neg.strip():
        parts = [s.strip() for s in neg.replace(";", ",").split(",") if s.strip()]
        neg = parts if parts else []
    if not isinstance(neg, list):
        neg = []
    cleaned_neg = [str(x).strip() for x in neg if str(x).strip()]
    cleaned_neg = [x for x in cleaned_neg if len(x) >= 2]
    if not cleaned_neg:
        cleaned_neg = [
            "watermark",
            "subtitle overlay",
            "low resolution blur",
            "oversaturated HDR clipping",
            "deformed anatomy",
        ]
    obj["negative_style_hints_en"] = cleaned_neg[:24]


def normalize_core_visual_motif_kinds(obj: dict[str, Any]) -> None:
    """Map common LLM kind synonyms onto schema enums."""
    motifs = obj.get("core_visual_motifs")
    if not isinstance(motifs, list):
        return
    for m in motifs:
        if not isinstance(m, dict):
            continue
        k = m.get("kind")
        if k in MOTIF_KIND:
            continue
        if isinstance(k, str):
            kk = k.strip().lower().replace(" ", "_").replace("-", "_")
            if kk in MOTIF_KIND_ALIASES:
                m["kind"] = MOTIF_KIND_ALIASES[kk]
            elif kk in MOTIF_KIND:
                m["kind"] = kk
            else:
                m["kind"] = "symbol"
        else:
            m["kind"] = "symbol"


RECURRENCE_ALIASES: dict[str, str] = {
    "recurring": "persistent",
    "repeat": "persistent",
    "repeated": "persistent",
    "throughout": "persistent",
    "continuous": "persistent",
    "constant": "persistent",
    "verse": "verse_emphasis",
    "verse_recurring": "verse_emphasis",
    "chorus": "chorus_emphasis",
    "hook": "through_hook_refrain",
    "refrain": "through_hook_refrain",
    "bridge": "bridge_shift",
    "bookend": "bookend_only",
    "intro_outro": "bookend_only",
}


def normalize_core_visual_motif_recurrence(obj: dict[str, Any]) -> None:
    """Map invalid recurrence strings onto schema enums."""
    motifs = obj.get("core_visual_motifs")
    if not isinstance(motifs, list):
        return
    for m in motifs:
        if not isinstance(m, dict):
            continue
        r = m.get("recurrence")
        if r in MOTIF_RECURRENCE:
            continue
        if isinstance(r, str):
            rr = r.strip().lower().replace(" ", "_").replace("-", "_")
            if rr in RECURRENCE_ALIASES:
                m["recurrence"] = RECURRENCE_ALIASES[rr]
            elif rr in MOTIF_RECURRENCE:
                m["recurrence"] = rr
            else:
                m["recurrence"] = "persistent"
        else:
            m["recurrence"] = "persistent"


def normalize_structural_rules_zh(obj: dict[str, Any]) -> None:
    """Pad short visual_tension_zh (models sometimes emit terse Chinese)."""
    rules = obj.get("structural_visual_rules")
    if not isinstance(rules, list):
        return
    fallback_extra = "段落间需与副歌或主歌形成清晰张力对比。"
    for r in rules:
        if not isinstance(r, dict):
            continue
        zh = str(r.get("visual_tension_zh", "") or "").strip()
        if len(zh) >= 8:
            continue
        en = str(r.get("visual_tension_en", "") or "").strip()
        if len(en) >= 16:
            r["visual_tension_zh"] = (zh + " " if zh else "") + en[:160].rstrip() + "… " + fallback_extra
        else:
            r["visual_tension_zh"] = (zh + " " if zh else "") + fallback_extra


def section_types_present(structure: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for sec in structure.get("sections", []):
        if isinstance(sec, dict):
            t = sec.get("section_type")
            if isinstance(t, str) and t.strip():
                out.add(t.strip())
    return out


def validate_structural_visual_rules(
    rules: Any,
    structure: dict[str, Any],
) -> None:
    if not isinstance(rules, list) or not (2 <= len(rules) <= 8):
        n = len(rules) if isinstance(rules, list) else "?"
        raise SystemExit(
            "structural_visual_rules must be an array of 2–8 objects, "
            f"got {type(rules).__name__} len={n}"
        )
    present_types = section_types_present(structure)
    must_cover = set()
    if "verse" in present_types:
        must_cover.add("verse")
    if "chorus" in present_types:
        must_cover.add("chorus")
    covered_roles: set[str] = set()

    for i, r in enumerate(rules):
        if not isinstance(r, dict):
            raise SystemExit(f"structural_visual_rules[{i}] is not an object.")
        rk = set(r.keys())
        if not rk.issubset(STRUCT_RULE_KEYS):
            raise SystemExit(
                f"structural_visual_rules[{i}] keys must be subset of {sorted(STRUCT_RULE_KEYS)!r}, got unknown {sorted(rk - STRUCT_RULE_KEYS)!r}"
            )
        roles = r["section_roles"]
        if not isinstance(roles, list) or not (1 <= len(roles) <= 6):
            raise SystemExit(f"structural_visual_rules[{i}].section_roles invalid.")
        role_set = {str(role) for role in roles if isinstance(role, str)}
        if "verse" in role_set and "chorus" in role_set:
            raise SystemExit(
                f"structural_visual_rules[{i}] must not combine verse and chorus in one "
                "entry; use separate rule objects for contrasting tension."
            )
        for role in roles:
            if not isinstance(role, str) or role not in VALID_SECTION_ROLE:
                raise SystemExit(
                    f"structural_visual_rules[{i}] invalid section_roles entry {role!r}"
                )
        covered_roles.update(roles)

        if len(str(r["visual_tension_en"]).strip()) < 16:
            raise SystemExit(f"structural_visual_rules[{i}].visual_tension_en too short.")
        if len(str(r["visual_tension_zh"]).strip()) < 8:
            raise SystemExit(f"structural_visual_rules[{i}].visual_tension_zh too short.")
        if len(str(r["camera_framing_en"]).strip()) < 12:
            raise SystemExit(f"structural_visual_rules[{i}].camera_framing_en too short.")
        if len(str(r["cut_motion_tempo_en"]).strip()) < 12:
            raise SystemExit(f"structural_visual_rules[{i}].cut_motion_tempo_en too short.")
        if len(str(r["contrast_vs_other_sections_en"]).strip()) < 16:
            raise SystemExit(
                f"structural_visual_rules[{i}].contrast_vs_other_sections_en too short."
            )

    missing = must_cover - covered_roles
    if missing:
        raise SystemExit(
            "structural_visual_rules must cover section_roles for song section_types "
            f"{sorted(must_cover)!r} (from section context). Missing: {sorted(missing)!r}. "
            f"Covered: {sorted(covered_roles)!r}"
        )


def validate_core_visual_motifs(motifs: Any) -> None:
    if not isinstance(motifs, list) or not (3 <= len(motifs) <= 10):
        raise SystemExit("core_visual_motifs must be an array of 3–10 objects.")
    seen_ids: set[str] = set()
    mid_pat = re.compile(r"^[a-z][a-z0-9_]*$")
    for i, m in enumerate(motifs):
        if not isinstance(m, dict):
            raise SystemExit(f"core_visual_motifs[{i}] is not an object.")
        mk = set(m.keys())
        allowed_motif = MOTIF_KEYS  # lyrics_line_refs optional
        if not mk.issubset(allowed_motif):
            raise SystemExit(f"core_visual_motifs[{i}] forbidden keys: {mk - allowed_motif!r}")
        req_m = {
            "motif_id", "name_en", "name_zh", "kind",
            "recurrence", "prompt_anchor_en", "motif_notes_zh",
        }
        if not req_m.issubset(mk):
            raise SystemExit(
                f"core_visual_motifs[{i}] missing keys: {sorted(req_m - mk)!r}"
            )

        mid = m["motif_id"]
        if not isinstance(mid, str) or len(mid) < 3 or not mid_pat.match(mid):
            raise SystemExit(f"core_visual_motifs[{i}].motif_id invalid snake_case.")
        if mid in seen_ids:
            raise SystemExit(f"Duplicate motif_id {mid!r}")
        seen_ids.add(mid)

        if m["kind"] not in MOTIF_KIND:
            raise SystemExit(f"core_visual_motifs[{i}].kind invalid.")
        if m["recurrence"] not in MOTIF_RECURRENCE:
            raise SystemExit(f"core_visual_motifs[{i}].recurrence invalid.")

        for fld in ("name_en", "name_zh"):
            if not isinstance(m[fld], str) or len(m[fld].strip()) < 2:
                raise SystemExit(f"core_visual_motifs[{i}].{fld} too short.")

        pa = m["prompt_anchor_en"]
        if not isinstance(pa, str) or not (12 <= len(pa.strip()) <= 400):
            raise SystemExit(f"core_visual_motifs[{i}].prompt_anchor_en length invalid.")

        notes = m["motif_notes_zh"]
        if not isinstance(notes, str) or len(notes.strip()) < 12:
            raise SystemExit(f"core_visual_motifs[{i}].motif_notes_zh too short.")

        if "lyrics_line_refs" in m:
            refs = m["lyrics_line_refs"]
            if refs is None:
                continue
            if not isinstance(refs, list) or len(refs) > 24:
                raise SystemExit(f"core_visual_motifs[{i}].lyrics_line_refs invalid.")
            if not all(isinstance(x, str) and len(x.strip()) >= 4 for x in refs):
                raise SystemExit(
                    f"core_visual_motifs[{i}].lyrics_line_refs must be line id strings."
                )


def validate_global_visual_style(data: dict[str, Any], structure: dict[str, Any]) -> None:
    keys = set(data.keys())
    if not keys.issubset(ALLOWED_TOP_KEYS):
        raise SystemExit(f"Forbidden top-level keys: {keys - ALLOWED_TOP_KEYS!r}")
    missing = REQUIRED_KEYS - keys
    if missing:
        raise SystemExit(f"Missing required keys: {sorted(missing)!r}")
    if data.get("schema_version") != "1.1":
        raise SystemExit('schema_version must be \"1.1\".')

    validate_structural_visual_rules(data.get("structural_visual_rules"), structure)
    validate_core_visual_motifs(data.get("core_visual_motifs"))

    def req_str(k: str, min_len: int, max_len: int | None = None) -> None:
        v = data[k]
        if not isinstance(v, str) or len(v.strip()) < min_len:
            raise SystemExit(f"{k} must be a non-empty string (min {min_len} chars).")
        if max_len is not None and len(v) > max_len:
            raise SystemExit(f"{k} exceeds max length {max_len}.")

    req_str("song_title", 1, 300)
    req_str("parsed_lyrics_ref", 1, 500)
    req_str("song_structure_ref", 1, 500)
    req_str("global_style_suffix", 8, 900)
    req_str("animation_art_style_en", 12, 4000)
    req_str("lighting_mood_en", 8, 2000)
    req_str("texture_material_en", 8, 2000)
    req_str("motion_camera_en", 8, 2000)
    req_str("art_direction_summary_zh", 20, 8000)

    if "artist" in data:
        if data["artist"] is not None and not isinstance(data["artist"], str):
            raise SystemExit("artist must be string or omitted.")
    if "global_style_suffix_zh" in data:
        gsz = data["global_style_suffix_zh"]
        if gsz is not None and not isinstance(gsz, str):
            raise SystemExit("global_style_suffix_zh must be string or omitted.")

    cp = data["color_palette_en"]
    if not isinstance(cp, list) or not (3 <= len(cp) <= 12):
        raise SystemExit(
            f"color_palette_en must be an array of 3–12 strings, got {cp!r}"
        )
    if not all(isinstance(x, str) and len(x.strip()) >= 2 for x in cp):
        raise SystemExit("color_palette_en entries must be non-empty strings.")

    neg = data["negative_style_hints_en"]
    if not isinstance(neg, list) or not (1 <= len(neg) <= 24):
        raise SystemExit(
            f"negative_style_hints_en must be an array of 1–24 strings, got {neg!r}"
        )
    if not all(isinstance(x, str) and len(x.strip()) >= 2 for x in neg):
        raise SystemExit("negative_style_hints_en entries must be non-empty strings.")


def inject_refs(
    obj: dict[str, Any],
    parsed_ref: str,
    structure_ref: str,
    song_title_fallback: str | None,
    artist_fallback: str | None,
) -> None:
    obj["parsed_lyrics_ref"] = parsed_ref
    obj["song_structure_ref"] = structure_ref
    if song_title_fallback and not (obj.get("song_title") or "").strip():
        obj["song_title"] = song_title_fallback
    if artist_fallback is not None and not obj.get("artist"):
        obj["artist"] = artist_fallback


def main() -> None:
    load_aigc_dotenv()
    if not os.getenv("AIGC_GITEE_API_KEY") and os.getenv("GITEE_API_TOKEN"):
        os.environ["AIGC_GITEE_API_KEY"] = os.getenv("GITEE_API_TOKEN", "")

    import config as qwen_cfg  # noqa: E402

    ap = argparse.ArgumentParser(
        description="Qwen3 → mv-global-visual-style.json (Stage 2 art direction)"
    )
    ap.add_argument(
        "--lyrics-timing",
        required=True,
        type=Path,
        help="lyrics-timing.json from parse_lyrics.py (sole source for line-level lyrics).",
    )
    ap.add_argument(
        "--song-structure",
        default=None,
        type=Path,
        help="Legacy: song-structure.json with section timing "
        "(use together with --lyrics-timing for line text).",
    )
    ap.add_argument(
        "--song-sections-llm",
        default=None,
        type=Path,
        help="Default path: song-sections-llm.json — paired with `--lyrics-timing`.",
    )
    ap.add_argument(
        "--song-title",
        default=None,
        help="Optional override when section context is built from timing + LLM segments.",
    )
    ap.add_argument(
        "--artist",
        default=None,
        help="Optional artist when section context is built from timing + LLM segments.",
    )
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument(
        "--lyrics-timing-ref",
        default=None,
        help="Value for parsed_lyrics_ref in output JSON (default: lyrics-timing basename)",
    )
    ap.add_argument(
        "--song-structure-ref",
        default=None,
        help="Value for song_structure_ref field "
        "(default: song-structure filename, or lyrics-timing+song-sections basenames)",
    )
    ap.add_argument("--temperature", type=float, default=0.35)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print request payload only, no API call",
    )
    args = ap.parse_args()

    lt_path = args.lyrics_timing.resolve()
    timing = load_lyrics_timing_strict(lt_path)
    secs_path = args.song_sections_llm
    legacy_path = args.song_structure

    if legacy_path is not None and secs_path is not None:
        raise SystemExit(
            "Use either `--song-structure` for section context, or "
            "`--song-sections-llm` — do not pass both."
        )
    if legacy_path is not None:
        ss_path_res = legacy_path.resolve()
        structure = load_song_structure(ss_path_res)
        struct_ref = args.song_structure_ref or ss_path_res.name
    elif secs_path is not None:
        llm_blob = load_song_sections_llm_strict(secs_path.resolve())
        structure = structure_from_timing_and_sections_llm(
            timing,
            llm_blob,
            song_title_override=args.song_title,
            artist_override=args.artist,
        )
        struct_ref = args.song_structure_ref or (
            f"{lt_path.name} + {secs_path.name}"
        )
    else:
        raise SystemExit(
            "Section context required: `--song-structure <path>` or "
            "`--song-sections-llm <path>`."
        )

    lyrics_ref = args.lyrics_timing_ref or lt_path.name

    user_blob: dict[str, Any] = {
        "task": "mv_global_visual_style",
        "parsed_lyrics_ref_output": lyrics_ref,
        "song_structure_ref_output": struct_ref,
        "parsed_lyrics": {
            "source_file": timing.get("source_file"),
            "detected_format": timing.get("detected_format"),
            "lines": slim_lines(timing["lines"]),
        },
        "song_structure": slim_structure_for_prompt(structure),
    }
    user_text = (
        "输入如下。请严格按系统说明只输出 JSON。\n"
        + json.dumps(user_blob, ensure_ascii=False)
    )

    if args.dry_run:
        print(json.dumps({"model": qwen_cfg.DEFAULT_MODEL, "stream": False, "enable_thinking": False, "max_tokens": args.max_tokens, "temperature": args.temperature, "top_p": 0.9, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_text}]}, ensure_ascii=False, indent=2))
        return

    if not qwen_cfg.API_KEY:
        raise SystemExit(
            "Missing AIGC_GITEE_API_KEY (or GITEE_API_TOKEN). Set in env or aigc/.env"
        )

    retry_hint = ""
    model_obj: dict[str, Any] | None = None
    for attempt in range(3):
        full_user = user_text + retry_hint
        payload = {
            "model": qwen_cfg.DEFAULT_MODEL,
            "stream": False,
            "enable_thinking": False,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "top_p": 0.9,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_user},
            ],
        }
        response = post_messages(
            qwen_cfg.API_URL, qwen_cfg.API_KEY, payload, timeout=args.timeout
        )
        assistant_text = extract_assistant_text(response)
        try:
            model_obj = parse_model_json(assistant_text)
        except SystemExit as e:
            if attempt >= 2:
                raise
            retry_hint = (
                "\n\n【上次校验失败，请仅输出修正后的完整 JSON，不要解释】\n"
                f"原因：{e.args[0] if e.args else 'JSON parse failed'}\n"
            )
            continue
        inject_refs(
            model_obj,
            parsed_ref=lyrics_ref,
            structure_ref=struct_ref,
            song_title_fallback=str(
                structure.get("song_title") or timing.get("song_title") or ""
            ),
            artist_fallback=structure.get("artist"),
        )
        normalize_palette_and_negatives(model_obj)
        normalize_structural_rules_zh(model_obj)
        normalize_core_visual_motif_kinds(model_obj)
        normalize_core_visual_motif_recurrence(model_obj)
        try:
            validate_global_visual_style(model_obj, structure)
        except SystemExit as e:
            if attempt >= 2:
                raise
            retry_hint = (
                "\n\n【上次校验失败，请仅输出修正后的完整 JSON，不要解释】\n"
                f"原因：{e.args[0] if e.args else 'validation failed'}\n"
            )
            continue
        break

    assert model_obj is not None

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(model_obj, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
