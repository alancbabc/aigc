#!/usr/bin/env python3
"""
Build Video Plan from MV Storyboard.

Generates render-ready video-plan.json for LTX video generation.
"""

import json
import argparse
from pathlib import Path
from typing import Any


def build_video_plan(storyboard: dict, output_dir: str = "video-assets") -> dict:
    """Build video plan from storyboard."""
    shots = storyboard.get("shots", [])
    entries = []

    for shot in shots:
        shot_id = shot.get("shot_id", "unknown")
        start_time = shot.get("start_time", 0)
        end_time = shot.get("end_time", start_time + 5)
        duration = end_time - start_time
        camera = shot.get("camera", "medium")
        action = shot.get("action", "")
        section_ref = shot.get("section_ref", "")

        render_mode = determine_render_mode(camera, duration)

        entry = {
            "entry_id": shot_id,
            "section_ref": section_ref,
            "render_mode": render_mode,
            "time_window": {
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "duration_seconds": round(duration, 2),
            },
            "source": {
                "camera": camera,
                "action": action,
            },
            "output_path": f"{output_dir}/{shot_id}.mp4",
        }

        if render_mode == "text_image_to_video_high_quality":
            entry["prompt"] = generate_prompt(camera, action, section_ref)
            entry["images"] = []
            entry["video_seconds"] = min(duration, 8)

        entries.append(entry)

    return {
        "schema_version": "mv-lrc-workflow-v1",
        "song_title": storyboard.get("song_title", "Unknown"),
        "artist": storyboard.get("artist", "Unknown"),
        "total_duration": storyboard.get("total_duration", 0),
        "output_dir": output_dir,
        "aspect_ratio": "16:9",
        "resolution": {"width": 1920, "height": 1080},
        "entries": entries,
    }


def determine_render_mode(camera: str, duration: float) -> str:
    """Determine which render mode to use."""
    if camera in ("static", "fade"):
        return "image_audio_ffmpeg"
    elif duration > 10:
        return "text_image_to_video_high_quality"
    else:
        return "text_image_to_video_high_quality"


def generate_prompt(camera: str, action: str, section_ref: str) -> str:
    """Generate English prompt for LTX."""
    camera_terms = {
        "slow_push": "slow push-in camera movement",
        "medium": "medium shot",
        "medium_wide": "medium wide shot",
        "wide": "wide establish shot",
        "close_up": "close-up facial shot",
        "establishing": "establishing wide shot",
    }

    camera_desc = camera_terms.get(camera, "medium shot")
    section_desc = section_ref.replace("_", " ").title()

    return f"Cinematic {camera_desc}, {action}, music video style, {section_desc} section, high quality, professional lighting"


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build video plan from storyboard")
    parser.add_argument("input", help="storyboard.json path")
    parser.add_argument("-o", "--output", help="Output video-plan.json path")
    parser.add_argument("-d", "--output-dir", default="video-assets", help="Output directory")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        storyboard = json.load(f)

    video_plan = build_video_plan(storyboard, args.output_dir)

    output = args.output or args.input.replace("storyboard.json", "video-plan.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(video_plan, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(video_plan['entries'])} render entries")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()