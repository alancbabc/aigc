---
name: keyframe-generation
description: Generate frame prompts and frame images from test-shoots stage output, while enforcing progression between frames instead of repetition.
trigger: Call when the project needs frame prompts, keyframe images, or keyframe review for one scene.
---

# Keyframe Generation

> Rule: all prompts sent into `generation/*` must be written in English.

## Overview

This skill converts Stage 1 shot planning into:
- frame prompts
- generated frame images
- frame review

It processes one scene at a time in two main steps:

| Step | Output | Purpose |
|------|------|------|
| `step 1` | `keyframe-prompts.json` | frame prompts |
| `step 2` | `keyframe-images.json` | frame images |

Review then produces:
- `keyframe-review.json`

## Knowledge Dependencies

Prioritize:
- `_knowledge/Camera/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/Transition/`
- `_knowledge/FamousDirectors/`
- `_prompts/PromptTemplates/Camera/`

Use rules:
1. inherit shot structure from `director/test-shoots`
2. inherit character appearance from three-view outputs
3. inherit environment from scene-design outputs
4. refine wording with knowledge layers, but do not invent new upstream design

## Inputs

- `director/test-shoots/test-shoots.example.json`
- character reference images from `art/character-three-view`
- scene references from `art/scene-design`

## Contract Chain

This skill sits in the middle of a four-step handoff:
1. upstream shot input: `director/test-shoots/test-shoots.example.json`
2. frame prompt output: `art/keyframe-generation/keyframe-prompts.example.json`
3. generated image output: `art/keyframe-generation/keyframe-images.example.json`
4. review output: `art/keyframe-generation/keyframe-review.example.json`

Keep the same `intent` and `change_focus` semantics across all four stages.

## Contracts

- Frame prompt example: `art/keyframe-generation/keyframe-prompts.example.json`
- Frame prompt schema: `art/keyframe-generation/keyframe-prompts.schema.json`
- Final image example: `art/keyframe-generation/keyframe-images.example.json`
- Final image schema: `art/keyframe-generation/keyframe-images.schema.json`
- Review example: `art/keyframe-generation/keyframe-review.example.json`
- Review schema: `art/keyframe-generation/keyframe-review.schema.json`

## Step 1: Generate Frame Prompts

### Frame Count Rule

Default frame logic:
- every shot may have `first`
- add `intermediate` only when the shot has a real middle state
- add `last` only when the shot ends in a different state or supports a transition

Maximum:
- 3 frames: `first + intermediate + last`

## Frame Progression Principle

Frames inside the same shot must form a progression, not a repetition set.

This means:
- `first`, `intermediate`, and `last` must not be near-duplicate images
- each frame must carry a distinct state, action phase, or transition value
- if a shot does not contain meaningful internal change, generate fewer frames

### Prompt Structure

Recommended template:
```text
[Core Token], [shot type], [camera angle], [character appearance], [environment], [action or state], [atmosphere]
```

Scene-design read rule:
- read `scene_design.json -> scenes[] -> reference_images[]`
- pick references matching the current `scene_no`
- extract environment wording from `reference_images[].prompt`

### Frame Role Differences

- `first`: opening state, starting pose, initial framing anchor
- `intermediate`: visible change in progress compared with `first`
- `last`: resolved or transition-ready ending state

### Anti-Duplication Rules

When writing frame prompts, force visible progression.

Do not allow:
- the same pose repeated three times
- the same hand or object position repeated with only wording changes
- the same framing repeated without new narrative value
- `intermediate` that is only a weak restatement of `first`
- `last` that does not create an ending state

Useful progression dimensions:
- body pose change
- hand or object state change
- gaze direction change
- emotional expression change
- camera distance change
- composition shift
- transition preparation

### Prompt Writing Rule For Multi-Frame Shots

Each later frame must explicitly reflect the change from the previous frame.

Recommended pattern:
- `first`: establish the readable initial state
- `intermediate`: show the key change in progress
- `last`: show the completed action, held result, or transition-ready image

If you cannot name a concrete change, do not keep the extra frame.

## Step 2: Generate Frame Images

Model rule:
- use `flux-image-edit` when scene or character reference images exist
- use `flux-text-to-image` only when no visual references exist

Reference rule:
- `first`: character reference + scene reference
- `intermediate`: character reference + first-frame result + scene reference
- `last`: character reference + first-frame result + scene reference

## Review

Check:
- image quality
- character consistency
- scene consistency
- frame progression
- whether the generated result matches `intent` and `change_focus`

Recommended review fields:
- `frame_progression_ok`
- `character_consistency_ok`
- `scene_consistency_ok`
- `intent_match_ok`

If quality fails or frames are too repetitive:
- mark `needs_regen`

