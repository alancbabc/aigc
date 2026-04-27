---
name: FamousDirectors
description: Director style control knowledge base. It provides cross-skill style mappings that can influence writing, directing, art, and generation without copying specific films.
trigger: Call when the user specifies a director style reference, or when the project needs a unified director-style influence across multiple skills.
---

# FamousDirectors

## Use This Knowledge For

This knowledge base is not just a list of directors.

It answers:
- if the user asks for a director-inspired style, how should that influence writing, directing, art, and prompts
- which traits should affect the whole project
- how strong the style influence should be

## Applies To

- `writer/story-outline`
- `writer/script-writing`
- `director/storyboard`
- `director/test-shoots`
- `director/transition`
- `art/character-three-view`
- `art/scene-design`
- `art/keyframe-generation`
- `generation/*`

## Affected Fields

- `project_meta.json -> director_style_reference`
- `project_meta.json -> style_intensity`
- `outline.json -> visual_style.references`
- `outline.json -> tone`
- `script.json -> tone`
- `storyboard.json -> scenes[].summary`
- `storyboard.json -> scenes[].shots[].description`
- `scene_design.json -> style`
- `test-shoots.json -> shot_prompt`

## Core Rules

1. Director style acts as a control layer, not as a replacement for story logic.
2. It can influence writing, directing, art, and generation, but must not replace genre or narrative fundamentals.
3. Always separate “borrowing style traits” from “copying specific works”.
4. Pass style influence through structured fields, not just one line in a prompt.
5. If multiple directors are referenced, there must be a clear primary one.

## Style Intensity

- `low`
  - borrow only a partial visual or tonal influence
- `medium`
  - let visuals, art direction, camera tone, and dialogue rhythm be influenced together
- `high`
  - allow full-chain influence, while still avoiding direct imitation of specific scenes or characters

## Director Extraction Targets

Extract at least:
- `director_style_reference`
- `style_intensity`
- `narrative_traits`
- `visual_traits`
- `camera_traits`
- `dialogue_traits`
- `character_traits`
- `color_traits`
- `rhythm_traits`
- `prompt_keywords`
- `anti_patterns`

## Cross-Skill Mapping

### Writer

Key influence:
- emotional tone
- information reveal style
- dialogue rhythm
- relationship presentation

### Director

Key influence:
- camera tone
- scene staging
- transition tendency
- rhythm control

### Art

Key influence:
- color system
- environment texture
- character appearance direction
- style keywords

### Generation

Key influence:
- prompt keywords
- style reinforcement phrasing
- anti-pattern reminders

## Files To Read

Priority files:
- `director-style-map.json`
- `wong-kar-wai.md`
- `xu-ke.md`
- `stephen-chow.md`

Machine-friendly index:
- `director-style-map.json`

## Usage Rule

1. confirm whether the project truly needs director-style control
2. extract style fields first
3. then pass them into writer, director, art, and generation
4. do not copy a director's original work directly; translate the style into constraints for the current project
