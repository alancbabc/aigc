#!/usr/bin/env python3
"""Generate still images for MV keyframes from mv-keyframe-director.json + mv-global-visual-style.json.

Calls the local Qwen Image service (POST /submit, same contract as generate_qwen_image_local.sh).

Outputs (under project root by default):
  - keyframes/<keyframe_id>.png
  - keyframes/<keyframe_id>_labeled.png  (requires Pillow)
  - keyframe-images-manifest.json  (paths relative to project root)

Use --project-root <dir> so manifests use stable relative paths (defaults to parent directory of --director).

Environment:
  QWEN_IMAGE_LOCAL_BASE_URL  (default http://10.0.180.14:9000)
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
import zlib
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = os.environ.get("QWEN_IMAGE_LOCAL_BASE_URL", "http://10.0.180.14:9000")
POLL_SECONDS = 15
MAX_POLLS = 120


def _load_aigc_dotenv() -> None:
    """Load aigc/.env before reading QWEN_IMAGE_LOCAL_BASE_URL / keys (same as generate_keyframes.py)."""
    root = Path(__file__).resolve().parents[3]
    for env_path in (root / ".env", Path.cwd() / ".env"):
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


def create_placeholder_png(path: Path, width: int, height: int, color: tuple[int, int, int]) -> None:
    """Write a minimal solid-color PNG without Pillow."""

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ensure_parent(path)
    header = b"\x89PNG\r\n\x1a\n"
    ihdr = make_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    raw_row = b"\x00" + bytes(color) * width
    raw_data = raw_row * height
    idat = make_chunk(b"IDAT", zlib.compress(raw_data))
    iend = make_chunk(b"IEND", b"")
    path.write_bytes(header + ihdr + idat + iend)


def build_negative_prompt(global_style: dict[str, Any]) -> str:
    hints = global_style.get("negative_style_hints_en") or []
    return ", ".join(str(h) for h in hints if h)


def build_positive_prompt(
    kf: dict[str, Any],
    global_style: dict[str, Any],
    style_prefix: str = "",
) -> str:
    base = (kf.get("keyframe_image_prompt_en") or "").strip()
    extras: list[str] = []
    tex = global_style.get("texture_material_en")
    if tex:
        extras.append(str(tex))
    mood = global_style.get("lighting_mood_en")
    if mood:
        extras.append(str(mood))
    if extras:
        base = f"{base}, {', '.join(extras)}"
    pre = (style_prefix or "").strip()
    if pre:
        base = f"{pre}, {base}"
    return base


def fmt_clock(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    m = int(seconds // 60)
    s = seconds - (m * 60)
    return f"{m:d}:{s:06.3f}"


def wrap_lines(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if cur and cur_len + add > width:
            lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
        else:
            cur.append(w)
            cur_len += add
    if cur:
        lines.append(" ".join(cur))
    return lines


def add_caption_overlay(
    src: Path,
    dst: Path,
    kf: dict[str, Any],
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(src).convert("RGBA")
    w, h = img.size
    lines_block: list[str] = [
        f"Keyframe: {kf.get('keyframe_id', '')}  |  {fmt_clock(float(kf['start_time']))} – {fmt_clock(float(kf['end_time']))}",
        f"Section: {kf.get('primary_section_ref', '')} ({kf.get('section_type_focus', '')})",
        "",
        "Lyrics:",
    ]
    for line in kf.get("lines") or []:
        t0 = float(line["start_time"])
        t1 = float(line["end_time"])
        body = str(line.get("text", ""))
        prefix = f"[{fmt_clock(t0)}–{fmt_clock(t1)}]"
        for sub in wrap_lines(f"{prefix} {body}", max(24, w // 14)):
            lines_block.append(sub)

    text = "\n".join(lines_block)

    overlay_h = min(int(h * 0.42), max(160, 14 * (2 + len(lines_block))))
    bar = Image.new("RGBA", (w, overlay_h), (0, 0, 0, 200))
    composite = Image.new("RGBA", (w, h + overlay_h))
    composite.paste(img, (0, 0))
    composite.paste(bar, (0, h), bar)

    draw = ImageDraw.Draw(composite)
    try:
        font = ImageFont.truetype("arial.ttf", max(14, min(22, w // 55)))
    except OSError:
        font = ImageFont.load_default()

    margin = 16
    y = h + margin
    for raw_line in text.split("\n"):
        draw.text((margin, y), raw_line, fill=(255, 255, 255, 255), font=font)
        bbox = draw.textbbox((margin, y), raw_line, font=font)
        y = bbox[3] + 4

    composite.convert("RGB").save(dst, format="PNG")


def qwen_submit(
    base_url: str,
    prompt: str,
    negative: str,
    width: int,
    height: int,
    steps: int,
) -> str:
    url = f"{base_url.rstrip('/')}/submit"
    data: dict[str, str] = {
        "prompt": prompt,
        "height": str(height),
        "width": str(width),
        "num_inference_steps": str(steps),
        "pipeline_name": "qwen_image",
    }
    if negative:
        data["negative_prompt"] = negative
    resp = requests.post(url, data=data, timeout=120)
    resp.raise_for_status()
    body = resp.json()
    tid = body.get("task_id")
    if not tid:
        raise RuntimeError(f"Missing task_id: {body}")
    return str(tid)


def qwen_poll_until_done(base_url: str, task_id: str) -> None:
    url = f"{base_url.rstrip('/')}/status/{task_id}"
    for _ in range(MAX_POLLS):
        time.sleep(POLL_SECONDS)
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        st = r.json().get("status")
        if st == "done":
            return
        if st == "error":
            raise RuntimeError(f"Task error: {r.text}")
    raise TimeoutError(f"Task {task_id} did not finish within {MAX_POLLS * POLL_SECONDS}s")


def qwen_download(base_url: str, task_id: str, out: Path) -> None:
    url = f"{base_url.rstrip('/')}/download/{task_id}"
    ensure_parent(out)
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    out.write_bytes(r.content)


def rel_or_abs(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def caption_dict(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Instrumental bookends have no lyric lines; synthesize one caption line for labeling."""
    if kind == "lyric":
        return payload
    st = float(payload["start_time"])
    et = float(payload["end_time"])
    role = str(payload.get("role") or "instrumental")
    cap = dict(payload)
    cap["lines"] = [
        {
            "line_id": f"instrumental_{role}",
            "text": f"({role}, instrumental — no vocals)",
            "start_time": st,
            "end_time": et,
        }
    ]
    return cap


