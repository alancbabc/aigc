---
name: Transition
description: Shared transition knowledge for storyboarding, transition design, and test-shoot planning. Provides AI-friendly transition types, selection heuristics, bridge patterns, and prompt-safe terminology.
trigger: Use when a skill needs to decide how to move from one scene, shot, or segment into the next.
---

# Transition

## Use For

- `director/storyboard`
- `director/transition`
- `director/test-shoots`
- `art/keyframe-generation`

## Common Use Cases

- scene-to-scene transition design
- emotional transition design
- time jump expression
- space jump expression
- visual bridge selection

## Output Impact

- `storyboard.json -> scenes[].transition_to_next`
- `storyboard.json -> scenes[].transition_notes`
- `transition.json -> transition_type`
- `transition.json -> visual_bridge`
- `transition.json -> execution_notes`
- `test-shoots.json -> shots[].transition_context`

## AI Usage Principles

1. Decide the relationship between the two segments first, then choose the transition.
2. Prefer stable defaults: `CUT`, `DISSOLVE`, `FADE`, `MATCH CUT`, `SMASH CUT`.
3. Use advanced transitions only when there is a clear visual bridge.
4. For downstream generation, keep prompt wording short, concrete, and in English.
5. Every transition decision should answer three questions:
   - Why are we transitioning this way?
   - What is the visual or emotional bridge?
   - Do we need extra frames?

## Decision Dimensions

Check these dimensions before choosing a transition:

- `time_change`: Is there a meaningful time jump?
- `space_change`: Does the next segment move to a different place or viewpoint?
- `emotion_change`: Is the emotion continuous, escalated, interrupted, or reversed?
- `rhythm_goal`: Should the pacing accelerate, hold, or soften?
- `visual_bridge`: Is there a reusable bridge such as shape, motion, direction, color, framing, sky, door, mirror, or light source?

## Core Transition Types

| Type | Use When | Avoid When | Prompt-Safe Wording |
|------|----------|------------|---------------------|
| `CUT` | default change, fast pacing, clean progression | when a soft time passage is needed | `clean cut`, `direct cut` |
| `FADE` | opening, ending, major section break | ordinary scene continuation | `fade in`, `fade out to black` |
| `DISSOLVE` | memory, passage of time, lyrical continuity | sharp emotional interruption | `soft dissolve`, `gentle dissolve` |
| `MATCH CUT` | shape, motion, framing, or direction can bridge the two shots | when no clear match exists | `match cut by motion`, `match cut by shape` |
| `SMASH CUT` | emotional shock, comedic break, hard contrast | soft continuity | `smash cut`, `abrupt cut` |
| `WIPE` | explicit stylization, retro or playful tone | realistic neutral filmmaking | `stylized wipe transition` |

## Advanced Transition Types

### Aerial Match Cut

- Use when space changes but the emotional line should remain continuous.
- Requires a shared overhead or sky-related bridge.
- Typical bridge elements:
  - sky
  - clouds
  - birds
  - aircraft
  - paper airplane
  - upward or downward camera travel
- Usually benefits from `first`, `intermediate`, and `last` frame planning.
- Prompt-safe wording:
  - `aerial match cut`
  - `camera follows the object upward into the sky`
  - `sky bridge into the next scene`

### Sky Transition

- Use when the new scene can be revealed from the sky downward.
- Good for opening a new location with a gentle handoff.
- Typical prompt-safe wording:
  - `sky transition`
  - `camera starts from the sky and moves down`
  - `sky reveal into the next environment`

## Situation Guide

| Situation | Recommended | Usually Avoid | Reason |
|-----------|-------------|---------------|--------|
| ordinary dialogue cut | `CUT` | `DISSOLVE` | dialogue pacing usually wants clarity |
| entering a memory | `DISSOLVE` or `FADE` | `SMASH CUT` | memory benefits from separation or softness |
| emotional shock | `SMASH CUT` | `DISSOLVE` | contrast is the point |
| same action across spaces | `MATCH CUT` | `FADE` | action continuity is the bridge |
| lyrical spatial jump | `DISSOLVE` or `AERIAL MATCH CUT` | mechanical `CUT` | emotion and association matter |
| fast short-drama escalation | `CUT` | over-designed advanced transitions | pacing wins |

## Visual Bridge Library

When attempting `MATCH CUT` or an advanced transition, check for:

- motion direction: turn, throw, fall, rise, enter, exit
- shape echo: circle to moon, airplane to bird, lamp to sun
- framing echo: centered subject, doorway framing, silhouette, foreground obstruction
- color echo: warm dusk to warm interior, neon to neon
- space element: sky, window, mirror, corridor, door, water surface
- camera movement echo: tilt up, tilt down, pan, orbit, push-in

## Rule Set

### Rule 1: Time Change First

- clear time passage -> prefer `DISSOLVE`
- opening or ending -> prefer `FADE`
- fast time jump with strong pace -> `CUT` can still work

### Rule 2: Emotion Change First

- smooth emotional continuation -> `CUT` or `DISSOLVE`
- rupture, surprise, comedic break -> `SMASH CUT`
- dream, memory, nostalgia -> `DISSOLVE`

### Rule 3: Space Change First

- same action across places -> `MATCH CUT`
- new scene revealed from sky -> `SKY TRANSITION`
- airborne element bridges two spaces -> `AERIAL MATCH CUT`

### Rule 4: Rhythm First

- ad, short-form, aggressive pacing -> default to `CUT`
- lyrical, reflective pacing -> consider `DISSOLVE`
- advanced transitions -> use sparingly

## Prompt Terminology Map

| Concept | Recommended Prompt Wording | Avoid |
|---------|----------------------------|-------|
| hard cut | `clean cut` | `hard switch` |
| dissolve | `soft dissolve` | `blending edit` |
| match cut | `match cut by motion` | `similar cut` |
| smash cut | `smash cut` | `strong cut` |
| sky transition | `sky transition` | `sky switch` |
| aerial match cut | `aerial match cut` | `air cut` |

## Suggested Output Shape

```json
{
  "transition_type": "MATCH CUT",
  "transition_goal": "Cross space while keeping movement continuity",
  "visual_bridge": "paper airplane exits frame -> bird crosses the sky",
  "reason": "Both shots share directional movement and a readable visual bridge.",
  "execution_notes": [
    "Keep the outgoing motion direction readable in the last frame.",
    "Let the next shot begin with a matching directional movement."
  ],
  "frame_requirement": {
    "needs_extra_frames": true,
    "recommended_frames": ["first", "intermediate", "last"]
  },
  "prompt_hint": "motion match cut, subject exits frame left to right, next shot begins with the same directional movement"
}
```

## Anti-Patterns

- Do not force complex transitions into ordinary scenes.
- If the bridge is unclear, fall back to `CUT` or `DISSOLVE`.
- Do not use aerial or sky transitions without a believable spatial logic.
- Do not send long theory text downstream to generation models.
