---
name: film-production
description: Master workflow for short-film and narrative film production. Orchestrates Writer, Art, Director, and Generation skills from idea intake to reviewed keyframe assets and optional LTX video assets.
trigger: Use when the user wants an end-to-end short film, micro-film, or narrative visual project rather than a single isolated task.
---

# Film Production

## Overview

This is the master workflow for standard short-film production inside this repo.

It is responsible for:

- turning user intent into staged production tasks
- routing work to the correct leaf skills
- enforcing artifact contracts
- applying knowledge extraction before generation
- running review passes before downstream stages continue

This workflow is the orchestration entry for standard film production.
It defines stage order, artifact dependencies, and hard gates.
It does not replace Writer, Art, Director, or Generation leaf-skill rules inside the master document.

## Inputs

- the user's project goal, genre, target duration, style references, and output goal
- optional intermediate artifacts such as `outline.json`, `script.json`, or `storyboard.json`
- optional model preferences and confirmation preferences

## Outputs

- one or more stage artifacts, depending on where the user wants to stop
- common artifacts include:
  - `project_meta.json`
  - `user_requirements.json`
  - `outline.json`
  - `characters.json`
  - `script.json`
  - `storyboard.json`
  - `scene_design.json`
  - `test-shoots.json`
  - `keyframe-prompts.json`
  - `keyframe-images.json`
  - `keyframes/`
  - `video-prompt-drafts.json`
  - `video-ltx-prompts.json`
  - `video-plan.json`
  - `video-assets.json`
  - `video-assets/`

The workflow's done condition depends on the user-requested stopping stage.

## Workflow Rules

### Prompt Language Rule

In this standard workflow, all prompts sent into `generation/*` must be in English.

Some models may support Chinese natively, but the workflow default stays English for cross-model consistency.

### Use This Workflow When

Use this workflow when:

- the user wants an end-to-end film pipeline
- the user does not already have a complete nearby intermediate artifact
- the task spans multiple stages across writing, directing, art, and generation

Do not use this workflow when:

- the user only wants one isolated task
- the user already has a valid intermediate artifact and only wants to continue from there

### First Contact

Confirm these project-level inputs first:

- `genre`
- `target_duration`
- `core_premise`
- `visual_style_reference`
- `director_style_reference`
- `style_intensity`
- `output_goal`
- `model_preference`
- `confirmation_mode`

Recommended stored artifacts:

- `project_meta.json`
- `user_requirements.json`

## Knowledge Dependencies

Read by stage, not all at once.

### Requirement And Strategy

- `_knowledge/Genre/`
- `_knowledge/Narrative/`
- `_knowledge/FamousDirectors/` when a style reference exists

### Character Design

- `_knowledge/Genre/`
- `_knowledge/Actor/`
- `_knowledge/FamousDirectors/` when a style reference exists

### Script And Dialogue

- `_knowledge/Narrative/`
- `_knowledge/Dialogue/`
- `_knowledge/Actor/`

### Storyboard And Direction

- `_knowledge/Camera/`
- `_knowledge/Narrative/`
- `_knowledge/Transition/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`

### Scene And Keyframe Planning

- `_knowledge/Camera/`
- `_knowledge/Transition/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`

## Prompt Dependencies

Use prompt assets only after concept and rule extraction:

- `_prompts/PromptTemplates/Style/`
- `_prompts/PromptTemplates/Camera/`
- `_prompts/ModelGuides/*`

Principles:

1. Extract rules from `_knowledge` first.
2. Use `_prompts` to translate those rules into model-friendly wording.
3. Read `ModelGuides` only when a specific model is selected.

## Extraction Before Generation

Before downstream artifact generation, extract the decision layer first.

### Before Outline

Extract:

- `genre`
- `tone`
- `structure_pattern`
- `rhythm_goal`
- `director_style_reference`
- `style_intensity`

### Before Character Package

Extract:

- `role_archetype`
- `relationship_signal`
- `body_language`
- `costume_anchor`

### Before Script

Extract:

- `scene_engine`
- `dialogue_goal`
- `power_balance`
- `subtext_pattern`

### Before Storyboard

Extract:

- `shot_function`
- `beat_structure`
- `transition_need`
- `environment_anchor_plan`

These extraction results may live inside stage artifacts or intermediate planning notes, but they must exist before downstream production.

## Workflow Stages

### Stage 1: Requirement Intake

Goal:

- lock project scope, style direction, and completion target

Dependencies:

- `_knowledge/Genre/`
- `_knowledge/Narrative/`
- `_knowledge/FamousDirectors/` when needed

Outputs:

