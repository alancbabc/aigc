---
name: script-writing
description: Create a full script with scenes, events, and dialogue from an outline and character package.
trigger: Use when the task is to generate a screenplay-style script rather than only an outline, notes, or isolated dialogue polishing.
---

# Script Writing

## Purpose

This skill turns an outline and character package into a full script artifact.

It is responsible for:

- converting story structure into scene-by-scene script form
- writing events and dialogue that match character logic
- estimating scene-level duration and pacing

It is not responsible for:

- replacing outline design upstream
- replacing storyboard design downstream
- treating dialogue volume alone as a sign of quality

## Inputs

- `outline.json`
- `characters.json`

## Outputs

- film / short-film mode: `script.json`
- episodic short-drama mode: `episodes/episode_01.json` ... `episode_N.json`

The output must satisfy the appropriate contract files.

### Film Contract

- example: `writer/script-writing/script.example.json`
- schema: `writer/script-writing/script.schema.json`

### Episodic Contract

- example: `writer/script-writing/episode.example.json`
- schema: `writer/script-writing/episode.schema.json`

## Decision Extraction

### Narrative Extraction

Read `_knowledge/Narrative/` and extract:

- `scene_engine`
- `reveal_strategy`
- `rhythm_goal`

Assign every important scene a narrative function such as conflict, reveal, bridge, compression, or payoff before drafting dialogue.

## Dependencies

### Core Knowledge

- `_knowledge/Narrative/`
- `_knowledge/Dialogue/`
- `_knowledge/Genre/`

### Dependency Rules

1. Decide the narrative function of each scene before writing events and lines.
2. Dialogue should serve relationship, tension, and rhythm rather than mechanically increasing word count.
3. Extracted knowledge should influence `scenes[].event`, `characters[].dialogue`, and scene duration.

## Output Contract

```json
{
  "title": "Story Title",
  "genre": "Genre",
  "duration": "5 minutes",
  "scenes": [
    {
      "scene_no": 1,
      "location": "Location",
      "time_of_day": "Time",
      "presence": ["People present"],
      "enter": ["People entering"],
      "exit": ["People leaving"],
      "event": "What happens in the scene",
      "duration": "About X seconds",
      "characters": [
        {
          "character": "Character Name",
          "state_num": 1,
          "parenthetical": "Action or expression",
          "dialogue": "Line of dialogue"
        }
      ]
    }
  ]
}
```

## Scene Arrangement Rules

1. Merge adjacent scenes when location, continuity, and dramatic function are effectively the same.
2. Split scenes when content density, time jumps, or emotional turns require clearer separation.
3. Scene transitions must preserve causal, temporal, or spatial logic.
4. Duration estimates should consider dialogue load, action beats, and emotional pauses.
5. Every scene must justify its existence through narrative function.

## Workflow

1. Read the outline and character package.
2. Extract scene-level narrative and dialogue guidance from the knowledge layer.
3. Plan scene sequence and estimate duration.
4. Write the script scene by scene.
5. Flag obvious duration overages or shortages.
6. In episodic mode, add episode-level hook, beats, and ending-hook structure.

## Review

Review should check:

- fidelity to the outline and character package
- appropriate narrative technique
- natural dialogue rhythm
- character voice consistency
- duration plausibility

## Storage Path

Recommended logical paths:

- `memory/[date]/[title]/v[version]/script.json`
- episodic mode: `memory/[date]/[title]/v[version]/episodes/episode_01.json`

## Iteration

User feedback should produce a new version while preserving history.

## Next Step

After the script is accepted, continue with:

- `director/storyboard`

## Changelog

- 2026-04-01: Rewritten into English-first format and aligned with repo-wide writer skill structure.
