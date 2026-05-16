#!/usr/bin/env python3
"""Execute image generation from queue with annotation.

Calls Gitee image API (POST /v1/images/generations) for each generation task.
After successful generation, creates an annotated copy (timestamp + lyrics + section)
in assets/images/labeled/. Each shot generates exactly 1 candidate image.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

# Optional annotation import (PIL required)
try:
    _AIGC_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(_AIGC_ROOT / "workflows" / "mv-production" / "scripts"))
    from annotate_selected import annotate_image  # noqa: E402
    _HAS_ANNOTATION = True
except ImportError:
    _HAS_ANNOTATION = False

KOLORS_SIZES = {(1024, 576), (1024, 768), (1024, 1024), (512, 512)}
FLUX_SIZES = {(1024, 576), (1024, 768), (1024, 1024), (768, 1024), (1920, 1080), (2048, 1152)}
DEFAULT_MODEL = "FLUX.2-klein-9B"


def load_dotenv() -> None:
    try:
        from dotenv import load_dotenv as _load
        _load(Path(__file__).resolve().parents[3] / ".env")
    except ImportError:
        pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_resolution(res_str: str, model: str = "") -> tuple[int, int]:
    parts = res_str.lower().replace("x", " ").split()
    if len(parts) >= 2:
        w, h = int(parts[0]), int(parts[1])
        supported = KOLORS_SIZES if model == "kolors" else FLUX_SIZES
        if (w, h) in supported:
            return w, h
        # Find closest supported size
        for sz in supported:
            if abs(w - sz[0]) < 100 and abs(h - sz[1]) < 100:
                return sz
    print(f"  [warn] Resolution {res_str} not supported, falling back to 1024x576")
    return (1024, 576)


def call_image_api(api_key: str, prompt: str, negative: str, size: str, model: str = "FLUX.2-klein-9B") -> tuple[bytes | None, str | None]:
    """Return (image_bytes, None) on success or (None, error_msg) on failure."""
    url = "https://ai.gitee.com/v1/images/generations"
    payload_dict: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "size": size,
    }
    if model == "kolors":
        payload_dict["negative_prompt"] = negative
    else:
        # FLUX / Qwen-Image models
        payload_dict["num_inference_steps"] = 4
        if model.startswith("FLUX"):
            payload_dict["guidance_scale"] = 1
    payload = json.dumps(payload_dict).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        req = urllib_request.Request(url, data=payload, headers=headers, method="POST")
        with urllib_request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
        data_item = body.get("data", [{}])[0]
        b64 = data_item.get("b64_json", "")
        if b64:
            return (base64.b64decode(b64), None)
        img_url = data_item.get("url", "")
        if img_url:
            return (None, "API returned url field - b64_json expected")
        return (None, f"Empty response: {json.dumps(body)[:200]}")
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return (None, f"HTTP {e.code}: {err_body[:300]}")
    except Exception as e:
        return (None, str(e))


def main() -> None:
    ap = argparse.ArgumentParser(description="Execute image generation from queue with annotation")
    ap.add_argument("--queue", required=True, type=Path)
    ap.add_argument("--image-video-prompts", type=Path, default=None, help="image-video-prompts.json for annotation metadata")
    ap.add_argument("--segment-interpretation", type=Path, default=None, help="segment-interpretation.json for section type lookup")
    ap.add_argument("--out", required=True, type=Path, help="Results JSON output path")
    ap.add_argument("--project-root", type=Path, default=None, help="Project root for resolving relative paths")
    ap.add_argument("--delay", type=float, default=2.0, help="Delay between API calls (seconds)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Image generation model (FLUX.2-klein-9B, Qwen-Image-2512, kolors)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_dotenv()
    API_KEY = os.getenv("AIGC_GITEE_API_KEY", "") or os.getenv("GITEE_API_TOKEN", "")
    if not API_KEY and not args.dry_run:
        raise SystemExit("Missing AIGC_GITEE_API_KEY / GITEE_API_TOKEN.")

    queue_data = load_json(args.queue.resolve())
    project_root = args.project_root.resolve() if args.project_root else args.queue.resolve().parent

    # Load annotation metadata
    prompt_data = None
    seg_data = None
    prompt_lookup: dict[str, Any] = {}
    section_lookup: dict[str, str] = {}
    if args.image_video_prompts:
        prompt_data = load_json(args.image_video_prompts.resolve())
        for p in prompt_data.get("prompts", []):
            prompt_lookup[p["shot_id"]] = p
    if args.segment_interpretation:
        seg_data = load_json(args.segment_interpretation.resolve())
        for seg in seg_data.get("segments", []):
            sid = seg.get("segment_id", "")
            st = seg.get("section_type", "")
            if sid:
                section_lookup[sid] = st

    tasks = queue_data.get("generation_queue", [])
    if not tasks:
        print("No generation tasks in queue.")
        return

    total = len(tasks)
    completed = 0
    failed = 0
    skipped = 0
    results: list[dict[str, Any]] = []

    labeled_dir = project_root / "assets" / "images" / "labeled"

    for i, task in enumerate(tasks):
        task_id = task["task_id"]
        shot_id = task["shot_id"]
        prompt = task.get("image_prompt", "")
        negative = task.get("negative_prompt", "")
        params = task.get("generation_parameters", {})
        res_str = params.get("resolution", "1024x576")
        model_name = task.get("model") or args.model
        width, height = parse_resolution(res_str, model_name)
        size = f"{width}x{height}"
        candidates = task.get("output_candidates", [])

        if not prompt and task.get("generate_new_image"):
            results.append({"task_id": task_id, "shot_id": shot_id, "status": "skipped", "generated_images": [], "error": {"message": "Empty prompt.", "retryable": False}})
            skipped += 1
            continue

        out_path = candidates[0] if candidates else f"assets/images/candidates/{task.get('sequence_index', 0):03d}_{shot_id}_c1.png"
        abs_path = project_root / out_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        # Helper to create annotated version
        def make_annotated(src_path: Path) -> None:
            if not _HAS_ANNOTATION:
                return
            seq = task.get("sequence_index", 0)
            p_data = prompt_lookup.get(shot_id, {})
            tr = p_data.get("time_range", {})
            lt = p_data.get("lyrics_text", "")
            ps = p_data.get("parent_segment_id", "")
            st = section_lookup.get(ps, "")
            labeled_name = f"{seq:03d}_{shot_id}.png" if seq else f"{shot_id}.png"
            dst = labeled_dir / labeled_name
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                annotate_image(src_path, dst, shot_id, tr.get("start_time", 0), tr.get("end_time", 0), lt, st)
            except Exception as e:
                print(f"  [warn] annotation failed for {shot_id}: {e}")

        if abs_path.exists() and abs_path.stat().st_size > 100:
            print(f"  [{i+1}/{total}] {shot_id}: SKIP (exists)")
            make_annotated(abs_path)
            results.append({"task_id": task_id, "shot_id": shot_id, "status": "completed", "generated_images": [{"candidate_id": abs_path.stem, "file_path": str(out_path), "api_status": "skipped_existing"}], "error": None})
            skipped += 1
            continue

        if args.dry_run:
            print(f"  [{i+1}/{total}] {shot_id}: DRY-RUN (size={size})")
            results.append({"task_id": task_id, "shot_id": shot_id, "status": "dry_run", "generated_images": [{"candidate_id": abs_path.stem, "file_path": str(out_path), "api_status": "dry_run"}], "error": None})
            skipped += 1
            continue

        print(f"  [{i+1}/{total}] {shot_id}: generating...", end=" ", flush=True)
        img_bytes, err = call_image_api(API_KEY, prompt, negative, size, model_name)

        generated = []
        if img_bytes:
            abs_path.write_bytes(img_bytes)
            generated.append({"candidate_id": abs_path.stem, "file_path": str(out_path), "api_status": "success"})
            print("OK")
            make_annotated(abs_path)
            results.append({"task_id": task_id, "shot_id": shot_id, "status": "completed", "generated_images": generated, "error": None})
            completed += 1
        else:
            generated.append({"candidate_id": abs_path.stem, "file_path": str(out_path), "api_status": "failed", "error": err})
            print(f"FAIL: {err[:80]}")
            results.append({"task_id": task_id, "shot_id": shot_id, "status": "failed", "generated_images": generated, "error": {"message": "Image generation failed.", "retryable": True}})
            failed += 1

        time.sleep(args.delay)

    print(f"\nDone: {completed} completed, {failed} failed, {skipped} skipped (of {total} tasks)")

    out_obj = {
        "schema_version": "1.0",
        "source_queue_file": args.queue.name,
        "generation_results": results,
    }
    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