def main() -> None:
    _load_aigc_dotenv()

    ap = argparse.ArgumentParser(
        description="Generate MV keyframe images from mv-keyframe-director.json (canonical mv-production path)",
    )
    ap.add_argument(
        "--director",
        type=Path,
        required=True,
        help="Path to mv-keyframe-director.json",
    )
    ap.add_argument(
        "--global-style",
        type=Path,
        required=True,
        help="Path to mv-global-visual-style.json",
    )
    ap.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project directory for relative paths in manifest (default: directory containing --director)",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory for PNGs (default: <project-root>/keyframes)",
    )
    ap.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Output manifest path (default: <project-root>/keyframe-images-manifest.json)",
    )
    ap.add_argument(
        "--base-url",
        default=None,
        help="Qwen Image local base URL (default: env QWEN_IMAGE_LOCAL_BASE_URL or http://10.0.180.14:9000)",
    )
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--steps", type=int, default=50)
    ap.add_argument(
        "--max-keyframes",
        type=int,
        default=0,
        help="If > 0, only process the first N keyframes (smoke tests). Writes manifest.partial.json by default.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip API; write solid-color placeholders and optional captions",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="On API failure, exit with error instead of writing a placeholder image",
    )
    ap.add_argument(
        "--style-prefix",
        default="",
        help="Prepended to every English prompt (guofeng / look lock). Overrides MV_KEYFRAME_STYLE_PREFIX when non-empty.",
    )
    ap.add_argument(
        "--user-requirements",
        type=Path,
        default=None,
        help="Optional JSON; uses keyframe_style_prefix when --style-prefix is empty, plus reference_images and resolution",
    )
    ap.add_argument(
        "--reference-images",
        type=str,
        default=None,
        help="Comma-separated paths to singer/artist reference images for character_singing keyframes",
    )
    args = ap.parse_args()

    base_url = (args.base_url or os.getenv("QWEN_IMAGE_LOCAL_BASE_URL") or "http://10.0.180.14:9000").rstrip("/")
    print(f"[qwen-image] base URL: {base_url}")

    director_path = Path(args.director).resolve()
    project_root = Path(args.project_root).resolve() if args.project_root else director_path.parent
    default_manifest = project_root / "keyframe-images-manifest.json"
    manifest_path = Path(args.manifest).resolve() if args.manifest else default_manifest
    if args.max_keyframes > 0 and manifest_path.resolve() == default_manifest.resolve():
        manifest_path = project_root / "keyframe-images-manifest.partial.json"

    out_dir = Path(args.out_dir).resolve() if args.out_dir else (project_root / "keyframes")
    out_dir.mkdir(parents=True, exist_ok=True)

    director = load_json(director_path)
    global_style = load_json(Path(args.global_style).resolve())
    negative = build_negative_prompt(global_style)

    style_prefix = (args.style_prefix or "").strip()
    if not style_prefix and args.user_requirements:
        req = load_json(Path(args.user_requirements).resolve())
        style_prefix = str(req.get("keyframe_style_prefix") or "").strip()
    if not style_prefix:
        style_prefix = str(os.environ.get("MV_KEYFRAME_STYLE_PREFIX", "") or "").strip()

    reference_images: list[str] = []
    if args.reference_images:
        reference_images = [p.strip() for p in args.reference_images.split(",") if p.strip()]
    if not reference_images and args.user_requirements:
        req = load_json(Path(args.user_requirements).resolve())
        refs = req.get("reference_images") or []
        if isinstance(refs, list):
            reference_images = [str(r) for r in refs if r]
    if reference_images:
        print(f"[refs] {len(reference_images)} reference image(s) for character_singing keyframes")
        for r in reference_images:
            if not Path(r).exists():
                print(f"[warn] reference image not found: {r}")

    gen_width = args.width
    gen_height = args.height
    # Read resolution from user_requirements.json (overrides CLI defaults)
    if args.user_requirements:
        req = load_json(Path(args.user_requirements).resolve())
        res = req.get("resolution")
        if isinstance(res, dict) and res.get("width") and res.get("height"):
            gen_width = int(res.get("width", gen_width))
            gen_height = int(res.get("height", gen_height))

    song_title = director.get("song_title") or global_style.get("song_title") or ""
    manifest_keyframes: list[dict[str, Any]] = []

    colors = [
        (35, 42, 75),
        (55, 32, 62),
        (28, 58, 46),
        (62, 42, 24),
        (42, 24, 52),
    ]

    lyric_kfs = list(director.get("keyframes") or [])
    if args.max_keyframes and args.max_keyframes > 0:
        lyric_kfs = lyric_kfs[: args.max_keyframes]

    timeline: list[tuple[str, dict[str, Any]]] = []
    for k in lyric_kfs:
        timeline.append(("lyric", k))
    for seg in director.get("instrumental_bookends") or []:
        timeline.append(("instrumental", seg))
    timeline.sort(key=lambda x: float(x[1]["start_time"]))

    had_api_failure = False

    for i, (kind, kf) in enumerate(timeline):
        kid = str(kf.get("keyframe_id") or f"kf_{i+1:02d}")
        kf_type = str(kf.get("keyframe_type") or "lyric_visual")
        # Normalize legacy alias
        if kf_type == "lyric_imagery":
            kf_type = "lyric_visual"
        prompt = build_positive_prompt(kf, global_style, style_prefix)

        if kf_type == "character_singing" and reference_images:
            ref = reference_images[0]
            print(f"[{kid}] character_singing (ref: {ref})")
            if Path(ref).exists():
                prompt = f"{prompt}, character singing on stage, spotlight, expressive performance, close-up on face, emotional delivery"
            else:
                print(f"[warn] {kid}: reference image missing, falling back to lyric_emotional")
                kf_type = "lyric_emotional"
        elif kf_type == "instrumental":
            print(f"[{kid}] instrumental — using wide empty environmental shot")
        elif kf_type == "lyric_emotional":
            print(f"[{kid}] lyric_emotional — translating emotional temperature to visual metaphor")
        elif kf_type == "lyric_philosophical":
            print(f"[{kid}] lyric_philosophical — symbolic imagery")

        raw_path = out_dir / f"{kid}.png"
        labeled_path = out_dir / f"{kid}_labeled.png"
        caption_src = caption_dict(kind, kf)

        api_ok: bool | None = None
        placeholder_fallback = False

        if args.dry_run:
            create_placeholder_png(raw_path, gen_width, gen_height, colors[i % len(colors)])
            print(f"[dry-run] placeholder {raw_path.name} ({kind}, {kf_type})")
            api_ok = None
        else:
            try:
                tid = qwen_submit(base_url, prompt, negative, gen_width, gen_height, args.steps)
                print(f"[submit] {kid} ({kind}, {kf_type}) task_id={tid}")
                qwen_poll_until_done(base_url, tid)
                qwen_download(base_url, tid, raw_path)
                api_ok = True
                print(f"[done] {raw_path.name}")
            except Exception as exc:
                print(f"[fail] {kid}: {exc}")
                had_api_failure = True
                api_ok = False
                if args.strict:
                    print("Exiting (--strict): no placeholder written.", file=sys.stderr)
                    sys.exit(1)
                create_placeholder_png(raw_path, gen_width, gen_height, colors[i % len(colors)])
                placeholder_fallback = True

        try:
            add_caption_overlay(raw_path, labeled_path, caption_src)
        except Exception as exc:
            print(f"[caption] {kid}: {exc} (install Pillow: pip install Pillow)")
            labeled_path = raw_path

        lines_out: list[dict[str, Any]] = []
        for ln in caption_src.get("lines") or []:
            lines_out.append(
                {
                    "line_id": ln.get("line_id"),
                    "text": ln.get("text"),
                    "start_time": float(ln["start_time"]),
                    "end_time": float(ln["end_time"]),
                }
            )

        file_ok = raw_path.exists()
        if args.dry_run:
            generation_ok = file_ok
        else:
            generation_ok = file_ok and api_ok is True

        entry: dict[str, Any] = {
            "keyframe_id": kid,
            "segment_kind": kind,
            "keyframe_type": kf_type,
            "primary_section_ref": kf.get("primary_section_ref"),
            "section_type_focus": kf.get("section_type_focus"),
            "start_time": float(kf["start_time"]),
            "end_time": float(kf["end_time"]),
            "lyrics": lines_out,
            "image_png": rel_or_abs(raw_path, project_root),
            "image_labeled_png": rel_or_abs(labeled_path, project_root),
            "prompt_used": prompt,
            "negative_prompt_used": negative,
            "generation_ok": generation_ok,
            "dry_run": bool(args.dry_run),
            "api_generation_ok": api_ok,
            "placeholder_fallback": placeholder_fallback,
        }
        if kind == "instrumental":
            entry["role"] = kf.get("role")
        manifest_keyframes.append(entry)

    manifest = {
        "schema_version": "1.1",
        "song_title": song_title,
        "artist": director.get("artist") or global_style.get("artist"),
        "source_files": {
            "mv_keyframe_director": str(director_path),
            "mv_global_visual_style": str(Path(args.global_style).resolve()),
        },
        "project_root": str(project_root),
        "style_prefix_applied": style_prefix or None,
        "service_base_url": base_url,
        "image_size": {"width": gen_width, "height": gen_height},
        "dry_run": bool(args.dry_run),
        "strict_mode": bool(args.strict),
        "max_keyframes_applied": args.max_keyframes if args.max_keyframes > 0 else None,
        "max_keyframes_note": "Caps lyric keyframes only; instrumental_bookends are always included when present.",
        "lyric_keyframes_total": len(director.get("keyframes") or []),
        "instrumental_bookends_total": len(director.get("instrumental_bookends") or []),
        "keyframes_total_in_source": len(director.get("keyframes") or []),
        "keyframes_in_manifest": len(manifest_keyframes),
        "keyframes": manifest_keyframes,
    }
    ensure_parent(manifest_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {manifest_path}")

    if had_api_failure and not args.strict:
        print(
            "WARNING: one or more API calls failed; placeholders were written. "
            "Re-run with --strict to fail fast, or fix Qwen Image service / network.",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
