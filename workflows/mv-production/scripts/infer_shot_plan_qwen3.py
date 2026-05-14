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
4. 不限制 shot 的最短和最长时长
5. 画面偏意象化：剪影、轮廓、发光丝线、倒影、远景、半透明元素
6. 避免剧情化人物表演（无牵手、拥抱、哭泣、对话、面部特写）
7. 输出严格 JSON，不要解释文字

# 视频生成约束

- API 一次生成视频最大长度为 8 秒
- 大于 8 秒的分镜需用尾帧延长拼接
- 如果分镜生成的视频长度大于对应的时间戳时长，需要裁剪

# 拆分规则

- 按意象转换拆：当核心视觉主体从 A 变为 B 时，应拆为两个 shot
- 按情绪推进拆：当情绪从一种状态推向另一种状态时，应拆为不同 shot
- 按运动方式拆：一个 shot 只保留一个主运动
- recommended_shot_count 是建议值，实际数量可以 ±1

# 每个 shot 必须包含的信息

1. literal_meaning_zh：该 shot 对应歌词的字面含义（直译）
2. deep_meaning：歌词对应的深层意味和含义（它在表达什么？不只是功能描述）
3. static_frame_description：画面里有什么 — 景别、实体、位置、空间关系。必须可被图像模型直接理解执行。简洁具体
4. key_imagery：只取歌词中明确出现的具象实体名。无实体则为空数组 []
5. shot_direction：整合了运镜方式、速度、转场方式的完整镜向

# shot_type 路由（必须遵守）

- shot_type = "lyric_imagery"：歌词有明确视觉实体 → 正常生成意象画面
- shot_type = "singer_performance"：歌词完全抽象、无任何实体 → 歌手演唱场景
  歌手演唱场景的 static_frame_description：一位歌手在画面中演唱（可以是侧影、正面或背影），背景与全片视觉风格一致的油画质感。不同 shot 可以有不同的角度

# key_imagery 规则（关键）

- 只提取歌词中明确出现的具象实体
- 有实体："星空" "麦田" "紫罗兰色的云" "画框" "雪地" "眼睛" "调色板"
- 比喻中的实体也算："他像星星一样闪耀" → "星星" 算
- 无实体 → key_imagery = []
- 禁止：抽象概念（"爱" "痛苦" "孤独"）
- 禁止：自创意象（歌词没说"鱼"就不要加"鱼"）

# static_frame_description 规则

- 必须回答：画面里有什么？在哪里？景别多大？
- 包含：主体、位置关系（前景中景后景）、空间
- 必须可被图像模型直接执行
- 禁止：纯情绪描述、抽象修饰

# shot_direction 规则

- 整合运镜方式（camera_motion, movement_speed, lens_feeling, stability）
- 画面运动（subject_motion, environment_motion, motion_intensity）
- 转场（transition_in, transition_out, transition_duration）

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

# shot_direction 字段枚举

camera_motion: static | slow_push_in | slow_pull_out | slow_pan_left | slow_pan_right | slow_tilt_up | slow_tilt_down | slow_dolly | slow_tracking | slow_zoom_in | slow_zoom_out | floating_drift | none_or_minimal_drift
movement_speed: very_slow | slow | moderate
lens_feeling: wide_cinematic | standard | telephoto_compressed | macro_dreamlike
stability: locked | floating | handheld_subtle | drifting
motion_intensity: very_low | low | medium | high

# visual_style 和 emotion

visual_style.scene_type: 来自 parent segment 的 scene_type
visual_style.color_palette: 来自 parent segment 的 color_palette
visual_style.lighting: 来自 parent segment 的 lighting
emotion.intensity: 来自 parent segment 的 emotional_intensity，每个 shot 可微调 ±0.1

# generation_notes

image_prompt_focus: 静帧 prompt 的关键词（英文词或短语）
video_prompt_focus: 视频 prompt 的关键词（英文词或短语）
avoid: 必须避免的元素

# JSON 输出格式

