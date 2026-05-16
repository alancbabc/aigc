#!/usr/bin/env python3
"""Assemble final MV from still images + original song audio.

Reads timeline.json + selected-asset-manifest.json.
For each shot with a selected image, creates a still-image video segment
(Ken Burns slow zoom effect) via FFmpeg. Then concatenates all segments
and overlays the original song audio.
"""

import argparse, json, os, subprocess, sys
from pathlib import Path
from typing import Any


def check_ffmpeg(ffmpeg_bin: str = "ffmpeg") -> None:
    try:
        subprocess.run([ffmpeg_bin, "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise SystemExit(f"FFmpeg not found: '{ffmpeg_bin}' is not installed or not in PATH.")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_ffmpeg(cmd: list[str], label: str = "") -> bool:
    prefix = f"  {label}: " if label else "  "
    print(f"{prefix}{cmd[1]}...", end=" ", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL ({r.stderr.strip()[-200:]})")
        return False
    print("OK")
    return True


def still_to_video(
    image_path: Path, output_path: Path, duration: float,
    width: int = 1024, height: int = 576,
) -> bool:
    """Convert a still image to video with slow Ken Burns zoom."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dur = max(duration, 1.0)
    fps = 24
    frames = int(dur * fps + 0.5)  # round to nearest frame
    zoom_end = 1.03

    zoom_filter = (
        f"zoompan=z='if(eq(on,1),1,min(zoom+({zoom_end}-1)/{frames},{zoom_end}))':"
        f"d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"fps={fps}:s={width}x{height}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-r", str(fps), "-i", str(image_path),
        "-vf", zoom_filter,
        "-t", str(dur),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-an",
        "-movflags", "+faststart",
        str(output_path),
    ]
    return run_ffmpeg(cmd, f"img2vid {image_path.name}")


def build_segments_video(
    segments: list[dict], project_root: Path, work_dir: Path,
    width: int, height: int,
    seq_lookup: dict[str, int] | None = None,
) -> list[Path]:
    """Create video segments from still images."""
    video_paths: list[Path] = []
    for i, seg in enumerate(segments):
        dur = max(seg["duration_seconds"], 1.0)
        img_str = seg.get("input_image", "")
        if not img_str:
            sid = seg["shot_id"]
            seq = seq_lookup.get(sid, 0) if seq_lookup else 0
            img_str = f"assets/images/selected/{seq:03d}_{sid}.png" if seq else f"assets/images/selected/{sid}.png"
        img_path = project_root / img_str
        
        if not img_path.exists():
            print(f"  [skip] {seg['shot_id']}: image not found: {img_path}")
            # Create a black placeholder
            placeholder = work_dir / f"_black_{i}.png"
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=black:size={width}x{height}:duration=1", "-frames:v", "1", str(placeholder)]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode != 0:
                print(f"  [warn] Failed to create black placeholder: {r.stderr.decode(errors='replace')[:100]}")
            img_path = placeholder
        
        out_path = work_dir / f"seg_{i:03d}_{seg['shot_id']}.mp4"
        still_to_video(img_path, out_path, dur, width, height)
        video_paths.append(out_path)
    return video_paths


def concat_and_mux(
    video_paths: list[Path], song_path: Path, output_path: Path, work_dir: Path,
) -> bool:
    """Concatenate video segments and overlay audio."""
    list_file = work_dir / "segments.txt"
    list_file.write_text("\n".join(f"file '{p.as_posix()}'" for p in video_paths) + "\n", encoding="utf-8")
    
    concat_path = work_dir / "concat.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", str(concat_path),
    ]
    if not run_ffmpeg(cmd, "concat"):
        return False
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(concat_path), "-i", str(song_path),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", "-movflags", "+faststart", str(output_path),
    ]
    return run_ffmpeg(cmd, "mux audio")


def main() -> None:
    ap = argparse.ArgumentParser(description="Assemble final MV from still images + song audio")
    ap.add_argument("--timeline", required=True, type=Path)
    ap.add_argument("--song-audio", required=True, type=Path)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--project-root", type=Path, default=None)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    args = ap.parse_args()

    check_ffmpeg()

    timeline = load_json(args.timeline.resolve())
    project_root = (args.project_root or args.timeline.parent).resolve()
    song_path = args.song_audio.resolve()
    output_path = (args.output or project_root / "assets" / "videos" / "final" / "output.mp4").resolve()
    work_dir = output_path.parent / "_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    segments = timeline.get("segments", [])
    segments.sort(key=lambda s: s["start_time"])
    print(f"Building {len(segments)} segments...")

    # Build shot_id → sequence from segment order
    seq_lookup = {seg.get("shot_id", ""): i + 1 for i, seg in enumerate(segments)}

    video_paths = build_segments_video(segments, project_root, work_dir, args.width, args.height, seq_lookup)

    if not video_paths:
        print("No video segments created.")
        return

    total_dur = sum(s["duration_seconds"] for s in segments)
    print(f"Concat {len(video_paths)} segments ({total_dur:.1f}s) + audio...")
    
    if concat_and_mux(video_paths, song_path, output_path, work_dir):
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\nFinal MV: {output_path} ({size_mb:.1f} MB, {total_dur:.1f}s)")
    else:
        print("\nAssembly failed.")


if __name__ == "__main__":
    main()
