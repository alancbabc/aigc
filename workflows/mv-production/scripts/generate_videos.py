#!/usr/bin/env python3
"""Execute video generation from image-video-prompts.json + selected-asset-manifest.json.

Calls Gitee image-to-video API (POST /v1/async/videos/image-to-video) for each shot.
Supports LTX-2 and Wan2_2-I2V-A14B models.
Uploads the selected keyframe image, submits an image-to-video task, polls
until complete, then downloads the generated video.

Supports resume (skips existing video files). Aspect ratio follows --width/--height.

Outputs:
  - assets/videos/candidates/{shot_id}.mp4
  - video-generation-results.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
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


def submit_ltx_hq(api_key: str, prompt: str, image_path: Path, duration_seconds: float, width: int = 1024, height: int = 576, model: str = "LTX-2") -> tuple[str | None, str | None]:
    url = "https://ai.gitee.com/v1/async/videos/image-to-video"
    dur = max(duration_seconds, 3.0)
    # Cap at 15s for API generation; longer shots get tail-frame extension after download
    gen_dur = min(dur, 15.0)
    num_frames = int(gen_dur * 24 + 0.5)  # round to nearest frame
    num_frames = max(((num_frames - 1) // 8) * 8 + 1, 9)
    # Wan2_2-I2V-A14B model: num_frames must be in [25, 50]
    if model == "Wan2_2-I2V-A14B":
        num_frames = min(max(num_frames, 25), 50)
    else:
        num_frames = max(num_frames, 9)

    fields: dict[str, str] = {
        "prompt": prompt,
        "model": model,
        "num_frames": str(num_frames),
        "fps": "24",
        "height": str(height),
        "width": str(width),
    }
    if model == "LTX-2":
        fields["num_inference_steps"] = "8"
        fields["guidance_scale"] = "1"
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
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return (None, f"HTTP {e.code}: {err_body[:500]}")
    except Exception as e:
        return (None, str(e))


def poll_and_download(api_key: str, task_id: str, output_path: Path, timeout: int = 600) -> bool:
    status_url = f"https://ai.gitee.com/api/v1/task/{task_id}"
    elapsed = 0
    interval = 10
    last_error = ""
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
                    try:
                        urllib_request.urlretrieve(file_url, str(output_path))
                    except Exception as dl_e:
                        last_error = f"download failed: {dl_e}"
                        continue
                    if output_path.exists() and output_path.stat().st_size > 1000:
                        return True
                    last_error = f"file missing/small after download ({output_path.stat().st_size}B)"
                else:
                    last_error = "no file_url in success response"
            elif status in ("failed", "failure", "cancelled", "error"):
                reason = status_body.get("error") or status_body.get("message", "unknown")
                last_error = f"task {status}: {reason}"
                return False
        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            last_error = f"HTTP {e.code}: {err_body[:200]}"
        except Exception as e:
            last_error = str(e)
    print(f"  poll timeout, last error: {last_error}")
    return False


def extend_video_duration(video_path: Path, target_duration: float, ffmpeg_bin: str = "ffmpeg") -> bool:
    """Extend video with tail-frame freeze if shorter than target_duration."""
    if not video_path.exists():
        return False
    # Probe actual duration
    try:
        cmd = [ffmpeg_bin, "-i", str(video_path), "-f", "null", "-"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        import re
        dur_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
        if not dur_match:
            return True  # can't probe, assume ok
        h, m, s = float(dur_match[1]), float(dur_match[2]), float(dur_match[3])
        actual = h * 3600 + m * 60 + s
    except Exception:
        return True
    if actual >= target_duration - 0.05:
        return True  # already close enough
    extend = round(target_duration - actual, 2)
    tmp_path = video_path.with_suffix(".tmp.mp4")
    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(video_path),
        "-vf", f"tpad=stop_mode=clone:stop_duration={extend}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-an",
        str(tmp_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
        tmp_path.replace(video_path)
        print(f"  (extended {extend:.1f}s with tail freeze)", end=" ")
        return True
    except subprocess.CalledProcessError:
        return False


def extract_last_frame(video_path: Path, output_path: Path, ffmpeg_bin: str = "ffmpeg") -> bool:
    """Extract the last meaningful frame of a video as a PNG image."""
    if not video_path.exists():
        return False
    cmd = [
        ffmpeg_bin, "-y",
        "-sseof", "-0.5",
        "-i", str(video_path),
        "-update", "1",
        "-q:v", "1",
        "-vframes", "1",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        return output_path.exists() and output_path.stat().st_size > 100
    except subprocess.CalledProcessError:
        return False


def concat_video_segments(segment_paths: list[Path], output_path: Path, ffmpeg_bin: str = "ffmpeg") -> bool:
    """Concatenate multiple video segments into one file using the concat demuxer."""
    if not segment_paths:
        return False
    if len(segment_paths) == 1:
        segment_paths[0].replace(output_path)
        return output_path.exists()
    list_file = output_path.parent / f"_concat_{output_path.stem}.txt"
    list_file.write_text("\n".join(f"file '{p.as_posix()}'" for p in segment_paths) + "\n", encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-an",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=180)
        list_file.unlink(missing_ok=True)
        return output_path.exists()
    except subprocess.CalledProcessError:
        list_file.unlink(missing_ok=True)
        return False


def generate_tail_loop_video(
    output_path: Path,
    initial_keyframe: Path,
    video_prompt: str,
    total_duration: float,
    api_key: str,
    width: int,
    height: int,
    model: str,
    poll_timeout: int,
) -> bool:
    """Generate extended video via tail-frame loop.

    For shots > 15s with extension_strategy=tail_frame_loop:
    - Segment 0: generated from initial_keyframe (~15s)
    - Segment 1+: generated from previous segment's last frame (~15s each)
    - All segments concatenated into output_path.
    """
    max_seg_dur = 14.5  # leave 0.5s margin for API stability
    seg_dir = output_path.parent / f"_segs_{output_path.stem}"
    seg_dir.mkdir(parents=True, exist_ok=True)

    segments: list[Path] = []
    remaining = total_duration
    current_keyframe = initial_keyframe
    part = 0

    while remaining > 0.5:
        seg_dur = min(remaining, max_seg_dur)
        seg_path = seg_dir / f"p{part:02d}.mp4"

        # Extract tail frame from previous segment as new keyframe
        if part > 0 and segments:
            tail_path = seg_dir / f"tail_{part - 1:02d}.png"
            if extract_last_frame(segments[-1], tail_path):
                current_keyframe = tail_path

        print(f"    [{part}] dur={seg_dur:.1f}s...", end=" ", flush=True)
        task_id, err = submit_ltx_hq(api_key, video_prompt, current_keyframe, seg_dur, width, height, model)
        if err:
            print(f"FAIL({err[:50]})")
            break

        print(f"poll...", end=" ", flush=True)
        if poll_and_download(api_key, task_id, seg_path, poll_timeout):
            extend_video_duration(seg_path, seg_dur)
            segments.append(seg_path)
            print("OK")
        else:
            print("FAIL")
            break

        remaining -= seg_dur
        part += 1

    if not segments:
        return False

    print(f"    concat {len(segments)} segs...", end=" ", flush=True)
    return concat_video_segments(segments, output_path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate videos from image-video-prompts + selected images")
    ap.add_argument("--image-video-prompts", required=True, type=Path)
    ap.add_argument("--selected-manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path, help="Results JSON output path")
    ap.add_argument("--project-root", type=Path, default=None)
    ap.add_argument("--poll-timeout", type=int, default=600, help="Max seconds per video task")
    ap.add_argument("--width", type=int, default=1024, help="Video width (must be multiple of 64)")
    ap.add_argument("--height", type=int, default=576, help="Video height (must be multiple of 64)")
    ap.add_argument("--delay", type=float, default=3.0, help="Delay between submissions (seconds)")
    ap.add_argument("--model", default="Wan2_2-I2V-A14B", choices=["LTX-2", "Wan2_2-I2V-A14B"], help="Video generation model")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_dotenv()
    API_KEY = os.getenv("AIGC_GITEE_API_KEY", "") or os.getenv("GITEE_API_TOKEN", "")
    if not API_KEY and not args.dry_run:
        raise SystemExit("Missing AIGC_GITEE_API_KEY / GITEE_API_TOKEN.")

    ivp = load_json(args.image_video_prompts.resolve())
    sel = load_json(args.selected_manifest.resolve())
    project_root = args.project_root.resolve() if args.project_root else args.image_video_prompts.resolve().parent

    sel_lookup: dict[str, Any] = {a["shot_id"]: a for a in sel.get("assets", [])}

    prompts = ivp.get("prompts", [])
    total = len(prompts)
    completed = 0
    failed = 0
    results: list[dict[str, Any]] = []

    for i, p in enumerate(prompts):
        sid = p["shot_id"]
        gen_new = p.get("generate_new_image", True)
        ext_strategy = p.get("extension_strategy", "none")
        reuse_id = p.get("reuse_from_shot_id")

        # tail_frame_loop shots: need a video from the reused shot's keyframe
        # Pure ambient holds: no video needed
        is_ambient_hold = not gen_new and ext_strategy != "tail_frame_loop"
        if is_ambient_hold:
            results.append({"shot_id": sid, "status": "skipped", "video_path": None, "error": "Ambient hold — no video generated."})
            continue

        # For tail_frame_loop or normal shots: find the keyframe image
        sel_item = sel_lookup.get(sid, {})
        image_path_str = sel_item.get("selected_image")
        if not image_path_str and reuse_id:
            # tail_frame_loop: use the reused shot's selected image
            reused_sel = sel_lookup.get(reuse_id, {})
            image_path_str = reused_sel.get("selected_image")
        if not image_path_str:
            # Build fallback with sequence prefix from selected manifest
            all_assets = sel.get("assets", [])
            seq = 0
            for a in all_assets:
                if a.get("shot_id") == sid:
                    seq = a.get("sequence_index", 0)
                    break
            image_path_str = f"assets/images/selected/{seq:03d}_{sid}.png" if seq else f"assets/images/selected/{sid}.png"

        image_path = project_root / image_path_str
        duration = p["time_range"]["duration_seconds"]
        video_prompt = p.get("video_prompt", "")
        # Build sequence index from selected manifest for video naming
        all_assets = sel.get("assets", [])
        seq = 0
        for a in all_assets:
            if a.get("shot_id") == sid:
                seq = a.get("sequence_index", 0)
                break
        vfilename = f"{seq:03d}_{sid}.mp4" if seq else f"{sid}.mp4"
        output_path = project_root / "assets" / "videos" / "candidates" / vfilename

        if not video_prompt or not image_path.exists():
            results.append({"shot_id": sid, "status": "skipped", "video_path": None, "error": "Missing prompt or keyframe image."})
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

        # Route: tail_frame_loop shots use multi-segment generation
        use_tail_loop = ext_strategy == "tail_frame_loop" and duration > 15.0
        if use_tail_loop:
            success = generate_tail_loop_video(
                output_path, image_path, video_prompt, duration,
                API_KEY, args.width, args.height, args.model, args.poll_timeout,
            )
            if success:
                print("OK")
                results.append({"shot_id": sid, "status": "completed", "video_path": str(output_path.relative_to(project_root)), "error": None})
                completed += 1
            else:
                print("FAIL")
                results.append({"shot_id": sid, "status": "failed", "video_path": None, "error": "Tail-loop generation failed."})
                failed += 1
        else:
            task_id, err = submit_ltx_hq(API_KEY, video_prompt, image_path, duration, args.width, args.height, args.model)
            if err:
                print(f"FAIL: {err[:80]}")
                results.append({"shot_id": sid, "status": "failed", "video_path": None, "error": err})
                failed += 1
                continue

            print(f"task={task_id} polling...", end=" ", flush=True)
            success = poll_and_download(API_KEY, task_id, output_path, args.poll_timeout)
            if success:
                # Extend if generated video is shorter than shot duration
                extend_video_duration(output_path, duration)
                print("OK")
                results.append({"shot_id": sid, "status": "completed", "video_path": str(output_path.relative_to(project_root)), "error": None})
                completed += 1
            else:
                print("FAIL (timeout/error)")
                results.append({"shot_id": sid, "status": "failed", "video_path": None, "error": "Polling timeout or task failed."})
                failed += 1

        time.sleep(args.delay)

    print(f"\nDone: {completed} completed, {failed} failed, {total - completed - failed} skipped")

    out_obj = {
        "schema_version": "1.0",
        "source_image_video_prompts_ref": args.image_video_prompts.name,
        "video_generation_results": results,
    }
    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
