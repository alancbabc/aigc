#!/usr/bin/env python3
"""Qwen3.5 interprets each visual segment from song-sections-llm.json v2.0.

Reads song-sections-llm.json (v2.0, with enriched per-section fields),
extracts all visual_segments, and sends non-instrumental segments to
Qwen3.5 for semantic interpretation. Instrumental-only segments
(where ALL line_refs are is_instrumental=true) get placeholder entries.

Output matches contracts/segment-interpretation/segment-interpretation.schema.json.
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

SYSTEM_PROMPT = """你是 MV 视觉导演助理。你的任务不是写 prompt，而是把每个「歌词段落 segment」升级为「可供后续导演生成 prompt 的语义块」。

你会收到一组 segment，每个 segment 包含：
- segment_id, parent_section_id, section_type
- lyrics_text（该 segment 涵盖的歌词原始文本）
- parent_section 的 role_in_song_zh（该段落在全曲中的作用）、core_emotion_zh（核心情绪）、variation（与重复段落的情感冒化关系）

# 核心原则：这是「意象型 MV」，不是「剧情型 MV」

整支 MV 的风格是：梦境流、意识流、东方空灵美学。它不是线性故事，不依赖人物表演来推进叙事。

**人物表现规则**：
- 不要出现明确的人物动作（牵手、奔跑、拥抱、哭泣、对话等）
- 不要出现具体的面部表情或角色互动
- 人物应弱化为：剪影、轮廓、背影、丝线相连的光点、水中倒影、远处微小身影
- 如果歌词中有"执子手""凝望"等动作 → 翻译成象征：发光丝线相连的两道剪影、远处光点与暗影的对望

**构图规则**：
- composition_zh 不应描述人物动作，应描述：空间关系、光影分布、元素位置、尺度对比
- 正确示例："两道模糊剪影之间有发光丝线相连，远处烟波被风吹散"
- 错误示例："两人牵手背影，面对广阔海面"

**色彩规则**：
- 全曲的 color_palette 应保持统一的美学体系：深蓝、银白、青色微光、暖金、灰蓝、暗紫
- 即使是情绪最激烈的段落（chorus），也只能在统一色系内加深或提亮，不能突然跳入完全不同的色系
- 禁止使用："深红""惨白""纯黑""荧光色"等破坏整体氛围的颜色
- 副歌如需情绪强度 → 用"暗紫""冷白""微弱红光""亮金"等与基础色系有延续关系的颜色

**镜头规则**：
- camera_mood 描述的是镜头的呼吸节奏，不是人物的情绪
- 正确："缓慢、漂浮、梦境感""上升、释放、逐渐稀薄""凝视、静止、时间凝固"
- 错误："紧张、急促、不安""深情""决绝"（这些是人物情绪，不是镜头情绪）

# 重复段落的变奏关系

对于歌词相同或结构重复的 segment（如 seg_v1_01 和 seg_v2_01），你必须在 shot_planning_hint 中额外给出：
- variation_from: 与哪个 segment 构成重复关系（填 segment_id）
- variation_strategy: 如何让两个 segment 在视觉上既统一又有差异（英文 snake_case 代号）

常用 variation_strategy：
- same_composition_colder_tone: 相同构图，色调更冷
- same_composition_darker_memory: 相同构图，加入回忆滤镜、暗角
- same_composition_reversed_angle: 相同构图，镜头角度反转
- same_elements_further_distance: 相同元素，拉远距离（人更小、空间更大）
- same_elements_more_ethereal: 相同元素，更虚化、更透明、更梦幻

# 回答以下问题

对每个 segment，你必须回答：

1) interpretation — 核心语义层
   - literal_meaning_zh
   - deep_meaning_zh
   - emotional_state_zh: 情绪关键词数组，2-5 个词
   - emotional_intensity: 0.0-1.0

2) imagery — 意象素材库
   每个意象：image_zh, image_en, type, visual_priority(0.0-1.0), symbolic_meaning_zh

3) visual_direction — 视觉方向（遵循意象型MV约束）
   - scene_type: 英文 snake_case
   - setting_zh: 场景描述（梦境空间，不是真实地点）
   - color_palette: 3-6 个中文颜色词（保持在统一色系内）
   - lighting: 光照描述
   - composition_zh: 构图（空间关系、光影、元素位置，不是人物动作）
   - camera_mood: 镜头呼吸节奏，不是人物情绪

