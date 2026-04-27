#!/usr/bin/env python3
"""Build mixed render-plan.json from audio timeline, clip plan, and source visual assets."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any


DEFAULT_ANCHOR_IMAGE_BY_MODE = {
    "female_solo": "builtin-anchor-templates/default-news-duo-v1/visuals/anchors/female_solo.png",
    "male_solo": "builtin-anchor-templates/default-news-duo-v1/visuals/anchors/male_solo.png",
}
DEFAULT_OPENING_LTX_IMAGES = [
    "builtin-anchor-templates/default-news-duo-v1/visuals/anchors/duo_close.png",
]
DEFAULT_MIDDLE_DUO_LTX_IMAGES = [
    "builtin-anchor-templates/default-news-duo-v1/visuals/anchors/duo_close.png",
]
DEFAULT_CLOSING_LTX_IMAGES = [
    "builtin-anchor-templates/default-news-duo-v1/visuals/anchors/duo_close.png",
]

DEFAULT_LTX_MAX_DURATION_SECONDS = 16.0
DEFAULT_LTX_AUDIO_START_TIME_SECONDS = 0.0
DEFAULT_LTX_AUDIO_INSERT_VIDEO_TIME_SECONDS = 0.5
DEFAULT_LTX_VIDEO_DURATION_PADDING_SECONDS = 1.0
DEFAULT_PAD_COLOR = "#000000"
DEFAULT_LTX_NEGATIVE_PROMPT = (
    "text, subtitles, watermarks, logos, readable signage, overlay, titles, has blurbox, has subtitles, "
    "artifacts around text, unreadable text, incorrect lettering, incorrect slogan, camera shake, frame jitter"
)

# LTX three-template visual prompt system
# Top-level, fixed templates that map a clip's position to a visual prompt style.
SPOKEN_DIALOGUE_PLACEHOLDER = "[[SPOKEN_DIALOGUE]]"
DUO_SPEAKER_LABEL_PLACEHOLDER = "[[DUO_SPEAKER_LABEL]]"
DUO_LISTENER_LABEL_PLACEHOLDER = "[[DUO_LISTENER_LABEL]]"

OPENING_TEMPLATE = (
    "Middle shot, tight two-anchor composition in a clean modern studio with balanced framing, neutral lighting, and clear face visibility. "
    f"Only the {DUO_SPEAKER_LABEL_PLACEHOLDER} speaks. {SPOKEN_DIALOGUE_PLACEHOLDER} The {DUO_SPEAKER_LABEL_PLACEHOLDER} shows clearly visible, active speech mouth movement synchronized to the spoken Chinese line, with distinct mouth opening and closing, readable articulation, visible lip shaping, active jaw movement on syllables, a steady eyeline, and subtle blinking with very small head motion. The {DUO_LISTENER_LABEL_PLACEHOLDER} listens attentively, remains silent and mostly still, with restrained micro-reactions and no visible speaking motion. Both anchors maintain formal professional posture. Both anchors remain visible in the same frame at all times. The shot stays a fixed two-anchor composition for the entire clip with no cut to a solo shot, no reframing, and no change in shot size. The camera remains fully locked and stable throughout. The overall feeling is calm, steady, and professional."
)
MIDDLE_TEMPLATE_SOLO = (
    "Middle shot, tight close-up on one anchor in a clean modern studio with neutral lighting, stable framing, and clear face visibility. "
    f"The anchor is speaking directly to the camera. {SPOKEN_DIALOGUE_PLACEHOLDER} The anchor keeps a steady eyeline and clearly visible, active speech mouth movement synchronized to the spoken Chinese line. Mouth motion stays natural but obvious, with distinct mouth opening and closing, clearly readable articulation, visible lip shaping, and active jaw movement on spoken syllables. Facial motion stays subtle and professional, with restrained blinking, minimal head movement, and calm posture so the speaking motion reads clearly. The camera remains fixed and stable throughout. The overall feeling is controlled, informative, formal, and professional."
)
MIDDLE_TEMPLATE_DUO = (
    "Middle shot, tight two-anchor composition in a clean modern studio with balanced framing, neutral lighting, and clear face visibility. "
    f"Only the {DUO_SPEAKER_LABEL_PLACEHOLDER} speaks. {SPOKEN_DIALOGUE_PLACEHOLDER} The {DUO_SPEAKER_LABEL_PLACEHOLDER} shows clearly visible, active speech mouth movement synchronized to the spoken Chinese line, with distinct mouth opening and closing, clearly readable articulation, visible lip shaping, active jaw movement on syllables, a steady eyeline, and natural delivery with subtle blinking and very small head motion. The {DUO_LISTENER_LABEL_PLACEHOLDER} remains mostly still and silent, with restrained micro-reactions, minimal gaze shifts, and no visible speaking motion. Both anchors maintain formal professional posture. The camera remains fixed and stable with no noticeable drift. The overall feeling is calm, steady, and professional."
)
OPENING_TEMPLATE_DUO_EXCHANGE = (
    "Middle shot, tight two-anchor composition in a clean modern studio with balanced framing, neutral lighting, and clear face visibility. "
    f"The two anchors speak in sequence during this clip. {SPOKEN_DIALOGUE_PLACEHOLDER} Only the anchor delivering the current line shows clearly visible, active speech mouth movement synchronized to the spoken Chinese line, with distinct mouth opening and closing, readable articulation, visible lip shaping, active jaw movement on syllables, a steady eyeline, and subtle blinking with very small head motion. The other anchor listens attentively, remains silent and mostly still, with restrained micro-reactions and no visible speaking motion. Both anchors maintain formal professional posture. Both anchors remain visible in the same frame at all times. The shot stays a fixed two-anchor composition for the entire clip with no cut to a solo shot, no reframing, and no change in shot size. The camera remains fully locked and stable throughout. The overall feeling is calm, steady, and professional."
)
MIDDLE_TEMPLATE_DUO_EXCHANGE = (
    "Middle shot, tight two-anchor composition in a clean modern studio with balanced framing, neutral lighting, and clear face visibility. "
    f"The two anchors speak in sequence during this clip. {SPOKEN_DIALOGUE_PLACEHOLDER} Only the anchor delivering the current line should show visible speaking motion, while the other remains attentive and mostly still. The camera remains fixed and stable with no noticeable drift. The overall feeling is calm, steady, and professional."
)
CLOSING_TEMPLATE_DUO_EXCHANGE = (
    "Closing shot in a tight duo frame. Both anchors remain at the desk in a clean, quiet studio with stable framing and neutral lighting. "
    f"The two anchors speak in turn during this closing clip. {SPOKEN_DIALOGUE_PLACEHOLDER} They alternate naturally with restrained movement and professional posture so the ending feels composed and complete."
)
CLOSING_TEMPLATE = (
    "Closing shot in a tight duo frame. Both anchors remain at the desk in a clean, quiet studio with stable framing and neutral lighting. "
    f"The {DUO_SPEAKER_LABEL_PLACEHOLDER} delivers the closing line. {SPOKEN_DIALOGUE_PLACEHOLDER} The {DUO_SPEAKER_LABEL_PLACEHOLDER} keeps clearly visible, active speech mouth movement with distinct mouth opening and closing, clearly readable articulation, visible lip shaping, active jaw movement on spoken syllables, steady gaze, subtle blinking, and calm professional posture. The {DUO_LISTENER_LABEL_PLACEHOLDER} remains silent, composed, and mostly still, with only slight natural listening reactions and no visible speaking motion. Both anchors may show very subtle sign-off behavior such as slight paper settling or small posture adjustment, but movement stays minimal and controlled. The camera remains stable and the ending feels composed, polished, and naturally complete."
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def determine_template_type(ltx_clip_index: int, total_ltx_clips: int) -> str:
    """Map LTX clip position to one of three top-level templates: opening, middle, closing."""
    if total_ltx_clips <= 0:
        return "opening"
    if ltx_clip_index == 0:
        return "opening"
    if ltx_clip_index == total_ltx_clips - 1:
        return "closing"
    return "middle"


def build_template_prompt(clip: dict[str, Any], template_type: str, image_mode: str, speaker_focus: str) -> str:
    """Return the appropriate opening/middle/closing prompt based on the template type."""
    if image_mode == "duo_frame" and speaker_focus == "duo":
        if template_type == "opening":
            return OPENING_TEMPLATE_DUO_EXCHANGE
        if template_type == "middle":
            return MIDDLE_TEMPLATE_DUO_EXCHANGE
        return CLOSING_TEMPLATE_DUO_EXCHANGE
    if template_type == "opening":
        return OPENING_TEMPLATE
    if template_type == "middle":
        # For middle, choose between solo or duo close-up based on clip context
        if image_mode == "duo_frame" or speaker_focus == "duo":
            return MIDDLE_TEMPLATE_DUO
        else:
            return MIDDLE_TEMPLATE_SOLO
    # closing template
    return CLOSING_TEMPLATE


def collect_clip_spoken_text(clip: dict[str, Any], audio_entry_map: dict[str, dict[str, Any]]) -> str:
    parts: list[str] = []
    for entry_id in clip.get("audio_entry_ids", []):
        entry = audio_entry_map.get(entry_id)
        if entry is None:
            raise ValueError(f"Clip {clip['clip_id']} references missing audio_entry_id for prompt text: {entry_id}")
        text = str(entry.get("text") or "").strip().replace("\n", " ")
        if text:
            parts.append(text)
    return " ".join(parts).strip()


def build_duo_sequence_dialogue(clip: dict[str, Any], audio_entry_map: dict[str, dict[str, Any]]) -> str:
    ordered_parts: list[str] = []
    for index, entry_id in enumerate(clip.get("audio_entry_ids", []), start=1):
        entry = audio_entry_map.get(entry_id)
        if entry is None:
            raise ValueError(f"Clip {clip['clip_id']} references missing audio_entry_id for ordered dialogue: {entry_id}")
        text = str(entry.get("text") or "").strip().replace("\n", " ")
        if not text:
            continue
        speaker = str(entry.get("speaker") or "").strip()
        speaker_label = "left female anchor" if speaker == "host" else "right male anchor"
        if index == 1:
            ordered_parts.append(f'The {speaker_label} says in Chinese: "{escape_dialogue_for_prompt(text)}".')
        else:
            ordered_parts.append(f'Then the {speaker_label} says in Chinese: "{escape_dialogue_for_prompt(text)}".')
    return " ".join(ordered_parts).strip()


def escape_dialogue_for_prompt(text: str) -> str:
    return text.replace('"', '\\"')


def speaker_label_from_focus(template_prompt: str, speaker_focus: str, image_mode: str) -> str:
    is_duo = image_mode == "duo_frame" or "two-anchor" in template_prompt.lower() or "duo frame" in template_prompt.lower()
    if speaker_focus == "host":
        return "left female speaker" if is_duo else "female anchor"
    if speaker_focus == "guest":
        return "right male speaker" if is_duo else "male anchor"
    return "left female speaker" if is_duo else "speaking anchor"


def listener_label_from_focus(template_prompt: str, speaker_focus: str, image_mode: str) -> str:
    is_duo = image_mode == "duo_frame" or "two-anchor" in template_prompt.lower() or "duo frame" in template_prompt.lower()
    if not is_duo:
        return "listener"
    if speaker_focus == "host":
        return "right male listener"
    if speaker_focus == "guest":
        return "left female listener"
    return "right male listener"


def resolve_prompt_speaker_focus(clip: dict[str, Any], audio_entry_map: dict[str, dict[str, Any]]) -> str:
    clip_speaker_focus = str(clip.get("speaker_focus") or "").strip()
    image_mode = str(clip.get("image_mode") or "")
    if image_mode != "duo_frame":
        return clip_speaker_focus or "host"

    audio_entry_ids = clip.get("audio_entry_ids", [])
    speakers = {
        str(audio_entry_map.get(entry_id, {}).get("speaker") or "").strip()
        for entry_id in audio_entry_ids
        if audio_entry_map.get(entry_id) is not None
    }
    if len([speaker for speaker in speakers if speaker]) > 1:
        return "duo"
    if len(audio_entry_ids) == 1:
        entry = audio_entry_map.get(audio_entry_ids[0])
        if entry is not None:
            speaker = str(entry.get("speaker") or "").strip()
            if speaker in {"host", "guest"}:
                return speaker

    if clip_speaker_focus in {"host", "guest"}:
        return clip_speaker_focus
    return "host"


def assemble_ltx_prompt(template_prompt: str, spoken_text: str, speaker_focus: str, image_mode: str, dialogue_override: str | None = None) -> str:
    if SPOKEN_DIALOGUE_PLACEHOLDER not in template_prompt:
        if not spoken_text:
            return template_prompt
        return f'{template_prompt} The anchor speaks in Chinese: "{escape_dialogue_for_prompt(spoken_text)}".'

    if image_mode == "duo_frame" and speaker_focus == "duo":
        dialogue_sentence = dialogue_override or ""
        return " ".join(template_prompt.replace(SPOKEN_DIALOGUE_PLACEHOLDER, dialogue_sentence).split())

    speaker_label = speaker_label_from_focus(template_prompt, speaker_focus, image_mode)
    listener_label = listener_label_from_focus(template_prompt, speaker_focus, image_mode)
    dialogue_sentence = (
        f'The {speaker_label} says in Chinese: "{escape_dialogue_for_prompt(spoken_text)}".' if spoken_text else ""
    )
    prompt = template_prompt.replace(SPOKEN_DIALOGUE_PLACEHOLDER, dialogue_sentence)
    prompt = prompt.replace(DUO_SPEAKER_LABEL_PLACEHOLDER, speaker_label)
    prompt = prompt.replace(DUO_LISTENER_LABEL_PLACEHOLDER, listener_label)
    return " ".join(prompt.split())


def index_audio_entries(audio_timeline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["entry_id"]: entry for entry in audio_timeline.get("entries", [])}


def index_source_images(source_visual_assets: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not source_visual_assets:
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for index, image in enumerate(source_visual_assets.get("images", []), start=1):
        if not isinstance(image, dict):
            continue
        image_id = str(image.get("image_id") or image.get("filename") or f"legacy_img_{index:02d}")
        path = str(image.get("path") or image.get("source_path") or image.get("filename") or "")
        indexed[image_id] = {
            **image,
            "image_id": image_id,
            "path": path.replace("\\", "/"),
        }
    return indexed


def read_image_size(path: Path) -> tuple[int | None, int | None]:
    suffix = path.suffix.lower()
    try:
        with open(path, "rb") as image_file:
            if suffix == ".png":
                header = image_file.read(24)
                if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
                    width, height = struct.unpack(">II", header[16:24])
                    return int(width), int(height)
            elif suffix in {".jpg", ".jpeg"}:
                image_file.read(2)
                while True:
                    marker_prefix = image_file.read(1)
                    if marker_prefix != b"\xff":
                        return None, None
                    marker = image_file.read(1)
                    while marker == b"\xff":
                        marker = image_file.read(1)
                    if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3", b"\xc5", b"\xc6", b"\xc7", b"\xc9", b"\xca", b"\xcb", b"\xcd", b"\xce", b"\xcf"}:
                        segment_length = struct.unpack(">H", image_file.read(2))[0]
                        if segment_length < 7:
                            return None, None
                        image_file.read(1)
                        height, width = struct.unpack(">HH", image_file.read(4))
                        return int(width), int(height)
                    if marker in {b"\xd8", b"\xd9"}:
                        continue
                    segment_length_data = image_file.read(2)
                    if len(segment_length_data) != 2:
                        return None, None
                    segment_length = struct.unpack(">H", segment_length_data)[0]
                    image_file.seek(max(segment_length - 2, 0), 1)
    except OSError:
        return None, None

    return None, None


def clip_duration_from_audio_entries(clip: dict[str, Any], audio_entry_map: dict[str, dict[str, Any]]) -> float:
    total = 0.0
    for entry_id in clip.get("audio_entry_ids", []):
        entry = audio_entry_map.get(entry_id)
        if entry is None:
            raise ValueError(f"Clip {clip['clip_id']} references missing audio_entry_id: {entry_id}")
        total += float(entry.get("duration_seconds", 0))
        total += float(entry.get("pause_before", 0))
        total += float(entry.get("pause_after", 0))
    return round(total, 3)


def resolve_target_dimensions_from_path(path: str) -> dict[str, int]:
    width, height = read_image_size(Path(path))
    if width is None or height is None:
        raise ValueError(f"Could not resolve image dimensions for {path}")
    return {"width": width, "height": height}


def resolve_target_dimensions_for_source_image(source_image_ids: list[str], source_image_paths: list[str], source_image_map: dict[str, dict[str, Any]]) -> dict[str, int]:
    if source_image_ids:
        first_image = source_image_map.get(source_image_ids[0])
        if first_image is not None:
            width = first_image.get("width")
            height = first_image.get("height")
            if isinstance(width, int) and isinstance(height, int):
                return {"width": width, "height": height}
    if source_image_paths:
        return resolve_target_dimensions_from_path(source_image_paths[0])
    raise ValueError("Source image dimensions unavailable")


def resolve_audio_paths(clip: dict[str, Any], audio_entry_map: dict[str, dict[str, Any]]) -> list[str]:
    resolved_audio_paths: list[str] = []
    for entry_id in clip.get("audio_entry_ids", []):
        entry = audio_entry_map.get(entry_id)
        if entry is None:
            raise ValueError(f"Clip {clip['clip_id']} references missing audio_entry_id: {entry_id}")
        resolved_audio_paths.append(entry["audio_path"])

    clip_audio_paths = clip.get("audio_paths", [])
    if clip_audio_paths and resolved_audio_paths and clip_audio_paths != resolved_audio_paths:
        raise ValueError(
            f"Clip {clip['clip_id']} has stale audio_paths that do not match audio timeline: {clip_audio_paths} != {resolved_audio_paths}"
        )

    return resolved_audio_paths or clip_audio_paths


def resolve_source_image_paths(
    clip: dict[str, Any],
    source_image_map: dict[str, dict[str, Any]],
    require_source_visuals: bool,
) -> tuple[list[str], list[str]]:
    source_image_ids = clip.get("source_image_ids", [])
    clip_source_paths = clip.get("source_image_paths", [])

    resolved_paths: list[str] = []
    if source_image_ids:
        if not source_image_map and require_source_visuals:
            raise ValueError(
                f"Clip {clip['clip_id']} needs source_visual_assets to resolve source_image_ids: {source_image_ids}"
            )
        for image_id in source_image_ids:
            image = source_image_map.get(image_id)
            if image is None:
                raise ValueError(f"Clip {clip['clip_id']} references missing source_image_id: {image_id}")
            resolved_paths.append(image["path"])

    if clip_source_paths and resolved_paths and clip_source_paths != resolved_paths:
        raise ValueError(
            f"Clip {clip['clip_id']} has source_image_paths that do not match source_visual_assets: {clip_source_paths} != {resolved_paths}"
        )

    return source_image_ids, resolved_paths or clip_source_paths


def build_ltx_request(
    clip: dict[str, Any],
    image_paths: list[str],
    audio_paths: list[str],
    duration_seconds: float,
) -> dict[str, Any]:
    video_duration_seconds = round(duration_seconds + DEFAULT_LTX_VIDEO_DURATION_PADDING_SECONDS, 3)
    payload = {
        "mode": "audio_to_video",
        "audio_paths": audio_paths,
        "images": image_paths,
        "save_path": f"video/segments/{clip['clip_id']}.mp4",
        "a2v_audio_start_time": DEFAULT_LTX_AUDIO_START_TIME_SECONDS,
        "a2v_audio_insert_video_time": DEFAULT_LTX_AUDIO_INSERT_VIDEO_TIME_SECONDS,
        "negative_prompt": DEFAULT_LTX_NEGATIVE_PROMPT,
        "duration_seconds": video_duration_seconds,
    }
    if len(audio_paths) == 1:
        payload["audio"] = audio_paths[0]
    return payload


def resolve_ltx_image_paths(clip: dict[str, Any], anchor_image_path: str, ltx_clip_index: int | None) -> list[str]:
    is_first_opening_duo_clip = (
        ltx_clip_index == 0 and clip.get("segment_type") == "opening" and clip.get("image_mode") == "duo_frame"
    )
    if is_first_opening_duo_clip:
        return DEFAULT_OPENING_LTX_IMAGES
    if clip.get("segment_type") == "closing" and clip.get("image_mode") == "duo_frame":
        return DEFAULT_CLOSING_LTX_IMAGES
    if clip.get("image_mode") == "duo_frame":
        return DEFAULT_MIDDLE_DUO_LTX_IMAGES
    return [anchor_image_path]


def build_ffmpeg_request(clip: dict[str, Any], image_paths: list[str], audio_paths: list[str], target_dimensions: dict[str, int]) -> dict[str, Any]:
    return {
        "mode": "image_audio_ffmpeg",
        "image_paths": image_paths,
        "audio_paths": audio_paths,
        "save_path": f"video/segments/{clip['clip_id']}.mp4",
        "target_width": target_dimensions["width"],
        "target_height": target_dimensions["height"],
        "image_fit_mode": "scale_pad",
        "pad_color": DEFAULT_PAD_COLOR,
        "motion_style": "ken_burns",
        "subtitle_mode": "none",
    }


def build_render_item(
    clip: dict[str, Any],
    audio_entry_map: dict[str, dict[str, Any]],
    source_image_map: dict[str, dict[str, Any]],
    require_source_visuals: bool,
    ltx_max_duration_seconds: float,
    ltx_clip_index: int | None,
    total_ltx_clips: int,
) -> dict[str, Any]:
    audio_paths = resolve_audio_paths(clip, audio_entry_map)
    output_path = f"video/segments/{clip['clip_id']}.mp4"
    computed_duration_seconds = clip_duration_from_audio_entries(clip, audio_entry_map)

    render_item: dict[str, Any] = {
        "clip_id": clip["clip_id"],
        "render_mode": clip["render_mode"],
        "audio_paths": audio_paths,
        "output_path": output_path,
        "computed_duration_seconds": computed_duration_seconds,
        "duration_source": "audio_timeline",
        "pad_color": DEFAULT_PAD_COLOR,
    }

    if clip["render_mode"] == "ltx":
        if computed_duration_seconds > ltx_max_duration_seconds:
            raise ValueError(
                f"Clip {clip['clip_id']} is {computed_duration_seconds:.2f}s, exceeding LTX limit of {ltx_max_duration_seconds:.2f}s; split the clip earlier"
            )
        image_mode = clip["image_mode"]
        anchor_image_path = DEFAULT_ANCHOR_IMAGE_BY_MODE.get(image_mode, "")
        if image_mode != "duo_frame" and not anchor_image_path:
            raise ValueError(f"Unsupported LTX image_mode: {image_mode}")
        ltx_image_paths = resolve_ltx_image_paths(clip, anchor_image_path, ltx_clip_index)
        if not ltx_image_paths:
            raise ValueError(f"Clip {clip['clip_id']} resolved no LTX image paths")
        anchor_image_path = ltx_image_paths[0]
        target_dimensions = resolve_target_dimensions_from_path(anchor_image_path)

        speaker_focus = resolve_prompt_speaker_focus(clip, audio_entry_map)

        render_item["anchor_image_path"] = anchor_image_path
        render_item["video_size_source"] = "anchor_image"
        render_item["target_dimensions"] = target_dimensions
        render_item["image_fit_mode"] = "match_image"
        template_type = determine_template_type(ltx_clip_index or 0, total_ltx_clips)
        template_prompt = build_template_prompt(clip, template_type, image_mode, speaker_focus)
        spoken_text = collect_clip_spoken_text(clip, audio_entry_map)
        ordered_dialogue = build_duo_sequence_dialogue(clip, audio_entry_map) if image_mode == "duo_frame" and speaker_focus == "duo" else None
        ltx_prompt = assemble_ltx_prompt(template_prompt, spoken_text, speaker_focus, image_mode)
        if ordered_dialogue is not None:
            ltx_prompt = assemble_ltx_prompt(template_prompt, spoken_text, speaker_focus, image_mode, ordered_dialogue)
        render_item["optimized_prompt"] = ltx_prompt
        render_item["ltx_request"] = build_ltx_request(
            clip,
            ltx_image_paths,
            audio_paths,
            computed_duration_seconds,
        )
        return render_item

    if clip["render_mode"] == "image_audio_ffmpeg":
        source_image_ids, source_image_paths = resolve_source_image_paths(clip, source_image_map, require_source_visuals)
        if not source_image_paths:
            raise ValueError(f"Clip {clip['clip_id']} requires source images for image_audio_ffmpeg")
        target_dimensions = resolve_target_dimensions_for_source_image(source_image_ids, source_image_paths, source_image_map)

        render_item["source_image_ids"] = source_image_ids
        render_item["source_image_paths"] = source_image_paths
        render_item["video_size_source"] = "source_image"
        render_item["target_dimensions"] = target_dimensions
        render_item["image_fit_mode"] = "scale_pad"
        render_item["ffmpeg_request"] = build_ffmpeg_request(clip, source_image_paths, audio_paths, target_dimensions)
        return render_item

    raise ValueError(f"Unsupported render_mode: {clip['render_mode']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build mixed render plan for news-commentary workflow")
    parser.add_argument("--audio-timeline", required=True, help="Path to audio/timeline.json")
    parser.add_argument("--clip-plan", required=True, help="Path to video/clip-plan.json")
    parser.add_argument("--source-visual-assets", help="Optional path to source-assets/source-visual-assets.json")
    parser.add_argument("--output", required=True, help="Output path for video/render-plan.json")
    args = parser.parse_args()

    audio_timeline_path = Path(args.audio_timeline).resolve()
    clip_plan_path = Path(args.clip_plan).resolve()
    output_path = Path(args.output).resolve()

    audio_timeline = load_json(audio_timeline_path)
    clip_plan = load_json(clip_plan_path)
    source_visual_assets = load_json(Path(args.source_visual_assets).resolve()) if args.source_visual_assets else None

    audio_entry_map = index_audio_entries(audio_timeline)
    source_image_map = index_source_images(source_visual_assets)
    ltx_max_duration_seconds = float(
        clip_plan.get("aggregation_rules", {}).get("ltx_max_duration_seconds", DEFAULT_LTX_MAX_DURATION_SECONDS)
    )

    clips = clip_plan.get("clips", [])
    ltx_clip_ids = [clip["clip_id"] for clip in clips if clip.get("render_mode") == "ltx"]
    ltx_clip_index_map = {clip_id: index for index, clip_id in enumerate(ltx_clip_ids)}
    total_ltx_clips = len(ltx_clip_ids)
    render_items = [
        build_render_item(
            clip,
            audio_entry_map,
            source_image_map,
            bool(args.source_visual_assets or clip_plan.get('source_visual_assets_ref')),
            ltx_max_duration_seconds,
            ltx_clip_index_map.get(clip["clip_id"]),
            total_ltx_clips,
        )
        for clip in clips
    ]

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "title": clip_plan.get("title", audio_timeline.get("title", "news-commentary-render-plan")),
        "clip_plan_ref": str(Path(args.clip_plan).as_posix()),
        "render_items": render_items,
    }
    source_visual_assets_ref = args.source_visual_assets or clip_plan.get("source_visual_assets_ref")
    if source_visual_assets_ref:
        payload["source_visual_assets_ref"] = str(Path(source_visual_assets_ref).as_posix())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
