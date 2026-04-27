---
name: VisualEnvironment
description: Shared environment-design knowledge for scene planning, storyboard atmosphere, test-shoot prompts, and keyframe generation. Covers setting, lighting, dynamic elements, and environment consistency.
trigger: Use when a skill needs to define scene setting, lighting logic, atmosphere, or environmental motion.
---

# VisualEnvironment

## Use For

- `art/scene-design`
- `director/storyboard`
- `director/test-shoots`
- `art/keyframe-generation`

## Common Use Cases

- defining `scene_base`
- choosing `environment.setting`
- choosing `environment.lighting`
- choosing `environment.dynamic_elements`
- translating environment logic into prompt-safe wording
- keeping multi-view scene references visually consistent

## Output Impact

- `storyboard.json -> scenes[].environment.setting`
- `storyboard.json -> scenes[].environment.lighting`
- `storyboard.json -> scenes[].environment.dynamic_elements`
- `scene_design.json -> scenes[].scene_base`
- `scene_design.json -> scenes[].reference_images[].prompt`
- `test-shoots.json -> shots[].shot_prompt`
- `keyframe-prompts.json -> prompts[].environment`

## AI Usage Principles

1. Environment should support story function, not act as random decoration.
2. Build environment in layers:
   - space
   - light
   - motion
3. Lock the stable scene base first, then vary viewpoint.
4. Keep prompt wording concrete and visual.
5. If a scene has multiple reference images, they must share the same environment anchors unless the script clearly changes the location.

## Environment Layers

### 1. Setting Layer

Defines what the place is and what anchors make it identifiable.

Useful questions:

- Is it indoor, outdoor, or a special space?
- What are the most important visual anchors?
- What makes this place readable in one glance?
- What emotional tone should the place carry?

### 2. Lighting Layer

Defines how the place is seen.

Useful questions:

- What is the main light source?
- What is the light direction?
- Is the tone warm, cool, neutral, harsh, or soft?
- Is contrast high or low?

### 3. Dynamic Layer

Defines what in the environment is moving or changing.

Useful questions:

- Is there wind, rain, smoke, flicker, traffic, crowd motion, dust, waves, leaves, or reflections?
- Does the scene need static stillness or visible motion?
- Which dynamic element helps the mood most?

## Setting Types

### Indoor

Common useful spaces:

- living room
- bedroom
- kitchen
- dining room
- study
- bathroom
- corridor
- staircase
- office
- shop
- classroom
- hospital room
- prison cell

### Outdoor

Common useful spaces:

- city street
- rural road
- bamboo forest
- forest
- desert
- mountain path
- seaside
- grassland
- garden
- rooftop
- parking lot
- ruins

### Special Spaces

Use only when the project world requires them:

- space station
- submarine
- cave
- tunnel
- tower interior

## Lighting Guide

### Light Sources

- daylight
- skylight
- moonlight
- practical indoor light
- candlelight
- screen light
- vehicle light
- neon light

### Light Direction

- front light
- side light
- back light
- top light
- under light
- 45-degree light

### Light Quality

- harsh light
- soft light
- low light
- dim ambient light

### Color Temperature

- cool tone
- warm tone
- neutral tone

### Contrast

- high contrast
- medium contrast
- low contrast

## Dynamic Element Library

### Weather

- clear sky
- cloudy
- overcast
- rain
- snow
- fog
- strong wind

### Natural Motion

- moving leaves
- drifting petals
- smoke or mist
- fire flicker
- water flow
- dust in light

### Artificial Motion

- passing headlights
- flickering neon
- screen flicker
- unstable fluorescent light
- fan-driven cloth or curtain movement

## Decision Heuristics

### Rule 1: Environment Must Support Emotion

- warm interiors -> comfort, memory, intimacy
- cool night exteriors -> distance, loneliness, tension
- high contrast low-key light -> danger, secrecy, pressure
- soft low-contrast light -> tenderness, calm, melancholy

### Rule 2: Anchors First

For every important scene, define at least 2-4 stable anchors such as:

- doorway
- window grid
- old sofa
- neon sign
- bamboo shadows
- wet street reflection

These anchors should survive across scene-design views and keyframes.

### Rule 3: Dynamic Elements Must Be Selective

- use one or two meaningful moving elements
- avoid stacking too many environment motions at once
- choose motion that supports tone or transition logic

### Rule 4: Multi-View Consistency

If a scene has multiple reference images:

- setting must remain the same
- lighting logic must remain the same
- anchor elements must remain the same
- only view, scale, and framing should change

## Prompt-Safe Wording

Use concrete phrases such as:

- `dim kitchen with a single warm practical light`
- `rain-soaked neon street with reflective pavement`
- `bamboo forest with drifting mist and broken sunlight`
- `old apartment corridor with peeling walls and weak overhead light`

Avoid vague phrases such as:

- `beautiful environment`
- `cinematic space`
- `nice dramatic lighting`

## Suggested Extraction Targets

Before generating scene art or shot prompts, extract:

- `setting_type`
- `environment_anchors`
- `lighting_source`
- `lighting_direction`
- `lighting_tone`
- `contrast_level`
- `dynamic_elements`
- `mood_goal`

## Suggested Questions

- What makes this space identifiable in one glance?
- Which light source defines the scene?
- What should be moving, if anything?
- Which details must remain stable across multiple views?
- Is this environment helping the emotion or just filling space?

## Anti-Patterns

- over-describing space without clear visual anchors
- changing environment identity across views of the same scene
- adding too many unrelated moving elements
- using generic lighting words without source or direction
- making the scene visually rich but emotionally empty