4) shot_planning_hint — 给后续 shot_plan 阶段的提示
   - recommended_shot_count (>=1)
   - keyframe_count (>=1)
   - motion_intensity: "none"/"low"/"medium"/"high"
   - transition_in, transition_out
   - variation_from: 如有重复段落，填对应 segment_id，否则 null
   - variation_strategy: 如有重复段落，填策略代号，否则 null

5) generation_constraints — 生成约束
   - must_include: 3-5 个
   - avoid: 3-5 个（额外避免：人物正面、明确动作、剧情化场景）

硬性规则：
- 只输出「一个合法 JSON 对象」，不要 Markdown、不要前后说明文字。
- schema_version 必须为 "1.0"。

JSON 输出格式：
{
  "schema_version": "1.0",
  "segments": [
    {
      "segment_id": "seg_v1_01",
      "interpretation": {
        "literal_meaning_zh": "…",
        "deep_meaning_zh": "…",
        "emotional_state_zh": ["静谧", "神秘", "温柔"],
        "emotional_intensity": 0.45
      },
      "imagery": [
        { "image_zh": "无声海浪", "image_en": "silent ocean waves", "type": "natural", "visual_priority": 0.9, "symbolic_meaning_zh": "…" }
      ],
      "visual_direction": {
        "scene_type": "dream_ocean_night",
        "setting_zh": "夜空与海洋交融的梦境空间",
        "color_palette": ["深蓝", "银白", "青色微光"],
        "lighting": "柔和月光从水面渗透",
        "composition_zh": "两道模糊剪影之间有发光丝线相连，远处烟波被风吹散",
        "camera_mood": "缓慢、漂浮、梦境感"
      },
      "shot_planning_hint": {
        "recommended_shot_count": 2,
        "keyframe_count": 2,
        "motion_intensity": "low",
        "transition_in": "fade_from_dark_blue",
        "transition_out": "soft_dissolve",
        "variation_from": null,
        "variation_strategy": null
      },
      "generation_constraints": {
        "must_include": ["大鱼轮廓", "海天交融", "梦境氛围"],
        "avoid": ["人物正面", "明确动作", "现实街景", "剧情化"]
      }
    }
  ]
}
"""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def unwrap_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        stripped = []
        for row in lines:
            if stripped or not row.strip().startswith("```"):
                stripped.append(row)
            elif row.strip() == "```":
                break
        text = "\n".join(stripped[1:] if stripped and stripped[0].strip() == "```" else stripped).strip()
    return text


def parse_model_json(raw_text: str) -> dict[str, Any]:
    text = unwrap_json_fence(raw_text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Assistant did not return valid JSON: {e}\n{text[:1200]}") from e


def load_sections_llm(path: Path) -> dict[str, Any]:
    data = load_json(path)
    ver = data.get("schema_version")
    if ver not in ("1.0", "2.0"):
        raise SystemExit(f"Unsupported song-sections-llm schema_version: {ver!r}")
    if not isinstance(data.get("sections"), list) or not data["sections"]:
        raise SystemExit("song-sections-llm missing non-empty 'sections'.")
    return data


def load_timing(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema_version") not in ("1.0", "1.1"):
        raise SystemExit(f"Unsupported lyrics-timing schema_version: {data.get('schema_version')!r}")
    if not isinstance(data.get("lines"), list):
        raise SystemExit("lyrics-timing missing 'lines'.")
    return data


def extract_non_instrumental_segments(
    llm: dict[str, Any],
    lyrics_timing: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract all visual_segments, split into non-instrumental (to send to Qwen3) and instrumental (placeholder)."""
    by_id = {}
    for ln in lyrics_timing.get("lines", []):
        by_id[str(ln.get("line_id", ""))] = ln

    qwen_input: list[dict[str, Any]] = []
    instrumental_placeholders: list[dict[str, Any]] = []

    for sec in llm.get("sections", []):
        if not isinstance(sec, dict):
            continue
        section_id = sec.get("section_id", "")
        section_type = sec.get("section_type", "")
        role = sec.get("role_in_song_zh", "")
        emotion = sec.get("core_emotion_zh", "")
        variation = sec.get("variation", {})

        for seg in sec.get("visual_segments", []):
            if not isinstance(seg, dict):
                continue
            seg_id = seg.get("segment_id", "")
            refs = seg.get("line_refs", [])
            lyrics_text = seg.get("lyrics_text", "")

            # Check if ALL lines in this segment are instrumental
            all_instrumental = True
            for rid in refs:
                ln = by_id.get(str(rid))
                if ln and ln.get("is_instrumental") is not True:
                    all_instrumental = False
                    break
            if not refs:
                all_instrumental = False

            if all_instrumental:
                # Instrumental: create placeholder
                instrumental_placeholders.append({
                    "segment_id": seg_id,
                    "parent_section_id": section_id,
                    "section_type": section_type,
                    "is_instrumental": True,
                    "line_refs": refs,
                    "lyrics_text": "",
                })
            else:
                qwen_input.append({
                    "segment_id": seg_id,
                    "parent_section_id": section_id,
                    "section_type": section_type,
                    "line_refs": refs,
                    "lyrics_text": lyrics_text,
                    "parent_role_in_song_zh": role,
                    "parent_core_emotion_zh": emotion,
                    "parent_variation": {
                        "related_section": variation.get("related_section"),
                        "relationship_zh": variation.get("relationship_zh", ""),
                    } if variation else None,
                })

    return qwen_input, instrumental_placeholders


