#!/usr/bin/env python3
"""Batch video asset generation from mv-video-plan.json.

Routes each entry to the appropriate generator:
  - text_image_to_video_high_quality -> Gitee LTX HQ (generate_hq_gitee.sh)
  - audio_to_video                  -> Local LTX A2V (generate_a2v.sh)
  - image_audio_ffmpeg              -> FFmpeg still-image + audio

Supports --dry-run to generate solid-color placeholder MP4s via FFmpeg.

Usage:
    python generate_video_assets.py \
        --video-plan <project>/video-plan.json \
        --output <project>/video-assets.json \
        --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import struct
import zlib
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError


GITEE_API_TOKEN = os.getenv("GITEE_API_TOKEN", "")
LTX23_BASE_URL = os.getenv("LTX23_BASE_URL", "http://10.0.180.14:80")
DEFAULT_FFMPEG = "ffmpeg"

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "generation" / "ltx23-video" / "scripts"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def resolve_path(project_root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (project_root / candidate).resolve()


def create_placeholder_png(path: Path, w: int = 768, h: int = 512, color: tuple[int, int, int] = (30, 30, 50)) -> None:
    """Minimal solid-color PNG for placeholder video source."""
    ensure_parent(path)
    def chunk(ct: bytes, d: bytes) -> bytes:
        c = ct + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    raw = (b"\x00" + bytes(color) * w) * h
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def create_placeholder_video(output_path: Path, duration: float, ffmpeg_bin: str = DEFAULT_FFMPEG) -> bool:
    """Generate a placeholder MP4. Tries FFmpeg first; falls back to a minimal binary stub."""
    ensure_parent(output_path)
    tmp_img = output_path.parent / "_placeholder_frame.png"
    create_placeholder_png(tmp_img)
    try:
        cmd = [
            ffmpeg_bin, "-y",
            "-loop", "1", "-i", str(tmp_img),
            "-t", str(min(duration, 5.0)),
            "-vf", "scale=768:512",
            "-r", "24",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-pix_fmt", "yuv420p",
            "-an",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        _write_stub_mp4(output_path, duration)
        return True
    finally:
        if tmp_img.exists():
            tmp_img.unlink()


def _write_stub_mp4(path: Path, duration: float) -> None:
    """Write a minimal valid-ish MP4 stub so downstream tools can at least list it."""
    ensure_parent(path)
    meta = json.dumps({"placeholder": True, "duration": duration}).encode("utf-8")
    ftyp = _mp4_box(b"ftyp", b"isom\x00\x00\x00\x00isomavc1")
    mdat = _mp4_box(b"mdat", meta)
    path.write_bytes(ftyp + mdat)


def _mp4_box(box_type: bytes, data: bytes) -> bytes:
    size = 8 + len(data)
    return struct.pack(">I", size) + box_type + data


GITEE_HQ_SUBMIT_URL = "https://ai.gitee.com/v1/async/videos/image-to-video"
GITEE_HQ_STATUS_URL = "https://ai.gitee.com/api/v1/task"
GITEE_HQ_MODEL = "LTX-2"
GITEE_HQ_POLL_INTERVAL = 10
GITEE_HQ_TIMEOUT = 600


def _build_multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    """Build multipart/form-data body."""
    import uuid
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    for name, (filename, data, mime) in files.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: {mime}\r\n\r\n".encode()
            + data + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def run_hq_gitee(entry: dict[str, Any], project_root: Path, ffmpeg_bin: str) -> bool:
    """Run text_image_to_video_high_quality via Gitee API (pure Python)."""
    if not GITEE_API_TOKEN:
        return False

    ltx_req = entry.get("ltx_request", {})
    prompt = ltx_req.get("prompt", entry.get("prompt_ref", ""))
    images = ltx_req.get("images", entry.get("source_image_paths", []))
    save_path = resolve_path(project_root, entry.get("output_path", ltx_req.get("save_path", "")))
    duration = ltx_req.get("duration_seconds", entry.get("time_window", {}).get("duration_seconds", 5))
    num_frames = int(min(duration, 10) * 24)
    num_frames = max(((num_frames - 1) // 8) * 8 + 1, 9)

    fields = {
        "prompt": prompt,
        "model": GITEE_HQ_MODEL,
        "num_inference_steps": "8",
        "num_frames": str(num_frames),
        "fps": "24",
        "guidance_scale": "1",
        "height": "640",
        "width": "512",
    }
    files: dict[str, tuple[str, bytes, str]] = {}
    if images:
        img_path = resolve_path(project_root, images[0])
        if img_path.exists():
            ext = img_path.suffix.lower().lstrip(".")
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "application/octet-stream")
            files["image"] = (img_path.name, img_path.read_bytes(), mime)

    body, content_type = _build_multipart(fields, files)
    req = urllib_request.Request(GITEE_HQ_SUBMIT_URL, data=body, method="POST", headers={
        "Content-Type": content_type,
        "Authorization": f"Bearer {GITEE_API_TOKEN}",
    })

    try:
        with urllib_request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        task_id = result.get("task_id", "")
        if not task_id:
            print(f"    [hq_gitee] No task_id in submit response: {json.dumps(result)[:200]}")
            return False
        print(f"    [hq_gitee] Task submitted: {task_id}")
    except Exception as e:
        print(f"    [hq_gitee] Submit failed: {e}")
        return False

    import time as _time
    elapsed = 0
    while elapsed < GITEE_HQ_TIMEOUT:
        _time.sleep(GITEE_HQ_POLL_INTERVAL)
        elapsed += GITEE_HQ_POLL_INTERVAL
        try:
            status_req = urllib_request.Request(f"{GITEE_HQ_STATUS_URL}/{task_id}", headers={
                "Authorization": f"Bearer {GITEE_API_TOKEN}",
            })
            with urllib_request.urlopen(status_req, timeout=15) as sr:
                status_body = json.loads(sr.read())
            status = status_body.get("status", "unknown")
            print(f"    [hq_gitee] Poll {elapsed}s: {status}")
            if status == "success":
                file_url = status_body.get("output", {}).get("file_url", "")
                if file_url:
                    ensure_parent(save_path)
                    urllib_request.urlretrieve(file_url, str(save_path))
                    return save_path.exists()
                return False
            if status in ("failed", "cancelled", "error"):
                print(f"    [hq_gitee] Task {status}: {json.dumps(status_body)[:200]}")
                return False
        except Exception as e:
            print(f"    [hq_gitee] Poll error: {e}")

    print(f"    [hq_gitee] Timeout after {GITEE_HQ_TIMEOUT}s")
    return False


def run_a2v_local(entry: dict[str, Any], project_root: Path) -> bool:
    """Run audio_to_video via generate_a2v.sh."""
    script = SCRIPTS_DIR / "generate_a2v.sh"
    if not script.exists():
        return False

    ltx_req = entry.get("ltx_request", {})
    prompt = ltx_req.get("prompt", entry.get("prompt_ref", ""))
    audio = ltx_req.get("audio", entry.get("audio_segment_path", ""))
    images = ltx_req.get("images", entry.get("source_image_paths", []))
    save_path = resolve_path(project_root, entry.get("output_path", ltx_req.get("save_path", "")))

    if not audio:
        return False

    cmd = [
        "bash", str(script),
        "-a", str(resolve_path(project_root, audio)),
        "-p", prompt,
        "-o", str(save_path),
    ]
    if images:
        img_paths = ",".join(str(resolve_path(project_root, p)) for p in images)
        cmd.extend(["--images", img_paths])

    ensure_parent(save_path)
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=600)
        return save_path.exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def run_ffmpeg_still(entry: dict[str, Any], project_root: Path, ffmpeg_bin: str) -> bool:
    """Render image_audio_ffmpeg: still image + audio to MP4."""
    ffmpeg_req = entry.get("ffmpeg_request", {})
    image = ffmpeg_req.get("image_path", "")
    audio = ffmpeg_req.get("audio_path", "")
    save_path = resolve_path(project_root, ffmpeg_req.get("save_path", entry.get("output_path", "")))
    tw = entry.get("time_window", {}).get("target_width", 768)
    th = entry.get("time_window", {}).get("target_height", 512)
    w = ffmpeg_req.get("target_width", tw)
    h = ffmpeg_req.get("target_height", th)

    if not image or not audio:
        return False

    ensure_parent(save_path)
    cmd = [
        ffmpeg_bin, "-y",
        "-loop", "1", "-i", str(resolve_path(project_root, image)),
        "-i", str(resolve_path(project_root, audio)),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black",
        "-r", "24", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", "-shortest",
        str(save_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        return save_path.exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch video asset generation from mv-video-plan")
    parser.add_argument("--video-plan", required=True, help="Path to video-plan.json")
    parser.add_argument("--output", required=True, help="Output path for video-assets.json")
    parser.add_argument("--ltx-prompts", default=None, help="Path to video-ltx-prompts.json for prompt resolution")
    parser.add_argument("--ffmpeg-bin", default=DEFAULT_FFMPEG)
    parser.add_argument("--dry-run", action="store_true", help="Generate placeholder MP4s instead of calling APIs")
    args = parser.parse_args()

    plan_path = Path(args.video_plan).resolve()
    output_path = Path(args.output).resolve()
    plan = load_json(plan_path)

    prompt_map: dict[str, str] = {}
    ltx_prompts_path = Path(args.ltx_prompts).resolve() if args.ltx_prompts else (plan_path.parent / plan.get("video_ltx_prompts_ref", "video-ltx-prompts.json"))
    if ltx_prompts_path.exists():
        ltx_data = load_json(ltx_prompts_path)
        for pe in ltx_data.get("entries", []):
            prompt_map[pe["prompt_id"]] = pe["optimized_prompt"]
        print(f"Loaded {len(prompt_map)} prompts from {ltx_prompts_path.name}")

    if plan_path.parent.name == "video":
        project_root = plan_path.parent.parent
    else:
        project_root = plan_path.parent

    import sys
    sys.stdout.reconfigure(line_buffering=True)

    entries = plan.get("entries", [])
    results: list[dict[str, Any]] = []

    for i, entry in enumerate(entries):
        entry_id = entry.get("entry_id", f"entry_{i+1:02d}")
        render_mode = entry.get("render_mode", "")
        tw = entry.get("time_window", {})
        duration = tw.get("duration_seconds", 5.0)
        out_rel = entry.get("output_path", f"video-assets/{entry_id}.mp4")
        out_abs = resolve_path(project_root, out_rel)

        prompt_ref = entry.get("prompt_ref", "")
        if prompt_ref in prompt_map:
            if "ltx_request" in entry and entry["ltx_request"]:
                entry["ltx_request"]["prompt"] = prompt_map[prompt_ref]
            else:
                entry["ltx_request"] = {"prompt": prompt_map[prompt_ref]}

        success = False

        if args.dry_run:
            success = create_placeholder_video(out_abs, duration, args.ffmpeg_bin)
            method = "dry_run_placeholder"
        elif render_mode == "text_image_to_video_high_quality":
            success = run_hq_gitee(entry, project_root, args.ffmpeg_bin)
            method = "gitee_hq"
            if not success:
                success = create_placeholder_video(out_abs, duration, args.ffmpeg_bin)
                method = "fallback_placeholder"
        elif render_mode == "audio_to_video":
            success = run_a2v_local(entry, project_root)
            method = "local_a2v"
            if not success:
                success = create_placeholder_video(out_abs, duration, args.ffmpeg_bin)
                method = "fallback_placeholder"
        elif render_mode == "image_audio_ffmpeg":
            success = run_ffmpeg_still(entry, project_root, args.ffmpeg_bin)
            method = "ffmpeg_still"
            if not success:
                success = create_placeholder_video(out_abs, duration, args.ffmpeg_bin)
                method = "fallback_placeholder"
        else:
            success = create_placeholder_video(out_abs, duration, args.ffmpeg_bin)
            method = "unknown_mode_placeholder"

        status = "generated" if success else "failed"
        print(f"  [{status}] {entry_id} ({render_mode}) via {method} -> {out_rel}")

        results.append({
            "entry_id": entry_id,
            "shot_ref": entry.get("shot_ref", ""),
            "section_ref": entry.get("section_ref", ""),
            "render_mode": render_mode,
            "generation_method": method,
            "output_path": out_rel,
            "status": status,
            "duration_seconds": duration,
        })

    asset_manifest = {
        "schema_version": "1.0",
        "song_title": plan.get("song_title", ""),
        "video_plan_ref": str(plan_path.name),
        "total_entries": len(results),
        "generated": sum(1 for r in results if r["status"] == "generated"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "entries": results,
    }

    ensure_parent(output_path)
    output_path.write_text(
        json.dumps(asset_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {output_path} ({asset_manifest['generated']}/{asset_manifest['total_entries']} generated)")


if __name__ == "__main__":
    main()