- `project_meta.json`
- `user_requirements.json`

### Stage 2: Story Strategy And Outline

Primary skill:

- `writer/story-outline`

Goal:

- build story structure, central conflict, tone, and scene progression

Dependencies:

- `_knowledge/Genre/`
- `_knowledge/Narrative/`
- `_knowledge/FamousDirectors/`

Outputs:

- `outline.json`

Contracts:

- `writer/story-outline/outline.example.json`
- `writer/story-outline/outline.schema.json`

### Stage 3: Character Package

Primary skills:

- `writer/character-profile`
- `art/character-three-view`

Goal:

- define characters in writing and produce usable character visual references

Dependencies:

- `_knowledge/Genre/`
- `_knowledge/Actor/`
- `_knowledge/FamousDirectors/`
- `_prompts/PromptTemplates/Style/`

Outputs:

- `characters.json`
- `characters/`

Contracts:

- `writer/character-profile/characters.example.json`
- `writer/character-profile/characters.schema.json`

### Stage 3A: Character Review

Primary review skill path:

- `art/character-three-view`
- `generation/qwen2.5-vl` as review support

Goal:

- verify three-view completeness and character consistency before script and storyboard depend on them

Review artifact:

- `art/character-three-view/three-view-review.example.json`
- `art/character-three-view/three-view-review.schema.json`

### Stage 4: Script Writing

Primary skill:

- `writer/script-writing`

Goal:

- expand the outline and character package into a full script

Dependencies:

- `_knowledge/Narrative/`
- `_knowledge/Dialogue/`
- `_knowledge/Genre/`
- `_knowledge/Actor/`

Outputs:

- `script.json`

Contracts:

- `writer/script-writing/script.example.json`
- `writer/script-writing/script.schema.json`

### Stage 5: Storyboard

Primary skills:

- `director/storyboard`
- `director/transition` when a boundary needs explicit transition design

Goal:

- convert the script into narrative beats, shots, camera language, environment logic, and transition planning

Dependencies:

- `_knowledge/Camera/`
- `_knowledge/Narrative/`
- `_knowledge/Transition/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`

Outputs:

- `storyboard.json`

Contracts:

- `director/storyboard/storyboard.example.json`
- `director/storyboard/storyboard.schema.json`

### Stage 5A: Storyboard Review

Goal:

- remove redundant shots
- fix unsupported durations
- catch weak beat separation before scene-design and test-shoot stages

Review artifact:

- `director/storyboard/storyboard-review.example.json`
- `director/storyboard/storyboard-review.schema.json`

### Stage 6: Scene Design

Primary skill:

- `art/scene-design`

Goal:

- create a `scene base` and, when needed, a `multi-view set` for each scene

Dependencies:

- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`
- `_knowledge/Genre/`
- `_prompts/PromptTemplates/Style/`

Outputs:

- `scene_design.json`
- `scenes/`

Contracts:

- `art/scene-design/scene-design.example.json`
- `art/scene-design/scene-design.schema.json`

### Stage 6A: Scene Review

Goal:

- verify environment identity, lighting logic, anchor consistency, and multi-view stability

Review artifact:

- `art/scene-design/scene-review.example.json`
- `art/scene-design/scene-review.schema.json`

### Stage 7: Test Shoots

Primary skills:

- `director/test-shoots`
- `director/transition` when frame planning depends on transition complexity

Goal:

- convert the storyboard into shot prompts, frame plans, and transition-aware boundary planning

Dependencies:

- `_knowledge/Camera/`
- `_knowledge/Transition/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`
- `_prompts/PromptTemplates/Camera/`
- `_prompts/PromptTemplates/Style/`

Outputs:

- `test-shoots.json`

Contracts:

- `director/test-shoots/test-shoots.example.json`
- `director/test-shoots/test-shoots.schema.json`

### Stage 8: Keyframe Planning And Generation

Primary skill:

- `art/keyframe-generation`

Goal:

- generate frame prompts and frame images that preserve progression, character consistency, and scene consistency

Outputs:

- `keyframe-prompts.json`
- `keyframe-images.json`
- `keyframes/`

Contracts:

- `art/keyframe-generation/keyframe-prompts.example.json`
- `art/keyframe-generation/keyframe-prompts.schema.json`
- `art/keyframe-generation/keyframe-images.example.json`
- `art/keyframe-generation/keyframe-images.schema.json`

### Stage 8A: Keyframe Review

Goal:

- verify frame progression
- verify intent alignment
- verify character consistency
- verify scene consistency

Review artifact:

- `art/keyframe-generation/keyframe-review.example.json`
- `art/keyframe-generation/keyframe-review.schema.json`

### Stage 9: Generation Assets

Primary skills:

- `generation/flux-text-to-image`
- `generation/flux-image-edit`
- `generation/qwen-image-2512`
- `generation/qwen2.5-vl`

Goal:

- execute image generation, image editing, and visual analysis
- prepare assets for downstream human editing or direct handoff into the LTX video stage

Important boundary:

- `generation/*` is the execution layer, not the high-level creative decision layer
- VLM should be used as analysis and review support, not as a replacement for Writer, Art, or Director decisions

### Stage 9A: LTX Video Planning

Primary skill:

- `generation/ltx23-video`

Goal:

- convert reviewed keyframe outputs into raw video prompt drafts and then into a minimal, executable video generation plan
- decide whether each scene or shot should use `audio_to_video` or `text_image_to_video_high_quality`
- keep this stage focused on video asset generation, not final assembly

Prompt handling requirement:

- first write the original per-shot or per-scene prompts to `video-prompt-drafts.json`
- then optimize those prompts using `_prompts/ModelGuides/LTX-Video/SKILL.md` and write the results to `video-ltx-prompts.json`
- do not overwrite the raw prompt drafts; keep both artifacts as first-class outputs
- `video-plan.json` should reference the optimized prompt entries used for final execution
- if a scene boundary uses `CUT`, do not create a standalone transition clip entry
- if a scene boundary uses a non-`CUT` transition, call `director/transition` and persist a separate `clip_type=transition` entry that references the previous shot tail frame and next shot head frame

Routing rules:

- start from reviewed `keyframe-images.json` and `keyframes/`, not from raw storyboard ideas alone
- prefer `text_image_to_video_high_quality` when the user only wants visual motion from keyframes
- prefer `audio_to_video` only when the project already has valid audio inputs for the target shot or scene
- if a shot has multiple keyframes, use them as ordered reference images and keep the prompt aligned with approved shot intent
- if the project lacks the required audio for `audio_to_video`, do not invent a dubbing pipeline here; route that shot back to image-driven video or stop at planning
- before any `ltx23-video` request is finalized, pass the raw prompt through the LTX prompt guide so the execution prompt is explicitly optimized for LTX-2
- for non-`CUT` scene or shot boundaries, let `director/transition` design the bridge clip; the workflow should consume that result instead of improvising transition logic locally

Outputs:

- `video-prompt-drafts.json`
- `video-ltx-prompts.json`
- `video-plan.json`

Contracts:

- `workflows/film-production/contracts/video-prompt-drafts/video-prompt-drafts.schema.json`
- `workflows/film-production/contracts/video-prompt-drafts/video-prompt-drafts.example.json`
- `workflows/film-production/contracts/video-ltx-prompts/video-ltx-prompts.schema.json`
- `workflows/film-production/contracts/video-ltx-prompts/video-ltx-prompts.example.json`
- `generation/ltx23-video/ltx23-video.schema.json`
- `generation/ltx23-video/ltx23-video.example.json`
- `generation/ltx23-video/ltx23-video-hq.example.json`
- `_prompts/ModelGuides/LTX-Video/SKILL.md`

### Stage 9B: LTX Video Asset Generation

Primary skill:

- `generation/ltx23-video`

Goal:

- execute the per-shot or per-scene LTX requests defined in `video-plan.json`
- generate reusable video assets without expanding the workflow into final edit, subtitle, dubbing, or delivery packaging

Outputs:

- `video-assets.json`
- `video-assets/`

Asset expectations:

- each video asset should map back to a specific `scene_id`, `shot_id`, or equivalent stable upstream identifier
- each asset entry should record the chosen LTX mode, input image paths, output video path, and generation status
- each asset entry should preserve references to both the raw prompt draft and the optimized LTX prompt used for execution
- output paths should stay inside the project memory tree, for example `video-assets/scene_01_shot_03.mp4`
- transition assets should be stored as standalone clips between neighboring shot clips rather than hidden inside a normal shot asset when `transition_type != CUT`

### Stage 9C: Video Asset Review

Goal:

- verify that generated video assets preserve keyframe intent, scene identity, and shot-level motion direction
- catch obvious failures before the user treats the assets as approved downstream material

Review focus:

- motion should extend the approved keyframe progression rather than replace it with unrelated action
- character identity, costume anchor, and environment anchor should remain consistent with reviewed upstream assets
- if the generated clip materially breaks shot intent, revise the raw prompt draft and regenerate the optimized LTX prompt rather than silently accepting drift

## Contracts And Artifact Rules

### VLM Assist Points

Use `generation/qwen2.5-vl` as a review and analysis helper at these points:

- three-view sheet review
- scene board review
- boundary-frame analysis for transition decisions
- keyframe review support when a single composed board is easier to inspect than separate frames

### Early Exit Rules

This workflow does not need to run to the end if the user only wants a partial result.

Valid completion points:

- after `outline.json`
- after `characters.json` and character views
- after `script.json`
- after `storyboard.json`
- after `scene_design.json`
- after `test-shoots.json`
- after reviewed `keyframes/`
- after `video-prompt-drafts.json`
- after `video-ltx-prompts.json`
- after `video-plan.json`
- after reviewed `video-assets/`

### Intermediate Artifact Recovery

If the user provides an existing artifact, resume from the nearest valid stage:

- `outline.json` -> continue to character package or script
- `characters.json` -> continue to script, storyboard, or character views
- `script.json` -> continue to storyboard
- `storyboard.json` -> continue to scene design or test shoots
- `test-shoots.json` -> continue to keyframe generation
- `keyframe-images.json` -> continue to video prompt drafting, prompt optimization, video planning, or video asset generation
- `video-prompt-drafts.json` -> continue to LTX prompt optimization or video planning
- `video-ltx-prompts.json` -> continue to video planning or video asset generation
- `video-plan.json` -> continue to video asset generation

Do not rerun earlier stages unless the user asks for revision.

### Artifact Layout

```text
memory/[date]/[project-name]/v[version]/
├── project_meta.json
├── user_requirements.json
├── outline.json
├── characters.json
├── characters/
├── script.json
├── storyboard.json
├── storyboard-review.json
├── scene_design.json
├── scene-review.json
├── scenes/
├── test-shoots.json
├── keyframe-prompts.json
├── keyframe-images.json
├── keyframe-review.json
├── keyframes/
├── video-prompt-drafts.json
├── video-ltx-prompts.json
├── video-plan.json
├── video-assets.json
└── video-assets/
```

### Orchestration Rules

1. Read the current stage contract before generating output.
2. Run review before handing critical artifacts to the next downstream stage.
3. Move one stage at a time unless the user explicitly wants batching.
4. If the user only wants a local goal, stop at the nearest valid early-exit stage.
5. Let Writer, Art, and Director make the creative decisions; let Generation execute and review.
6. Do not auto-expand this workflow from video asset generation into final edit or delivery assembly unless the user explicitly asks for that larger scope.
7. For advanced transitions, workflow routing should defer to `director/transition`; do not let the master workflow invent bridge prompts on its own.

## Example Flow

### Keyframe-Only Output

1. The user asks for a 5-minute wuxia short film with Tsui Hark influence and a keyframe-only output goal.
2. The workflow confirms `genre`, `target_duration`, `director_style_reference`, `style_intensity`, and `output_goal`.
3. The workflow runs:
   - `writer/story-outline`
   - `writer/character-profile`
   - `art/character-three-view`
   - character review
   - `writer/script-writing`
   - `director/storyboard`
   - storyboard review
   - `art/scene-design`
   - scene review
   - `director/test-shoots`
   - `art/keyframe-generation`
   - keyframe review
4. Because the requested output goal is keyframes, the workflow can stop there without entering a later video pipeline.

### LTX Video Asset Output

1. The user asks for a short narrative film and wants scene-level video assets after keyframe approval.
2. The workflow runs through outline, character package, script, storyboard, scene design, test shoots, keyframe generation, and keyframe review.
3. After keyframes are approved, the workflow creates `video-prompt-drafts.json`, then optimizes them into `video-ltx-prompts.json`, and then creates `video-plan.json`.
4. For each planned scene or shot:
   - use `text_image_to_video_high_quality` when the job is to animate approved keyframes into a short visual clip
   - use `audio_to_video` only when valid audio already exists and the user explicitly wants that mode
   - if the boundary is `CUT`, connect neighboring shot clips directly without a standalone transition clip
   - if the boundary is not `CUT`, call `director/transition` and create a standalone transition clip from the previous shot tail frame and next shot head frame
5. The workflow generates `video-assets/*.mp4`, writes `video-assets.json`, runs a video asset review, and keeps both the original and optimized prompt JSON artifacts for later reuse or audit.

## Changelog

- 2026-04-01: Rewritten into English-first format and aligned with workflow-boundary style used across the repo.
- 2026-03-31: Extended workflow beyond reviewed keyframes with minimal LTX video planning, generation, and review stages.
- 2026-03-24: Aligned to the repository template and added standard overview, inputs, outputs, dependencies, rules, workflow, contracts, and example sections.
