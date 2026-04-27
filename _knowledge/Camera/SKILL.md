---
name: Camera
description: Shared camera-language knowledge for storyboard, test-shoot planning, and keyframe prompt design. Covers shot types, angles, composition, movement, and prompt-safe phrasing.
trigger: Use when a skill needs to choose or explain shot type, camera angle, camera movement, composition, or focal behavior.
---

# Camera

## Use For

- `director/storyboard`
- `director/test-shoots`
- `art/keyframe-generation`

## Common Use Cases

- choosing `shot_type`
- choosing `camera_angle`
- choosing `camera_movement`
- planning `composition`
- translating camera ideas into prompt-safe wording

## Output Impact

- `storyboard.json -> scenes[].shots[].shot_type`
- `storyboard.json -> scenes[].shots[].camera_angle`
- `storyboard.json -> scenes[].shots[].camera_movement`
- `storyboard.json -> scenes[].shots[].composition`
- `test-shoots.json -> shots[].shot_prompt`
- `test-shoots.json -> shots[].frame_plan`
- `keyframe-prompts.json -> prompts[].camera_language`

## AI Usage Principles

1. Camera choices should serve narrative function, not decoration.
2. Choose shot type first, then angle, then movement, then composition.
3. Prefer readable, stable terms over over-stylized jargon.
4. When writing prompts for generation, use short English phrases the model can parse reliably.
5. Avoid inventing custom camera labels that do not exist elsewhere in the repo.

## Shot Types

| Shot Type | Use When | Typical Effect | Prompt-Safe Wording |
|-----------|----------|----------------|---------------------|
| Establishing Shot | introduce space and scale | orientation, atmosphere | `wide establishing shot` |
| Wide Shot | show full body and environment relation | movement, blocking, geography | `wide shot` |
| Medium Shot | dialogue, readable action | balance of person and environment | `medium shot` |
| Close-up | face or emotional detail | intimacy, pressure, focus | `close-up` |
| Extreme Close-up | tiny detail or emotional intensity | emphasis, tension | `extreme close-up` |

## Camera Angles

| Angle | Use When | Typical Effect | Prompt-Safe Wording |
|-------|----------|----------------|---------------------|
| Eye Level | neutral observation | objective, balanced | `eye-level view` |
| High Angle | subject should feel weaker or observed | vulnerability, distance | `high-angle shot` |
| Low Angle | subject should feel stronger or imposing | power, scale | `low-angle shot` |
| Dutch Angle | instability matters | unease, tension, distortion | `dutch angle` |
| Bird's-Eye View | top-down orientation is useful | map-like clarity, fate, distance | `bird's-eye view`, `overhead view` |
| Worm's-Eye View | extreme upward scale matters | awe, distortion, pressure | `worm's-eye view` |
| POV | audience should see through a character's eyes | immersion, subjectivity | `point-of-view shot` |

## Focal Behavior

| Focal Style | Use When | Typical Effect |
|-------------|----------|----------------|
| Ultra Wide | architecture, extreme space, distortion | exaggerated perspective |
| Wide | environment and spatial clarity matter | strong depth and openness |
| Standard | neutral, natural scenes | familiar perspective |
| Medium Telephoto | portrait emphasis, compressed space | gentle background compression |
| Long Lens | distance, isolation, shallow depth | strong compression and separation |

## Composition Rules

### Core Rules

| Rule | Use When | Effect |
|------|----------|--------|
| Rule of Thirds | general readable composition | balance and focus |
| Symmetry | stylized order or tension | control, ritual, visual lock |
| Leading Lines | movement or gaze should be guided | directional attention |
| Framing | doors, windows, mirrors, foreground shapes exist | layered focus, emotional enclosure |
| Negative Space | loneliness or emphasis matters | isolation, clarity |
| Triangular Composition | three-key-point stability helps | visual balance |

### Subject Size Guide

- full body
- knee-up
- waist-up
- chest-up
- shoulder-up
- face detail