def make_instrumental_placeholder(
    seg: dict[str, Any],
    timing: dict[str, Any],
) -> dict[str, Any]:
    """Create a full instrumental placeholder segment."""
    by_id = {}
    for ln in timing.get("lines", []):
        by_id[str(ln.get("line_id", ""))] = ln

    refs = seg.get("line_refs", [])
    first_ln = by_id.get(str(refs[0])) if refs else None
    last_ln = by_id.get(str(refs[-1])) if refs else None
    start = float(first_ln.get("start_time", 0)) if first_ln else 0.0
    end = float(last_ln.get("end_time", start)) if last_ln else 0.0

    return {
        "segment_id": seg["segment_id"],
        "parent_section_id": seg["parent_section_id"],
        "section_type": seg["section_type"],
        "is_instrumental": True,
        "time_range": {
            "start_time": start,
            "end_time": end,
            "duration_seconds": round(end - start, 2),
        },
        "lyrics": {
            "line_refs": refs,
            "lyrics_text": "",
        },
        "interpretation": {
            "literal_meaning_zh": "(器乐间奏，无歌词)",
            "deep_meaning_zh": "间奏/过渡段落，画面延续前一段的梦境氛围，不做单独画面切换。后续阶段可复用前一 segment 的最后一帧作为静态画面。",
            "emotional_state_zh": ["延续"],
            "emotional_intensity": 0.0,
        },
        "imagery": [],
        "visual_direction": {
            "scene_type": "instrumental_hold",
            "setting_zh": "延续前段画面，保持视觉连续性",
            "color_palette": ["延续前段"],
            "lighting": "延续前段",
            "composition_zh": "保持前段画面的最后一帧，不做切换",
            "camera_mood": "静止",
        },
        "shot_planning_hint": {
            "recommended_shot_count": 0,
            "keyframe_count": 0,
            "motion_intensity": "none",
            "transition_in": "none",
            "transition_out": "none",
            "variation_from": None,
            "variation_strategy": None,
        },
        "generation_constraints": {
            "must_include": [],
            "avoid": [],
        },
    }


