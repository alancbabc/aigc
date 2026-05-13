#!/usr/bin/env python3
"""Add intro / outro instrumental bookends to mv-keyframe-director.json (no Qwen call).

Fills timeline gaps where there are no lyric-driven keyframes:
  - intro:  [0, first_line.start_time)
  - outro:  (last_lyric_keyframe.end_time, audio_duration_seconds]

Prompts are derived from mv-global-visual-style.json (motifs + global_style_suffix + lighting).

Does not modify lyrics keyframes or line_refs; adds optional top-level instrumental_bookends[].

Usage:
  python extend_instrumental_bookends.py \\
    --lyrics-timing <project>/lyrics-timing.json \\
    --director <project>/mv-keyframe-director.json \\
    --global-style <project>/mv-global-visual-style.json \\
    --out <project>/mv-keyframe-director.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MID = re.compile(r"^[a-z][a-z0-9_]*$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def motif_anchors(style: dict[str, Any], limit: int = 4) -> str:
    parts: list[str] = []
    for mo in (style.get("core_visual_motifs") or [])[:limit]:
        if not isinstance(mo, dict):
            continue
        a = mo.get("prompt_anchor_en")
        if a:
            parts.append(str(a).strip())
    return ", ".join(parts)


def first_last_section_refs(llm: dict[str, Any] | None) -> tuple[str, str]:
    if not llm:
        return "verse_placeholder", "outro"
    secs = [s for s in llm.get("sections", []) if isinstance(s, dict) and s.get("section_id")]
    if not secs:
        return "verse_placeholder", "outro"
    first_sid = str(secs[0]["section_id"])
    last_sid = str(secs[-1]["section_id"])
    for s in secs:
        if str(s.get("section_type") or "").lower() == "outro":
            last_sid = str(s["section_id"])
            break
    return first_sid, last_sid


def build_intro_en(style: dict[str, Any]) -> tuple[str, str, str]:
    suffix = str(style.get("global_style_suffix") or "").strip()
    anchors = motif_anchors(style)
    mood = str(style.get("lighting_mood_en") or "").strip()
    img = (
        f"Cinematic 16:9 wide establishing shot, instrumental prelude before vocals, "
        f"no singing or lip-sync, slow atmospheric build, sense of anticipation and space; "
        f"{suffix}. "
        f"Visual motifs: {anchors}. "
        f"{('Lighting: ' + mood + '. ') if mood else ''}"
        f"Soft ambient motion, empty horizon or texture-heavy environment, painterly depth."
    )
    i2v = (
        "Very slow dolly or crane into the environment, drifting mist or ink-like particles, "
        "8–12 second breath, hold silence; gentle parallax; dissolve-ready end point matching first vocal entry."
    )
    zh = "器乐前奏段：建立世界与情绪基调，为首个唱词镜头留出呼吸空间。"
    return img.strip(), i2v.strip(), zh


def build_outro_en(style: dict[str, Any]) -> tuple[str, str, str]:
    suffix = str(style.get("global_style_suffix") or "").strip()
    anchors = motif_anchors(style)
    mood = str(style.get("lighting_mood_en") or "").strip()
    tex = str(style.get("texture_material_en") or "").strip()
    img = (
        f"Extreme wide cinematic 16:9 resolution shot, post-vocal emotional dissolving, "
        f"instrumental tail space, lingering emptiness after last lyric; no singing action; "
        f"{suffix}. "
        f"Motifs returning as distant echoes: {anchors}. "
        f"{('Materials: ' + tex + '. ') if tex else ''}"
        f"{('Mood: ' + mood + '. ') if mood else ''}"
        f"Slow fade toward void or horizon, cathartic stillness."
    )
    i2v = (
        "Gradual pullback or slow zoom-out, decelerating motion, ink or light particles thinning, "
        "gentle fade to silence; long breath matching trailing instruments."
    )
    zh = "器乐尾奏/留白：情绪余韵消散，与曲终留白呼应。"
    return img.strip(), i2v.strip(), zh


def existing_ids(book: list[dict[str, Any]] | None) -> set[str]:
    out: set[str] = set()
    if not book:
        return out
    for seg in book:
        if not isinstance(seg, dict):
            continue
        kid = seg.get("keyframe_id")
        if isinstance(kid, str):
            out.add(kid)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Add instrumental intro/outro bookends to mv-keyframe-director JSON")
    ap.add_argument("--lyrics-timing", type=Path, required=True)
    ap.add_argument("--director", type=Path, required=True)
    ap.add_argument("--global-style", type=Path, required=True)
    ap.add_argument("--song-sections-llm", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None, help="Default: overwrite --director")
    ap.add_argument("--min-gap-seconds", type=float, default=2.0)
    ap.add_argument("--force", action="store_true", help="Replace existing inst_intro / inst_outro entries")
    ap.add_argument("--dry-run", action="store_true", help="Print plan + JSON patch only; do not write")
    args = ap.parse_args()

    timing = load_json(Path(args.lyrics_timing).resolve())
    director = load_json(Path(args.director).resolve())
    style = load_json(Path(args.global_style).resolve())
    llm = load_json(Path(args.song_sections_llm).resolve()) if args.song_sections_llm else None

    lines = timing.get("lines") or []
    if not lines:
        raise SystemExit("lyrics-timing has no lines")

    first_st = lines[0].get("start_time")
    if not isinstance(first_st, (int, float)):
        raise SystemExit("first line has no start_time — cannot derive intro gap")

    audio_end = timing.get("audio_duration_seconds")
    if not isinstance(audio_end, (int, float)) or float(audio_end) <= 0:
        audio_end = None

    kfs = director.get("keyframes") or []
    if not kfs:
        raise SystemExit("director has no keyframes")

    try:
        last_end = float(kfs[-1]["end_time"])
    except (KeyError, TypeError, ValueError) as e:
        raise SystemExit(f"cannot read keyframe times: {e}")

    head_gap = float(first_st) - 0.0
    tail_gap: float | None = None
    if audio_end is not None:
        tail_gap = float(audio_end) - last_end

    fi, la = first_last_section_refs(llm)

    book: list[dict[str, Any]] = list(director.get("instrumental_bookends") or [])
    if args.force:
        book = [
            b
            for b in book
            if isinstance(b, dict) and b.get("keyframe_id") not in ("inst_intro", "inst_outro")
        ]
    ids = existing_ids(book)

    added: list[str] = []

    intro_img, intro_i2v, intro_zh = build_intro_en(style)
    out_img, out_i2v, out_zh = build_outro_en(style)

    if head_gap >= args.min_gap_seconds and (args.force or "inst_intro" not in ids):
        if not MID.match("inst_intro"):
            raise SystemExit("internal: bad id")
        seg_intro = {
            "keyframe_id": "inst_intro",
            "role": "intro",
            "primary_section_ref": fi,
            "section_type_focus": "instrumental",
            "start_time": 0.0,
            "end_time": float(first_st),
            "narrative_beat_zh": intro_zh,
            "continuity_previous_en": "N/A",
            "continuity_next_en": "Transition into first vocal line; preserve texture language and palette.",
            "keyframe_image_prompt_en": intro_img,
            "video_from_keyframe_prompt_en": intro_i2v,
        }
        book.append(seg_intro)
        added.append("inst_intro")

    if (
        tail_gap is not None
        and tail_gap >= args.min_gap_seconds
        and (args.force or "inst_outro" not in ids)
    ):
        seg_out = {
            "keyframe_id": "inst_outro",
            "role": "outro",
            "primary_section_ref": la,
            "section_type_focus": "instrumental",
            "start_time": last_end,
            "end_time": float(audio_end),
            "narrative_beat_zh": out_zh,
            "continuity_previous_en": "Continue from last vocal keyframe mood; release tension into silence.",
            "continuity_next_en": "N/A",
            "keyframe_image_prompt_en": out_img,
            "video_from_keyframe_prompt_en": out_i2v,
        }
        book.append(seg_out)
        added.append("inst_outro")

    plan = {
        "head_gap_seconds": head_gap,
        "tail_gap_seconds": tail_gap,
        "would_add": added,
        "min_gap_seconds": args.min_gap_seconds,
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))

    if not added:
        print("No instrumental bookends added (gaps below threshold or inst_intro/outro already present).")
        return

    book.sort(key=lambda s: float(s["start_time"]))

    director["instrumental_bookends"] = book

    out_path = Path(args.out).resolve() if args.out else Path(args.director).resolve()
    if args.dry_run:
        print("--- instrumental_bookends (would write) ---")
        print(json.dumps(book, ensure_ascii=False, indent=2))
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(director, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
