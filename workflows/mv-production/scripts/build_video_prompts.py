#!/usr/bin/env python3
"""Build video-prompts.json from shot-plan.json + selected-asset-manifest.json / image-prompts.json.

Uses Qwen3.5 to generate video motion prompts from camera/motion_design data.
Reads shot-plan.json for camera/motion/emotion per shot, combines with selected
images from the asset manifest (or image-prompt data if manifest not yet available).
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

SYSTEM_PROMPT = """You generate video motion prompts for an imagery-type music video.

You will receive per-shot data:
- A static image description (what the keyframe looks like)
- Camera motion instruction (slow_push_in, slow_tracking, floating_drift, etc.)
- Subject motion description (what moves in the scene)
- Environment motion description
- Motion intensity (very_low, low, medium, high)
- Transition out
- Duration in seconds
- Shot role

Generate ONE English video prompt per shot. Rules:
- Describe what the camera does and what moves in the scene AFTER the keyframe starts
- DO NOT re-describe the static image itself — only the motion/change
- Use natural cinematic language
- Match the motion intensity to the emotional tone
- Keep prompts concise (2-3 sentences)
- For ambient_hold shots: minimal drift only

Output ONLY a JSON array of objects with:
{ "shot_id": "...", "video_prompt": "..." }
"""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    load_aigc_dotenv()
    if not os.getenv("AIGC_GITEE_API_KEY") and os.getenv("GITEE_API_TOKEN"):
        os.environ["AIGC_GITEE_API_KEY"] = os.getenv("GITEE_API_TOKEN", "")

    import config as qwen_cfg  # noqa: E402

    ap = argparse.ArgumentParser(description="Build video-prompts.json")
    ap.add_argument("--shot-plan", required=True, type=Path)
    ap.add_argument("--image-prompts", required=True, type=Path)
    ap.add_argument("--selected-manifest", type=Path, default=None, help="Optional: selected-asset-manifest for resolved image paths")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--temperature", type=float, default=0.25)
    ap.add_argument("--max-tokens", type=int, default=12288)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    shot_data = load_json(args.shot_plan.resolve())
    img_data = load_json(args.image_prompts.resolve())

    # Build selected image lookup if manifest provided
    selected_lookup: dict[str, str] = {}
    if args.selected_manifest:
        sel = load_json(args.selected_manifest.resolve())
        for a in sel.get("assets", []):
            if a.get("selected_image"):
                selected_lookup[a["shot_id"]] = a["selected_image"]

    # Build image prompt lookup
    img_lookup: dict[str, dict[str, Any]] = {}
    for p in img_data.get("image_prompts", []):
        img_lookup[p["shot_id"]] = p

    # Build context for Qwen3.5
    tasks: list[dict[str, Any]] = []
    for shot in shot_data["shots"]:
        sid = shot["shot_id"]
        tr = shot["time_range"]
        cam = shot.get("camera", {})
        md = shot.get("motion_design", {})
        img_info = img_lookup.get(sid, {})
        pc = img_info.get("prompt_components", {})
        ip = img_info.get("image_prompt", "")
        is_hold = img_info.get("render_strategy", {}).get("generate_new_image") is False

        # Extract static image description (the visual concept, not the full prompt)
        static_desc = pc.get("environment", "")
        if not static_desc and ip:
            prefix_marker = "elegant composition, "
            static_desc = ip.split(prefix_marker, 1)[1] if prefix_marker in ip else ip
            # Truncate to visual concept portion
            for term in [", extreme wide", ", wide cinematic", ", medium", ", close-up",
                         ", soft moonlight", ", 16:9"]:
                if term in static_desc:
                    static_desc = static_desc.split(term)[0].strip()

        tasks.append({
            "shot_id": sid,
            "static_image_description": static_desc if not is_hold else "(ambient hold - minimal drift only)",
            "camera_motion": cam.get("camera_motion", "static"),
            "movement_speed": cam.get("movement_speed", "slow"),
            "subject_motion": md.get("subject_motion", "") if not is_hold else "subtle particle drift",
            "environment_motion": md.get("environment_motion", "") if not is_hold else "minimal ambient change",
            "motion_intensity": md.get("motion_intensity", "very_low") if not is_hold else "very_low",
            "transition_out": shot.get("transition", {}).get("transition_out", "dissolve"),
            "duration_seconds": tr["duration_seconds"],
            "shot_role": shot.get("shot_role", "symbolic_detail"),
        })

    user_text = (
        "Generate video motion prompts for these shots:\n"
        + json.dumps(tasks, ensure_ascii=False)
        + "\n\nOutput ONLY: [{ \"shot_id\": \"...\", \"video_prompt\": \"...\" }]"
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

    print(f"Generating video prompts for {len(tasks)} shots via Qwen3.5...")
    response = post_messages(qwen_cfg.API_URL, qwen_cfg.API_KEY, payload, timeout=600)
    text = extract_assistant_text(response).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:]) if lines[0].strip() in ("```", "```json") else text
        if text.endswith("```"):
            text = text[: text.rindex("```")].strip()

    try:
        model_prompts = json.loads(text)
    except json.JSONDecodeError:
        raise SystemExit(f"Qwen3.5 returned invalid JSON: {text[:500]}")

    # Merge with shot data
    shot_lookup = {s["shot_id"]: s for s in shot_data["shots"]}
    result: list[dict[str, Any]] = []
    for mp in model_prompts:
        sid = mp["shot_id"]
        shot = shot_lookup.get(sid, {})
        tr = shot.get("time_range", {})
        img_info = img_lookup.get(sid, {})
        image_path = selected_lookup.get(sid, img_info.get("input_image", ""))
        result.append({
            "video_prompt_id": f"vid_{sid}",
            "shot_id": sid,
            "input_image": image_path or f"assets/images/selected/{sid}.png",
            "duration_seconds": tr.get("duration_seconds", 0),
            "video_prompt": mp.get("video_prompt", ""),
            "camera_motion": shot.get("camera", {}).get("camera_motion", ""),
            "subject_motion": shot.get("motion_design", {}).get("subject_motion", ""),
            "motion_intensity": shot.get("motion_design", {}).get("motion_intensity", ""),
            "transition_out": shot.get("transition", {}).get("transition_out", ""),
        })

    out = {
        "schema_version": "1.0",
        "song_title": shot_data.get("song_title", ""),
        "source_shot_plan_ref": args.shot_plan.name,
        "source_selected_manifest_ref": args.selected_manifest.name if args.selected_manifest else None,
        "video_prompts": result,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(result)} video prompts)")


if __name__ == "__main__":
    main()
