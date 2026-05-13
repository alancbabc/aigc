#!/usr/bin/env python3
"""Qwen3 acts as MV director: grouped keyframe image prompts + I2V prompts with lyrics/times.

Reads Stage 1 (**lyrics-timing.json**, **song-sections-llm.json**) and Stage 2
(**mv-global-visual-style.json**), calls Gitee Qwen3,
validates line coverage (consecutive groups; not one keyframe per line), then
injects **start_time**, **end_time**, and **lines** from **lyrics-timing.json**.

Output matches ``contracts/mv-keyframe-director/mv-keyframe-director.schema.json``.
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

ALLOWED_MODEL_TOP = frozenset({
    "schema_version",
    "song_title",
    "artist",
    "director_notes_zh",
    "keyframes",
})

ALLOWED_KF_IN = frozenset({
    "keyframe_id",
    "primary_section_ref",
    "section_type_focus",
    "line_refs",
    "keyframe_type",
    "narrative_beat_zh",
    "continuity_previous_en",
    "continuity_next_en",
    "keyframe_image_prompt_en",
    "video_from_keyframe_prompt_en",
})

VALID_KEYFRAME_TYPES = frozenset({
    "lyric_visual",
    "lyric_emotional",
    "lyric_philosophical",
    "character_singing",
    "instrumental",
    # legacy aliases
    "lyric_imagery",
})

MID_PAT = re.compile(r"^[a-z][a-z0-9_]*$")


SYSTEM_PROMPT = """你是 MV 总导演 + 摄影指导 + 视觉叙事设计师。你将收到：逐行歌词与时间码、段落结构（每段内含该段歌词文本）、全片视觉风格锁定（global_style_suffix、段落张力规则、core_visual_motifs），以及歌曲背景知识和参考图像信息。

# 一、情感结构分析（先想后画）

在规划任何画面之前，先识别整首歌的 **多层叙事结构**：

1. **表层意象**：歌词里直接出现的视觉实体（海、鱼、天空、眼泪……）
2. **深层情感**：歌词背后的情绪内核（守望、放手、孤独、自由的释然……）
3. **精神层**：整首歌最底层的哲学含义（"自由比占有更重要"、"世界无法理解敏感之人"……）

以及整首歌的 **情绪弧线**：每个段落的 emotional_state 和 color_temperature 应有所不同。
- 主歌：克制、沉溺 → 深蓝/冷色调
- 副歌：释放、爆发 → 暖金/亮色调
- 桥段/尾声：接受、消散 → 银白/灰蓝

# 二、意象矩阵（同一个意象，不同段落的含义必须演化）

core_visual_motifs 中的每个 motif 在整首歌中应反复出现，但 **每次出现承载不同的情绪重量**：
- 第一次出现：神秘、引入
- 第二次出现（重复段落）：宿命感加深
- 最后一次出现：升华、放手、消散

例如：同一个「大鱼」意象：
- verse_1 出现 → 神秘的远古存在
- chorus_1 出现 → 注定离去的宿命
- verse_2 出现 → 被理解的生命
- chorus_2 出现 → 终于回归自由

不同段落使用同一个 motif 的 prompt_anchor_en 时，要根据段落的 emotional_state 调整画面氛围。

# 三、镜头策略（镜头不是技巧，是情绪功能）

1. **环境 vs 特写的比例**：
   - 70-80% 用环境/中远景（超广角、深焦），因为 MV 真正的主角是「情绪空间」，不是人
   - 20% 用特写/近景，只在情绪核爆点使用（放手瞬间、高潮泪水），用多了会疲劳
   - 特写是为了情感功能，不是为了展示细节

2. **镜头长度的情绪含义**：
   - 主歌：慢、安静、凝视，像在用眼睛抚摸画面
   - 副歌：镜头运动加速，但不乱；whip pan 只在节拍点上用
   - 尾声：镜头逐渐静止，或无限拉远（人极小，天地极大 — 东方审美）

3. **焦段 = 距离感**：
   - 广角/超广角 → 人在环境中的渺小、孤独、自由
   - 长焦压缩 → "明明很近，却永远追不上"的距离感
   - 浅景深 → 梦境、不确定、记忆感
   - 深焦全清晰 → 现实、清醒、接受

# 四、转场规则（转场本身就在叙事）

MV 是一场连续的梦，不是碎片拼接。转场必须自然：

1. **段落边界**（verse→chorus, chorus→bridge）：强转场但不硬切
   推荐：water dissolve, cloud dissolve, color bleed, ripple fade, 星光融入
