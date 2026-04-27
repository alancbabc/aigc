---
name: Knowledge
description: Shared knowledge layer for the AIGC skill system. Provides reusable narrative, genre, character, camera, dialogue, transition, sound, environment, and style-reference knowledge.
trigger: Use when a skill needs shared creative rules, concept libraries, or decision heuristics before generating an artifact.
---

# Knowledge

## What This Layer Is

`_knowledge/` is the shared professional foundation for the whole skill system.

It is meant for:

- rule extraction
- decision support
- field shaping
- style and craft reference

It should not be treated as a direct user-facing output layer.

Skills should usually:

1. read the relevant knowledge libraries
2. extract usable decision fields
3. generate the target artifact
4. review against the target contract

Start with:

- [knowledge-map.md](/c:/Users/jyfa/Desktop/aigc-skill/aigc/_knowledge/knowledge-map.md)

## Main Libraries

### `Genre`

- story tone
- world rules
- conflict defaults
- genre-fit expectations

### `Narrative`

- structure patterns
- scene engines
- reveal strategies
- rhythm logic

### `Actor`

- role archetypes
- body language
- relationship signaling
- costume anchors

### `Dialogue`

- dialogue rhythm
- subtext
- reaction priority
- dialogue-to-visual conversion

### `Camera`

- shot types
- camera angles
- movement
- composition
- prompt-safe camera phrasing

### `Transition`

- transition selection
- visual bridge logic
- frame-boundary planning

### `VisualEnvironment`

- setting anchors
- lighting logic
- dynamic environment elements
- scene consistency rules

### `FamousDirectors`

- director-style control
- cross-skill style influence
- narrative and visual trait mapping

### `Sound`

- sound and music reference
- atmosphere support
- rhythm reinforcement

### `ShortDrama`

- episodic modifier layer
- platform rhythm
- hook and cliffhanger logic
- episode payoff density

## Usage Principles

1. Start from the current skill and artifact contract.
2. Read only the most relevant libraries first.
3. Use knowledge to make decisions, not to copy text directly.
4. If multiple libraries apply, lock structure first, then add style.
5. If a project is episodic or platform-first, route `ShortDrama` earlier in the writing stages.

## Suggested Entry Point

When you are unsure where to start, use:

- [knowledge-map.md](/c:/Users/jyfa/Desktop/aigc-skill/aigc/_knowledge/knowledge-map.md)

It explains:

- which libraries matter for Writer, Director, and Art
- which libraries affect each output artifact
- how to route knowledge reads more efficiently