Use `_knowledge/Actor` when body language, pose, or relationship blocking matters.

## Camera Movement

| Movement | Use When | Typical Effect | Prompt-Safe Wording |
|----------|----------|----------------|---------------------|
| Static Shot | observation, calm, clarity | control, stillness | `static shot` |
| Dolly In | attention should narrow or emotion should intensify | focus, intimacy | `slow dolly in`, `camera pushes in` |
| Dolly Out | reveal context or distance | separation, reveal | `dolly out`, `camera pulls back` |
| Pan | horizontal discovery or follow action | survey, follow | `slow pan left`, `slow pan right` |
| Tilt | vertical reveal matters | scale, reveal | `tilt up`, `tilt down` |
| Tracking Shot | subject movement matters | momentum, continuity | `tracking shot`, `camera follows the subject` |
| Orbit | subject-centered stylization matters | intensity, display | `camera circles around the subject` |
| Crane/Jib | height reveal matters | grandeur, lift, descent | `crane shot` |
| Handheld | instability should be felt | realism, tension | `handheld camera`, `subtle handheld movement` |
| Steadicam | smooth mobile follow is needed | fluid continuity | `steadicam follow shot` |

## Practical Combinations

### Dialogue Scene

- shot type: `medium shot`
- angle: `eye-level view`
- movement: `static shot` or gentle push-in
- composition: balanced thirds or over-the-shoulder

### Emotional Close Moment

- shot type: `close-up`
- angle: `eye-level view` or slight `low-angle shot`
- movement: mostly static
- composition: centered face or slightly off-center with negative space

### Action Scene

- shot type: `wide shot` to `medium shot`
- angle: eye level by default
- movement: tracking, handheld, or pan depending on clarity needs
- composition: readable direction of motion

### Environment Reveal

- shot type: `wide establishing shot`
- angle: eye level, high angle, or bird's-eye view depending on scale
- movement: pan, tilt, or dolly out
- composition: leading lines or thirds

## Emotion and Camera Heuristics

- low angle -> power, intimidation, pressure
- high angle -> weakness, exposure, distance
- dutch angle -> instability, fear, chaos
- close-up -> emotional specificity
- wide shot -> spatial truth, isolation, or movement clarity
- push-in -> emotional convergence
- pull-back -> emotional withdrawal or contextual reveal

## Decision Heuristics

### Rule 1: Narrative Function First

- if the audience needs orientation -> prefer `wide establishing shot`
- if the audience needs emotional reading -> prefer `close-up`
- if the audience needs body plus environment -> prefer `medium shot`

### Rule 2: Movement Must Earn It

- no movement unless it reveals, follows, intensifies, or reframes
- if movement adds no narrative value, stay static

### Rule 3: Composition Must Support Attention

- if emotion matters, simplify background and focus attention
- if space matters, preserve readable layout and anchors

### Rule 4: Prompt Language Must Stay Stable

- use short phrases such as `eye-level medium shot`, `slow dolly in`, `rule of thirds composition`
- avoid abstract theory language in prompt output

## Prompt Vocabulary Map

| Concept | Recommended Prompt Wording | Avoid |
|---------|----------------------------|-------|
| eye level | `eye-level view` | `normal human perspective shot` |
| high angle | `high-angle shot` | `camera from above but not top view` |
| low angle | `low-angle shot` | `heroic upward camera` |
| overhead | `bird's-eye view` | `god perspective` |
| tracking | `tracking shot` | `following moving lens` |
| push in | `slow dolly in` | `dramatic move closer` |
| handheld | `handheld camera` | `shaky realism lens` |

## Anti-Patterns

- Do not stack too many camera effects into one shot.
- Do not choose movement before defining shot purpose.
- Do not use handheld unless instability helps the scene.
- Do not use extreme angles everywhere just to make things feel cinematic.
- Do not output long technical explanations into downstream prompts.
