#!/usr/bin/env python3
"""Build image-prompts.json from shot-plan.json.

Programmatic assembly + Qwen3.5 batch translation of visual_concept_zh.
Reads shot-plan.json and segment-interpretation.json, builds a global
visual style by aggregating segment data, translates visual concepts
to English, then assembles full image prompts with composition/emotion
mappings.

Output matches contracts/image-prompts/image-prompts.schema.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_MV_SCRIPTS = Path(__file__).resolve().parent
_AIGC_ROOT = _MV_SCRIPTS.parents[2]
_QWEN_DIR = _AIGC_ROOT / "generation" / "qwen3-chat-gitee"
if str(_QWEN_DIR) not in sys.path:
    sys.path.insert(0, str(_QWEN_DIR))

from client import (  # noqa: E402
    extract_assistant_text,
    load_aigc_dotenv,
    post_messages,
)

# ── Translation maps ──────────────────────────────────────────────

COLOR_MAP: dict[str, str] = {
    "深蓝": "deep blue", "银白": "silver white", "青色微光": "cyan glow",
    "雾黑": "mist black", "灰蓝": "slate blue", "暗紫": "dark violet",
    "冷白": "cool white", "暖金": "warm gold", "淡金": "pale gold",
    "亮金": "bright gold", "天蓝": "sky blue", "纯白": "pure white",
    "暗银": "dark silver", "墨绿": "dark teal", "冷蓝": "cool blue",
    "灰黑": "grey black", "灰白": "grey white", "透明蓝": "transparent blue",
    "珍珠白": "pearl white", "暗金": "dark gold", "紫罗兰": "violet",
    "暖橙": "warm orange", "淡粉": "pale pink", "柔白": "soft white",
    "墨黑": "ink black", "透明": "transparent", "深红": "deep red",
    "焦黑": "burnt black", "橙黄": "orange-yellow", "暗红": "dark red",
    "琥珀": "amber", "翡翠绿": "jade green", "雪白": "snow white",
}

MOOD_MAP: dict[str, str] = {
    "缓慢": "slow and deliberate", "漂浮": "floating and weightless",
    "梦境感": "dreamlike and surreal", "静止": "still and contemplative",
    "流动": "flowing and fluid", "上升": "ascending and liberating",
    "沉重": "heavy and profound", "宏大": "grand and epic",
    "温暖": "warm and tender", "永恒": "eternal and timeless",
    "梦幻": "dreamlike and fantastical", "超现实": "surreal and otherworldly",
    "紧张": "tense and anxious", "不安": "uneasy and restless",
    "安静": "quiet and peaceful", "回望": "retrospective and distant",
    "自由": "free and boundless", "释放": "releasing and cathartic",
    "神圣": "sacred and luminous", "决绝": "resolute and decisive",
    "深情": "affectionate and tender", "坚定": "steadfast and resolute",
    "凝视": "gazing and intent", "激烈": "intense and turbulent",
    "爆发": "explosive and cathartic", "动荡": "turbulent and dynamic",
    "延续": "continuing and sustained", "循环": "cyclical and recurring",
    "告别": "farewell and departing", "释然": "releasing and bittersweet",
    "逐渐稀薄": "gradually fading and dissolving",
}

EMOTION_MAP: dict[str, str] = {
    "静谧": "quiet and serene", "神秘": "mysterious and ethereal",
    "温柔": "tender and gentle", "朦胧": "dreamlike and hazy",
    "流动": "fluid and flowing", "释然": "releasing and bittersweet",
    "不舍": "reluctant and lingering", "决绝": "resolute and decisive",
    "矛盾": "conflicted and torn", "悲伤": "melancholic and haunting",
    "深情": "deeply affectionate", "恐惧": "fearful and anxious",
    "挣扎": "struggling and restless", "奇幻": "fantastical and surreal",
    "逆流": "reversing and flowing upward", "回望": "retrospective and distant",
    "宿命": "fated and resigned", "深沉": "profound and heavy",
    "宁静": "calm and peaceful", "坚定": "steadfast and determined",
    "辽阔": "vast and boundless", "释怀": "released and accepting",
    "成全": "selfless and fulfilling", "升华": "transcendent and sublime",
    "圆满": "complete and fulfilled", "永恒": "eternal and timeless",
    "轮回": "cyclical and recurring", "纪念": "commemorative and reflective",
    "自由": "free and liberated", "告别": "farewell and parting",
    "延续": "continuing and sustained", "初遇": "first encounter and wonder",
    "治愈": "soothing and healing", "孤寂": "lonely and desolate",
    "压抑": "oppressive and suffocating", "狂欢": "ecstatic and liberating",
}

# Static emotion descriptors — suitable for image prompts (no motion)
STATIC_EMOTION: set[str] = {
    "quiet and serene", "mysterious and ethereal", "tender and gentle",
    "dreamlike and hazy", "conflicted and torn", "melancholic and haunting",
    "deeply affectionate", "fearful and anxious", "struggling and restless",
    "fantastical and surreal", "retrospective and distant", "fated and resigned",
    "profound and heavy", "calm and peaceful", "steadfast and determined",
    "vast and boundless", "released and accepting", "selfless and fulfilling",
    "transcendent and sublime", "complete and fulfilled", "eternal and timeless",
    "cyclical and recurring", "commemorative and reflective", "free and liberated",
    "farewell and parting", "first encounter and wonder", "soothing and healing",
    "lonely and desolate", "oppressive and suffocating", "ecstatic and liberating",
}

# Video motion descriptors — NOT for static image prompts
VIDEO_MOTION: set[str] = {
    "fluid and flowing", "releasing and bittersweet",
    "resolute and decisive", "reluctant and lingering",
    "reversing and flowing upward", "continuing and sustained",
}

COMPOSITION_MAP: dict[str, str] = {
    "extreme_wide_shot": "extreme wide shot, deep cinematic space, vast perspective",
    "wide_shot": "wide cinematic composition, atmospheric distance",
    "medium_wide_shot": "medium-wide shot, balanced framing with environment",
    "medium_shot": "medium shot, intimate framing with context",
    "medium_close_up": "medium close-up, focused and personal",
    "close_up": "close-up, detailed and emotional, shallow depth",
    "extreme_close_up": "extreme close-up, abstract and symbolic, textured detail",
}

# Static replacement for motion verbs in image descriptions
MOTION_TO_STATIC: dict[str, str] = {
    "glides through": "suspended within",
    "glides": "rests suspended",
    "flowing slowly": "resting in stillness",
    "flows upward": "hangs suspended",
    "connect and separate": "caught between connection and separation",
    "snaps": "caught at the moment of breaking",
    "unfurl": "spread in frozen stillness",
    "swallows the": "looms over the",
    "dissolving": "frozen mid-dissolve",
    "drifting": "resting",
    "rises into": "stands against",
    "surges": "holds in place",
}

# Environment prefixes that should be stripped from main_subject
ENV_PREFIX = {
    "amidst", "within", "in the", "between the", "above the", "below the",
    "across the", "through the", "into the", "around the", "beneath the",
    "against the", "from the", "at the", "on the", "under the",
    "inside the", "beyond the", "over the", "along the",
}

# Function words that mark incomplete phrases
PREPOSITION_TAIL = {"a", "an", "the", "against", "with", "from", "and", "or", "their", "its", "of", "to", "in", "on", "at", "by", "are", "is", "was", "as"}
PREPOSITION_HEAD = {"Against", "With", "From", "And", "Or", "Their", "Its", "Of", "To", "In", "On", "At", "By",
                    "Amidst", "Within", "Between", "Above", "Below", "Through", "Into", "Across", "Around", "Beneath", "Inside", "Beyond", "Over", "Along"}

FIXED_NEGATIVE = (
    "text, subtitles, watermark, logo, low quality, blurry, "
    "distorted anatomy, extra limbs, ugly face, bad hands, "
    "plain documentary photography, tourist photo, casual snapshot, "
    "cartoon, anime, plastic texture, oversaturated colors, "
    "cluttered composition, harsh daylight"
)


# ── Core logic ────────────────────────────────────────────────────

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_global_style(segments: list[dict[str, Any]], style_prefix: str = "") -> dict[str, Any]:
    """Aggregate segment data into a global visual style."""
    if not segments:
        raise SystemExit("No segments found for global style induction.")

    all_colors: list[str] = []
    all_scenes: list[str] = []
    all_lightings: list[str] = []
    all_moods: list[str] = []

    for s in segments:
        vd = s.get("visual_direction", {})
        all_colors.extend(vd.get("color_palette", []))
        if vd.get("scene_type"):
            all_scenes.append(vd["scene_type"])
        if vd.get("lighting"):
            all_lightings.append(vd["lighting"])
        if vd.get("camera_mood"):
            import re as _re
            words = _re.split(r"[、，, ；\s]+", vd["camera_mood"])
            all_moods.extend(w.strip() for w in words if w.strip())

    color_freq = Counter(all_colors)
    top_colors_cn = [c for c, _ in color_freq.most_common(5)]
    top_colors_en = [COLOR_MAP.get(c, c.lower()) for c in top_colors_cn[:3]]
    color_phrase = ", ".join(top_colors_en)

    mood_freq = Counter(all_moods)
    top_moods_cn = [m for m, _ in mood_freq.most_common(5)]
    top_moods_en = [MOOD_MAP[m] for m in top_moods_cn[:3] if m in MOOD_MAP]
    if not top_moods_en:
        top_moods_en = ["dreamlike and surreal", "quiet and serene"]  # universal fallback
    mood_phrase = ", ".join(top_moods_en)

    scene_freq = Counter(all_scenes)
    dominant_scene = scene_freq.most_common(1)[0][0] if scene_freq else "dreamlike"
    style_name = dominant_scene.replace("_", " ") + " fantasy realism"

    # Lighting — derive English from dominant scene type keywords
    if any(kw in dominant_scene for kw in ("dream", "night", "ocean", "water")):
        dominant_lighting = "soft moonlight, low contrast, gentle cinematic glow"
    elif any(kw in dominant_scene for kw in ("dawn", "sunrise", "morning", "light")):
        dominant_lighting = "warm dawn light, soft atmospheric haze, golden hour glow"
    elif any(kw in dominant_scene for kw in ("storm", "turmoil", "dark", "shadow")):
        dominant_lighting = "dramatic backlight, high contrast, moody atmosphere"
    elif any(kw in dominant_scene for kw in ("freedom", "sky", "release", "climax")):
        dominant_lighting = "sacred backlight, luminous atmosphere, heavenly rays"
    elif any(kw in dominant_scene for kw in ("memory", "echo", "time", "loop")):
        dominant_lighting = "soft nostalgic glow, dreamy haze, gentle light beams"
    elif any(kw in dominant_scene for kw in ("instrumental", "hold")):
        dominant_lighting = "ambient soft light, minimal contrast"
    else:
        dominant_lighting = "soft ambient light with subtle glow, cinematic lighting"

    global_prompt_prefix = (
        f"{style_prefix}, " if style_prefix else ""
    ) + (
        f"A poetic symbolic music video keyframe, "
        f"{color_phrase} atmosphere, "
        f"ethereal cinematic realism, "
        f"elegant composition"
    )

    return {
        "style_name": style_name,
        "global_prompt_prefix": global_prompt_prefix,
        "global_negative_prompt": FIXED_NEGATIVE,
        "color_system": top_colors_en[:5],
        "lighting_system": dominant_lighting,
        "texture_system": "misty, fluid, luminous, dreamlike, painterly cinematic texture",
    }


def _has_chinese(text: str) -> bool:
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff' or '\u3400' <= ch <= '\u4dbf':
            return True
    return False


def translate_batch(
    concepts: list[tuple[str, str]],
    api_key: str,
    api_url: str,
    model: str,
    timeout: int = 120,
) -> dict[str, str]:
    """Translate a batch of Chinese visual concepts to English."""
    if not concepts:
        return {}

    text_to_translate = "\n".join(
        f"{idx}: {text}" for idx, (_, text) in enumerate(concepts)
    )
    system = (
        "You are a translator for AI image generation prompts. "
        "Translate each Chinese visual concept into natural English suitable for an AI image model prompt. "
        "Output ONLY a JSON object with keys as the input indices and values as the English translations. "
        "Do not include markdown, do not add explanations."
        "\n\nRules:"
        "\n- Keep visual details, remove abstract commentary"
        "\n- Use poetic but specific English"
        "\n- Preserve symbolic elements (silhouettes, light threads, reflections)"
        "\n- Describe each scene as a FROZEN STILL MOMENT. Use static language: suspended, resting, frozen, caught at the moment of, floating still, hanging in place. Avoid active motion: gliding, flowing, rising, falling, unfurling, moving, drifting, spinning, connecting and separating."
    )
    user = f"Translate these visual concepts to English image-prompt style:\n{text_to_translate}"

    payload = {
        "model": model,
        "stream": False,
        "enable_thinking": False,
        "max_tokens": 4096,
        "temperature": 0.2,
        "top_p": 0.9,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    response = post_messages(api_url, api_key, payload, timeout=timeout)
    text = extract_assistant_text(response)
    # Clean markdown fences
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:]) if lines[0].strip() in ("```", "```json") else text
        if text.endswith("```"):
            text = text[: text.rindex("```")].strip()

    try:
        translations = json.loads(text)
    except json.JSONDecodeError:
        print("[warn] Translation JSON parse failed, using raw text as fallback")
        # Fallback: treat each concept as untranslated
        return {idx: cn for idx, cn in concepts}

    result: dict[str, str] = {}
    contaminated: list[tuple[str, str]] = []
    for idx, cn in concepts:
        key = str(idx)
        val = translations.get(key, translations.get(str(idx), cn))
        result[idx] = val
        if _has_chinese(val):
            contaminated.append((idx, cn))
            print(f"  [warn] Chinese detected in translation {key}")
    if contaminated:
        print(f"  Retrying {len(contaminated)} contaminated translations...")
        retry_text = "\n".join(f"{idx}: {cn}" for idx, cn in contaminated)
        retry_user = (
            f"These translations still contain Chinese. Please re-translate them to English:\n"
            f"{retry_text}"
        )
        payload["messages"][1]["content"] = retry_user
        try:
            r2 = post_messages(api_url, api_key, payload, timeout=timeout)
            t2 = extract_assistant_text(r2)
            t2 = t2.strip()
            if t2.startswith("```"):
                lines = t2.splitlines()
                t2 = "\n".join(lines[1:]) if lines[0].strip() in ("```", "```json") else t2
                if t2.endswith("```"):
                    t2 = t2[: t2.rindex("```")].strip()
            fixes = json.loads(t2)
            for idx, _ in contaminated:
                fv = fixes.get(str(idx), fixes.get(idx, result.get(idx, "")))
                if not _has_chinese(fv):
                    result[idx] = fv
            still_bad = sum(1 for v in result.values() if _has_chinese(v))
            if still_bad > 0:
                print(f"  [warn] {still_bad} translations still contain Chinese after retry")
        except (json.JSONDecodeError, Exception) as e:
            print(f"  [warn] Retry failed: {e}")
    return result


# Words that indicate abstract/non-visual content — should NOT appear in must_include
ABSTRACT_WORDS = {
    "symbolizing", "representing", "meaning", "signifying", "expressing",
    "conveying", "reflecting", "embodying", "evoking", "suggesting",
    "sadness", "loneliness", "hope", "fear", "love", "hatred", "anger",
    "forgiveness", "acceptance", "letting go", "release", "freedom",
}

# Trailing junk that should be stripped
TRAILING_JUNK = set(PREPOSITION_TAIL) | {",", ".", ";", ":", "!", "?"}


def _apply_static_fix(concept_en: str) -> str:
    """Replace motion verbs in the translated concept with static equivalents."""
    result = concept_en
    for motion, static in MOTION_TO_STATIC.items():
        result = result.replace(motion, static)
    return result


def _extract_main_subject(concept_en: str) -> str:
    """Extract the true subject, stripping leading environment preposition phrases."""
    text = concept_en.strip()
    lower = text.lower()
    for prefix in sorted(ENV_PREFIX, key=len, reverse=True):
        if lower.startswith(prefix) and len(text) > len(prefix) + 3:
            after_prefix = text[len(prefix):].lstrip()
            if ", " in after_prefix[:80]:
                after_comma = text.split(", ", 1)[1] if ", " in text else text
                for delim in (". ", "; "):
                    if delim in after_comma:
                        return after_comma.split(delim)[0].strip()
                return after_comma.split(", ")[0].strip()
    for delim in (", ", ". ", "; "):
        if delim in text:
            return text.split(delim)[0].strip()
    return text.strip()[:100]


def _clean_phrase(p: str) -> str | None:
    """Return a clean visual-element phrase, or None if invalid."""
    # Strip outer quotes and punctuation, normalize internal commas
    p = p.strip().strip('"').strip("'").strip(".").strip(",").strip(";").strip()
    p = p.replace(",", " ").replace("  ", " ")  # normalize misplaced commas
    if len(p) < 5 or len(p) > 50:
        return None

    # Reject if contains abstract/non-visual words
    p_lower = p.lower()
    for aw in ABSTRACT_WORDS:
        if aw in p_lower:
            return None

    words = p.split()
    if len(words) < 2:
        return None

    # Reject if ends in a junk word (article, preposition, etc.)
    if words[-1].lower() in TRAILING_JUNK:
        return None

    # Reject if starts with a preposition (case-insensitive)
    if words[0].lower() in {ph.lower() for ph in PREPOSITION_HEAD}:
        return None

    # Count content words (longer than 2 chars, not prep/art/conj)
    content_count = sum(
        1 for w in words
        if len(w) > 2 and w.lower() not in PREPOSITION_TAIL
        and w not in PREPOSITION_HEAD
    )
    if content_count < 2:
        return None

    # Clean: strip trailing junk words one at a time
    while words and words[-1].lower() in TRAILING_JUNK:
        words.pop()
    if len(words) < 2:
        return None

    result = " ".join(words).lower().rstrip(".").rstrip(",").rstrip(";").strip()
    return result if len(result) >= 5 else None


def _extract_must_include(concept_en: str) -> list[str]:
    """Extract 3-4 valid, checkable visual objects from the concept."""
    # Split by commas and semicolons
    raw_parts = [p.strip() for p in concept_en.replace(", ", "|").replace("; ", "|").split("|")]
    result = []
    for p in raw_parts:
        clean = _clean_phrase(p)
        if clean and clean not in result:
            result.append(clean)
        if len(result) >= 4:
            break
    if not result:
        # Fallback: take short 2-3 word groups from the first sentence
        words = concept_en.split()
        groups = []
        i = 0
        while i < len(words) and len(groups) < 4:
            g = " ".join(words[i:i+3])
            c = _clean_phrase(g)
            if c:
                groups.append(c)
            i += 2
        result = groups
    return result[:4]


def assemble_prompts(
    shot_data: dict[str, Any],
    seg_data: dict[str, Any],
    translations: dict[str, str],
    global_style: dict[str, Any],
) -> list[dict[str, Any]]:
    """Assemble image prompt entries for each shot.
    
    visual_concept_zh → Qwen3.5 translation → visual_concept_en
    visual_concept_en is the single source of truth for:
      - main_subject  (first clause)
      - environment   (first full sentence)
      - must_include  (key phrases extracted)
      - image_prompt  (assembled from concept_en + composition + lighting + per-shot emotion + prefix)
    """
    result: list[dict[str, Any]] = []

    for i, shot in enumerate(shot_data["shots"]):
        sid = shot["shot_id"]
        psid = shot["parent_segment_id"]
        is_hold = (
            shot.get("shot_role") == "ambient_hold"
            or shot.get("generation_notes", {}).get("generate_new_image") is False
        )
        reuse_id = shot.get("generation_notes", {}).get("reuse_from_shot_id", "")

        tr = shot["time_range"]
        prompt_id = f"img_prompt_{sid}"

        if is_hold:
            result.append({
                "prompt_id": prompt_id,
                "shot_id": sid,
                "parent_segment_id": psid,
                "parent_section_id": shot.get("parent_section_id", ""),
                "time_range": {"start_time": tr["start_time"], "end_time": tr["end_time"], "duration_seconds": tr["duration_seconds"]},
                "render_strategy": {"generate_new_image": False, "reuse_from_shot_id": reuse_id or None},
                "prompt_language": "en",
                "image_prompt": None,
                "negative_prompt": None,
                "prompt_components": {"main_subject": None, "environment": None, "composition": None, "lighting": None, "emotion": None, "style_keywords": []},
                "generation_parameters": {"aspect_ratio": "16:9", "resolution": "1920x1080", "seed": None, "num_candidates": 0},
                "quality_check": {"must_include": [], "must_avoid": [], "continuity_tags": []},
                "generation_notes": "Ambient hold, reuses previous shot image.",
            })
            continue

        # ── Single source: visual_concept_en ──
        concept_en = translations.get(str(i), shot.get("visual_concept_zh", ""))
        concept_en = _apply_static_fix(concept_en)
        main_subject = _extract_main_subject(concept_en)
        environment = concept_en.split(". ")[0].strip() if ". " in concept_en else concept_en.strip()

        # Composition
        shot_size = shot.get("composition", {}).get("shot_size", "wide_shot")
        comp_hint = COMPOSITION_MAP.get(shot_size, "wide cinematic composition")

        # Lighting (global, English)
        lighting_hint = global_style["lighting_system"]

        # Per-shot emotion (filter out video-motion descriptors)
        emotion = shot.get("emotion", {})
        primary_cn = emotion.get("primary", "")
        raw_emotion = EMOTION_MAP.get(primary_cn, "")
        if raw_emotion in VIDEO_MOTION:
            # Fall back to secondary emotion, or first static emotion found
            secondaries = emotion.get("secondary", [])
            fallback = ""
            for s in secondaries:
                fb = EMOTION_MAP.get(s, "")
                if fb and fb not in VIDEO_MOTION:
                    fallback = fb
                    break
            emotion_hint = fallback or "mysterious and ethereal"
        elif raw_emotion:
            emotion_hint = raw_emotion
        else:
            emotion_hint = ""

        # ── Assemble image_prompt ──
        parts = [
            global_style["global_prompt_prefix"],
            concept_en,
            comp_hint,
            lighting_hint,
        ]
        if emotion_hint:
            parts.append(emotion_hint)
        parts.append("16:9")
        image_prompt = ", ".join(parts)

        # Negative prompt
        negative_prompt = FIXED_NEGATIVE

        # Style keywords
        top_colors = global_style.get("color_system", [])[:3]
        style_kw = ["poetic symbolic music video", "ethereal cinematic realism", "cinematic composition"] + top_colors

        # ── Quality check ──
        must_include = _extract_must_include(concept_en)
        vs = shot.get("visual_style", {})
        scene_type = vs.get("scene_type", "")
        cp = vs.get("color_palette", [])
        cp_en = [COLOR_MAP.get(c, c.lower()) for c in cp[:2]]
        continuity_tags = [scene_type] + cp_en
        continuity_tags = [t for t in continuity_tags if t]

        result.append({
            "prompt_id": prompt_id,
            "shot_id": sid,
            "parent_segment_id": psid,
            "parent_section_id": shot.get("parent_section_id", ""),
            "time_range": {"start_time": tr["start_time"], "end_time": tr["end_time"], "duration_seconds": tr["duration_seconds"]},
            "render_strategy": {"generate_new_image": True, "reuse_from_shot_id": None},
            "prompt_language": "en",
            "image_prompt": image_prompt,
            "negative_prompt": negative_prompt,
            "prompt_components": {
                "main_subject": main_subject,
                "environment": environment,
                "composition": comp_hint,
                "lighting": lighting_hint,
                "emotion": emotion_hint or primary_cn,
                "style_keywords": style_kw[:5],
            },
            "generation_parameters": {
                "aspect_ratio": "16:9", "resolution": "1920x1080", "seed": None, "num_candidates": 2,
            },
            "quality_check": {
                "must_include": must_include,
                "must_avoid": ["modern city", "tourist beach", "literal characters", "subtitles"],
                "continuity_tags": continuity_tags,
            },
        })

    return result


def main() -> None:
    load_aigc_dotenv()
    if not os.getenv("AIGC_GITEE_API_KEY") and os.getenv("GITEE_API_TOKEN"):
        os.environ["AIGC_GITEE_API_KEY"] = os.getenv("GITEE_API_TOKEN", "")

    import config as qwen_cfg  # noqa: E402

    ap = argparse.ArgumentParser(description="Build image-prompts.json from shot-plan.json")
    ap.add_argument("--shot-plan", required=True, type=Path, help="shot-plan.json")
    ap.add_argument("--segment-interpretation", required=True, type=Path, help="segment-interpretation.json")
    ap.add_argument("--out", required=True, type=Path, help="Output image-prompts.json")
    ap.add_argument("--no-translate", action="store_true", help="Skip Qwen3 translation, use visual_concept_zh as-is")
    ap.add_argument("--user-requirements", type=Path, default=None, help="Optional user_requirements.json for keyframe_style_prefix")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    shot_path = args.shot_plan.resolve()
    seg_path = args.segment_interpretation.resolve()

    shot_data = load_json(shot_path)
    seg_data = load_json(seg_path)
    segments = seg_data.get("segments", [])

    if not segments:
        raise SystemExit("No segments in segment-interpretation.json")

    # Read user visual style prefix if provided
    style_prefix = ""
    if args.user_requirements:
        req_data = load_json(args.user_requirements.resolve())
        style_prefix = str(req_data.get("keyframe_style_prefix") or "").strip()

    global_style = build_global_style(segments, style_prefix)
    song_title = seg_data.get("song_title") or shot_data.get("song_title") or shot_path.stem

    # Collect visual_concept_zh for translation
    translation_tasks: list[tuple[str, str]] = []
    for i, shot in enumerate(shot_data["shots"]):
        if shot.get("shot_role") == "ambient_hold":
            continue
        if shot.get("generation_notes", {}).get("generate_new_image") is False:
            continue
        vc = shot.get("visual_concept_zh", "")
        if vc:
            translation_tasks.append((str(i), vc))

    print(f"Shots: {len(shot_data['shots'])} total, {len(translation_tasks)} need translation")

    if args.no_translate or args.dry_run:
        translations = {idx: cn for idx, cn in translation_tasks}
        if args.no_translate:
            print("[no-translate] Using visual_concept_zh as-is")
        if args.dry_run:
            print(f"[dry-run] global_style: {json.dumps(global_style, ensure_ascii=False, indent=2)[:500]}")
            return
    else:
        if not qwen_cfg.API_KEY:
            raise SystemExit("Missing AIGC_GITEE_API_KEY for translation.")
        print(f"Translating {len(translation_tasks)} concepts via Qwen3.5...")
        translations = translate_batch(
            translation_tasks, qwen_cfg.API_KEY, qwen_cfg.API_URL, qwen_cfg.DEFAULT_MODEL
        )
        print(f"  Translated {len(translations)} concepts")

    image_prompts = assemble_prompts(shot_data, seg_data, translations, global_style)

    out_obj: dict[str, Any] = {
        "schema_version": "1.0",
        "song_title": song_title,
        "artist": seg_data.get("artist") or shot_data.get("artist"),
        "source_shot_plan_ref": shot_path.name,
        "project_info": {
            "mv_type": "imagery_based_music_video",
            "visual_mode": "poetic_symbolic",
            "aspect_ratio": "16:9",
        },
        "global_style": global_style,
        "image_prompts": image_prompts,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    new_count = sum(1 for p in image_prompts if p["render_strategy"]["generate_new_image"])
    hold_count = sum(1 for p in image_prompts if not p["render_strategy"]["generate_new_image"])
    print(f"Wrote {out_path} ({new_count} new images, {hold_count} ambient holds)")


if __name__ == "__main__":
    main()