2. **段落内部**（同一 section 内的 keyframe 切换）：弱转场
   推荐：match cut, slow cross-fade, beat-sync dissolve
3. **避免**：炫酷特效、硬切、花哨转场、3D 翻转、zoom blur
4. 转场应暗示叙事连续性，continuity_previous / continuity_next 要描述空间的连贯或对比

# 五、叙事密度（留白！）

MV 忌讳：
- 太满、太解释、太具体、太剧情化、太热闹、太拥挤
- 每个关键帧最多 2 个显著角色或物体
- 不要太"实"，不要一直解释剧情
- 画面要像错觉、记忆、意识流 — 不是说明书

MV 需要的是留白。有些情感无法说清，只能让画面自己讲话。

尤其对于歌词抽象、缺乏视觉意象的段落：
- 不要强行"制造"画面 → 去感受情绪的"温度"，把温度翻译成视觉
- 例如"怕你飞远去" → 不是画"害怕的脸"，而是画"长焦下无尽的空间中一个追不上的人影"
- 例如"suffered for sanity" → 不是画"痛苦"，而是画"极度敏感的人站在麻木世界中央的孤独"

# 六、你的任务

规划 **关键帧 Keyframe** —— 用于先生成 **静帧首图**，再以该静帧做 **图生视频**。不是每一句歌词都需要一张关键帧；通常 **多句连续歌词合并为同一关键帧画面**。

硬性规则（必须遵守）：
1) 只输出「一个合法 JSON 对象」，不要使用 Markdown、不要前后说明文字。
2) 顶层键仅允许：schema_version, song_title?, artist?, director_notes_zh?, keyframes。
3) schema_version 必须为字符串 "1.0"。
4) keyframes 为数组；**每个元素**仅允许下列键：
   keyframe_id, primary_section_ref, section_type_focus,
   line_refs, keyframe_type, narrative_beat_zh?, continuity_previous_en?, continuity_next_en?,
   keyframe_image_prompt_en, video_from_keyframe_prompt_en。
5) **line_refs**：非空字符串数组，元素必须是输入里出现过的 line_id；同一 line_id 在全曲中 **恰好出现一次**；按 keyframes 数组顺序拼接所有 line_refs，必须 **与全曲 line_id 顺序完全一致**（把时间轴完整切分为若干 **连续块**）。
6) 每个 keyframe 内的 line_refs 在原曲顺序中必须是 **连续递增** 的若干句（不得跳句拼块）。
7) **不要**为每一句单独做一张关键帧；全曲关键帧总数应 **明显少于** 总行数（典型约为每 8–20 秒一粒，或每 2–5 句一粒，视叙事密度而定）。副歌重复意象时可 **合并**。
8) primary_section_ref：该关键帧 **叙事与画面主导** 对应的 section_id（来自段落 JSON）；若跨段，取 **主叙事所在段**。
9) section_type_focus：该粒关键帧在视听上对应的段落角色（如 verse / chorus / bridge / pre_chorus / outro 等），与同段 **mv-global-visual-style / structural_visual_rules** 的张力与剪辑节奏 **一致**。
10) **keyframe_type**（必填）：按该关键帧覆盖歌词的 **视觉具象程度 + 功能** 决定：
    - 歌词有 **具体视觉实体**（海、鱼、天空、翅膀、眼泪等可画之物）→ `"lyric_visual"`（文本生图）
    - 歌词 **抽象但情感浓烈**（怕、等待、希望等不可直接画的事物）→ `"lyric_emotional"`（把情绪温度翻译为视觉隐喻 → 文本生图）
    - 歌词有 **哲学/精神含义**（命运、自由、释然等深层概念）→ `"lyric_philosophical"`（象征性画面 → 文本生图）
    - 歌词为 **纯情绪渲染 / 无任何视觉锚点** → `"character_singing"`（使用歌手参考图做图生图）
    - 纯器乐间奏 / 段落留白 → `"instrumental"`（抽象纹理或环境空镜头）
