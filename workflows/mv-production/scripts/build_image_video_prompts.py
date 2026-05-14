#!/usr/bin/env python3
"""Build image-video-prompts.json from shot-plan.json.

Programmatic assembly + Qwen3.5 batch translation of static_frame_description.
For each shot:
  - image_prompt: English static frame description only (no motion)
  - video_prompt: English motion description only (minimal content)
  - Timing, lyrics, and generation parameters from shot-plan.
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

# Motion keyword CN → EN mapping (programmatic, no Qwen3 needed)
MOTION_CN_EN: dict[str, str] = {
    "缓慢": "slowly", "旋转": "rotating", "流动": "flowing", "漂浮": "drifting",
    "上升": "rising", "下降": "falling", "飘移": "drifting", "闪烁": "flickering",
    "颤动": "trembling", "消散": "dissipating", "拂过": "brushing past",
    "涌动": "surging", "推近": "pushing in", "拉远": "pulling out",
    "静止": "static", "往复": "swaying", "扩散": "spreading",
    "星光": "starlight", "光粒子": "light particles", "色块": "color blocks",
    "云层": "cloud layers", "雾气": "mist", "丝线": "threads of light",
    "尾迹": "trails", "剪影": "silhouette", "暗影": "shadows",
    "颜料": "pigment", "笔触": "brushstrokes", "纹路": "texture",
    "漩涡": "vortex", "涟漪": "ripples", "光斑": "specks of light",
    # Additional common motion vocabulary
    "色彩": "colors", "光线": "light rays", "光柱": "light beams",
    "画布": "canvas", "瞳孔": "pupils", "眼瞳": "eyes",
    "背景": "background", "星空": "starry sky", "天空": "sky",
    "水面": "water surface", "纹路": "texture", "线条": "lines",
    "光芒": "glow", "光晕": "halo", "光束": "light beam",
    "扩张": "dilating", "收缩": "contracting", "呼吸": "breathing",
    "渲染": "blending", "渐变": "gradient shift", "移动": "moving",
    "轻微": "slight", "缓缓": "gradually", "剧烈": "intense",
    "飞舞": "dancing", "飘扬": "waving", "蔓延": "spreading",
    "流淌": "streaming", "翻滚": "rolling", "沸散": "boiling away",
    "脉搏": "pulse", "跳动": "beating", "无变化": "unchanged",
    "脉动": "pulsing", "定格": "frozen", "驻足": "paused",
    "静止不动": "motionless", "凝固": "solidified",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def translate_batch(
    texts: list[tuple[str, str]],
    api_key: str, api_url: str, model: str, timeout: int = 120,
) -> dict[str, str]:
    if not texts:
        return {}
    lines = "\n".join(f"{idx}: {cn}" for idx, cn in texts)
    system = (
        "You translate Chinese static frame descriptions to English image-generation prompts. "
        "Translate each into concise English suitable for an AI image model. "
        "Describe ONLY the static visual scene — no camera motion, no action verbs. "
        "Output ONLY a JSON object with indices as keys and translations as values."
    )
    payload = {
        "model": model, "stream": False, "enable_thinking": False,
        "max_tokens": 4096, "temperature": 0.2, "top_p": 0.9,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Translate:\n{lines}"},
        ],
    }
    resp = post_messages(api_url, api_key, payload, timeout=timeout)
    text = extract_assistant_text(resp).strip()
    if text.startswith("```"): 
        lines_t = text.splitlines()
        text = "\n".join(lines_t[1:]) if lines_t[0].strip() in ("```","```json") else text
        if text.endswith("```"): text = text[:text.rindex("```")].strip()
    try:
        translations = json.loads(text)
    except json.JSONDecodeError:
        print("[warn] Translation parse failed")
        return {idx: cn for idx, cn in texts}
    result: dict[str, str] = {}
    for idx, cn in texts:
        result[idx] = translations.get(str(idx), cn)
    return result


def make_video_prompt(sd: dict[str, Any]) -> str:
    """Build English video prompt from shot_direction. Translates Chinese motion terms."""
    parts: list[str] = []

    # Camera
    cm = sd.get("camera_motion", "")
    if cm and cm not in ("static", "none_or_minimal_drift"):
        speed = sd.get("movement_speed", "slow")
        parts.append(f"camera {cm.replace('_', ' ')}, {speed}")

    import re
    # Subject motion — translate CN → EN using word map
    sm = sd.get("subject_motion", "")
    if sm:
        translated = sm
        for cn, en in sorted(MOTION_CN_EN.items(), key=lambda x: -len(x[0])):
            translated = translated.replace(cn, en + " ")
        translated = " ".join(translated.split())
        # Strip remaining Chinese characters (unmapped words)
        translated = re.sub(r"[\u4e00-\u9fff]+", "", translated).strip()
        if translated:
            parts.append(f"subject: {translated}")

    # Environment motion
    em = sd.get("environment_motion", "")
    if em:
        translated = em
        for cn, en in sorted(MOTION_CN_EN.items(), key=lambda x: -len(x[0])):
            translated = translated.replace(cn, en + " ")
        translated = " ".join(translated.split())
        translated = re.sub(r"[\u4e00-\u9fff]+", "", translated).strip()
        if translated:
            parts.append(f"environment: {translated}")

    # Transition
    ti = sd.get("transition_out", "")
    if ti and ti != "none":
        parts.append(f"transition: {ti}")

    return ". ".join(parts) + "." if parts else "minimal drift."


def main() -> None:
    load_aigc_dotenv()
    if not os.getenv("AIGC_GITEE_API_KEY") and os.getenv("GITEE_API_TOKEN"):
        os.environ["AIGC_GITEE_API_KEY"] = os.getenv("GITEE_API_TOKEN", "")
    import config as qwen_cfg  # noqa: E402

    ap = argparse.ArgumentParser(description="Build image-video-prompts from shot-plan")
    ap.add_argument("--shot-plan", required=True, type=Path)
    ap.add_argument("--user-requirements", type=Path, default=None)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--no-translate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    shot_data = load_json(args.shot_plan.resolve())
    style_prefix = ""
    if args.user_requirements:
        req = load_json(args.user_requirements.resolve())
        style_prefix = str(req.get("keyframe_style_prefix", "")).strip()

    # Collect static_frame_description for translation
    tasks: list[tuple[str, str]] = []
    for shot in shot_data["shots"]:
        if shot.get("shot_role") == "ambient_hold":
            continue
        sfd = shot.get("static_frame_description", "")
        if sfd:
            tasks.append((shot["shot_id"], sfd))

    print(f"Shots: {len(shot_data['shots'])} total, {len(tasks)} need translation")

    if args.no_translate or args.dry_run:
        trans = {sid: cn for sid, cn in tasks}
        if args.dry_run:
            print("[dry-run]")
            return
    else:
        print(f"Translating {len(tasks)} frame descriptions...")
        trans = translate_batch(tasks, qwen_cfg.API_KEY, qwen_cfg.API_URL, qwen_cfg.DEFAULT_MODEL)

    prompts: list[dict[str, Any]] = []
    for shot in shot_data["shots"]:
        sid = shot["shot_id"]
        tr = shot["time_range"]
        is_hold = shot.get("shot_role") == "ambient_hold"

        frame_en = trans.get(sid, shot.get("static_frame_description", ""))
        image_prompt = f"{style_prefix}, {frame_en}" if style_prefix else frame_en
        if not is_hold:
            comp = shot.get("composition", {})
            size = comp.get("shot_size", "").replace("_", " ")
            image_prompt = f"{image_prompt}, {size}, 16:9"

        video_prompt = make_video_prompt(shot.get("shot_direction", {})) if not is_hold else "static hold."

        prompts.append({
            "shot_id": sid,
            "parent_segment_id": shot.get("parent_segment_id", ""),
            "shot_type": shot.get("shot_type", "lyric_imagery"),
            "shot_role": shot.get("shot_role", ""),
            "time_range": {
                "start_time": tr["start_time"],
                "end_time": tr["end_time"],
                "duration_seconds": tr["duration_seconds"],
            },
            "lyric_refs": shot.get("lyric_refs", []),
            "literal_meaning_zh": shot.get("literal_meaning_zh", ""),
            "image_prompt": image_prompt,
            "video_prompt": video_prompt,
            "key_imagery": shot.get("key_imagery", []),
            "composition": shot.get("composition", {}),
            "shot_direction": shot.get("shot_direction", {}),
            "generate_new_image": not is_hold,
        })

    out = {
        "schema_version": "1.0",
        "song_title": shot_data.get("song_title", ""),
        "source_shot_plan_ref": args.shot_plan.name,
        "style_prefix": style_prefix,
        "prompts": prompts,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    new_count = sum(1 for p in prompts if p["generate_new_image"])
    hold_count = sum(1 for p in prompts if not p["generate_new_image"])
    print(f"Wrote {out_path} ({new_count} images, {hold_count} holds)")


if __name__ == "__main__":
    main()
