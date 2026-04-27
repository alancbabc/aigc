---
name: character-profile
description: Create structured character profiles from a story outline, including role design, relationship logic, and state planning for downstream visual work.
trigger: Use when the task is to build character definitions from an outline rather than to generate standalone art only.
---

# Character Profile

## Purpose

This skill creates `characters.json` from a story outline or partial character input.

It is responsible for:

- defining each character's writing-side identity
- mapping role function, personality, motivation, and relationships
- planning meaningful character states for downstream visual generation

It is not responsible for:

- inventing characters that are not supported by the outline
- replacing the art-side three-view generation step
- turning state planning into final image generation by itself

## Inputs

- `outline.json`
- character list or partial character notes
- optional user-supplied character JSON to continue from

## Outputs

- primary artifact: `characters.json`
- downstream consumer: `art/character-three-view`

The output must satisfy:

- `writer/character-profile/characters.example.json`
- `writer/character-profile/characters.schema.json`

## Decision Extraction

### Genre Extraction

Read `_knowledge/Genre/` and extract:

- `genre_label`
- `tone`
- `character_archetypes`
- `world_rules`

Use these to constrain role design, relationship dynamics, costume direction, and behavior boundaries.

### Actor Extraction

Read `_knowledge/Actor/` and extract:

- `role_archetype`
- `relationship_signal`
- `body_language`
- `emotion_expression_mode`
- `costume_anchor`
- `habit_action`

Use these to make the character recognizable in writing, image prompts, and staging.

## Dependencies

### Core Knowledge

- `_knowledge/Genre/`
- `_knowledge/Actor/`
- `_prompts/PromptTemplates/Style/` for downstream visual-style token support

### Dependency Rules

1. Start from the outline's story function for each character.
2. Use knowledge sources to complete archetype, relationship, and state expression details.
3. Let extracted knowledge influence `character_type`, `personality`, `relationships`, and `states[].description`.
4. Actor knowledge strengthens expression and staging cues; it does not replace the outline's story logic.

## Output Contract

```json
{
  "project_title": "Project Title",
  "genre": "Genre",
  "characters": [
    {
      "name": "Character Name",
      "age": "Age",
      "role": "lead/supporting/antagonist",
      "character_type": "Archetype",
      "personality": "Key personality traits",
      "background": "Backstory",
      "goals": "Motivation",
      "relationships": ["Relationship notes"],
      "states": [
        {
          "state_num": 1,
          "state_name": "State Name",
          "description": "Appearance description",
          "scene_reference": "Where it appears",
          "views": {
            "front": {"prompt": "Front-view prompt", "image_path": null},
            "side": {"prompt": "Side-view prompt", "image_path": null},
            "back": {"prompt": "Back-view prompt", "image_path": null}
          }
        }
      ]
    }
  ]
}
```

Contract files:

- example: `writer/character-profile/characters.example.json`
- schema: `writer/character-profile/characters.schema.json`

## State Model

A state represents a distinct appearance condition for the same character at a different time or under a clearly different circumstance.

Create a new state only when the outline supports a real appearance change, such as:

- age change
- costume or identity change
- injury or makeup change
- major status transformation

Do not create a new state for temporary expression or motion alone, such as:

- smiling
- crying
- running
- waving

State naming convention:

- `[character_name]_[state_num]`

## Core Rules

1. Use existing story information and knowledge sources instead of inventing unsupported lore.
2. Extract characters only from the outline's role set; do not add extra characters unless the user explicitly asks for it.
3. Every state must be clear enough for downstream three-view generation.
4. Relationship design must stay consistent with the story's conflict and theme.
5. State count should stay minimal but sufficient.

## Workflow

1. Read the story outline.
2. Identify required characters and their story functions.
3. Extract genre and actor-side decisions from the knowledge layer.
4. Build the writing-side profile for each character.
5. Decide whether the character needs one or more meaningful states.
6. Prepare state descriptions for downstream three-view work.
7. Merge any returned art-side prompt and image data when that downstream stage completes.
8. Return the completed `characters.json`.

## Partial Artifact Support

This skill can continue from intermediate artifacts. For example:

- partially completed character lists
- incomplete state definitions
- an existing `characters.json` that needs revision

## Review

Review should check:

- whether character design matches the outline
- whether personality and relationship logic are coherent
- whether state division is justified by actual story changes
- whether each state description is useful for image generation

Writer and Art should review together when the downstream visual step is active.

## Storage Path

Recommended logical paths:

- `memory/[date]/[title]/v[version]/characters.json`
- `memory/[date]/[title]/v[version]/character_images/`

## Iteration

Typical iteration types:

- add or remove states
- adjust appearance or costume direction
- revise personality or background emphasis
- refine relationship descriptions

Each revision should produce a new version while preserving history.

## Next Step

After character profiles are accepted, continue with:

- `art/character-three-view`
- `writer/script-writing`

## Changelog

- 2026-04-01: Rewritten into English-first format and aligned with repo-wide writer skill boundaries.
