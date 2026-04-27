#!/usr/bin/env python3
"""
Render MV Segments from Video Plan.

Generates video segments from storyboard + keyframes using LTX or ffmpeg.
"""

import json
import argparse
import subprocess
from pathlib import Path


def render_segments(video_plan: dict, output_dir: str) -> dict:
    """Render video segments according to plan."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rendered = []

    for item in video_plan.get("render_items", []):
        item_id = item.get("item_id", f"item_{len(rendered)}")
        render_mode = item.get("render_mode", "ltx")

        if render_mode == "ltx":
            result = _render_ltx(item, output_path / f"{item_id}.mp4")
        elif render_mode == "ffmpeg":
            result = _render_ffmpeg(item, output_path / f"{item_id}.mp4")
        else:
            result = {"status": "skipped", "reason": f"unknown mode {render_mode}"}

        rendered.append({
            "item_id": item_id,
            "output_path": str(output_path / f"{item_id}.mp4"),
            "status": result.get("status", "unknown"),
        })

    return {
        "total_items": len(video_plan.get("render_items", [])),
        "rendered": rendered,
    }


def _render_ltx(item: dict, output_path) -> dict:
    """Render using LTX Video."""
    return {
        "status": "placeholder",
        "reason": "LTX rendering requires generation/ltx23-video skill",
        "output_path": str(output_path),
    }


def _render_ffmpeg(item: dict, output_path) -> dict:
    """Render using ffmpeg."""
    image_path = item.get("image_path")
    audio_path = item.get("audio_path")

    if not image_path or not audio_path:
        return {"status": "skipped", "reason": "missing image or audio"}

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black",
        "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return {"status": "success", "output_path": str(output_path)}
    except subprocess.CalledProcessError as e:
        return {"status": "failed", "error": str(e)}


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Render MV segments from video plan")
    parser.add_argument("input", help="video-plan.json path")
    parser.add_argument("-o", "--output-dir", default="video-assets", help="Output directory")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        video_plan = json.load(f)

    result = render_segments(video_plan, args.output_dir)

    print(f"Rendered {len(result['rendered'])} / {result['total_items']} items")
    print(f"Output: {args.output_dir}/")


if __name__ == "__main__":
    main()