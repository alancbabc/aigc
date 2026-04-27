#!/usr/bin/env python3
"""
LRC Parser for MV-LRC-Workflow.

Parses LRC format with section labels:
  [00:00.00](Intro)
  [00:15.00](Verse 1)
  [00:30.50]第一句歌词
  [00:34.20]第二句歌词
  ...

Supports formats:
  - Section start: [mm:ss.xx](SectionLabel)
  - Lyric line: [mm:ss.xx]Lyric text
  - Metadata: :key:value or [key:value]
"""

import re
import json
from typing import Optional
from dataclasses import dataclass, field


SECTION_TYPE_MAP = {
    "intro": "intro",
    " verses ": "verse",
    "pre-chorus": "pre_chorus",
    "pre chorus": "pre_chorus",
    "chorus": "chorus",
    "post-chorus": "post_chorus",
    " post chorus ": "post_chorus",
    "bridge": "bridge",
    "breakdown": "breakdown",
    "instrumental": "instrumental",
    "outro": "outro",
    "interlude": "interlude",
}


def parse_timestamp(ts: str) -> float:
    """Parse LRC timestamp [mm:ss.xx] to seconds."""
    ts = ts.strip("[]")
    parts = ts.split(":")
    if len(parts) != 2:
        return 0.0
    minutes = int(parts[0])
    seconds = float(parts[1])
    return minutes * 60 + seconds


def normalize_section_type(label: str) -> str:
    """Normalize section label to standard type."""
    label_lower = label.lower().strip()
    for key, value in SECTION_TYPE_MAP.items():
        if key in label_lower:
            return value
    return "verse"


def extract_section_number(label: str) -> Optional[int]:
    """Extract section number from label like 'Verse 1' or 'Chorus 2'."""
    match = re.search(r"\d+", label)
    return int(match.group()) if match else None


@dataclass
class LyricLine:
    """Represents a single lyric line with timing."""
    timestamp: float
    text: str


@dataclass
class SongSection:
    """Represents a song section with timing and lyrics."""
    section_id: str
    section_type: str
    section_label: str
    start_time: float
    lyrics: list = field(default_factory=list)

    @property
    def lyrics_text(self) -> list:
        return [line.text for line in self.lyrics if line.text.strip()]


class LRCParser:
    """Parser for LRC format files."""

    SECTION_LABEL_PATTERN = re.compile(r"\[(\d+:\d+\.\d+)\]\((.+?)\)")
    LYRIC_PATTERN = re.compile(r"\[(\d+:\d+\.\d+)\](.+)")
    METADATA_PATTERN = re.compile(r"^\[(\w+):(.+)\]$")
    COMMENT_PATTERN = re.compile(r"^#")

    def __init__(self):
        self.sections: list = []
        self.metadata: dict = {}
        self.artist: Optional[str] = None
        self.song_title: Optional[str] = None

    def parse_file(self, filepath: str) -> dict:
        """Parse LRC file and return song structure dict."""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse_content(content)

    def parse_content(self, content: str) -> dict:
        """Parse LRC content string."""
        lines = content.split("\n")
        current_section: Optional[SongSection] = None
        sections: list = []
        section_counts: dict = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            label_match = self.SECTION_LABEL_PATTERN.match(line)
            if label_match:
                timestamp = parse_timestamp(label_match.group(1))
                section_label = label_match.group(2).strip()

                normalized_type = normalize_section_type(section_label)
                section_number = extract_section_number(section_label) or 1
                type_key = normalized_type

                if normalized_type not in section_counts:
                    section_counts[normalized_type] = 0
                section_counts[normalized_type] += 1

                section_id = f"{normalized_type}_{section_counts[normalized_type]}"

                current_section = SongSection(
                    section_id=section_id,
                    section_type=normalized_type,
                    section_label=section_label,
                    start_time=timestamp,
                )
                sections.append(current_section)
                continue

            lyric_match = self.LYRIC_PATTERN.match(line)
            if lyric_match and current_section:
                timestamp = parse_timestamp(lyric_match.group(1))
                text = lyric_match.group(2).strip()
                current_section.lyrics.append(LyricLine(timestamp=timestamp, text=text))
                continue

            if line.startswith(":") or line.startswith("[") and ":" in line:
                key_val = line.lstrip(":[").split(":", 1)
                if len(key_val) == 2:
                    key = key_val[0].strip()
                    val = key_val[1].strip()
                    if key.lower() in ("ar", "artist"):
                        self.artist = val
                    elif key.lower() in ("ti", "title"):
                        self.song_title = val
                    else:
                        self.metadata[key] = val

        structured = self._build_song_structure(sections)
        structured["metadata"] = self.metadata

        return structured

    def _build_song_structure(self, sections: list) -> dict:
        """Build song-structure.json from parsed sections."""
        if not sections:
            return {
                "schema_version": "mv-lrc-workflow-v1",
                "song_title": self.song_title or "Unknown",
                "artist": self.artist,
                "total_duration_seconds": 0.0,
                "sections": [],
            }

        total_duration = 0.0
        structured_sections = []

        for i, section in enumerate(sections):
            if i + 1 < len(sections):
                end_time = sections[i + 1].start_time
            else:
                end_time = section.lyrics[-1].timestamp + 5.0 if section.lyrics else section.start_time + 30.0

            duration = end_time - section.start_time

            structured_sections.append({
                "section_id": section.section_id,
                "section_type": section.section_type,
                "section_label": section.section_label,
                "start_time": section.start_time,
                "end_time": end_time,
                "duration_seconds": duration,
                "lyrics_lines": section.lyrics_text,
                "lyrics_summary": self._generate_summary(section.lyrics_text) if section.lyrics_text else None,
            })

            total_duration = max(total_duration, end_time)

        return {
            "schema_version": "mv-lrc-workflow-v1",
            "song_title": self.song_title or "Unknown",
            "artist": self.artist,
            "total_duration_seconds": total_duration,
            "analysis_method": "lrc_parse",
            "sections": structured_sections,
        }

    def _generate_summary(self, lyrics_lines: list) -> str:
        """Generate brief summary from first lyric line."""
        if not lyrics_lines:
            return None
        first_line = lyrics_lines[0][:20]
        suffix = "..." if len(lyrics_lines[0]) > 20 else ""
        return f"{first_line}{suffix}"


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Parse LRC file to song-structure.json")
    parser.add_argument("input", help="LRC file path")
    parser.add_argument("-o", "--output", help="Output JSON file path")
    parser.add_argument("-t", "--title", help="Song title")
    parser.add_argument("-a", "--artist", help="Artist name")
    args = parser.parse_args()

    parser = LRCParser()
    result = parser.parse_file(args.input)

    if args.title:
        result["song_title"] = args.title
    if args.artist:
        result["artist"] = args.artist

    output = args.output or args.input.replace(".lrc", "-structure.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Parsed {len(result['sections'])} sections, duration: {result['total_duration_seconds']:.1f}s")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()