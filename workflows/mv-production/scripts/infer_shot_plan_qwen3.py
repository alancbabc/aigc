#!/usr/bin/env python3
"""Qwen3.5 splits each segment-interpretation segment into executable shots.

Reads segment-interpretation.json, sends non-instrumental segments to
Qwen3.5 for shot planning. Instrumental segments get ambient_hold placeholders.

Output matches contracts/shot-plan/shot-plan.schema.json.
"""

from __future__ import annotations

import argparse
import json
import os
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

SHOT_ROLES = [
    "establishing_image",
    "symbolic_detail",
    "emotional_peak",
    "transition_image",
    "motif_development",
    "ambient_hold",
    "memory_echo",
    "climax_image",
    "resolution_image",
]

SYSTEM_PROMPT = """你是意象型音乐 MV 分镜规划器。根据 segment-interpretation.json 生成 shot_plan。

# 核心约束

1. 每个 shot 必须属于一个 parent_segment_id
2. 每个 shot 的 start_time/end_time 必须落在 parent segment 的 time_range 内
3. 每个 segment 的多个 shot 必须完整覆盖该 segment 的时间窗（无空隙无重叠）
4. 每个 shot 时长建议 5–14 秒
5. 每个 shot 只保留一个核心视觉动作（一个主运动）
6. 画面偏意象化：剪影、轮廓、发光丝线、倒影、远景、半透明元素
7. 避免剧情化人物表演（无牵手、拥抱、哭泣、对话、面部特写）
8. 输出严格 JSON，不要解释文字

# 拆分规则

- 按意象转换拆：当核心视觉主体从 A 变为 B 时，应拆为两个 shot
- 按情绪推进拆：当情绪从一种状态推向另一种状态时，应拆为不同 shot
- 按运动方式拆：一个 shot 只保留一个主运动（如"海浪上升"和"大鱼游过"应分开）
- recommended_shot_count 是建议值，实际数量可以 ±1

# shot_role 枚举

establishing_image: 建立画面世界
symbolic_detail: 象征物特写或细节
emotional_peak: 情绪顶点
transition_image: 过渡画面
motif_development: 意象演化
ambient_hold: 空段延续（不生成新图，复用前一个 shot）
memory_echo: 回忆回响
climax_image: 高潮画面
resolution_image: 收束画面

# composition 字段枚举

shot_size: extreme_wide_shot | wide_shot | medium_wide_shot | medium_shot | medium_close_up | close_up | extreme_close_up
camera_angle: eye_level | low_angle | slightly_low_angle | high_angle | slightly_high_angle | dutch_angle | overhead
depth: shallow_space | medium_space | deep_space | flat_space

# camera 字段枚举

camera_motion: static | slow_push_in | slow_pull_out | slow_pan_left | slow_pan_right | slow_tilt_up | slow_tilt_down | slow_dolly | slow_tracking | slow_zoom_in | slow_zoom_out | floating_drift | none_or_minimal_drift
movement_speed: very_slow | slow | moderate
lens_feeling: wide_cinematic | standard | telephoto_compressed | macro_dreamlike
stability: locked | floating | handheld_subtle | drifting

# motion_design

motion_intensity: very_low | low | medium | high

# visual_style 和 emotion

visual_style.scene_type: 来自 parent segment 的 scene_type
visual_style.color_palette: 来自 parent segment 的 color_palette，可以微调但必须与全曲统一色系一致
visual_style.lighting: 来自 parent segment 的 lighting
emotion.intensity: 来自 parent segment 的 emotional_intensity，每个 shot 可在此基础上微调 ±0.1

# transition

transition_in / transition_out 使用英文描述
transition_duration 默认为 1.0 秒

# generation_notes

image_prompt_focus: 这个 shot 如果要生成静帧，prompt 应该聚焦什么（英文词或短语）
video_prompt_focus: 这个 shot 如果要生成视频，prompt 应该聚焦什么（英文词或短语）
avoid: 必须避免的元素，3-5 个中文短语

# JSON 输出格式

{
  "schema_version": "1.0",
  "shots": [
    {
      "shot_id": "shot_v1_01_01",
      "parent_segment_id": "seg_v1_01",
      "time_range": {"start_time": 43.65, "end_time": 56.0, "duration_seconds": 12.35},
      "lyric_refs": ["line_01", "line_02"],
      "shot_role": "establishing_image",
      "visual_concept_zh": "...",
      "deep_function_zh": "...",
      "key_imagery": ["...", "..."],
      "secondary_imagery": ["...", "..."],
      "composition": {
        "shot_size": "extreme_wide_shot",
        "camera_angle": "slightly_low_angle",
        "foreground": "...",
        "midground": "...",
        "background": "...",
        "focal_point": "...",
        "depth": "deep_space"
      },
      "camera": {
        "camera_motion": "slow_push_in",
        "movement_speed": "very_slow",
        "lens_feeling": "wide_cinematic",
        "stability": "floating"
      },
      "motion_design": {
        "subject_motion": "...",
        "environment_motion": "...",
        "motion_intensity": "low"
      },
      "visual_style": {
        "scene_type": "dream_ocean_night",
        "color_palette": ["深蓝", "银白"],
        "lighting": "...",
        "texture": "..."
      },
      "emotion": {"primary": "静谧", "secondary": ["神秘"], "intensity": 0.45},
      "transition": {"transition_in": "fade_from_dark_blue", "transition_out": "soft_dissolve", "transition_duration": 1.0},
      "generation_notes": {
        "image_prompt_focus": "...",
        "video_prompt_focus": "...",
        "avoid": ["...", "..."]
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


def load_segment_interpretation(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema_version") != "1.0":
        raise SystemExit(f"Unsupported segment-interpretation schema_version: {data.get('schema_version')!r}")
    if not isinstance(data.get("segments"), list) or not data["segments"]:
        raise SystemExit("segment-interpretation missing non-empty 'segments'.")
    return data


def build_qwen_input(seg_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract non-instrumental segments to send to Qwen3.5."""
    qwen_input: list[dict[str, Any]] = []
    for seg in seg_data["segments"]:
        if seg.get("is_instrumental"):
            continue
        imag_list = seg.get("imagery", [])
        core_img = []
        for img in imag_list:
            if not isinstance(img, dict):
                continue
            core_img.append({
                "image_zh": img.get("image_zh", ""),
                "image_en": img.get("image_en", ""),
                "visual_priority": img.get("visual_priority", 0.5),
            })
        vd = seg.get("visual_direction", {})
        interp = seg.get("interpretation", {})
        qwen_input.append({
            "segment_id": seg["segment_id"],
            "start_time": seg["time_range"]["start_time"],
            "end_time": seg["time_range"]["end_time"],
            "duration_seconds": seg["time_range"]["duration_seconds"],
            "lyrics_text": seg["lyrics"]["lyrics_text"],
            "deep_meaning_zh": interp.get("deep_meaning_zh", ""),
            "emotional_state_zh": interp.get("emotional_state_zh", []),
            "emotional_intensity": interp.get("emotional_intensity", 0.5),
            "core_imagery": core_img,
            "scene_type": vd.get("scene_type", ""),
            "color_palette": vd.get("color_palette", []),
            "lighting": vd.get("lighting", ""),
            "recommended_shot_count": seg["shot_planning_hint"].get("recommended_shot_count", 2),
            "variation_from": seg["shot_planning_hint"].get("variation_from"),
            "variation_strategy": seg["shot_planning_hint"].get("variation_strategy"),
            "must_include": seg.get("generation_constraints", {}).get("must_include", []),
            "avoid": seg.get("generation_constraints", {}).get("avoid", []),
        })
    return qwen_input


