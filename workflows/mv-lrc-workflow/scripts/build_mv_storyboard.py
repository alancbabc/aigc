#!/usr/bin/env python3
"""
Build MV Storyboard from Song Structure.

Uses song-structure.json to generate beat-synced storyboard with:
- Shot breakdown per section
- Time windows aligned to song timeline
- Beat sync metadata
- Camera and transition suggestions
"""

import json
import argparse
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Shot:
    """Represents a single shot in the storyboard."""
    shot_id: str
    section_ref: str
    shot_type: str
    start_time: float
    end_time: float
    camera: str
    action: str
    lyrics_line_refs: list = field(default_factory=list)
    beat_sync: str = "on_beat"
    transition_from_previous: str = "cut"


SECTION_CAMERA_SUGGESTIONS = {
    "intro": {"default": "slow_push", "style": "cinematic"},
    "verse": {"default": "medium_steady", "style": "intimate"},
    "pre_chorus": {"default": "slow_zoom_in", "style": "building"},
    "chorus": {"default": "wide_dynamic", "style": "energetic"},
    "post_chorus": {"default": "medium", "style": "maintain"},
    "bridge": {"default": "close_up", "style": "intense"},
    "breakdown": {"default": "slow_motion", "style": "dramatic"},
    "instrumental": {"default": "static_or_pan", "style": "ambient"},
    "outro": {"default": "wide_fade", "style": "resolution"},
}


def estimate_shot_count(section_duration: float, section_type: str) -> int:
    """Estimate number of shots for a section based on duration and type."""
    if section_type in ("intro", "outro"):
        return max(1, int(section_duration / 8))
    elif section_type in ("chorus", "post_chorus"):
        return max(2, int(section_duration / 5))
    elif section_type in ("bridge", "breakdown"):
        return max(1, int(section_duration / 10))
    else:
        return max(2, int(section_duration / 6))


def determine_camera_for_shot(shot_num: int, total_shots: int, section_type: str) -> str:
    """Determine camera type for a specific shot."""
    suggestions = SECTION_CAMERA_SUGGESTIONS.get(section_type, SECTION_CAMERA_SUGGESTIONS["verse"])

    if shot_num == 0 and total_shots == 1:
        return suggestions.get("default", "medium")
    elif shot_num == 0:
        return "wide" if section_type in ("chorus", "intro") else "medium_wide"
    elif shot_num == total_shots - 1:
        return "close_up" if section_type in ("verse", "bridge") else "medium"
    else:
        return "medium"


def generate_shot_action(section_type: str, shot_num: int, total_shots: int) -> str:
    """Generate action description for shot."""
    actions = {
        "intro": ["establishing shot", "slow reveal", "camera push"],
        "verse": ["character walking", "looking around", "moment of reflection"],
        "pre_chorus": ["building intensity", "camera approach", "emotion rises"],
        "chorus": ["wide energetic shot", "crowd or lights", "dynamic movement"],
        "post_chorus": ["maintain energy", "continue motion"],
        "bridge": ["close-up moment", "intense gaze", "emotional beat"],
        "breakdown": ["slow motion", "dramatic pause"],
        "outro": ["fade out", "final moment", "resolution"],
    }

    options = actions.get(section_type, actions["verse"])
    return options[min(shot_num, len(options) - 1)]


def determine_transition(section_type: str, is_first_shot: bool = False) -> str:
    """Determine transition into this shot."""
    if is_first_shot:
        return "fade_in" if section_type == "intro" else "cut"

    transitions = {
        "intro": "fade_in",
        "verse": "match_cut",
        "pre_chorus": "smooth_zoom",
        "chorus": "jump_cut",
        "post_chorus": "smooth_transition",
        "bridge": "dissolve",
        "breakdown": "slow_motion",
        "outro": "fade_out",
    }
    return transitions.get(section_type, "cut")


def build_storyboard(song_structure: dict, mv_type: str = "mixed") -> dict:
    """Build complete MV storyboard from song structure."""
    shots = []
    shot_counter = 1

    sections = song_structure.get("sections", [])

    for section_idx, section in enumerate(sections):
        section_type = section.get("section_type", "verse")
        section_id = section.get("section_id", f"section_{section_idx}")
        start_time = section.get("start_time", 0)
        end_time = section.get("end_time", start_time + 30)
        duration = end_time - start_time
        lyrics_lines = section.get("lyrics_lines", [])

        shot_count = estimate_shot_count(duration, section_type)

        for shot_idx in range(shot_count):
            shot_start = start_time + (duration * shot_idx / shot_count)
            shot_end = start_time + (duration * (shot_idx + 1) / shot_count)

            camera = determine_camera_for_shot(shot_idx, shot_count, section_type)
            action = generate_shot_action(section_type, shot_idx, shot_count)
            transition = determine_transition(section_type, shot_idx == 0)

            beat_sync = "on_beat" if section_type in ("chorus", "pre_chorus") else "natural"

            shot = {
                "shot_id": f"shot_{shot_counter:03d}",
                "section_ref": section_id,
                "shot_type": determine_shot_type(section_type, shot_idx, shot_count),
                "start_time": round(shot_start, 2),
                "end_time": round(shot_end, 2),
                "duration_seconds": round(shot_end - shot_start, 2),
                "camera": camera,
                "action": action,
                "lyrics_line_refs": get_lyric_refs_for_shot(lyrics_lines, shot_idx, shot_count),
                "beat_sync": beat_sync,
                "transition_from_previous": transition,
            }

            shots.append(shot)
            shot_counter += 1

    return {
        "schema_version": "mv-lrc-workflow-v1",
        "mv_type": mv_type,
        "song_title": song_structure.get("song_title", "Unknown"),
        "artist": song_structure.get("artist", "Unknown"),
        "total_duration": song_structure.get("total_duration_seconds", 0),
        "total_shots": len(shots),
        "shots": shots,
    }


def determine_shot_type(section_type: str, shot_idx: int, total_shots: int) -> str:
    """Determine shot type."""
    if shot_idx == 0 and total_shots == 1:
        return "establishing"
    elif shot_idx == 0:
        return "wide"
    elif shot_idx == total_shots - 1:
        return "close_up"
    else:
        return "medium"


def get_lyric_refs_for_shot(lyrics_lines: list, shot_idx: int, total_shots: int) -> list:
    """Get lyric lines that fall within this shot."""
    if not lyrics_lines:
        return []

    lines_per_shot = max(1, len(lyrics_lines) // total_shots)
    start_idx = shot_idx * lines_per_shot
    end_idx = min(start_idx + lines_per_shot, len(lyrics_lines))

    return lyrics_lines[start_idx:end_idx]


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build MV storyboard from song-structure.json")
    parser.add_argument("input", help="song-structure.json path")
    parser.add_argument("-o", "--output", help="Output storyboard.json path")
    parser.add_argument("-t", "--mv-type", default="mixed", choices=["narrative", "performance", "concept", "mixed"])
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        song_structure = json.load(f)

    storyboard = build_storyboard(song_structure, args.mv_type)

    output = args.output or args.input.replace("song-structure.json", "storyboard.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(storyboard, f, ensure_ascii=False, indent=2)

    print(f"Generated {storyboard['total_shots']} shots")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()