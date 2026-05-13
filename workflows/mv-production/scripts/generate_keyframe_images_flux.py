#!/usr/bin/env python3
"""Generate still images for MV keyframes using Gitee Kolors API.

Outputs (under project root by default):
  - keyframes/<keyframe_id>.png
  - keyframes/<keyframe_id>_labeled.png  (requires Pillow)
  - keyframe-images-manifest.json  (paths relative to project root)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import struct
import sys
import time
import zlib
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parents[3] / ".env"
    load_dotenv(str(_env_path))
except ImportError:
    pass

API_KEY = os.getenv("AIGC_GITEE_API_KEY", "")
DEFAULT_BASE_URL = "https://ai.gitee.com/v1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def create_placeholder_png(path: Path, width: int, height: int, color: tuple[int, int, int]) -> None:
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


def caption_dict(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
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


def rel_or_abs(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def flux_submit_and_wait(
    api_key: str,
    base_url: str,
    prompt: str,
    negative: str,
    width: int,
    height: int,
    output_path: Path,
) -> bool:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "kolors",
        "prompt": prompt,
        "negative_prompt": negative,
        "size": f"{width}x{height}",
    }

    try:
        req = urllib_request.Request(
            f"{base_url}/images/generations",
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())

        data_item = result.get("data", [{}])[0]
        b64 = data_item.get("b64_json", "")
        if b64:
            ensure_parent(output_path)
            output_path.write_bytes(base64.b64decode(b64))
            return True
        image_url = data_item.get("url", "")
        if image_url:
            urllib_request.urlretrieve(image_url, str(output_path))
            return True
        return False
    except HTTPError as e:
        import sys
        body = e.read()
        sys.stderr.write(f"  HTTP Error {e.code}: {body.decode('utf-8', errors='replace')[:500]}\n")
        sys.stderr.flush()
    except Exception as e:
        import sys
        sys.stderr.write(f"  API error: {type(e).__name__}: {e}\n")
        sys.stderr.flush()
    return False


def rel_or_abs(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate MV keyframe images using Gitee FLUX API",
    )
    ap.add_argument("--director", type=Path, required=True)
    ap.add_argument("--global-style", type=Path, required=True)
    ap.add_argument("--project-root", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--width", type=int, default=1024, help="Output width (default 1024, kolors supports 1024x576, 1024x768, 1024x1024, 512x512)")
    ap.add_argument("--height", type=int, default=576, help="Output height (default 576)")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--max-keyframes", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--style-prefix", default="")
    ap.add_argument("--user-requirements", type=Path, default=None)
    args = ap.parse_args()

    gen_width = args.width
    gen_height = args.height
    if args.user_requirements:
        req = load_json(Path(args.user_requirements).resolve())
        res = req.get("resolution")
        if isinstance(res, dict) and res.get("width") and res.get("height"):
            gen_width = int(res.get("width", args.width))
            gen_height = int(res.get("height", args.height))

    # Validate against Kolors supported sizes
    KOLORS_SIZES = {(1024, 576), (1024, 768), (1024, 1024), (512, 512)}
    if (gen_width, gen_height) not in KOLORS_SIZES:
        print(
            f"[warn] resolution {gen_width}x{gen_height} not in Kolors supported sizes {KOLORS_SIZES}. "
            f"Falling back to 1024x576.",
            file=sys.stderr,
        )
        gen_width, gen_height = 1024, 576

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

    song_title = director.get("song_title") or global_style.get("song_title") or ""
    manifest_keyframes: list[dict[str, Any]] = []

    colors = [
        (35, 42, 75),
        (55, 32, 62),
        (28, 58, 46),
        (62, 42, 24),
        (42, 24, 52),
        (75, 42, 35),
        (32, 55, 62),
        (46, 28, 58),
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
        prompt = build_positive_prompt(kf, global_style, style_prefix)
        raw_path = out_dir / f"{kid}.png"
        labeled_path = out_dir / f"{kid}_labeled.png"
        caption_src = caption_dict(kind, kf)

        api_ok: bool | None = None
        placeholder_fallback = False

        if args.dry_run:
            create_placeholder_png(raw_path, args.width, args.height, colors[i % len(colors)])
            print(f"[dry-run] placeholder {raw_path.name} ({kind})")
            api_ok = None
        else:
            if not API_KEY:
                print("[error] AIGC_GITEE_API_KEY not set")
                had_api_failure = True
                api_ok = False
                if args.strict:
                    sys.exit(1)
                create_placeholder_png(raw_path, args.width, args.height, colors[i % len(colors)])
                placeholder_fallback = True
            else:
                print(f"[generating] {kid} ({kind})")
                success = flux_submit_and_wait(
                    API_KEY, args.base_url, prompt, negative,
                    gen_width, gen_height, raw_path
                )
                if success:
                    api_ok = True
                    print(f"[done] {raw_path.name}")
                else:
                    print(f"[fail] {kid}")
                    had_api_failure = True
                    api_ok = False
                    if args.strict:
                        print("Exiting (--strict): no placeholder written.", file=sys.stderr)
                        sys.exit(1)
                    create_placeholder_png(raw_path, args.width, args.height, colors[i % len(colors)])
                    placeholder_fallback = True

        try:
            add_caption_overlay(raw_path, labeled_path, caption_src)
        except Exception as exc:
            print(f"[caption] {kid}: {exc} (install Pillow: pip install Pillow)")
            labeled_path = raw_path

        lines_out: list[dict[str, Any]] = []
        for ln in caption_src.get("lines") or []:
            lines_out.append({
                "line_id": ln.get("line_id"),
                "text": ln.get("text"),
                "start_time": float(ln["start_time"]),
                "end_time": float(ln["end_time"]),
            })

        file_ok = raw_path.exists()
        if args.dry_run:
            generation_ok = file_ok
        else:
            generation_ok = file_ok and api_ok is True

        entry: dict[str, Any] = {
            "keyframe_id": kid,
            "segment_kind": kind,
            "keyframe_type": kf.get("keyframe_type", "lyric_imagery"),
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
        "service_base_url": args.base_url,
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
            "Re-run with --strict to fail fast, or fix API key / network.",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()