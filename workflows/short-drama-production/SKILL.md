---
name: short-drama-production
description: Master workflow for episodic short-drama production. Reuses the film-production skeleton, but adds ShortDrama knowledge for platform rhythm, hook design, and episode-level cliffhanger control.
trigger: Use when the user wants a vertical short drama, episodic short-form series, or platform-first serial rather than a standalone short film.
---

# Short Drama Production

This workflow is the episodic variant of `film-production`.

It stays structurally close to the film workflow, while adding short-drama-specific controls for:

- platform rhythm
- opening hooks
- episode payoff density
- episode-end cliffhangers
- retention-first pacing

## Workflow Rule

In this standard workflow, all prompts sent into `generation/*` must be in English.

## Relationship To Film Production

This workflow reuses the same backbone as `workflows/film-production`:

1. Requirement Intake
2. Story Outline
3. Character Package
4. Script Writing
5. Storyboard
6. Scene Design
7. Test Shoots
8. Keyframe Generation
9. Generation Assets

The difference is that `short-drama-production` applies `_knowledge/ShortDrama/` as an episodic modifier layer in the writing and pacing stages.

This workflow is the orchestration entry for episodic short-drama production.
It defines stage order, artifact dependencies, and hard gates.
It does not replace Writer, Art, Director, or Generation leaf-skill rules inside the master document.

## Use This When

Use this workflow when:

- the user wants an episodic short drama
- the project is platform-first or vertical-first
- hook retention and episode-end momentum matter as much as visual quality

Do not use this workflow when:

- the user wants a standalone short film
- the user only wants one isolated task

## First Contact

Confirm these project-level inputs first:

- `platform`
- `genre`
- `planned_episode_count`
- `target_episode_duration`
- `core premise`
- `visual_style_reference`
- `director_style_reference`
- `style_intensity`
- `output_goal`
- `model_preference`
- `confirmation_mode`

Short-drama-specific additions:

- `hook_strength`
- `cliffhanger_density`
- `payoff_density`
- `relationship_engine`

Recommended stored artifacts:

- `project_meta.json`
- `user_requirements.json`

## Knowledge Dependencies

### Requirement And Strategy

- `_knowledge/ShortDrama/`
- `_knowledge/Narrative/`
- `_knowledge/Genre/`
- `_knowledge/FamousDirectors/` when needed

### Character Design

- `_knowledge/ShortDrama/`
- `_knowledge/Genre/`
- `_knowledge/Actor/`

### Episode Writing

- `_knowledge/ShortDrama/`
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

- `_prompts/PromptTemplates/Style/`
- `_prompts/PromptTemplates/Camera/`
- `_prompts/ModelGuides/*`

Use prompt assets only after extracting short-drama rhythm and hook strategy.

## Extraction Before Generation

### Before Outline

Extract:

- `platform_mode`
- `genre`
- `structure_pattern`
- `hook_strategy`
- `cliffhanger_pattern`
- `payoff_schedule`
- `director_style_reference`
- `style_intensity`

### Before Character Package

Extract:

- `role_archetype`
- `relationship_signal`
- `body_language`
- `costume_anchor`
- `relationship_engine`

### Before Episode Scripts

Extract:

- `episode_engine`
- `opening_hook`
- `payoff_beats`
- `ending_hook`
- `dialogue_goal`
- `subtext_pattern`

### Before Storyboard

Extract:

- `shot_function`
- `beat_structure`
- `hook_emphasis`
- `transition_need`
- `environment_anchor_plan`

## Workflow Stages

### Stage 1: Requirement Intake

Goal:

- lock platform, format, pacing expectation, and target output

Dependencies:

- `_knowledge/ShortDrama/`
- `_knowledge/Narrative/`

Outputs:

- `project_meta.json`
- `user_requirements.json`

### Stage 2: Story Strategy And Outline

Primary skill:

- `writer/story-outline`

Goal:

- build the season-level or project-level outline with strong short-drama hook logic

