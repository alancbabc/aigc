#!/usr/bin/env python3
"""Render Stage 11 segments from news-commentary render-plan.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


DEFAULT_FRAME_RATE = 24
DEFAULT_VIDEO_CODEC = "libx264"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_AUDIO_BITRATE = "128k"
DEFAULT_FFMPEG_BIN = "ffmpeg"
DEFAULT_MERGED_AUDIO_SILENCE_SECONDS = 1.0
DEFAULT_LTX_VARIANT_COUNT = 4


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def project_root_from_render_plan(render_plan_path: Path) -> Path:
    if render_plan_path.parent.name == "video":
        return render_plan_path.parent.parent
    return render_plan_path.parent


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def resolve_project_path(project_root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return Path(str(candidate).replace("\\", "/"))
    return (project_root / candidate).resolve()


def to_bash_path(path: Path) -> str:
    p = str(path)
    if re.match(r"^[A-Za-z]:", p):
        return "/mnt/c/" + p.replace("\\", "/")[3:]
    return p


def default_ltx_node_script_path() -> Path:
    temp_script = Path("C:/Users/15712/AppData/Local/Temp/jinyi_stage11/stage11_render_ltx_node.mjs")
    if temp_script.exists():
        return temp_script
    return (Path(__file__).resolve().parents[1] / "stage11_render_ltx_node.mjs").resolve()


def run_command(command: list[str], log_path: Path) -> None:
    ensure_parent(log_path)
    command_str = " ".join(command)
    log_path.write_text("COMMAND:\n" + command_str + "\n\nSTDOUT:\n", encoding="utf-8")
    completed = subprocess.run(command, capture_output=True, text=True, check=False, shell=False)
    if completed.stdout:
        existing = log_path.read_text(encoding="utf-8")
        log_path.write_text(existing + completed.stdout + "\nSTDERR:\n" + completed.stderr, encoding="utf-8")
    else:
        existing = log_path.read_text(encoding="utf-8")
        log_path.write_text(existing + "\nSTDERR:\n" + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {command_str}")
    existing = log_path.read_text(encoding="utf-8")
    log_path.write_text(
        existing
        + completed.stdout
        + "\nSTDERR:\n"
        + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}")


def build_silence_frames(params: wave._wave_params, silence_seconds: float) -> bytes:
    frame_rate = int(params.framerate)
    sample_width = int(params.sampwidth)
    channels = int(params.nchannels)
    frame_count = max(int(round(frame_rate * silence_seconds)), 0)
    return b"\x00" * frame_count * sample_width * channels


def mergeable_params(p1: wave._wave_params, p2: wave._wave_params) -> bool:
    return p1.nchannels == p2.nchannels and p1.sampwidth == p2.sampwidth and p1.framerate == p2.framerate and p1.comptype == p2.comptype and p1.compname == p2.compname


def merge_wav_audio_files(audio_paths: list[Path], output_path: Path, silence_seconds: float = DEFAULT_MERGED_AUDIO_SILENCE_SECONDS) -> Path:
    if not audio_paths:
        raise ValueError("No audio paths provided for WAV merge")

    ensure_parent(output_path)
    with wave.open(str(audio_paths[0]), "rb") as first_audio:
        params = first_audio.getparams()
        frames = [first_audio.readframes(first_audio.getnframes())]

    for audio_path in audio_paths[1:]:
        with wave.open(str(audio_path), "rb") as current_audio:
            if not mergeable_params(current_audio.getparams(), params):
                raise ValueError(f"Cannot merge WAV files with incompatible format: {audio_path}")
            if silence_seconds > 0:
                frames.append(build_silence_frames(params, silence_seconds))
            frames.append(current_audio.readframes(current_audio.getnframes()))

    with wave.open(str(output_path), "wb") as merged_audio:
        merged_audio.setparams(params)
        for chunk in frames:
            merged_audio.writeframes(chunk)

    return output_path


def variant_output_path(output_path: Path, variant_index: int) -> Path:
    return output_path.with_name(f"{output_path.stem}_v{variant_index}{output_path.suffix}")


def deterministic_variant_seed(clip_id: str, variant_index: int) -> int:
    seed_source = f"{clip_id}:v{variant_index}".encode("utf-8")
    digest = hashlib.sha256(seed_source).digest()
    return int.from_bytes(digest[:4], "big")


def render_ltx_item(
    item: dict[str, Any],
    project_root: Path,
    node_bin: str,
    ltx_node_path: Path,
    log_path: Path,
    variant_index: int = 1,
) -> Path:
    ltx_request = item["ltx_request"]
    audio_values = [str(path) for path in ltx_request.get("audio_paths", [])]
    if not audio_values:
        audio_values = [str(ltx_request["audio"])]
    resolved_audio_paths = [resolve_project_path(project_root, audio_value) for audio_value in audio_values]
    if len(resolved_audio_paths) == 1:
        audio_path = resolved_audio_paths[0]
    else:
        if any(audio_path.suffix.lower() != ".wav" for audio_path in resolved_audio_paths):
            raise ValueError(f"LTX multi-audio merge currently supports WAV only: {resolved_audio_paths}")
        merged_audio_path = log_path.parent / f"{item['clip_id']}.ltx-merged.wav"
        audio_path = merge_wav_audio_files(resolved_audio_paths, merged_audio_path)
    output_path = resolve_project_path(project_root, ltx_request["save_path"])
    image_paths = [resolve_project_path(project_root, image) for image in ltx_request.get("images", [])]
    optimized_prompt = item["optimized_prompt"]

    ensure_parent(output_path)
    temp_output = Path("C:/Users/15712/AppData/Local/Temp/jinyi_stage11") / f"{item['clip_id']}_v{variant_index}_out.mp4"
    cmd = [
        node_bin, str(ltx_node_path),
        "--audio", str(audio_path),
        "--prompt", optimized_prompt,
        "--output", str(temp_output),
        "--fps", str(DEFAULT_FRAME_RATE),
        "--duration", str(ltx_request["duration_seconds"]),
        "--audio-start", str(ltx_request.get("a2v_audio_start_time", 0.0)),
        "--insert-time", str(ltx_request.get("a2v_audio_insert_video_time", 0.0)),
    ]
    if ltx_request.get("negative_prompt"):
        cmd.extend(["--negative", str(ltx_request["negative_prompt"])])
    if ltx_request.get("seed") is not None:
        cmd.extend(["--seed", str(ltx_request["seed"])])
    if image_paths:
        cmd.extend(["--images", ",".join(str(p) for p in image_paths)])
    run_command(cmd, log_path)
    import shutil
    shutil.copy2(str(temp_output), str(output_path))
    temp_output.unlink(missing_ok=True)
    return output_path


def render_ltx_variant(
    item: dict[str, Any],
    project_root: Path,
    node_bin: str,
    ltx_node_path: Path,
    log_path: Path,
    variant_index: int,
) -> dict[str, Any]:
    variant_item = json.loads(json.dumps(item))
    base_output_path = resolve_project_path(project_root, variant_item["ltx_request"]["save_path"])
    output_path = variant_output_path(base_output_path, variant_index)
    variant_item["ltx_request"]["save_path"] = str(output_path)
    variant_item["ltx_request"]["seed"] = deterministic_variant_seed(item["clip_id"], variant_index)
    variant_log_path = log_path.with_name(f"{log_path.stem}.v{variant_index}{log_path.suffix}")
    resolved_output = render_ltx_item(variant_item, project_root, node_bin, ltx_node_path, variant_log_path, variant_index)
    return {
        "variant": f"v{variant_index}",
        "status": "ok",
        "output_path": str(resolved_output),
        "log_path": str(variant_log_path),
        "seed": variant_item["ltx_request"]["seed"],
    }


def render_ltx_variants(
    item: dict[str, Any],
    project_root: Path,
    node_bin: str,
    ltx_node_path: Path,
    log_path: Path,
    variant_count: int = DEFAULT_LTX_VARIANT_COUNT,
) -> list[dict[str, Any]]:
    results_by_index: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=variant_count) as executor:
        futures = {
            executor.submit(render_ltx_variant, item, project_root, node_bin, ltx_node_path, log_path, variant_index): variant_index
            for variant_index in range(1, variant_count + 1)
        }
        for future in as_completed(futures):
            variant_index = futures[future]
            results_by_index[variant_index] = future.result()

    return [results_by_index[index] for index in sorted(results_by_index)]


def build_scale_pad_filter(target_width: int, target_height: int, pad_color: str) -> str:
    return (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color={pad_color},"
        "setsar=1"
    )


def render_ffmpeg_item(
    item: dict[str, Any],
    project_root: Path,
    ffmpeg_bin: str,
    log_path: Path,
) -> Path:
    ffmpeg_request = item["ffmpeg_request"]
    image_paths = [resolve_project_path(project_root, path) for path in ffmpeg_request.get("image_paths", [])]
    audio_paths = [resolve_project_path(project_root, path) for path in ffmpeg_request.get("audio_paths", [])]
    output_path = resolve_project_path(project_root, ffmpeg_request["save_path"])
    ensure_parent(output_path)

    if not image_paths:
        raise ValueError(f"Render item {item['clip_id']} has no image_paths for ffmpeg_request")
    if not audio_paths:
        raise ValueError(f"Render item {item['clip_id']} has no audio_paths for ffmpeg_request")

    if len(audio_paths) > 1:
        if any(audio_path.suffix.lower() != ".wav" for audio_path in audio_paths):
            raise ValueError(f"FFmpeg multi-audio merge currently supports WAV only: {audio_paths}")
        merged_audio_path = log_path.parent / f"{item['clip_id']}.ffmpeg-merged.wav"
        audio_paths = [merge_wav_audio_files(audio_paths, merged_audio_path)]

    target_width = int(ffmpeg_request["target_width"])
    target_height = int(ffmpeg_request["target_height"])
    pad_color = str(ffmpeg_request.get("pad_color") or item.get("pad_color") or "black")
    vf_filter = build_scale_pad_filter(target_width, target_height, pad_color)

    command = [ffmpeg_bin, "-y", "-loop", "1", "-i", str(image_paths[0])]
    for audio_path in audio_paths:
        command.extend(["-i", str(audio_path)])

    if len(audio_paths) == 1:
        command.extend(
            [
                "-vf",
                vf_filter,
                "-r",
                str(DEFAULT_FRAME_RATE),
                "-c:v",
                DEFAULT_VIDEO_CODEC,
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-tune",
                "stillimage",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                DEFAULT_AUDIO_CODEC,
                "-b:a",
                DEFAULT_AUDIO_BITRATE,
                "-movflags",
                "+faststart",
                "-shortest",
                str(output_path),
            ]
        )
    run_command(command, log_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Stage 11 segment videos from render-plan.json")
    parser.add_argument("--render-plan", required=True, help="Path to video/render-plan.json")
    parser.add_argument("--project-root", help="Optional project root override")
    parser.add_argument("--log-dir", help="Optional log directory; defaults to <project>/logs")
    parser.add_argument("--ffmpeg-bin", default=DEFAULT_FFMPEG_BIN, help="ffmpeg executable name or path")
    parser.add_argument("--bash-bin", default="bash", help="bash executable name or path")
    parser.add_argument("--ltx-script", help="Optional override for stage11_render_ltx_node.mjs")
    parser.add_argument("--node-bin", default="node", help="Node.js executable")
    parser.add_argument("--ltx-variants", type=int, default=DEFAULT_LTX_VARIANT_COUNT, help="How many parallel LTX variants to render per LTX clip")
    parser.add_argument("--fail-fast", action="store_true", help="Stop at first failed segment")
    args = parser.parse_args()

    render_plan_path = Path(args.render_plan).resolve()
    render_plan = load_json(render_plan_path)
    project_root = Path(args.project_root).resolve() if args.project_root else project_root_from_render_plan(render_plan_path)
    log_dir = Path(args.log_dir).resolve() if args.log_dir else (project_root / "logs").resolve()
    ltx_node_path = Path(args.ltx_script).resolve() if args.ltx_script else default_ltx_node_script_path()
    node_bin = args.node_bin

    ensure_parent(log_dir / "placeholder.log")
    results: list[dict[str, Any]] = []
    failures = 0

    for item in render_plan.get("render_items", []):
        clip_id = item["clip_id"]
        log_path = log_dir / f"stage11_render.{clip_id}.log"
        try:
            if item["render_mode"] == "ltx":
                variant_results = render_ltx_variants(item, project_root, node_bin, ltx_node_path, log_path, args.ltx_variants)
                results.append(
                    {
                        "clip_id": clip_id,
                        "status": "ok",
                        "render_mode": "ltx",
                        "variant_outputs": variant_results,
                    }
                )
            elif item["render_mode"] == "image_audio_ffmpeg":
                output_path = render_ffmpeg_item(item, project_root, args.ffmpeg_bin, log_path)
                results.append({"clip_id": clip_id, "status": "ok", "render_mode": "image_audio_ffmpeg", "output_path": str(output_path)})
            else:
                raise ValueError(f"Unsupported render_mode for {clip_id}: {item['render_mode']}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            results.append({"clip_id": clip_id, "status": "failed", "error": str(exc)})
            if args.fail_fast:
                break

    summary_path = log_dir / "stage11_render.summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "render_plan": str(render_plan_path),
                "project_root": str(project_root),
                "total_items": len(render_plan.get("render_items", [])),
                "failures": failures,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
