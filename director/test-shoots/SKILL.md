---
name: test-shoots
description: Plan shot-level prompts and frame plans from storyboard, then hand off cleanly to art/keyframe-generation for frame prompts, images, and review.
trigger: Call after storyboard is ready and the project needs shot prompts, frame planning, and keyframe orchestration.
---

# Test Shoots

> Rule: all prompts sent into `generation/*` must be written in English.

## Overview

This skill is the orchestration layer between:
- `director/storyboard`
- `art/scene-design`
- `art/character-three-view`
- `art/keyframe-generation`

It works scene by scene in three stages:

| Stage | Owner | Output | Purpose |
|------|------|------|------|
| `stage 1` | Director | `test-shoots.stage1.json` | shot prompt planning and frame planning |
| `stage 2` | Art | `keyframe-prompts.json` | frame prompts |
| `stage 3` | Art | `keyframe-images.json` | generated frame images |

## Knowledge Dependencies

Prioritize:
- `_knowledge/Camera/`
- `_knowledge/Transition/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`
- `_knowledge/Sound/` when a shot depends on off-screen cues, impact sounds, ambience, or silence emphasis
- `_prompts/PromptTemplates/Camera/`

Use rules:
1. inherit structure from storyboard first
2. inherit environment from `scene_design.json` first
3. inherit character appearance from three-view outputs first
4. use Sound only for sound-effect support, not background music
5. only use knowledge and prompt layers to refine, never to override upstream design

## Inputs

- `storyboard.json`
- `characters.json`
- `scene_design.json`

Scene-design read rule:
- read `scene_design.json -> scenes[] -> reference_images[]`
- prefer references matching the current `scene_no`
- extract environment wording from `reference_images[].prompt`

## Contract Chain

The expected handoff chain is:
1. `director/test-shoots/test-shoots.example.json`
2. `art/keyframe-generation/keyframe-prompts.example.json`
3. `art/keyframe-generation/keyframe-images.example.json`
4. `art/keyframe-generation/keyframe-review.example.json`

In practice:
- Stage 1 outputs shot planning plus `frame_plan`
- Stage 2 outputs frame prompts
- Stage 3 outputs generated frame images
- final review checks progression, consistency, and intent match

## Transition Skill Routing

Use `director/transition` before writing prompts for a boundary shot when the transition itself affects frame planning.

Trigger it when:
- the last frame must connect to the next shot or next scene
- the transition may need an intermediate frame
- the transition type is not a simple `CUT`
- the prompt needs a stable English `prompt_hint`

Integration rule:
1. inherit transition choice from storyboard when already clear
2. if underspecified, call `director/transition`
3. map `frame_requirement` into `first` / `intermediate` / `last`
4. convert `prompt_hint` and `execution_notes` into frame-level guidance

### VLM-Assisted Boundary Review

Use this branch when the boundary itself is visually sensitive.

Recommended flow:
1. prepare the current shot's `last_frame_image`
2. prepare the next shot's `first_frame_image`
3. analyze both separately with `generation/qwen2.5-vl`
4. write `last-frame-analysis.json` and `first-frame-analysis.json`
5. call `director/transition`
6. inherit returned `transition_context` into the current shot plan

Important:
- VLM is only a frame analysis helper
- `director/transition` still owns the final transition decision

## Stage 1: Shot-Level Planning

Process one scene at a time.

### Step 1: Extract Style

Extract a shared Core Token from:
- `scene_design.json -> scenes[] -> reference_images[].prompt`

### Step 2: Write Shot Prompt

Recommended prompt structure:
```text
[Core Token], [shot type], [camera angle], [camera movement], [environment], [event], [atmosphere]
```

Environment rule:
- environment wording must come from `scene_design.json`
- do not guess a new environment from storyboard description alone

### Step 2.5: Add Sound Cues When Needed

Use `_knowledge/Sound/` only when the shot meaning depends on sound-effect design.

Typical cases:
- off-screen approach or reveal
- a strong impact beat
- a material-specific action sound
- a planned silence moment
- ambience that helps sell space or tension

Persistence rule:
- store these as `sound_cues`
- keep cues source-based and concrete
- do not write music instructions here

### Step 3: Logic Check

Check:
- adjacent shots that can be merged
- shots that are too dense and should be split
- durations that do not match content
- abrupt rhythm or continuity problems

Typical merge cases:
- lift object -> throw object
- pick up -> examine
- walk to mark -> stop at mark

### Step 4: Persist Stage 1 Output

Write:
- `test-shoots/scene_01_stage1.json`

Contract files:
- Example: `director/test-shoots/test-shoots.example.json`
- Schema: `director/test-shoots/test-shoots.schema.json`

## Stage 2: Frame Planning For Art

Call `art/keyframe-generation` after Stage 1 is stable.

### Frame Planning Rule

Before calling `art/keyframe-generation`, define what each frame is supposed to do.

Do not request `first + intermediate + last` only because a shot is long enough.

Use multiple frames only when the shot contains real internal progression:
- a clear action phase change
- a pose change
- an object state change
- a meaningful framing or distance change
- a transition need at the boundary

Default role definitions:
- `first`: opening state of the shot
- `intermediate`: meaningful mid-action or mid-state change
- `last`: ending state or transition-ready boundary state

If the planned frames would look almost the same, reduce frame count instead of keeping duplicates.

### Anti-Duplication Check

Before locking the frame plan, ask:
- does `intermediate` show a real change from `first`
- does `last` create a real end state or transition value
- if one frame were removed, would anything important be lost

If the answer is no, remove that frame from the plan.

Stage 1 should persist this decision as `frame_plan`, so downstream `art/keyframe-generation` receives:
- frame count
- frame type
- frame intent
- expected change focus

## Stage 3: Image Generation

Pass Stage 2 output to `art/keyframe-generation` to generate images.

User review at this stage should check:
- image quality
- character consistency
- scene consistency
- whether repeated frames should be regenerated

## Storage

```text
test-shoots/
  scene_01_stage1.json
  scene_02_stage1.json
  scene_01_stage2.json
  scene_02_stage2.json
  scene_01_images.json
  scene_02_images.json
```

## Downstream

- `art/keyframe-generation`
- later video generation or animation stages