11) keyframe_image_prompt_en：**英文**，16:9 电影静帧提示。必须 **融入** global_style_suffix 中的风格关键词与 core_visual_motifs 的 prompt_anchor。主歌/副歌的 **色彩与景别策略** 不得混用。根据 section_type_focus 采用对应的 camera_framing_en 风格。
12) video_from_keyframe_prompt_en：**英文**，基于该静帧的 **图生视频** 动作/摄影机/时长感提示（不要重复整张画面描述，强调 **从该帧出发的运动**、镜头推拉摇移、节奏与情绪），并与 continuity_* 衔接。
13) continuity_previous_en / continuity_next_en：可选，英文短语，说明与上一粒/下一粒的 **视线、空间、色调、转场方式** 连贯或对比（首粒写 "N/A"）。
14) narrative_beat_zh：**必填**，中文一句，说明该粒在 **叙事/情绪弧** 上的职责，并注明该粒中 motif 的含义演化（如"大鱼从神秘→宿命的转折点"）。

JSON 形状示例：
{
  "schema_version": "1.0",
  "song_title": "…",
  "artist": "…",
  "director_notes_zh": "…",
  "keyframes": [
    {
      "keyframe_id": "kf_01",
      "primary_section_ref": "verse_1",
      "section_type_focus": "verse",
      "line_refs": ["line_01", "line_02"],
      "keyframe_type": "lyric_visual",
      "narrative_beat_zh": "建立深海梦境与孤独基调",
      "continuity_previous_en": "N/A",
      "continuity_next_en": "Water dissolve into wider oceanic perspective.",
      "keyframe_image_prompt_en": "…",
      "video_from_keyframe_prompt_en": "…"
    }
  ]
}
"""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def round3(x: float) -> float:
    return round(float(x), 3)


def estimate_tail_duration_seconds(lines: list[dict[str, Any]]) -> float:
    durs = [
        float(ln["duration_seconds"])
        for ln in lines
        if isinstance(ln.get("duration_seconds"), (int, float))
    ]
    tail = durs[-10:] if len(durs) >= 3 else durs
    return float(statistics.median(tail)) if tail else 10.0


def effective_line_end_time(
    line: dict[str, Any],
    timing: dict[str, Any],
    lines_seq: list[dict[str, Any]],
) -> float:
    et = line.get("end_time")
    if isinstance(et, (int, float)):
        return float(et)
    st = line.get("start_time")
    if not isinstance(st, (int, float)):
        raise SystemExit(f"Line {line.get('line_id')!r} missing start_time/end_time.")
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


def load_timing(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema_version") not in ("1.0", "1.1"):
        raise SystemExit(f"Unsupported lyrics-timing schema_version {data.get('schema_version')!r}")
    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        raise SystemExit("lyrics-timing missing lines.")
    return data


def load_sections_llm(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema_version") != "1.0":
        raise SystemExit('song-sections-llm schema_version must be "1.0".')
    return data


def load_mv_style(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema_version") != "1.1":
        raise SystemExit('mv-global-visual-style schema_version must be "1.1".')
    return data


def line_id_order(timing: dict[str, Any]) -> list[str]:
    return [str(ln["line_id"]) for ln in timing["lines"] if isinstance(ln, dict) and "line_id" in ln]


def line_to_section_map(llm: dict[str, Any]) -> dict[str, str]:
    m: dict[str, str] = {}
    for sec in llm.get("sections", []):
        sid = sec.get("section_id")
        for r in sec.get("line_refs", []):
            m[str(r)] = str(sid)
    return m


def slim_style_for_prompt(style: dict[str, Any]) -> dict[str, Any]:
    motifs = []
    for mo in (style.get("core_visual_motifs") or [])[:12]:
        if not isinstance(mo, dict):
            continue
        motifs.append({
            "motif_id": mo.get("motif_id"),
            "kind": mo.get("kind"),
            "prompt_anchor_en": mo.get("prompt_anchor_en"),
            "name_zh": mo.get("name_zh"),
        })
    rules = []
    for r in (style.get("structural_visual_rules") or [])[:8]:
        if not isinstance(r, dict):
            continue
        rules.append({
            "section_roles": r.get("section_roles"),
            "visual_tension_en": r.get("visual_tension_en"),
            "camera_framing_en": r.get("camera_framing_en"),
            "cut_motion_tempo_en": r.get("cut_motion_tempo_en"),
            "contrast_vs_other_sections_en": r.get("contrast_vs_other_sections_en"),
        })
    return {
        "global_style_suffix": style.get("global_style_suffix"),
        "global_style_suffix_zh": style.get("global_style_suffix_zh"),
        "animation_art_style_en": style.get("animation_art_style_en"),
        "color_palette_en": style.get("color_palette_en"),
        "lighting_mood_en": style.get("lighting_mood_en"),
        "motion_camera_en": style.get("motion_camera_en"),
        "negative_style_hints_en": style.get("negative_style_hints_en"),
        "structural_visual_rules": rules,
        "core_visual_motifs": motifs,
        "art_direction_summary_zh": style.get("art_direction_summary_zh"),
    }


def sections_digest_for_director(llm: dict[str, Any], timing: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-section lyric text from timing (director derives imagery without lyrics-analysis JSON)."""
    by_id = {str(l["line_id"]): l for l in timing["lines"] if isinstance(l, dict) and "line_id" in l}
    out: list[dict[str, Any]] = []
    for sec in llm.get("sections", []):
        if not isinstance(sec, dict):
            continue
        refs = sec.get("line_refs") or []
        lines_pack: list[dict[str, Any]] = []
        for rid in refs:
            rid = str(rid)
            ln = by_id.get(rid)
            txt = ""
            if isinstance(ln, dict):
                txt = str(ln.get("text") or "")
            lines_pack.append({"line_id": rid, "text": txt[:400]})
        out.append({
            "section_id": sec.get("section_id"),
            "section_type": sec.get("section_type"),
            "line_refs_order": refs,
            "lines": lines_pack,
            "notes": sec.get("notes"),
        })
    return out


