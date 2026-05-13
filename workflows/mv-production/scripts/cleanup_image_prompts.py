#!/usr/bin/env python3
"""Cleanup pass for image-prompts.json — fixes must_include fragments, removes
abstract/interpretive phrases from image_prompt, and corrects env-only main_subject.

This is a programmatic post-processing stage. No Qwen3 calls.
Reads image-prompts.json, applies cleaning rules, writes cleaned version.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


# ── Cleaning rules ────────────────────────────────────────────────

# Phrases to rewrite from abstract/interpretive to concrete visual
ABSTRACT_TO_VISUAL: dict[str, str] = {
    "symbolizing": "as",
    "transforming sorrow into an eternal memorial": "faint silhouettes suspended inside streams of light",
    "opening imagery repeats": "",
    "representing the act of": "",
    "signifying": "",
    "embodying": "",
    "evoking memories of": "",
}

# Abstract phrases that should be deleted from the prompt
ABSTRACT_PATTERNS: list[str] = [
    r",?\s*symbolizing [^,]+",
    r",?\s*transforming [^,]+ into [^,]+",
    r",?\s*representing [^,]+",
    r",?\s*signifying [^,]+",
    r",?\s*meaning [^,]+",
    r",?\s*as if remembering [^,]+",
    r",?\s*evoking [^,]+ of [^,]+",
    r",?\s*opening imagery repeats[^,]*",
]

ENV_PREFIX = {
    "amidst", "within", "in the", "between the", "above the", "below the",
    "across the", "through the", "into the", "around the", "beneath the",
    "against the", "from the", "at the", "on the", "under the",
    "inside the", "beyond the", "over the", "along the",
}

PREPOSITION_TAIL = {"a", "an", "the", "against", "with", "from", "and", "or",
                    "their", "its", "of", "to", "in", "on", "at", "by",
                    "are", "is", "was", "as"}

PREPOSITION_HEAD = {"Against", "With", "From", "And", "Or", "Their", "Its",
                    "Of", "To", "In", "On", "At", "By",
                    "Amidst", "Within", "Between", "Above", "Below",
                    "Through", "Into", "Across", "Around", "Beneath",
                    "Inside", "Beyond", "Over", "Along"}

TRAILING_JUNK = PREPOSITION_TAIL | {",", ".", ";", ":", "!", "?"}

ABSTRACT_WORDS = {
    "symbolizing", "representing", "meaning", "signifying", "expressing",
    "conveying", "reflecting", "embodying", "evoking", "suggesting",
    "sadness", "loneliness", "hope", "fear", "love", "hatred", "anger",
    "forgiveness", "acceptance", "letting go", "release",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_prompt_text(image_prompt: str) -> str:
    """Remove abstract/interpretive phrases from the prompt."""
    text = image_prompt
    for pattern in ABSTRACT_PATTERNS:
        text = re.sub(pattern, "", text)
    # Clean up double spaces, double commas
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r", ,", ",", text)
    text = re.sub(r",\s*,", ",", text)
    text = text.strip().rstrip(",").strip()
    return text


def extract_main_subject(concept_en: str) -> str:
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


def extract_environment(concept_en: str) -> str:
    """Extract first full sentence as environment description."""
    for delim in (". ", "; "):
        if delim in concept_en:
            return concept_en.split(delim)[0].strip()
    return concept_en.strip()


def clean_phrase(p: str) -> str | None:
    """Return a clean visual-element phrase, or None if invalid."""
    p = p.strip().strip('"').strip("'").strip(".").strip(",").strip(";").strip()
    p = p.replace(",", " ").replace("  ", " ")
    if len(p) < 5 or len(p) > 50:
        return None

    p_lower = p.lower()
    for aw in ABSTRACT_WORDS:
        if aw in p_lower:
            return None

    words = p.split()
    if len(words) < 2:
        return None
    if words[-1].lower() in TRAILING_JUNK:
        return None
    if words[0].lower() in {ph.lower() for ph in PREPOSITION_HEAD}:
        return None

    content_count = sum(
        1 for w in words
        if len(w) > 2 and w.lower() not in PREPOSITION_TAIL
        and w not in PREPOSITION_HEAD
    )
    if content_count < 2:
        return None

    while words and words[-1].lower() in TRAILING_JUNK:
        words.pop()
    if len(words) < 2:
        return None

    result = " ".join(words).lower().rstrip(".").rstrip(",").rstrip(";").strip()
    return result if len(result) >= 5 else None


def extract_must_include(concept_en: str) -> list[str]:
    """Extract 3-4 valid, checkable visual objects from the concept."""
    raw_parts = [p.strip() for p in concept_en.replace(", ", "|").replace("; ", "|").split("|")]
    result = []
    for p in raw_parts:
        cleaned = clean_phrase(p)
        if cleaned and cleaned not in result:
            result.append(cleaned)
        if len(result) >= 4:
            break
    if not result:
        words = concept_en.split()
        i = 0
        while i < len(words) and len(result) < 4:
            g = " ".join(words[i:i+3])
            c = clean_phrase(g)
            if c:
                result.append(c)
            i += 2
    return result[:4]


def main() -> None:
    ap = argparse.ArgumentParser(description="Cleanup image-prompts.json")
    ap.add_argument("--input", required=True, type=Path, help="image-prompts.json to clean")
    ap.add_argument("--output", type=Path, default=None, help="Output path (default: overwrite input)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    in_path = args.input.resolve()
    out_path = args.output.resolve() if args.output else in_path
    data = load_json(in_path)

    fixed_count = 0
    for p in data["image_prompts"]:
        if not p["render_strategy"]["generate_new_image"]:
            continue

        sid = p["shot_id"]
        old_prompt = p["image_prompt"] or ""

        # Step 1: Clean abstract phrases from image_prompt
        cleaned = clean_prompt_text(old_prompt)

        # Step 2: Use the environment field (which is the visual concept) as body for extraction
        # Don't extract from full prompt which includes composition/lighting/emotion
        env = p["prompt_components"].get("environment", "") or ""
        if not env:
            # Fallback: strip prefix + known technical terms from the full prompt
            body = cleaned
            prefix_marker = "elegant composition, "
            if prefix_marker in body:
                body = body.split(prefix_marker, 1)[1].strip()
            body = re.split(r", (?:extreme wide|wide cinematic|medium|close-up|soft moonlight|gentle cinematic|low contrast|quiet and|mysterious and|vast and|deep blue)", body)[0].strip()
            body = body.rstrip(", ").strip()
        else:
            body = env

        # Step 3: Re-derive main_subject, environment, must_include from cleaned body
        main_subject = extract_main_subject(body)
        environment = extract_environment(body)
        must_include = extract_must_include(body)

        # Step 4: Apply changes
        changed = False
        if cleaned != old_prompt:
            p["image_prompt"] = cleaned
            changed = True

        old_main = p["prompt_components"]["main_subject"] or ""
        if main_subject != old_main and main_subject:
            p["prompt_components"]["main_subject"] = main_subject
            changed = True

        old_env = p["prompt_components"]["environment"] or ""
        if environment != old_env and environment:
            p["prompt_components"]["environment"] = environment
            changed = True

        old_mi = p["quality_check"]["must_include"]
        if must_include != old_mi and must_include:
            p["quality_check"]["must_include"] = must_include
            changed = True

        if changed:
            fixed_count += 1
            print(f"  [fixed] {sid}: prompt_cleaned={cleaned != old_prompt}, "
                  f"main={'*' if main_subject != old_main else '-'}, "
                  f"mi={'*' if must_include != old_mi else '-'}")

    if args.dry_run:
        print(f"[dry-run] Would fix {fixed_count} prompts")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({fixed_count} prompts fixed)")


if __name__ == "__main__":
    main()
