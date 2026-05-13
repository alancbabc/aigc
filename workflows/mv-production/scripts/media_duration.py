"""Best-effort audio duration probing (seconds). Used when ffprobe isn't required."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def probe_audio_duration_seconds(path: Path) -> float | None:
    """Return duration from ffprobe if available; else mutagen if installed; else None."""
    resolved = Path(path).resolve()
    if not resolved.is_file():
        return None

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            proc = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(resolved),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return round(float(proc.stdout.strip()), 3)
        except (ValueError, OSError, subprocess.SubprocessTimeoutExpired):
            pass

    try:
        from mutagen import File as mutagen_file
    except ImportError:
        return None

    try:
        audio = mutagen_file(resolved)
        if audio is None or audio.info is None:
            return None
        length = getattr(audio.info, "length", None)
        if isinstance(length, (int, float)) and length > 0:
            return round(float(length), 3)
    except (OSError, ValueError, AttributeError, TypeError):
        pass

    return None