REQUIRED_SHOT = [
    "shot_id", "parent_segment_id", "time_range", "lyric_refs", "shot_role",
    "visual_concept_zh", "key_imagery", "secondary_imagery",
    "composition", "camera", "motion_design",
    "transition", "generation_notes",
]


def validate_and_fix_shots(
    shots: list[dict[str, Any]],
    seg_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Post-process shots: inject parent_section_id, validate timing, validate enums."""
    seg_lookup: dict[str, dict[str, Any]] = {}
    for seg in seg_data["segments"]:
        seg_lookup[seg["segment_id"]] = seg

    for i, s in enumerate(shots):
        # Inject parent_section_id
        pseg = seg_lookup.get(s.get("parent_segment_id", ""), {})
        s["parent_section_id"] = pseg.get("parent_section_id", "")

        # Validate timing
        tr = s.get("time_range", {})
        seg_start = pseg.get("time_range", {}).get("start_time", 0)
        seg_end = pseg.get("time_range", {}).get("end_time", 0)
        st = tr.get("start_time", seg_start)
        et = tr.get("end_time", seg_end)
        if st < seg_start - 0.5 or et > seg_end + 0.5:
            print(f"  [warn] shot[{i}] {s.get('shot_id','?')} time {st}-{et} outside segment [{seg_start}-{seg_end}], clamping")
            st = max(st, seg_start)
            et = min(et, seg_end)
        s["time_range"]["start_time"] = round(st, 2)
        s["time_range"]["end_time"] = round(et, 2)
        s["time_range"]["duration_seconds"] = round(et - st, 2)

        # Validate shot_role
        if s.get("shot_role") not in SHOT_ROLES:
            s["shot_role"] = "symbolic_detail"

        # Inject visual_style / emotion from parent segment if missing
        vd = pseg.get("visual_direction", {})
        if not s.get("visual_style"):
            s["visual_style"] = {
                "scene_type": vd.get("scene_type", ""),
                "color_palette": vd.get("color_palette", []),
                "lighting": vd.get("lighting", ""),
                "texture": "柔雾感、梦境感",
            }
        interp = pseg.get("interpretation", {})
        if not s.get("emotion"):
            s["emotion"] = {
                "primary": interp.get("emotional_state_zh", [""])[0] if interp.get("emotional_state_zh") else "",
                "secondary": interp.get("emotional_state_zh", [])[1:],
                "intensity": interp.get("emotional_intensity", 0.5),
            }

        # Validate missing required fields
        missing = [k for k in REQUIRED_SHOT if k not in s]
        if missing:
            print(f"  [warn] shot[{i}] {s.get('shot_id','?')} missing keys: {missing}")

    return shots


def make_ambient_hold(
    seg: dict[str, Any],
    previous_shot_id: str | None,
    shot_index: int,
) -> dict[str, Any]:
    """Create ambient_hold placeholder for instrumental segments."""
    tr = seg.get("time_range", {})
    vd = seg.get("visual_direction", {})
    interp = seg.get("interpretation", {})
    return {
        "shot_id": f"shot_{seg['segment_id']}_hold",
        "parent_segment_id": seg["segment_id"],
        "parent_section_id": seg.get("parent_section_id", ""),
        "time_range": {
            "start_time": tr.get("start_time", 0),
            "end_time": tr.get("end_time", 0),
            "duration_seconds": tr.get("duration_seconds", 0),
        },
        "lyric_refs": seg.get("lyrics", {}).get("line_refs", []),
        "shot_role": "ambient_hold",
        "visual_concept_zh": "延续前一段画面的最后一帧，轻微淡出。",
        "deep_function_zh": "作为段落间的呼吸停顿，不生成新的关键帧。",
        "key_imagery": [],
        "secondary_imagery": [],
        "composition": {
            "shot_size": "wide_shot",
            "camera_angle": "eye_level",
            "foreground": "残留光粒子",
            "midground": "渐暗的空间",
            "background": "远方模糊剪影",
            "focal_point": "逐渐消散的光粒子",
            "depth": "medium_space",
        },
        "camera": {
            "camera_motion": "none_or_minimal_drift",
            "movement_speed": "very_slow",
            "lens_feeling": "standard",
            "stability": "drifting",
        },
        "motion_design": {
            "subject_motion": "光粒子尾迹逐渐消散",
            "environment_motion": "光点缓慢漂浮",
            "motion_intensity": "very_low",
        },
        "visual_style": {
            "scene_type": vd.get("scene_type", ""),
            "color_palette": vd.get("color_palette", []),
            "lighting": vd.get("lighting", ""),
            "texture": "柔雾感",
        },
        "emotion": {
            "primary": "延续",
            "secondary": [],
            "intensity": interp.get("emotional_intensity", 0.0),
        },
        "transition": {
            "transition_in": "none",
            "transition_out": "none",
            "transition_duration": 0,
        },
        "generation_notes": {
            "generate_new_image": False,
            "reuse_from_shot_id": previous_shot_id or "",
            "image_prompt_focus": "复用前一个shot画面",
            "video_prompt_focus": "静态保持，轻微淡出",
            "avoid": [],
        },
    }


def merge_and_sort(
    model_shots: list[dict[str, Any]],
    seg_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge Qwen3.5 shots with ambient_holds, sort by time."""
    result: list[dict[str, Any]] = []
    seg_order = [s["segment_id"] for s in seg_data["segments"]]
    seg_lookup = {s["segment_id"]: s for s in seg_data["segments"]}

    model_by_seg: dict[str, list[dict[str, Any]]] = {}
    for s in model_shots:
        ps = s.get("parent_segment_id", "")
        model_by_seg.setdefault(ps, []).append(s)

    previous_shot_id: str | None = None
    for seg_id in seg_order:
        seg = seg_lookup.get(seg_id, {})
        if seg.get("is_instrumental"):
            hold = make_ambient_hold(seg, previous_shot_id, 0)
            result.append(hold)
        else:
            shots_for_seg = model_by_seg.get(seg_id, [])
            for s in shots_for_seg:
                result.append(s)
                previous_shot_id = s.get("shot_id")
        # Update previous_shot_id to the last non-instrumental shot
        if not seg.get("is_instrumental"):
            seg_shots = model_by_seg.get(seg_id, [])
            if seg_shots:
                previous_shot_id = seg_shots[-1].get("shot_id")

    result.sort(key=lambda s: s["time_range"]["start_time"])
    return result


def verify_coverage(shots: list[dict[str, Any]], seg_data: dict[str, Any]) -> None:
    """Check that shots cover parent segments properly."""
    seg_lookup = {s["segment_id"]: s for s in seg_data["segments"]}
    for seg_id, seg in seg_lookup.items():
        if seg.get("is_instrumental"):
            continue
        seg_start = seg["time_range"]["start_time"]
        seg_end = seg["time_range"]["end_time"]
        seg_shots = [s for s in shots if s["parent_segment_id"] == seg_id]
        if not seg_shots:
            print(f"  [warn] segment {seg_id}: no shots generated")
            continue
        shot_start = min(s["time_range"]["start_time"] for s in seg_shots)
        shot_end = max(s["time_range"]["end_time"] for s in seg_shots)
        gap_start = abs(shot_start - seg_start)
        gap_end = abs(shot_end - seg_end)
        if gap_start > 1.0 or gap_end > 1.0:
            print(f"  [warn] segment {seg_id}: coverage gap ({seg_start}-{seg_end}) vs shots ({shot_start}-{shot_end})")


def main() -> None:
    load_aigc_dotenv()
    if not os.getenv("AIGC_GITEE_API_KEY") and os.getenv("GITEE_API_TOKEN"):
        os.environ["AIGC_GITEE_API_KEY"] = os.getenv("GITEE_API_TOKEN", "")

    import config as qwen_cfg  # noqa: E402

    ap = argparse.ArgumentParser(description="Qwen3.5 shot planner from segment-interpretation.json")
    ap.add_argument("--segment-interpretation", required=True, type=Path, help="segment-interpretation.json")
    ap.add_argument("--out", required=True, type=Path, help="Output shot-plan.json")
    ap.add_argument("--temperature", type=float, default=0.25)
    ap.add_argument("--max-tokens", type=int, default=24576)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    seg_path = args.segment_interpretation.resolve()
    seg_data = load_segment_interpretation(seg_path)
    qwen_input = build_qwen_input(seg_data)

    song_title = seg_data.get("song_title", seg_path.stem)

    non_inst = [s for s in seg_data["segments"] if not s.get("is_instrumental")]
    print(f"Segments: {len(seg_data['segments'])} total, {len(non_inst)} non-instrumental")

    if not qwen_input:
        raise SystemExit("No non-instrumental segments to process.")

    user_blob = {
        "task": "shot_planning",
        "constraints": {
            "shot_duration_range": "5–14 seconds per shot",
            "one_primary_motion_per_shot": True,
            "imagery_style": "imagery-type MV: silhouettes, light threads, reflections, distant views, semi-transparent elements",
            "avoid_narrative_acting": True,
            "tile_parent_segment_completely": True,
        },
        "song_title": song_title,
        "artist": seg_data.get("artist"),
        "segments_to_plan": qwen_input,
    }
    user_text = (
        f"为以下 {len(qwen_input)} 个 segment 规划分镜。\n"
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
            retry_hint = f"\n\n[上次失败] {msg}\n请仅输出修正后的完整JSON。"
            continue
        break

    assert model_obj is not None
    model_shots = model_obj.get("shots", [])

    model_shots = validate_and_fix_shots(model_shots, seg_data)
    all_shots = merge_and_sort(model_shots, seg_data)
    verify_coverage(all_shots, seg_data)

    out_obj = {
        "schema_version": "1.0",
        "song_title": song_title,
        "artist": seg_data.get("artist"),
        "source_segment_interpretation_ref": seg_path.name,
        "shot_generation_rules": {
            "min_shot_duration": 4.0,
            "target_shot_duration": 8.0,
            "max_shot_duration": 14.0,
            "instrumental_hold_policy": "reuse_previous_visual_or_create_ambient_hold",
            "long_segment_policy": "split_before_shot_planning_if_over_40_seconds",
        },
        "shots": all_shots,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    inst_count = sum(1 for s in all_shots if s.get("shot_role") == "ambient_hold")
    print(f"Wrote {out_path} ({len(all_shots)} shots, {inst_count} ambient_holds)")


if __name__ == "__main__":
    main()