{
  "schema_version": "1.0",
  "shots": [
    {
      "shot_id": "shot_v1_01_01",
      "parent_segment_id": "seg_v1_01",
      "time_range": {"start_time": 0.0, "end_time": 8.0, "duration_seconds": 8.0},
      "shot_type": "lyric_imagery",
      "shot_role": "establishing_image",
      "literal_meaning_zh": "星夜、蓝灰色的调色板、夏日的凝视",
      "deep_meaning": "第一段主歌通过梵高的画作《星月夜》入画，暗示画家眼中世界的美丽与灵魂深处的黑暗并存。",
      "static_frame_description": "深蓝夜空中旋转的星光漩涡占据画面上半部分，下方沉睡的村庄暗影横跨中景，前景是柏树火焰般的暗色剪影",
      "key_imagery": ["星空", "蓝灰调色板"],
      "composition": {
        "shot_size": "extreme_wide_shot",
        "camera_angle": "slightly_low_angle",
        "foreground": "柏树暗影",
        "midground": "沉睡村庄",
        "background": "旋转星夜",
        "focal_point": "最亮的星",
        "depth": "deep_space"
      },
      "shot_direction": {
        "camera_motion": "slow_push_in",
        "movement_speed": "very_slow",
        "lens_feeling": "wide_cinematic",
        "stability": "floating",
        "subject_motion": "星光缓慢旋转",
        "environment_motion": "云层轻轻飘移",
        "motion_intensity": "low",
        "transition_in": "fade_from_black",
        "transition_out": "soft_dissolve",
        "transition_duration": 1.0
      },
      "visual_style": {
        "scene_type": "starry_night",
        "color_palette": ["深蓝", "铬黄", "冷白"],
        "lighting": "月光与星光交织",
        "texture": "厚涂油画质感"
      },
      "emotion": {"primary": "静谧", "secondary": ["神秘"], "intensity": 0.4},
      "generation_notes": {
        "image_prompt_focus": "swirling starry night, cobalt blue, impasto brushwork",
        "video_prompt_focus": "rotating stars, cloud drift in violet haze",
        "avoid": ["写实照片", "现代建筑", "人物正脸", "平滑数字渲染"]
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
            })
        interp = seg.get("interpretation", {})
        # Derive recommended_shot_count from segment duration
        dur = seg["time_range"].get("duration_seconds", 10)
        rec_shot_count = max(1, int(dur / 8 + 0.5))
        qwen_input.append({
            "segment_id": seg["segment_id"],
            "start_time": seg["time_range"]["start_time"],
            "end_time": seg["time_range"]["end_time"],
            "duration_seconds": seg["time_range"]["duration_seconds"],
            "lyrics_text": seg["lyrics"]["lyrics_text"],
            "literal_meaning_zh": interp.get("literal_meaning_zh", ""),
            "deep_meaning_zh": interp.get("deep_meaning_zh", ""),
            "emotional_state_zh": interp.get("emotional_state_zh", []),
            "emotional_intensity": interp.get("emotional_intensity", 0.5),
            "core_imagery": core_img,
            "recommended_shot_count": rec_shot_count,
        })
    return qwen_input


REQUIRED_SHOT = [
    "shot_id", "parent_segment_id", "time_range", "lyric_refs", "shot_type", "shot_role",
    "literal_meaning_zh", "deep_meaning", "static_frame_description", "key_imagery",
    "composition", "shot_direction", "generation_notes",
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

        # Ensure key_imagery is a list (empty is valid)
        if not isinstance(s.get("key_imagery"), list):
            s["key_imagery"] = []

        # Inject visual_style / emotion from parent segment if missing (with defaults since S3 no longer has visual_direction)
        if not s.get("visual_style"):
            s["visual_style"] = {
                "scene_type": "",
                "color_palette": [],
                "lighting": "",
                "texture": "油画质感",
            }
        interp = pseg.get("interpretation", {})
        if not s.get("emotion"):
            s["emotion"] = {
                "primary": interp.get("emotional_state_zh", [""])[0] if interp.get("emotional_state_zh") else "",
                "secondary": interp.get("emotional_state_zh", [])[1:],
                "intensity": interp.get("emotional_intensity", 0.5),
            }

        # Validate shot_type
        if s.get("shot_type") not in ("lyric_imagery", "singer_performance"):
            s["shot_type"] = "lyric_imagery"

        # Validate missing required fields
        missing = [k for k in REQUIRED_SHOT if k not in s]
        if missing:
            print(f"  [warn] shot[{i}] {s.get('shot_id','?')} missing keys: {missing}")

    # ── Singer performance normalization ──
    singer_shots = [s for s in shots if s.get("shot_type") == "singer_performance"]
    if singer_shots and len(singer_shots) > 1:
        template_frame = singer_shots[0].get("static_frame_description", "")
        template_imagery: list[str] = list(singer_shots[0].get("key_imagery", []))
        if template_frame:
            for s in singer_shots[1:]:
                if not s.get("static_frame_description"):
                    s["static_frame_description"] = template_frame
                if not s.get("key_imagery") or s.get("key_imagery") == template_imagery:
                    s["key_imagery"] = list(template_imagery)
        print(f"  Normalized {len(singer_shots)} singer_performance shots to shared template")

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
        "shot_type": "lyric_imagery",
        "shot_role": "ambient_hold",
        "literal_meaning_zh": "(器乐间奏，无歌词)",
        "deep_meaning": "间奏/过渡段落，画面延续前一段氛围，不做单独画面切换。后续阶段可复用前一 shot 的最后一帧作为静态画面。",
        "static_frame_description": "延续前一段画面的最后一帧，轻微淡出。",
        "key_imagery": [],
        "composition": {
            "shot_size": "wide_shot",
            "camera_angle": "eye_level",
            "foreground": "残留光粒子",
            "midground": "渐暗的空间",
            "background": "远方模糊剪影",
            "focal_point": "逐渐消散的光粒子",
            "depth": "medium_space",
        },
        "shot_direction": {
            "camera_motion": "none_or_minimal_drift",
            "movement_speed": "very_slow",
            "lens_feeling": "standard",
            "stability": "drifting",
            "subject_motion": "光粒子尾迹逐渐消散",
            "environment_motion": "光点缓慢漂浮",
            "motion_intensity": "very_low",
            "transition_in": "none",
            "transition_out": "none",
            "transition_duration": 0,
        },
        "visual_style": {
            "scene_type": vd.get("scene_type", ""),
            "color_palette": vd.get("color_palette", []),
            "lighting": vd.get("lighting", ""),
            "texture": "油画质感",
        },
        "emotion": {
            "primary": "延续",
            "secondary": [],
            "intensity": interp.get("emotional_intensity", 0.0),
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
            "instrumental_hold_policy": "reuse_previous_visual_or_create_ambient_hold",
            "long_segment_policy": "split_before_shot_planning_if_over_40_seconds",
            "video_max_duration_seconds": 8.0,
            "over_max_policy": "use_tail_frame_extension_then_trim_to_lyric_duration",
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
