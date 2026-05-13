#!/usr/bin/env python3
"""Execute video generation from video-prompts.json + selected-asset-manifest.json.

Calls Gitee LTX HQ API (POST /v1/async/videos/image-to-video) for each shot.
Uploads the selected keyframe image, submits an image-to-video task, polls
until complete, then downloads the generated video.

Supports resume (skips existing video files). Aspect ratio follows the source image.

Outputs:
  - assets/videos/candidates/{shot_id}.mp4
  - video-generation-results.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError


def load_dotenv() -> None:
    try:
        from dotenv import load_dotenv as _load
        _load(Path(__file__).resolve().parents[3] / ".env")
    except ImportError:
        pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_multipart(fields: dict[str, str], file_field: tuple[str, str, bytes, str]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    fn, _, data, mime = file_field
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{fn}\"; filename=\"{Path(fn).name}\"\r\nContent-Type: {mime}\r\n\r\n".encode() + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def submit_ltx_hq(api_key: str, prompt: str, image_path: Path, duration_seconds: float) -> tuple[str | None, str | None]:
    url = "https://ai.gitee.com/v1/async/videos/image-to-video"
    dur = max(duration_seconds, 3.0)
    num_frames = int(min(dur, 10) * 24)
    num_frames = max(((num_frames - 1) // 8) * 8 + 1, 9)

    fields = {
        "prompt": prompt,
        "model": "LTX-2",
        "num_inference_steps": "8",
        "num_frames": str(num_frames),
        "fps": "24",
        "guidance_scale": "1",
        "height": "640",
        "width": "512",
    }
    img_data = image_path.read_bytes()
    ext = image_path.suffix.lower().lstrip(".")
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
    mime = mime_map.get(ext, "application/octet-stream")

    body, content_type = build_multipart(fields, ("image", image_path.name, img_data, mime))
    headers = {
        "Content-Type": content_type,
        "Authorization": f"Bearer {api_key}",
    }

    try:
        req = urllib_request.Request(url, data=body, headers=headers, method="POST")
        with urllib_request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        task_id = result.get("task_id", "")
        if not task_id:
            return (None, f"No task_id in response: {json.dumps(result)[:200]}")
        return (task_id, None)
    except Exception as e:
        return (None, str(e))


def poll_and_download(api_key: str, task_id: str, output_path: Path, timeout: int = 600) -> bool:
    status_url = f"https://ai.gitee.com/api/v1/task/{task_id}"
    elapsed = 0
    interval = 10
    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval
        try:
            req = urllib_request.Request(status_url, headers={"Authorization": f"Bearer {api_key}"})
            with urllib_request.urlopen(req, timeout=15) as sr:
                status_body = json.loads(sr.read())
            status = status_body.get("status", "unknown")
            if status == "success":
                file_url = status_body.get("output", {}).get("file_url", "")
                if file_url:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    urllib_request.urlretrieve(file_url, str(output_path))
                    return output_path.exists()
                return False
            if status in ("failed", "cancelled", "error"):
                return False
        except Exception:
            pass
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate videos from video-prompts + selected images")
    ap.add_argument("--video-prompts", required=True, type=Path)
    ap.add_argument("--selected-manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path, help="Results JSON output path")
    ap.add_argument("--project-root", type=Path, default=None)
    ap.add_argument("--poll-timeout", type=int, default=600, help="Max seconds per video task")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_dotenv()
    API_KEY = os.getenv("AIGC_GITEE_API_KEY", "") or os.getenv("GITEE_API_TOKEN", "")
    if not API_KEY and not args.dry_run:
        raise SystemExit("Missing AIGC_GITEE_API_KEY / GITEE_API_TOKEN.")

    vid_data = load_json(args.video_prompts.resolve())
    sel_data = load_json(args.selected_manifest.resolve())
    project_root = args.project_root.resolve() if args.project_root else args.video_prompts.resolve().parent

    sel_lookup: dict[str, Any] = {a["shot_id"]: a for a in sel_data.get("assets", [])}

    prompts = vid_data.get("video_prompts", [])
    total = len(prompts)
    completed = 0
    failed = 0
    results: list[dict[str, Any]] = []

    for i, vp in enumerate(prompts):
        sid = vp["shot_id"]
        sel = sel_lookup.get(sid, {})
        image_path_str = sel.get("selected_image", vp.get("input_image", ""))
        image_path = project_root / image_path_str
        duration = vp.get("duration_seconds", 5)
        video_prompt = vp.get("video_prompt", "")
        output_path = project_root / "assets" / "videos" / "candidates" / f"{sid}.mp4"

        if not video_prompt or not sel.get("selected_image"):
            results.append({"shot_id": sid, "status": "skipped", "video_path": None, "error": "Missing prompt or selected image."})
            continue

        if output_path.exists() and output_path.stat().st_size > 1000:
            print(f"  [{i+1}/{total}] {sid}: SKIP (exists)")
            results.append({"shot_id": sid, "status": "completed", "video_path": str(output_path.relative_to(project_root)), "error": None})
            completed += 1
            continue

        if args.dry_run:
            print(f"  [{i+1}/{total}] {sid}: DRY-RUN (dur={duration:.1f}s)")
            results.append({"shot_id": sid, "status": "dry_run", "video_path": str(output_path.relative_to(project_root)), "error": None})
            continue

        print(f"  [{i+1}/{total}] {sid}: submitting (dur={duration:.1f}s)...", end=" ", flush=True)
        task_id, err = submit_ltx_hq(API_KEY, video_prompt, image_path, duration)
        if err:
            print(f"FAIL: {err[:80]}")
            results.append({"shot_id": sid, "status": "failed", "video_path": None, "error": err})
            failed += 1
            continue

        print(f"task={task_id} polling...", end=" ", flush=True)
        success = poll_and_download(API_KEY, task_id, output_path, args.poll_timeout)
        if success:
            print("OK")
            results.append({"shot_id": sid, "status": "completed", "video_path": str(output_path.relative_to(project_root)), "error": None})
            completed += 1
        else:
            print("FAIL (timeout/error)")
            results.append({"shot_id": sid, "status": "failed", "video_path": None, "error": "Polling timeout or task failed."})
            failed += 1

    print(f"\nDone: {completed} completed, {failed} failed, {total - completed - failed} skipped")

    out_obj = {
        "schema_version": "1.0",
        "source_video_prompts_ref": args.video_prompts.name,
        "video_generation_results": results,
    }
    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
