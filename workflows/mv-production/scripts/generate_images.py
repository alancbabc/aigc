#!/usr/bin/env python3
"""Execute image generation tasks from image-generation-queue.json.

Calls Gitee Kolors API (POST /v1/images/generations) for each generation task.
Generates num_candidates images per shot. Supports resume (skips existing files).

Outputs:
  - assets/images/candidates/*.png
  - image-generation-results.json
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

KOLORS_SIZES = {(1024, 576), (1024, 768), (1024, 1024), (512, 512)}
DEFAULT_SIZE = (1024, 576)


def load_dotenv() -> None:
    try:
        from dotenv import load_dotenv as _load
        _load(Path(__file__).resolve().parents[3] / ".env")
    except ImportError:
        pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_resolution(res_str: str) -> tuple[int, int]:
    parts = res_str.lower().replace("x", " ").split()
    if len(parts) >= 2:
        w, h = int(parts[0]), int(parts[1])
        if (w, h) in KOLORS_SIZES:
            return w, h
        # Find closest supported size
        for sz in KOLORS_SIZES:
            if abs(w - sz[0]) < 100 and abs(h - sz[1]) < 100:
                return sz
    return DEFAULT_SIZE


def call_kolors(api_key: str, prompt: str, negative: str, size: str) -> tuple[bytes | None, str | None]:
    """Return (image_bytes, None) on success or (None, error_msg) on failure."""
    url = "https://ai.gitee.com/v1/images/generations"
    payload = json.dumps({
        "model": "kolors",
        "prompt": prompt,
        "negative_prompt": negative,
        "size": size,
    }).encode("utf-8")
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
            urllib_request.urlretrieve(img_url)
            return (None, None)
        return (None, f"Empty response: {json.dumps(body)[:200]}")
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return (None, f"HTTP {e.code}: {err_body[:300]}")
    except Exception as e:
        return (None, str(e))


def main() -> None:
    ap = argparse.ArgumentParser(description="Execute image generation from queue")
    ap.add_argument("--queue", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path, help="Results JSON output path")
    ap.add_argument("--project-root", type=Path, default=None, help="Project root for resolving relative paths")
    ap.add_argument("--delay", type=float, default=2.0, help="Delay between API calls (seconds)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_dotenv()
    API_KEY = os.getenv("AIGC_GITEE_API_KEY", "") or os.getenv("GITEE_API_TOKEN", "")
    if not API_KEY and not args.dry_run:
        raise SystemExit("Missing AIGC_GITEE_API_KEY / GITEE_API_TOKEN.")

    queue_data = load_json(args.queue.resolve())
    project_root = args.project_root.resolve() if args.project_root else args.queue.resolve().parent

    tasks = queue_data.get("generation_queue", [])
    if not tasks:
        print("No generation tasks in queue.")
        return

    total = len(tasks)
    completed = 0
    failed = 0
    skipped = 0
    results: list[dict[str, Any]] = []

    for i, task in enumerate(tasks):
        task_id = task["task_id"]
        shot_id = task["shot_id"]
        prompt = task.get("image_prompt", "")
        negative = task.get("negative_prompt", "")
        params = task.get("generation_parameters", {})
        res_str = params.get("resolution", "1024x576")
        width, height = parse_resolution(res_str)
        size = f"{width}x{height}"
        num_candidates = params.get("num_candidates", 2)
        candidates = task.get("output_candidates", [])

        if not prompt and task.get("generate_new_image"):
            results.append({"task_id": task_id, "shot_id": shot_id, "status": "skipped", "generated_images": [], "error": {"message": "Empty prompt.", "retryable": False}})
            skipped += 1
            continue

        generated: list[dict[str, Any]] = []
        task_failed = False

        for c in range(num_candidates):
            out_path = candidates[c] if c < len(candidates) else f"assets/images/candidates/{shot_id}_c{c+1}.png"
            abs_path = project_root / out_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)

            if abs_path.exists() and abs_path.stat().st_size > 100:
                print(f"  [{i+1}/{total}] {shot_id} c{c+1}: SKIP (exists)")
                generated.append({"candidate_id": abs_path.stem, "file_path": str(out_path), "api_status": "skipped_existing"})
                continue

            if args.dry_run:
                print(f"  [{i+1}/{total}] {shot_id} c{c+1}: DRY-RUN (size={size})")
                generated.append({"candidate_id": abs_path.stem, "file_path": str(out_path), "api_status": "dry_run"})
                continue

            print(f"  [{i+1}/{total}] {shot_id} c{c+1}: generating...", end=" ", flush=True)
            img_bytes, err = call_kolors(API_KEY, prompt, negative, size)

            if img_bytes:
                abs_path.write_bytes(img_bytes)
                generated.append({"candidate_id": abs_path.stem, "file_path": str(out_path), "api_status": "success"})
                print("OK")
            else:
                # Write placeholder on failure
                from struct import pack
                header = b"\x89PNG\r\n\x1a\n"
                import zlib
                raw = b"\x00" + bytes([width % 256, height % 256, 50]) * width
                raw_data = raw * height
                crc = lambda d: pack(">I", zlib.crc32(d) & 0xFFFFFFFF)
                abs_path.write_bytes(header + pack(">I", 13) + b"IHDR" + pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0) + crc(b"IHDR" + pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + pack(">I", len(zlib.compress(raw_data))) + b"IDAT" + zlib.compress(raw_data) + crc(b"IDAT" + zlib.compress(raw_data)) + pack(">I", 0) + b"IEND" + crc(b"IEND"))
                generated.append({"candidate_id": abs_path.stem, "file_path": str(out_path), "api_status": "failed", "error": err})
                task_failed = True
                print(f"FAIL: {err[:80]}")

            time.sleep(args.delay)

        status = "failed" if task_failed else "completed"
        if task_failed: failed += 1
        else: completed += 1

        results.append({
            "task_id": task_id,
            "shot_id": shot_id,
            "prompt_id": task.get("prompt_id", ""),
            "status": status,
            "generated_images": generated,
            "error": None if status == "completed" else {"message": "One or more candidates failed.", "retryable": True},
        })

    non_skipped = completed + failed
    print(f"\nDone: {completed} completed, {failed} failed, {skipped} skipped (of {total} tasks, {non_skipped} API calls)")

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