def inject_timing(
    qwen_keys: list[str],
    model_segments: list[dict[str, Any]],
    instrumental_placeholders: list[dict[str, Any]],
    qwen_input: list[dict[str, Any]],
    timing: dict[str, Any],
    all_segments_order: list[str],
) -> list[dict[str, Any]]:
    """Merge model output with timing data and instrumental placeholders."""
    by_id = {}
    for ln in timing.get("lines", []):
        by_id[str(ln.get("line_id", ""))] = ln

    # Build model output lookup
    model_by_seg_id: dict[str, dict[str, Any]] = {}
    for entry in model_segments:
        sid = entry.get("segment_id", "")
        model_by_seg_id[sid] = entry

    # Build qwen_input lookup for line_refs
    input_by_seg_id: dict[str, dict[str, Any]] = {}
    for item in qwen_input:
        input_by_seg_id[item["segment_id"]] = item

    # Build instrumental lookup
    inst_by_seg_id: dict[str, dict[str, Any]] = {}
    for inst in instrumental_placeholders:
        inst_by_seg_id[inst["segment_id"]] = inst

    result: list[dict[str, Any]] = []
    for seg_id in all_segments_order:
        if seg_id in inst_by_seg_id:
            result.append(make_instrumental_placeholder(inst_by_seg_id[seg_id], timing))
            continue

        model = model_by_seg_id.get(seg_id, {})
        inp = input_by_seg_id.get(seg_id, {})
        refs = inp.get("line_refs", [])
        first_ln = by_id.get(str(refs[0])) if refs else None
        last_ln = by_id.get(str(refs[-1])) if refs else None
        start = float(first_ln.get("start_time", 0)) if first_ln else 0.0
        end = float(last_ln.get("end_time", start)) if last_ln else 0.0

        interp = model.get("interpretation", {})
        result.append({
            "segment_id": seg_id,
            "parent_section_id": inp.get("parent_section_id", ""),
            "section_type": inp.get("section_type", ""),
            "is_instrumental": False,
            "time_range": {
                "start_time": start,
                "end_time": end,
                "duration_seconds": round(end - start, 2),
            },
            "lyrics": {
                "line_refs": refs,
                "lyrics_text": inp.get("lyrics_text", ""),
            },
            "interpretation": {
                "literal_meaning_zh": str(interp.get("literal_meaning_zh", "")),
                "deep_meaning_zh": str(interp.get("deep_meaning_zh", "")),
                "emotional_state_zh": interp.get("emotional_state_zh", []) or [],
                "emotional_intensity": float(interp.get("emotional_intensity", 0.5)),
            },
            "imagery": model.get("imagery", []) or [],
            "visual_direction": model.get("visual_direction", {}) or {},
            "shot_planning_hint": {
                "recommended_shot_count": int((model.get("shot_planning_hint", {}) or {}).get("recommended_shot_count", 1)),
                "keyframe_count": int((model.get("shot_planning_hint", {}) or {}).get("keyframe_count", 1)),
                "motion_intensity": str((model.get("shot_planning_hint", {}) or {}).get("motion_intensity", "medium")),
                "transition_in": str((model.get("shot_planning_hint", {}) or {}).get("transition_in", "dissolve")),
                "transition_out": str((model.get("shot_planning_hint", {}) or {}).get("transition_out", "dissolve")),
                "variation_from": (model.get("shot_planning_hint", {}) or {}).get("variation_from"),
                "variation_strategy": (model.get("shot_planning_hint", {}) or {}).get("variation_strategy"),
            },
            "generation_constraints": {
                "must_include": (model.get("generation_constraints", {}) or {}).get("must_include", []) or [],
                "avoid": (model.get("generation_constraints", {}) or {}).get("avoid", []) or [],
            },
        })
    return result


def validate_result(segments: list[dict[str, Any]], total_non_inst: int) -> None:
    """Basic validation of the merged result."""
    if not segments:
        raise SystemExit("Result has no segments.")

    required_top = [
        "segment_id", "parent_section_id", "section_type", "is_instrumental",
        "time_range", "lyrics", "interpretation", "imagery",
        "visual_direction", "shot_planning_hint", "generation_constraints",
    ]
    for i, seg in enumerate(segments):
        missing = [k for k in required_top if k not in seg]
        if missing:
            raise SystemExit(f"segments[{i}] ({seg.get('segment_id', '?')}) missing keys: {missing}")

    non_inst = [s for s in segments if not s["is_instrumental"]]
    print(f"Segments: {len(segments)} total, {len(non_inst)} non-instrumental, "
          f"{len(segments) - len(non_inst)} instrumental placeholders")


