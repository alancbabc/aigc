#!/usr/bin/env python3
"""Validate mv-keyframe-director coverage vs lyrics-timing and song duration.

Reports:
  - line_id partition (each line exactly once, same order as lyrics-timing)
  - timeline gaps: [0, first_kf.start), (last_kf.end, audio_duration] when known

Exit code 1 if partition is invalid; 0 if valid (warnings still printed for gaps).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate MV keyframe director vs lyrics timeline")
    ap.add_argument("--lyrics-timing", type=Path, required=True)
    ap.add_argument("--director", type=Path, required=True, help="mv-keyframe-director.json")
    ap.add_argument(
        "--gap-warn-seconds",
        type=float,
        default=2.0,
        help="Warn when head/tail gap exceeds this many seconds (default 2)",
    )
    args = ap.parse_args()

    timing = load_json(Path(args.lyrics_timing).resolve())
    director = load_json(Path(args.director).resolve())

    lines = timing.get("lines") or []
    line_order = [str(ln["line_id"]) for ln in lines if isinstance(ln, dict) and ln.get("line_id")]
    audio_end = timing.get("audio_duration_seconds")
    if not isinstance(audio_end, (int, float)) or float(audio_end) <= 0:
        audio_end = None

    kfs = director.get("keyframes") or []
    merged: list[str] = []
    seen: set[str] = set()
    for i, kf in enumerate(kfs):
        if not isinstance(kf, dict):
            print(f"ERROR keyframes[{i}] not an object", file=sys.stderr)
            sys.exit(1)
        refs = kf.get("line_refs") or kf.get("lines")
        if isinstance(refs, list) and refs and isinstance(refs[0], dict):
            refs = [str(x.get("line_id")) for x in refs if isinstance(x, dict) and x.get("line_id")]
        if not isinstance(refs, list):
            print(f"ERROR keyframes[{i}] missing line_refs", file=sys.stderr)
            sys.exit(1)
        for rid in refs:
            rid = str(rid)
            if rid in seen:
                print(f"ERROR duplicate line_id {rid!r}", file=sys.stderr)
                sys.exit(1)
            seen.add(rid)
            merged.append(rid)
            if rid not in line_order:
                print(f"ERROR unknown line_id {rid!r}", file=sys.stderr)
                sys.exit(1)

    missing = [lid for lid in line_order if lid not in seen]
    extra = [lid for lid in merged if lid not in line_order]
    if missing:
        print(f"ERROR lines not covered by any keyframe: {missing[:20]}{'…' if len(missing) > 20 else ''}", file=sys.stderr)
        sys.exit(1)
    if extra:
        print(f"ERROR extra line refs: {extra}", file=sys.stderr)
        sys.exit(1)
    if merged != line_order:
        print("ERROR line order in keyframes does not match lyrics-timing order", file=sys.stderr)
        sys.exit(1)

    print("OK line partition: all", len(line_order), "lines covered in order.")

    if not kfs:
        print("WARNING no keyframes")
        return

    try:
        t_first = float(kfs[0]["start_time"])
        t_last = float(kfs[-1]["end_time"])
    except (KeyError, TypeError, ValueError) as e:
        print(f"WARNING could not read start_time/end_time from keyframes: {e}")
        return

    head_gap = t_first - 0.0
    print(f"Head gap (0 -> first lyric keyframe): {head_gap:.3f}s (first lyric kf starts at {t_first:.3f}s)")

    tail_gap = None
    if audio_end is not None:
        tail_gap = float(audio_end) - t_last
        print(f"Tail gap (last keyframe -> end of audio): {tail_gap:.3f}s (audio_duration={float(audio_end):.3f}s, last_kf end={t_last:.3f}s)")

    ib_list = director.get("instrumental_bookends") or []
    intro_be = next((s for s in ib_list if isinstance(s, dict) and s.get("role") == "intro"), None)
    intro_covers = bool(
        intro_be
        and isinstance(intro_be.get("end_time"), (int, float))
        and abs(float(intro_be["end_time"]) - t_first) < 1.0
    )
    if intro_covers:
        print(
            f"OK inst_intro covers pre-vocal timeline 0 – {float(intro_be['end_time']):.3f}s "
            "(pair with video-plan for full MV coverage).",
        )
    elif head_gap >= args.gap_warn_seconds:
        print(
            f"  NOTE: Intro / pre-lyrics region is large — run extend_instrumental_bookends.py or add shots for 0–{t_first:.1f}s.",
        )

    if tail_gap is not None and tail_gap >= args.gap_warn_seconds:
        print(
            f"  NOTE: Outro / post-lyrics region is large — add b-roll, inst_outro via extend_instrumental_bookends.py, "
            f"or extend last segment in video-plan (~{tail_gap:.1f}s).",
        )

    if ib_list:
        print(f"instrumental_bookends present: {len(ib_list)} segment(s)")
        for seg in ib_list:
            if not isinstance(seg, dict):
                continue
            print(
                f"  - {seg.get('keyframe_id')} role={seg.get('role')} "
                f"{float(seg['start_time']):.3f}s – {float(seg['end_time']):.3f}s",
            )
        if any(isinstance(s, dict) and s.get("role") == "intro" for s in ib_list):
            print(
                "  NOTE: Use instrumental bookends for stills / I2V where LRC has no lines (intro/outro).",
            )


if __name__ == "__main__":
    main()