Dependencies:

- `_knowledge/ShortDrama/`
- `_knowledge/Narrative/`
- `_knowledge/Genre/`
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

- define characters that can support fast relational escalation and visual recall

Dependencies:

- `_knowledge/ShortDrama/`
- `_knowledge/Genre/`
- `_knowledge/Actor/`
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

Review artifact:

- `art/character-three-view/three-view-review.example.json`
- `art/character-three-view/three-view-review.schema.json`

### Stage 4: Episode Scripts

Primary skill:

- `writer/script-writing`

Goal:

- split the project into episode-level scripts with hook, escalation, payoff, and ending retention

Dependencies:

- `_knowledge/ShortDrama/`
- `_knowledge/Narrative/`
- `_knowledge/Dialogue/`
- `_knowledge/Genre/`
- `_knowledge/Actor/`

Outputs:

- `episodes/`

Contracts:

- `writer/script-writing/episode.example.json`
- `writer/script-writing/episode.schema.json`

### Stage 5: Storyboard

Primary skills:

- `director/storyboard`
- `director/transition` when a boundary needs explicit transition design

Goal:

- convert episodes into high-density, hook-aware shot structure while preserving the same storyboard logic used in film production

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

Review artifact:

- `director/storyboard/storyboard-review.example.json`
- `director/storyboard/storyboard-review.schema.json`

### Stage 6: Scene Design

Primary skill:

- `art/scene-design`

Goal:

- create stable scene bases and view sets for recurring episode spaces

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

Review artifact:

- `art/scene-design/scene-review.example.json`
- `art/scene-design/scene-review.schema.json`

### Stage 7: Test Shoots

Primary skills:

- `director/test-shoots`
- `director/transition` when frame planning depends on transition complexity

Goal:

- create shot prompts and frame plans that preserve hook moments and episode-end impact

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

- generate reviewable keyframes for the most important beats, hooks, reversals, and ending moments

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

- execute asset generation and visual analysis after the creative decisions are already locked upstream

## VLM Assist Points

Use `generation/qwen2.5-vl` as a review and analysis helper at these points:

- character sheet review
- scene board review
- transition boundary review
- hook-frame and ending-frame inspection

## Early Exit Rules

Valid completion points:

- after `outline.json`
- after `characters.json` and character views
- after `episodes/`
- after `storyboard.json`
- after `scene_design.json`
- after `test-shoots.json`
- after reviewed `keyframes/`

## Intermediate Artifact Recovery

- `outline.json` -> continue to character package or episode scripts
- `characters.json` -> continue to episode scripts or character views
- `episodes/episode_01.json` -> continue to storyboard
- `storyboard.json` -> continue to scene design or test shoots
- `test-shoots.json` -> continue to keyframe generation

## Artifact Layout

```text
memory/[date]/[project-name]/v[version]/
|- project_meta.json
|- user_requirements.json
|- outline.json
|- characters.json
|- characters/
|- episodes/
|  |- episode_01.json
|  `- ...
|- storyboard.json
|- storyboard-review.json
|- scene_design.json
|- scene-review.json
|- scenes/
|- test-shoots.json
|- keyframe-prompts.json
|- keyframe-images.json
|- keyframe-review.json
`- keyframes/
```

## Orchestration Rules

1. Keep the same backbone as `film-production`.
2. Use `_knowledge/ShortDrama/` to modify pacing and retention logic, not to replace the whole system.
3. Run review before handing critical artifacts downstream.
4. Prefer hook clarity and payoff readability before adding shot complexity.
5. Let Writer, Art, and Director make the creative decisions; let Generation execute and review.

## Example Flow

1. User asks for a 20-episode vertical comeback drama with Douyin pacing and a keyframe-first target.
2. The workflow confirms platform, episode count, episode duration, hook strength, and output target.
3. The workflow runs the same backbone as `film-production`, but injects `_knowledge/ShortDrama/` into outline, character, and episode-writing stages first.
