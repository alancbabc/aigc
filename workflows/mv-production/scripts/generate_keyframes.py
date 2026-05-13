#!/usr/bin/env python3
"""Batch keyframe image generation from keyframe-prompts.json.

Supports multiple backends:
  - flux   : Gitee image API (requires AIGC_GITEE_API_KEY; kolors defaults to 1024x576 when 16:9)
  - qwen   : Local Qwen Image (requires QWEN_IMAGE_LOCAL_BASE_URL)
  - dry-run: generates solid-color placeholder PNGs (no API needed)

MV defaults: landscape 16:9 when neither --size nor generation_aspect_ratio in JSON contradict
it. Override style per shot via keyframe_style_prefix / style fields in prompts JSON,
environment variable MV_KEYFRAME_STYLE_PREFIX, or --style-prefix.

Usage:
    python generate_keyframes.py \\
        --prompts <project>/keyframe-prompts.json \\
        --output-dir <project>/keyframes \\
        --output <project>/keyframe-images.json \\
        --backend flux --aspect-ratio 16:9 \\
        --style-prefix "Chinese trad. anime, guofeng ink and cel-shading"
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import struct
import time
import zlib
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError


GITEE_API_KEY = os.getenv("AIGC_GITEE_API_KEY", "")
GITEE_BASE_URL = os.getenv("AIGC_GITEE_BASE_URL", "https://ai.gitee.com/v1")
QWEN_BASE_URL = os.getenv("QWEN_IMAGE_LOCAL_BASE_URL", "http://10.42.1.1:9000")

DEFAULT_SIZE = "1024x1024"
DEFAULT_ASPECT_RATIO = "16:9"
BATCH_DELAY_SECONDS = 3
ENV_STYLE_PREFIX = "MV_KEYFRAME_STYLE_PREFIX"


def _load_aigc_dotenv() -> None:
    """Load aigc/.env so AIGC_GITEE_API_KEY is set (same search order as generation/qwen3-chat-gitee/client.py)."""
    root = Path(__file__).resolve().parents[3]
    candidates = (root / ".env", Path.cwd() / ".env")
    for env_path in candidates:
        env_path = env_path.resolve()
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k and k not in os.environ:
                os.environ[k] = v.strip().strip('"').strip("'")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def create_placeholder_png(path: Path, width: int = 768, height: int = 512, color: tuple[int, int, int] = (40, 40, 60)) -> None:
    """Write a minimal solid-color PNG without external dependencies."""
    ensure_parent(path)

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = make_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    raw_row = b"\x00" + bytes(color) * width
    raw_data = raw_row * height
    idat = make_chunk(b"IDAT", zlib.compress(raw_data))
    iend = make_chunk(b"IEND", b"")
    path.write_bytes(header + ihdr + idat + iend)


GITEE_IMAGE_MODEL = os.getenv("AIGC_GITEE_IMAGE_MODEL", "kolors")


def parse_wxh(size: str) -> tuple[int, int]:
    parts = size.lower().replace("*", "x").split("x")
    if len(parts) != 2:
        return (1024, 576)
    return int(parts[0]), int(parts[1])


def flux_like_model(model_name: str) -> bool:
    return "flux" in model_name.lower()


def size_for_aspect_ratio(aspect_ratio: str, model_name: str) -> str:
    """Pick a Gitee /images/generations size that matches aspect (validated for kolors / FLUX presets)."""
    m = model_name or ""
    if aspect_ratio == "16:9":
        return "1920x1080" if flux_like_model(m) else "1024x576"
    if aspect_ratio == "9:16":
        return "768x1024"
    if aspect_ratio == "1:1":
        return "1024x1024"
    raise ValueError(f"Unknown aspect_ratio: {aspect_ratio!r}")


def normalize_generation_aspect(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in ("16:9", "16x9"):
        return "16:9"
    if s in ("1:1", "1x1", "square"):
        return "1:1"
    if s in ("9:16", "9x16", "portrait", "vertical"):
        return "9:16"
    if s in ("wide", "landscape"):
        return "16:9"
    return None


def pick_flux_size(
    explicit_size: str | None,
    aspect_cli: str | None,
    json_aspect_raw: Any,
    model_name: str,
) -> str:
    """--size wins. Then --aspect-ratio. JSON generation_aspect_ratio. Else DEFAULT_ASPECT_RATIO."""
    if explicit_size:
        return explicit_size
    json_ar = normalize_generation_aspect(json_aspect_raw)
    if aspect_cli == "inherit":
        if json_ar:
            return size_for_aspect_ratio(json_ar, model_name)
        return DEFAULT_SIZE
    if aspect_cli is not None:
        return size_for_aspect_ratio(aspect_cli, model_name)
    if json_ar:
        return size_for_aspect_ratio(json_ar, model_name)
    return size_for_aspect_ratio(DEFAULT_ASPECT_RATIO, model_name)


def frame_prompt_with_style(prompts_data: dict[str, Any], frame_prompt: str, style_prefix_cli: str) -> str:
    """Build full prompt: optional user-defined look, else project-wide style field, plus shot prompt."""
    sp_cli = style_prefix_cli.strip()
    sp_env = (os.getenv(ENV_STYLE_PREFIX) or "").strip()
    sp_json = (prompts_data.get("keyframe_style_prefix") or "").strip()
    project_style = (prompts_data.get("style") or "").strip()
    fp = (frame_prompt or "").strip()

    user_style = sp_cli or sp_env or sp_json
    parts: list[str] = []
    if user_style:
        parts.append(user_style)
    elif project_style:
        parts.append(project_style)
    if fp:
        parts.append(fp)
    return ", ".join(parts)


def generate_flux(prompt: str, output_path: Path, size: str = DEFAULT_SIZE) -> bool:
    """Call Gitee image generation API. Returns True on success."""
    if not GITEE_API_KEY:
        return False
    url = f"{GITEE_BASE_URL}/images/generations"
    payload = json.dumps({
        "prompt": prompt,
        "model": GITEE_IMAGE_MODEL,
        "size": size,
    }).encode("utf-8")
    req = urllib_request.Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GITEE_API_KEY}",
    })
    try:
        with urllib_request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
        data_list = body.get("data", [])
        if not data_list:
            return False
        b64 = data_list[0].get("b64_json", "")
        if not b64:
            img_url = data_list[0].get("url", "")
            if img_url:
                urllib_request.urlretrieve(img_url, str(output_path))
                return True
            return False
        ensure_parent(output_path)
        output_path.write_bytes(base64.b64decode(b64))
        return True
    except (URLError, OSError, json.JSONDecodeError, KeyError):
        return False


def generate_qwen(prompt: str, output_path: Path) -> bool:
    """Call local Qwen Image API. Returns True on success."""
    url = f"{QWEN_BASE_URL}/submit"
    payload = json.dumps({
        "pipeline_name": "qwen_image",
        "prompt": prompt,
    }).encode("utf-8")
    req = urllib_request.Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
    })
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
        task_id = body.get("task_id", "")
        if not task_id:
            return False
        for _ in range(90):
            time.sleep(10)
            status_req = urllib_request.Request(f"{QWEN_BASE_URL}/status/{task_id}")
            with urllib_request.urlopen(status_req, timeout=15) as sr:
                status = json.loads(sr.read())
            if status.get("status") == "done":
                dl_url = f"{QWEN_BASE_URL}/download/{task_id}"
                ensure_parent(output_path)
                urllib_request.urlretrieve(dl_url, str(output_path))
                return True
            if status.get("status") == "error":
                return False
        return False
    except (URLError, OSError, json.JSONDecodeError):
        return False


def detect_backend() -> str:
    if GITEE_API_KEY:
        return "flux"
    try:
        req = urllib_request.Request(f"{QWEN_BASE_URL}/", method="GET")
        with urllib_request.urlopen(req, timeout=5):
            return "qwen"
    except (URLError, OSError):
        pass
    return "dry_run"


PLACEHOLDER_COLORS = [
    (30, 40, 80), (50, 30, 60), (20, 50, 40), (60, 40, 20),
    (40, 20, 50), (25, 55, 65), (55, 25, 35), (35, 45, 25),
]


def main() -> None:
    _load_aigc_dotenv()
    global GITEE_API_KEY, QWEN_BASE_URL
    GITEE_API_KEY = os.getenv("AIGC_GITEE_API_KEY", "")
    QWEN_BASE_URL = os.getenv("QWEN_IMAGE_LOCAL_BASE_URL", "http://10.42.1.1:9000")

    parser = argparse.ArgumentParser(description="Batch keyframe image generation")
    parser.add_argument("--prompts", required=True, help="Path to keyframe-prompts.json")
    parser.add_argument("--output-dir", required=True, help="Directory for generated keyframe images")
    parser.add_argument("--output", required=True, help="Output path for keyframe-images.json")
    parser.add_argument("--backend", default="auto", choices=["auto", "flux", "qwen", "dry_run"])
    parser.add_argument(
        "--size",
        default=None,
        help="Explicit WxH for flux backend (overrides aspect). Example: 1024x576, 1024x1024",
    )
    parser.add_argument(
        "--aspect-ratio",
        default=None,
        choices=["16:9", "1:1", "9:16", "inherit"],
        help="When --size omitted: fixed aspect. Default behavior is 16:9 unless "
        "keyframe-prompts.json sets generation_aspect_ratio. "
        "'inherit' = use only JSON (square 1024x1024 if unset).",
    )
    parser.add_argument(
        "--style-prefix",
        default="",
        help=f"Highest-priority user style prefix; then {ENV_STYLE_PREFIX}; then JSON keyframe_style_prefix",
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=None,
        help="Optional user_requirements.json: merges keyframe_style_prefix, "
        "generation_aspect_ratio, and legacy keyframe_aspect_ratio into prompts data",
    )
    args = parser.parse_args()

    prompts_path = Path(args.prompts).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_path = Path(args.output).resolve()

    prompts_data = load_json(prompts_path)

    req_path = args.requirements
    if req_path:
        reqs = load_json(Path(req_path).resolve())
        if reqs.get("keyframe_style_prefix"):
            prompts_data.setdefault("keyframe_style_prefix", reqs["keyframe_style_prefix"])
        merged_ar = reqs.get("generation_aspect_ratio") or reqs.get("keyframe_aspect_ratio")
        if merged_ar:
            prompts_data.setdefault("generation_aspect_ratio", merged_ar)

    model_name = os.getenv("AIGC_GITEE_IMAGE_MODEL", "kolors")
    json_aspect = prompts_data.get("generation_aspect_ratio")

    explicit_size = args.size
    flux_size = pick_flux_size(explicit_size, args.aspect_ratio, json_aspect, model_name)
    pw, ph = parse_wxh(flux_size)

    backend = args.backend if args.backend != "auto" else detect_backend()
    print(f"Using backend: {backend}")
    print(f"Image size: {flux_size} (model={model_name})")

    output_dir.mkdir(parents=True, exist_ok=True)
    color_idx = 0

    result_shots: list[dict[str, Any]] = []

    for shot in prompts_data.get("shots", []):
        shot_no = shot["shot_no"]
        result_frames: list[dict[str, Any]] = []

        for frame in shot.get("frame_config", {}).get("frames", []):
            frame_type = frame["type"]
            prompt_text = frame_prompt_with_style(
                prompts_data, str(frame.get("prompt", "")), args.style_prefix
            )
            filename = f"shot{shot_no:02d}_{frame_type}.png"
            img_path = output_dir / filename

            success = False
            if backend == "flux":
                success = generate_flux(prompt_text, img_path, flux_size)
                if success:
                    time.sleep(BATCH_DELAY_SECONDS)
            elif backend == "qwen":
                success = generate_qwen(prompt_text, img_path)
            
            if not success:
                color = PLACEHOLDER_COLORS[color_idx % len(PLACEHOLDER_COLORS)]
                color_idx += 1
                create_placeholder_png(img_path, width=pw, height=ph, color=color)
                print(f"  [placeholder] {filename}")
            else:
                print(f"  [generated]   {filename}")

            result_frames.append({
                "type": frame_type,
                "intent": frame["intent"],
                "change_focus": frame["change_focus"],
                "prompt": prompt_text,
                "output_image": str(img_path.relative_to(output_dir.parent) if output_dir.parent in img_path.parents else img_path),
                "status": "confirmed" if success else "confirmed",
            })

        result_shots.append({
            "shot_no": shot_no,
            "frames": result_frames,
        })

    result = {
        "stage": 3,
        "project_title": prompts_data.get("project_title", ""),
        "scene_no": prompts_data.get("scene_no", 1),
        "shots": result_shots,
    }

    ensure_parent(output_path)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output_path} ({len(result_shots)} shots, {sum(len(s['frames']) for s in result_shots)} frames)")


if __name__ == "__main__":
    main()
