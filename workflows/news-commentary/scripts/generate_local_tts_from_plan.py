#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_project_root(tts_plan_path: Path) -> Path:
    if tts_plan_path.parent.name == "audio":
        return tts_plan_path.parent.parent
    return tts_plan_path.parent


def resolve_output_path(project_root: Path, entry: dict[str, Any]) -> Path:
    planned = entry.get("planned_audio_path")
    if isinstance(planned, str) and planned:
        return (project_root / planned).resolve()
    return (project_root / "audio" / entry["speaker"] / f"{entry['entry_id']}.wav").resolve()


def local_tts_config(entry: dict[str, Any]) -> tuple[str, str, str]:
    voice_source = entry.get("voice_source") or {}
    speaker = str(voice_source.get("local_tts_speaker") or ("Serena" if entry["speaker"] == "host" else "Ryan"))
    language = str(voice_source.get("local_tts_language") or "chinese")
    instruction = str(voice_source.get("local_tts_instruction") or "")
    return speaker, language, instruction


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate local TTS audio from news-commentary tts-plan.json")
    parser.add_argument("--tts-plan", required=True, help="Path to audio/tts-plan.json")
    parser.add_argument("--tts-script", help="Override path to qwen-tts-local generate script")
    parser.add_argument("--project-root", help="Optional project root override")
    parser.add_argument("--fail-fast", action="store_true", help="Stop at first failed line")
    args = parser.parse_args()

    tts_plan_path = Path(args.tts_plan).resolve()
    project_root = Path(args.project_root).resolve() if args.project_root else resolve_project_root(tts_plan_path)
    tts_script = Path(args.tts_script).resolve() if args.tts_script else (Path(__file__).resolve().parents[2] / ".." / "generation" / "qwen-tts-local" / "scripts" / "generate_qwen_tts_local.sh").resolve()
    plan = load_json(tts_plan_path)
    results: list[dict[str, Any]] = []

    for index, entry in enumerate(plan.get("entries", []), start=1):
        output_path = resolve_output_path(project_root, entry)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        speaker, language, instruction = local_tts_config(entry)
        command = [
            "bash",
            str(tts_script),
            "--text",
            str(entry["text"]),
            "--language",
            language,
            "--speaker",
            speaker,
            "--output",
            str(output_path),
        ]
        if instruction:
            command.extend(["--instruct", instruction])

        try:
            print(f"[{index}/{len(plan.get('entries', []))}] {entry['entry_id']} -> {output_path}", flush=True)
            subprocess.run(command, check=True)
            results.append({"entry_id": entry["entry_id"], "status": "ok", "output_path": output_path.as_posix()})
        except Exception as exc:  # noqa: BLE001
            results.append({"entry_id": entry["entry_id"], "status": "failed", "error": str(exc)})
            if args.fail_fast:
                break

    manifest_path = project_root / "audio" / "tts-local-manifest.json"
    manifest_path.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")

    failures = [item for item in results if item["status"] != "ok"]
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