def main() -> None:
    load_aigc_dotenv()
    if not os.getenv("AIGC_GITEE_API_KEY") and os.getenv("GITEE_API_TOKEN"):
        os.environ["AIGC_GITEE_API_KEY"] = os.getenv("GITEE_API_TOKEN", "")

    import config as qwen_cfg  # noqa: E402

    ap = argparse.ArgumentParser(description="Qwen3.5 interprets visual segments from song-sections-llm.json v2.0")
    ap.add_argument("--song-sections-llm", required=True, type=Path, help="song-sections-llm.json (v2.0 with visual_segments)")
    ap.add_argument("--lyrics-timing", required=True, type=Path, help="lyrics-timing.json for timing injection")
    ap.add_argument("--out", required=True, type=Path, help="Output segment-interpretation.json")
    ap.add_argument("--temperature", type=float, default=0.25)
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    llm_path = args.song_sections_llm.resolve()
    timing_path = args.lyrics_timing.resolve()
    llm = load_sections_llm(llm_path)
    timing = load_timing(timing_path)

    song_title = llm.get("song_title") or timing.get("song_title") or \
                 (Path(timing.get("source_file", "")).stem if timing.get("source_file") else llm_path.stem)

    qwen_input, instrumental_placeholders = extract_non_instrumental_segments(llm, timing)
    # Build ordered list of ALL segment_ids
    all_segments_order: list[str] = []
    for sec in llm.get("sections", []):
        for seg in sec.get("visual_segments", []):
            all_segments_order.append(seg.get("segment_id", ""))

    print(f"Total visual segments: {len(all_segments_order)}")
    print(f"  Non-instrumental (to Qwen3): {len(qwen_input)}")
    print(f"  Instrumental (placeholder): {len(instrumental_placeholders)}")

    if not qwen_input:
        # All instrumental: produce placeholders only
        print("All segments are instrumental. Producing placeholder-only output.")
        result = [make_instrumental_placeholder(inst, timing) for inst in instrumental_placeholders]
        validate_result(result, 0)
        # Sort by segment order
        order_map = {sid: i for i, sid in enumerate(all_segments_order)}
        result.sort(key=lambda s: order_map.get(s["segment_id"], 999))
        out_obj = {
            "schema_version": "1.0",
            "song_title": song_title,
            "artist": llm.get("artist"),
            "source_sections_llm_ref": llm_path.name,
            "segments": result,
        }
        out_path = args.out.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out_path} ({len(result)} segments, all instrumental)")
        return

    user_blob = {
        "task": "segment_interpretation",
        "constraints": {
            "output_language": "Chinese (zh) for text fields, English (en) for image_en and scene_type",
            "emotional_intensity_range": "0.0 - 1.0",
            "visual_priority_range": "0.0 - 1.0 (most important = 1.0)",
            "keyframe_count_gt_zero": True,
            "each_segment_gets_full_analysis": True,
        },
        "context": {
            "song_title": song_title,
            "artist": llm.get("artist"),
        },
        "segments_to_interpret": qwen_input,
    }
    user_text = (
        f"请解释以下 {len(qwen_input)} 个歌词段落 segment。\n"
        + json.dumps(user_blob, ensure_ascii=False)
    )

    payload = {
        "model": qwen_cfg.DEFAULT_MODEL,
        "stream": False,
        "enable_thinking": False,
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
        raise SystemExit("Missing AIGC_GITEE_API_KEY.")

    retry_hint = ""
    model_obj: dict[str, Any] | None = None
    for attempt in range(3):
        full_user = user_text + retry_hint
        payload["messages"][1]["content"] = full_user
        try:
            response = post_messages(qwen_cfg.API_URL, qwen_cfg.API_KEY, payload, timeout=args.timeout)
            assistant_text = extract_assistant_text(response)
            model_obj = parse_model_json(assistant_text)
        except SystemExit as e:
            msg = e.args[0] if e.args else "unknown"
            if attempt >= 2:
                raise SystemExit(msg) from None
            retry_hint = (
                "\n\n【上次失败，请仅输出修正后的完整 JSON，不要解释】\n"
                f"原因：{msg}\n"
                f"请确保对全部 {len(qwen_input)} 个 segment 都给出了解释。"
            )
            continue

        # Validate we got all segments
        model_segments = model_obj.get("segments", []) if model_obj else []
        model_ids = {s.get("segment_id") for s in model_segments if isinstance(s, dict)}
        expected_ids = {item["segment_id"] for item in qwen_input}
        missing_ids = expected_ids - model_ids
        if missing_ids:
            if attempt >= 2:
                raise SystemExit(f"Model missed segments: {sorted(missing_ids)!r}")
            retry_hint = (
                "\n\n【上次遗漏了 segment，请补全后再输出】\n"
                f"缺失的 segment_id：{sorted(missing_ids)!r}，请确保全部 {len(qwen_input)} 个 segment 都在 segments 数组中。"
            )
            continue
        break

    assert model_obj is not None
    model_segments = model_obj.get("segments", [])

    result = inject_timing(
        [item["segment_id"] for item in qwen_input],
        model_segments,
        instrumental_placeholders,
        qwen_input,
        timing,
        all_segments_order,
    )
    validate_result(result, len(qwen_input))
    order_map = {sid: i for i, sid in enumerate(all_segments_order)}
    result.sort(key=lambda s: order_map.get(s["segment_id"], 999))

    out_obj = {
        "schema_version": "1.0",
        "song_title": song_title,
        "artist": llm.get("artist"),
        "source_sections_llm_ref": llm_path.name,
        "segments": result,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
