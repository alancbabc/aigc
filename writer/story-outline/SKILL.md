---
name: story-outline
description: Create a structured story outline from a user idea, genre, duration target, and optional style references.
trigger: Use when the task is to expand an idea into an outline that downstream writing or production stages can consume.
---

# Story Outline

## Purpose

This skill turns a user idea into a structured `outline.json`.

It is responsible for:

- expanding a premise into a usable story structure
- choosing a narrative shape that matches duration and genre
- producing an outline that downstream writing skills can continue from

It is not responsible for:

- polishing isolated copy without story structure work
- skipping directly into full script drafting
- inventing downstream character-package or storyboard details that belong to other skills

## Inputs

- genre or project type
- target duration
- the user's core idea or premise
- optional director style reference
- optional visual style reference
- optional partial notes or existing outline fragments

## Outputs

- primary artifact: `outline.json`
- downstream consumers: `writer/character-profile`, `writer/script-writing`

The output must satisfy:

- `writer/story-outline/outline.schema.json`
- `writer/story-outline/outline.example.json`

## Decision Extraction

Before writing the outline, explicitly extract reusable decisions rather than only "referencing" the knowledge base.

### Narrative Extraction

Read `_knowledge/Narrative/` and extract:

- `structure_pattern`
- `reveal_strategy`
- `rhythm_goal`
- `payoff_pattern`

Use these decisions to shape progression, pacing, and ending logic.

### Genre Extraction

Read `_knowledge/Genre/` and extract:

- `genre_label`
- `subgenre`
- `tone`
- `world_rules`
- `conflict_defaults`
- `visual_keywords`

Use these decisions to constrain tone, conflict design, and visual identity.

### Director Style Extraction

If the user provides a director reference, read `_knowledge/FamousDirectors/` and extract:

- `director_style_reference`
- `style_intensity`
- `narrative_traits`
- `rhythm_traits`

Use these to influence presentation and emphasis, but do not let them replace genre and narrative logic.

## Dependencies

### Core Knowledge

- `_knowledge/Narrative/`
- `_knowledge/Genre/`
- `_knowledge/FamousDirectors/` when the user specifies a director reference

### Dependency Rules

1. Match genre before locking structure.
2. Extract patterns from knowledge sources; do not copy them literally.
3. Let extracted knowledge influence `genre`, `visual_style`, `structure`, and `core_theme`.

## Output Contract

```json
{
  "title": "Story Title",
  "genre": "Genre",
  "subgenre": "Subgenre",
  "duration": "XX minutes",
  "visual_style": {
    "keywords": ["keyword 1", "keyword 2"],
    "references": ["reference 1", "reference 2"]
  },
  "narrative_focus": "Whose journey the story follows",
  "core_theme": "Central theme",
  "characters": [
    {
      "name": "Character Name",
      "role": "lead/supporting/antagonist",
      "gender": "male/female/other"
    }
  ],
  "structure": {
    "act_1": {
      "duration": "XX minutes",
      "description": "Setup",
      "key_events": [
        {"order": 1, "event": "Event Name", "description": "What happens"}
      ]
    },
    "act_2": {
      "duration": "XX minutes",
      "description": "Confrontation",
      "key_events": [
        {"order": 2, "event": "Event Name", "description": "What happens"}
      ]
    },
    "act_3": {
      "duration": "XX minutes",
      "description": "Resolution",
      "key_events": [
        {"order": 3, "event": "Event Name", "description": "What happens"}
      ]
    }
  },
  "scenes": [
    {
      "scene_no": 1,
      "name": "Scene Name",
      "location": "Location",
      "function": "Narrative function"
    }
  ]
}
```

Contract files:

- example: `writer/story-outline/outline.example.json`
- schema: `writer/story-outline/outline.schema.json`

## Core Rules

1. Each act must contain enough events to support the intended duration; Act 2 is usually the richest section.
2. `narrative_focus` must center on a specific character or viewpoint, not a vague topic.
3. `core_theme` must be explicit and echoed by the ending.
4. Character placeholders such as "little girl" or "young man" are not acceptable final names; use genre-appropriate names.
5. Duration must be plausible for the amount of story material included.

## Workflow

1. Read the user premise, target duration, and style references.
2. Extract genre and narrative decisions from the knowledge layer.
3. Choose a structure that fits the duration.
4. Expand the idea into a structured outline.
5. Check whether the story scope is too small or too large for the requested duration.
6. Return `outline.json` for downstream use.

## Quality Review

Review the outline for:

- complete beginning / development / resolution flow
- named and usable characters
- genre and visual-style consistency
- duration realism
- clear downstream usability for character and script writing

## Storage Path

Recommended logical path:

`memory/[date]/[title]/v[version]/outline.json`

## Iteration

User feedback should update only the affected sections and produce a new version such as `v2`, `v3`, and so on while preserving history.

## Next Step

After the outline is accepted, continue with:

- `writer/character-profile`
- `writer/script-writing`

## Changelog

- 2026-04-01: Rewritten into English-first format and aligned with the repo-wide writer skill structure.
- 2026-03-24: Aligned to the repository template and added standardized sections.
