#!/usr/bin/env python3
"""
Generate Keyframes from Storyboard.

Generates keyframe prompts and optionally calls image generation.
"""

import json
import argparse
from pathlib import Path
from typing import Any


KEYFRAME_CAMERA_SYSTEM = {
    "slow_push": "cinematic slow push-in camera, professional lighting",
    "medium": "medium shot, character-focused framing",
    "medium_wide": "medium wide shot, environmental context",
    "wide": "wide establishing shot, epic scale",
    "close_up": "close-up facial shot, intimate framing",
    "establishing": "establishing wide shot, atmospheric",
    "static": "static shot, subtle movement",
}


def generate_keyframe_prompts(storyboard: dict) -> dict:
    """Generate keyframe prompts from storyboard."""
    shots = storyboard.get("shots", [])
    prompts = []

    for shot in shots:
        shot_id = shot.get("shot_id", "unknown")
        camera = shot.get("camera", "medium")
        action = shot.get("action", "")
        section_ref = shot.get("section_ref", "")
        start_time = shot.get("start_time", 0)

        camera_system = KEYFRAME_CAMERA_SYSTEM.get(camera, KEYFRAME_CAMERA_SYSTEM["medium"])

        prompt = f"{camera_system}, {action}, music video aesthetic, high quality, professional cinematography"

        prompt_entry = {
            "shot_id": shot_id,
            "section_ref": section_ref,
            "start_time": start_time,
            "camera": camera,
            "prompt": prompt,
            "style": "cinematic",
        }

        prompts.append(prompt_entry)

    return {
        "schema_version": "mv-lrc-workflow-v1",
        "song_title": storyboard.get("song_title", "Unknown"),
        "artist": storyboard.get("artist", "Unknown"),
        "total_keyframes": len(prompts),
        "keyframe_prompts": prompts,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate keyframe prompts from storyboard")
    parser.add_argument("input", help="storyboard.json path")
    parser.add_argument("-o", "--output", help="Output keyframe-prompts.json path")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        storyboard = json.load(f)

    keyframes = generate_keyframe_prompts(storyboard)

    output = args.output or args.input.replace("storyboard.json", "keyframe-prompts.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(keyframes, f, ensure_ascii=False, indent=2)

    print(f"Generated {keyframes['total_keyframes']} keyframe prompts")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()