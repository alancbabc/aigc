#!/usr/bin/env python3
"""
Assemble Final MV from Video Segments.

Combines rendered video segments with original song audio.
"""

import json
import argparse
import subprocess
from pathlib import Path
from typing import List


def assemble_mv(segments: List[str], audio_path: str, output_path: str) -> dict:
    """Assemble final MV from segments."""
    temp_list = Path(output_path).parent / "segments_list.txt"
    with open(temp_list, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(temp_list),
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        temp_list.unlink()
        return {"status": "success", "output_path": output_path}
    except subprocess.CalledProcessError as e:
        return {"status": "failed", "error": str(e)}


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Assemble final MV")
    parser.add_argument("--segments-dir", default="video-assets", help="Directory with video segments")
    parser.add_argument("--audio", required=True, help="Original song audio file")
    parser.add_argument("--output", default="output.mp4", help="Output file path")
    args = parser.parse_args()

    seg_dir = Path(args.segments_dir)
    segments = sorted(seg_dir.glob("*.mp4"))

    if not segments:
        print(f"No segments found in {seg_dir}")
        return

    result = assemble_mv([str(s) for s in segments], args.audio, args.output)

    if result["status"] == "success":
        print(f"Assembled {len(segments)} segments -> {args.output}")
    else:
        print(f"Failed: {result.get('error')}")


if __name__ == "__main__":
    main()