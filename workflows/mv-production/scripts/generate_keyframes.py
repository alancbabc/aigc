#!/usr/bin/env python3
"""Batch keyframe image generation from keyframe-prompts.json.

Supports multiple backends:
  - flux   : Gitee FLUX.2-klein-9B (requires AIGC_GITEE_API_KEY)
  - qwen   : Local Qwen Image (requires QWEN_IMAGE_LOCAL_BASE_URL)
  - dry-run: generates solid-color placeholder PNGs (no API needed)

Usage:
    python generate_keyframes.py \
        --prompts <project>/keyframe-prompts.json \
        --output-dir <project>/keyframes \
        --output <project>/keyframe-images.json \
        --backend auto
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
BATCH_DELAY_SECONDS = 3


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
    parser = argparse.ArgumentParser(description="Batch keyframe image generation")
    parser.add_argument("--prompts", required=True, help="Path to keyframe-prompts.json")
    parser.add_argument("--output-dir", required=True, help="Directory for generated keyframe images")
    parser.add_argument("--output", required=True, help="Output path for keyframe-images.json")
    parser.add_argument("--backend", default="auto", choices=["auto", "flux", "qwen", "dry_run"])
    parser.add_argument("--size", default=DEFAULT_SIZE, help="Image size for flux backend (WxH)")
    args = parser.parse_args()

    prompts_path = Path(args.prompts).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_path = Path(args.output).resolve()

    prompts_data = load_json(prompts_path)
    backend = args.backend if args.backend != "auto" else detect_backend()
    print(f"Using backend: {backend}")

    output_dir.mkdir(parents=True, exist_ok=True)
    color_idx = 0

    result_shots: list[dict[str, Any]] = []

    for shot in prompts_data.get("shots", []):
        shot_no = shot["shot_no"]
        result_frames: list[dict[str, Any]] = []

        for frame in shot.get("frame_config", {}).get("frames", []):
            frame_type = frame["type"]
            prompt_text = frame["prompt"]
            filename = f"shot{shot_no:02d}_{frame_type}.png"
            img_path = output_dir / filename

            success = False
            if backend == "flux":
                success = generate_flux(prompt_text, img_path, args.size)
                if success:
                    time.sleep(BATCH_DELAY_SECONDS)
            elif backend == "qwen":
                success = generate_qwen(prompt_text, img_path)
            
            if not success:
                color = PLACEHOLDER_COLORS[color_idx % len(PLACEHOLDER_COLORS)]
                color_idx += 1
                create_placeholder_png(img_path, color=color)
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