def slim_lines_for_director(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for ln in lines:
        if not isinstance(ln, dict) or "line_id" not in ln:
            continue
        row: dict[str, Any] = {
            "line_id": ln["line_id"],
            "text": ln.get("text") or "",
        }
        if isinstance(ln.get("start_time"), (int, float)):
            row["start_time"] = round3(float(ln["start_time"]))
        if ln.get("is_instrumental") is True:
            row["is_instrumental"] = True
        out.append(row)
    return out


def unwrap_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        stripped: list[str] = []
        for i, row in enumerate(text.splitlines()):
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
        raise SystemExit(f"Assistant did not return valid JSON: {e}\n{text[:2200]}") from e


def validate_model_payload(
    data: dict[str, Any],
    line_order: list[str],
    duration_sec: float,
    l2s: dict[str, str],
) -> list[dict[str, Any]]:
    bad_top = set(data.keys()) - ALLOWED_MODEL_TOP
    if bad_top:
        raise SystemExit(f"Unexpected top-level keys from model: {bad_top!r}")
    if data.get("schema_version") != "1.0":
        raise SystemExit('schema_version must be "1.0".')
    kfs = data.get("keyframes")
    if not isinstance(kfs, list) or not kfs:
        raise SystemExit("keyframes must be non-empty array.")

    n = len(line_order)
    min_kf = max(4, int(duration_sec / 28)) if duration_sec > 0 else max(4, n // 8)
    max_kf = min(n, max(8, int(duration_sec / 9))) if duration_sec > 0 else min(n, max(8, n // 2))
    if len(kfs) < 3:
        raise SystemExit(f"Too few keyframes ({len(kfs)}); need at least 3.")
    if len(kfs) > max_kf:
        raise SystemExit(
            f"Too many keyframes ({len(kfs)}); director should merge lines. "
            f"Suggested max ~{max_kf} for this song (min suggested {min_kf})."
        )
    if len(kfs) >= n:
        raise SystemExit("Keyframes must be fewer than lyric lines (no one-line-per-keyframe).")
    if n >= 8 and len(kfs) > n * 0.55:
        raise SystemExit(
            f"Too many keyframes ({len(kfs)} vs {n} lines); merge more consecutive lines."
        )

    merged: list[str] = []
    seen: set[str] = set()
    for i, kf in enumerate(kfs):
        if not isinstance(kf, dict):
            raise SystemExit(f"keyframes[{i}] not an object.")
        extra = set(kf.keys()) - ALLOWED_KF_IN
        if extra:
            raise SystemExit(f"keyframes[{i}] forbidden keys: {extra!r}")
        missing = {
            "keyframe_id", "primary_section_ref", "section_type_focus",
            "line_refs", "keyframe_type", "narrative_beat_zh", "keyframe_image_prompt_en", "video_from_keyframe_prompt_en",
        } - set(kf.keys())
        if missing:
            raise SystemExit(f"keyframes[{i}] missing: {missing!r}")
        kid = kf["keyframe_id"]
        if not isinstance(kid, str) or not MID_PAT.match(kid):
            raise SystemExit(f"keyframes[{i}].keyframe_id must be snake_case like kf_01.")
        refs = kf["line_refs"]
        if not isinstance(refs, list) or not refs:
            raise SystemExit(f"keyframes[{i}].line_refs must be non-empty.")
        for rid in refs:
            if rid in seen:
                raise SystemExit(f"Duplicate line_id {rid!r} across keyframes.")
            seen.add(rid)
            if rid not in line_order:
                raise SystemExit(f"Unknown line_id {rid!r} in keyframe {kid}.")
        idxs = [line_order.index(r) for r in refs]
        for a, b in zip(idxs, idxs[1:]):
            if b != a + 1:
                raise SystemExit(
                    f"keyframes[{i}] line_refs must be consecutive in song order."
                )
        ps = kf["primary_section_ref"]
        span_secs = set(l2s.get(r) for r in refs)
        if ps not in span_secs:
            raise SystemExit(
                f"keyframes[{i}].primary_section_ref {ps!r} must match one of the "
                f"sections covering its line_refs ({span_secs!r})."
            )
        kt = kf.get("keyframe_type")
        if kt not in VALID_KEYFRAME_TYPES:
            raise SystemExit(
                f"keyframes[{i}].keyframe_type must be one of "
                f"{sorted(VALID_KEYFRAME_TYPES)!r}, got {kt!r}."
            )
        for fld in ("keyframe_image_prompt_en", "video_from_keyframe_prompt_en"):
            s = kf.get(fld)
            if not isinstance(s, str) or len(s.strip()) < 24:
                raise SystemExit(f"keyframes[{i}].{fld} too short.")
        stf = kf.get("section_type_focus")
        if not isinstance(stf, str) or len(stf.strip()) < 2:
            raise SystemExit(f"keyframes[{i}].section_type_focus invalid.")
        merged.extend(refs)

    if merged != line_order:
        raise SystemExit(
            "All lyrics lines must be covered exactly once in order. "
            f"Expected {len(line_order)} refs, got {len(merged)}."
        )

    return kfs


def enrich_keyframes(
    raw_kfs: list[dict[str, Any]],
    timing: dict[str, Any],
) -> list[dict[str, Any]]:
    lines = timing["lines"]
    by_id = {str(ln["line_id"]): ln for ln in lines if isinstance(ln, dict)}
    out: list[dict[str, Any]] = []
    for kf in raw_kfs:
        refs = kf["line_refs"]
        detail: list[dict[str, Any]] = []
        for rid in refs:
            ln = by_id[rid]
            row: dict[str, Any] = {
                "line_id": ln["line_id"],
                "text": ln.get("text") or "",
                "start_time": round3(float(ln["start_time"]))
                if isinstance(ln.get("start_time"), (int, float))
                else None,
            }
            et = effective_line_end_time(ln, timing, lines)
            row["end_time"] = round3(et)
            ds = ln.get("duration_seconds")
            if isinstance(ds, (int, float)):
                row["duration_seconds"] = round3(float(ds))
            else:
                st = ln.get("start_time")
                if isinstance(st, (int, float)):
                    row["duration_seconds"] = round3(max(et - float(st), 0.05))
                else:
                    row["duration_seconds"] = None
            detail.append(row)
        first_ln = by_id[refs[0]]
        last_ln = by_id[refs[-1]]
        st = first_ln.get("start_time")
        if not isinstance(st, (int, float)):
            raise SystemExit(f"Missing start_time for {refs[0]!r}")
        end_t = effective_line_end_time(last_ln, timing, lines)
        enriched = dict(kf)
        enriched["start_time"] = round3(float(st))
        enriched["end_time"] = round3(end_t)
        enriched["lines"] = detail
        out.append(enriched)
    return out


def timing_duration_hint(timing: dict[str, Any]) -> float:
    for key in ("audio_duration_seconds", "estimated_total_duration_seconds"):
        v = timing.get(key)
        if isinstance(v, (int, float)) and v > 0:
            return float(v)
    lines = timing["lines"]
    if not lines:
        return 0.0
    last = lines[-1]
    st = last.get("start_time")
    if isinstance(st, (int, float)):
        return float(st) + estimate_tail_duration_seconds(lines)
    return 0.0


def default_source_refs(args: argparse.Namespace) -> dict[str, str]:
    return {
        "lyrics_timing_ref": args.lyrics_timing.name,
        "song_sections_llm_ref": args.song_sections_llm.name,
        "mv_global_visual_style_ref": args.mv_global_visual_style.name,
    }


def main() -> None:
    load_aigc_dotenv()
    if not os.getenv("AIGC_GITEE_API_KEY") and os.getenv("GITEE_API_TOKEN"):
        os.environ["AIGC_GITEE_API_KEY"] = os.getenv("GITEE_API_TOKEN", "")

    import config as qwen_cfg  # noqa: E402

    ap = argparse.ArgumentParser(description="Qwen3 director → mv-keyframe-director JSON")
    ap.add_argument("--lyrics-timing", required=True, type=Path)
    ap.add_argument("--song-sections-llm", required=True, type=Path)
    ap.add_argument("--mv-global-visual-style", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--temperature", type=float, default=0.28)
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--timeout", type=int, default=420)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    timing = load_timing(args.lyrics_timing.resolve())
    llm = load_sections_llm(args.song_sections_llm.resolve())
    gstyle = load_mv_style(args.mv_global_visual_style.resolve())

    line_order = line_id_order(timing)
    l2s = line_to_section_map(llm)
    if set(l2s.keys()) != set(line_order):
        raise SystemExit("song-sections-llm line coverage does not match lyrics-timing lines.")

    dur = timing_duration_hint(timing)

    user_blob = {
        "director_task": "mv_keyframe_and_i2v_prompt_plan",
        "constraints": {
            "one_keyframe_covers_many_consecutive_lines": True,
            "full_timeline_partition": True,
            "enforce_visual_style_by_section_role": True,
            "narrative_and_visual_continuity": True,
            "song_duration_seconds_hint": round3(dur) if dur else None,
            "lines_total": len(line_order),
            "recommended_keyframe_count_range": [
                max(4, int(dur / 28)) if dur else None,
                min(len(line_order), max(8, int(dur / 9))) if dur else None,
            ],
        },
        "line_order": line_order,
        "song_sections": llm.get("sections"),
        "lyrics_timing_lines": slim_lines_for_director(timing["lines"]),
        "sections_with_lyrics": sections_digest_for_director(llm, timing),
        "mv_global_visual_style": slim_style_for_prompt(gstyle),
    }
    user_prefix = (
        "输入如下 JSON。请严格遵守系统说明输出 director JSON。\n"
        "【必须】keyframes 中所有 line_refs 依次拼接后，与 line_order 完全一致，"
        "共 " + str(len(line_order)) + " 个 line_id，不得遗漏、不得重复、不得打乱顺序。\n"
    )
    base_user_json = json.dumps(user_blob, ensure_ascii=False)

    if args.dry_run:
        payload = {
            "model": qwen_cfg.DEFAULT_MODEL,
            "stream": False,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "top_p": 0.85,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prefix + base_user_json},
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if not qwen_cfg.API_KEY:
        raise SystemExit("Missing AIGC_GITEE_API_KEY.")

    retry_hint = ""
    model_obj: dict[str, Any] | None = None
    raw_kfs: list[dict[str, Any]] | None = None
    for attempt in range(3):
        user_text = user_prefix + base_user_json + retry_hint
        payload = {
            "model": qwen_cfg.DEFAULT_MODEL,
            "stream": False,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "top_p": 0.85,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
        }
        resp = post_messages(qwen_cfg.API_URL, qwen_cfg.API_KEY, payload, timeout=args.timeout)
        model_obj = parse_model_json(extract_assistant_text(resp))
        try:
            raw_kfs = validate_model_payload(model_obj, line_order, dur, l2s)
        except SystemExit as e:
            msg = e.args[0] if e.args else "validation failed"
            if attempt >= 2:
                raise SystemExit(msg) from None
            retry_hint = (
                "\n\n【上次校验失败，请仅输出修正后的完整 JSON，不要解释】\n"
                f"原因：{msg}\n"
                f"line_order 共 {len(line_order)} 行；每个 line_id 必须出现且恰好一次；"
                "按 keyframes 顺序拼接 line_refs 必须等于 line_order。"
            )
            continue
        break

    assert model_obj is not None and raw_kfs is not None

    song_title = model_obj.get("song_title") or gstyle.get("song_title") or Path(
        str(timing.get("source_file") or "Untitled")
    ).stem or "Untitled"
    artist = model_obj.get("artist") or gstyle.get("artist")

    enriched_kfs = enrich_keyframes(raw_kfs, timing)

    out_payload: dict[str, Any] = {
        "schema_version": "1.0",
        "song_title": song_title or "Untitled",
        "source_refs": default_source_refs(args),
        "keyframes": enriched_kfs,
    }
    if artist:
        out_payload["artist"] = artist
    if model_obj.get("director_notes_zh"):
        out_payload["director_notes_zh"] = model_obj["director_notes_zh"]

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
