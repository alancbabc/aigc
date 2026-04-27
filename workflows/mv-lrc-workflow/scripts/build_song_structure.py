#!/usr/bin/env python3
"""
Build Song Structure from LRC.

Wrapper script that:
1. Parses LRC file using parse_lrc.py
2. Generates song-structure.json with proper schema
3. Calculates section boundaries and metadata
"""

import json
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from parse_lrc import LRCParser


def build_song_structure(lrc_path: str, output_path: str = None, title: str = None, artist: str = None) -> dict:
    """Build song structure from LRC file."""
    parser = LRCParser()
    result = parser.parse_file(lrc_path)

    if title:
        result["song_title"] = title
    if artist:
        result["artist"] = artist

    result["schema_version"] = "mv-lrc-workflow-v1"
    result["analysis_method"] = "lrc_parse"
    result["lrc_source"] = lrc_path

    for section in result.get("sections", []):
        section["lyrics_summary"] = section.get("lyrics_summary") or _generate_summary(section.get("lyrics_lines", []))
        section["visual_suggestion"] = _infer_visual_suggestion(section.get("section_type", "verse"))
        section["mood"] = _infer_mood(section.get("section_type", "verse"))
        section["energy_level"] = _infer_energy(section.get("section_type", "verse"))
        section["transition_to_next"] = _infer_transition(section.get("section_type", "verse"))

    result["mood_arc"] = _build_mood_arc(result.get("sections", []))
    result["energy_arc"] = _build_energy_arc(result.get("sections", []))

    if output_path is None:
        output_path = lrc_path.replace(".lrc", "-structure.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


def _generate_summary(lyrics_lines: list) -> str:
    if not lyrics_lines:
        return None
    first = lyrics_lines[0][:15]
    return f"{first}..." if len(lyrics_lines[0]) > 15 else first


def _infer_visual_suggestion(section_type: str) -> str:
    suggestions = {
        "intro": "Dark establishing shot, slow camera push",
        "verse": "Character-focused shot, intimate framing",
        "pre_chorus": "Camera slowly approaching, building intensity",
        "chorus": "Wide energetic shot, dynamic movement",
        "post_chorus": "Maintain energy, continue motion",
        "bridge": "Close-up on face, soft focus",
        "breakdown": "Slow motion, dramatic pause",
        "instrumental": "Ambient footage, subtle movement",
        "outro": "Fade to black or freeze frame",
    }
    return suggestions.get(section_type, "Medium shot")


def _infer_mood(section_type: str) -> str:
    moods = {
        "intro": "mysterious",
        "verse": "nostalgic",
        "pre_chorus": "anticipation",
        "chorus": "passionate",
        "post_chorus": "euphoric",
        "bridge": "contemplative",
        "breakdown": "intense",
        "instrumental": "ambient",
        "outro": "peaceful",
    }
    return moods.get(section_type, "neutral")


def _infer_energy(section_type: str) -> str:
    energies = {
        "intro": "low",
        "verse": "medium_low",
        "pre_chorus": "medium",
        "chorus": "high",
        "post_chorus": "high",
        "bridge": "medium_low",
        "breakdown": "medium",
        "instrumental": "low",
        "outro": "low",
    }
    return energies.get(section_type, "medium")


def _infer_transition(section_type: str) -> str:
    transitions = {
        "intro": "fade_in",
        "verse": "match_cut",
        "pre_chorus": "smooth_zoom",
        "chorus": "jump_cut",
        "post_chorus": "smooth_transition",
        "bridge": "dissolve",
        "breakdown": "slow_motion",
        "instrumental": "fade",
        "outro": "fade_to_black",
    }
    return transitions.get(section_type, "cut")


def _build_mood_arc(sections: list) -> list:
    moods = []
    for section in sections:
        mood = section.get("mood", "neutral")
        if mood not in moods:
            moods.append(mood)
    return moods


def _build_energy_arc(sections: list) -> list:
    energies = []
    for section in sections:
        energy = section.get("energy_level", "medium")
        if energy not in energies:
            energies.append(energy)
    return energies


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build song-structure.json from LRC")
    parser.add_argument("input", help="LRC file path")
    parser.add_argument("-o", "--output", help="Output JSON path")
    parser.add_argument("-t", "--title", help="Song title")
    parser.add_argument("-a", "--artist", help="Artist name")
    args = parser.parse_args()

    result = build_song_structure(args.input, args.output, args.title, args.artist)

    print(f"Parsed {len(result['sections'])} sections")
    print(f"Duration: {result['total_duration_seconds']:.1f}s")
    print(f"Output: {args.output or args.input.replace('.lrc', '-structure.json')}")


if __name__ == "__main__":
    main()