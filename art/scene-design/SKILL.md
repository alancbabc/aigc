---
name: scene-design
description: Generate scene-level environment reference sets from storyboard or standalone scene briefs. In workflow mode, build a stable scene base first, then add multi-view references when shot differences are large.
trigger: Call when the project needs environment reference images, scene boards, or scene design support for storyboard-driven production.
---

# Scene Design

## What This Skill Does

This skill generates **scene-level environment references**, not final character keyframes.

It is responsible for:
- extracting stable environment information for each scene
- defining one reusable **scene base**
- generating one or more **view-specific reference images** under the same scene setup
- supporting downstream consistency for `director/test-shoots` and `art/keyframe-generation`

It is not responsible for:
- replacing `director/storyboard` shot design
- generating character-action keyframes directly
- making every shot into an independent environment redesign

## Knowledge Dependencies

Prioritize:
- `_knowledge/VisualEnvironment/`: space, lighting, weather, material, environmental motion
- `_knowledge/FamousDirectors/`: optional tone and stylistic pressure
- `_knowledge/Genre/`: setting logic, era feel, and genre atmosphere
- `_prompts/PromptTemplates/Style/`: shared style prompt tokens

Use rules:
1. Follow storyboard `environment` first, then enrich visual detail.
2. Style should reinforce the setup, not replace it.
3. Environment references should optimize downstream consistency before visual flourish.

## Inputs

Workflow mode:
- `storyboard.json`
- optional `outline.json` or `visual_style`

Standalone mode:
- a scene description from the user
- optional output size requirements
- optional request for single-view or multi-view references

## Core Design Decision

This skill works in two layers:

### Layer 1: Scene Base

Define the stable environment for the whole scene:
- location and spatial structure
- time of day
- lighting direction and quality
- material and texture
- anchor props or landmarks
- atmosphere
- palette and style cues

This answers:
`What does this scene fundamentally look like?`

### Layer 2: View Set

Generate one or more environment references for the same scene base:
- `establishing`
- `medium_environment`
- `close_detail`
- `reverse_angle`
- `entrance_view`

This answers:
`From which angles or distances will this scene need to be seen?`

## View Planning Rule

Do **not** generate one unrelated image per shot by default.

Instead:
1. build one stable scene base
2. inspect shot differences inside the same scene
3. generate a small multi-view set only when the storyboard really needs it

### Use one main reference only when:

- the scene has only one shot
- multiple shots stay close in angle and scale
- the scene only needs a broad environment mood reference

### Generate a multi-view set when:

- the same scene includes both wide or medium shots and close shots
- downstream work needs both space layout and local detail
- the storyboard includes reverse angles, entrance views, or large perspective shifts
- the scene will be reused across multiple shots and must stay visually stable

## Workflow Mode

When input comes from `storyboard.json`:

- always extract one `scene_base`
- default to at least one `establishing` reference
- add more view references when shot differences are large

Typical workflow output for one scene:
- `establishing`: for overall space, layout, and atmosphere
- `medium_environment`: for character-environment relationship
- `close_detail`: for local texture, props, window, wall, table, doorway, or lighting detail

## Standalone Mode

When the user independently asks to design a scene:

- generate one scene base first
- generate 1-3 references depending on the request
- do not force a fixed three-angle pattern

## Prompt Rules

- All prompts sent into `generation/*` must be in English.
- Prefer environment-led prompts over character-led prompts.
- Default to `empty scene` or equivalent environment wording unless the task explicitly needs people as scale reference.
- Prompt content should come from:
  - `scene_base.setting`
  - `scene_base.lighting`
  - `scene_base.anchor_elements`
  - style Core Token

Recommended template:
```text
[Core Token], [view_type], empty scene, no people, [setting], [lighting], [anchor elements], [atmosphere]
```

## Generation Flow

### Step 1: Confirm Style

1. Read `visual_style` if available.
2. Scan `_prompts/PromptTemplates/Style/`.
3. Keep the style aligned with character design and project tone.

### Step 2: Read Scene-Level Environment

From `storyboard.json`, prioritize:
- `environment.setting`
- `environment.lighting`
- `environment.dynamic_elements`
- `summary`

Use `shots[]` as a **view-planning source**, not as the primary environment source.

This means:
- `shot.camera_angle`
- `shot.shot_type`
- `shot.description`

should help decide how many references are needed, but should not cause the scene to drift into unrelated environments.

### Step 3: Build Scene Base

For each scene, first create a stable shared design base:
- scene identity
- spatial layout
- main props and landmarks
- lighting logic
- palette and atmosphere

### Step 4: Plan the View Set

Inspect all shots within the same scene.

If shot differences are large, add view-specific references such as:
- `establishing`
- `medium_environment`
- `close_detail`
- `reverse_angle`
- `entrance_view`

If shot differences are small, keep only the main reference plus at most one support reference.

### Step 5: Generate Images

Prefer:
- `generation/flux-text-to-image`

When only a light variation of an existing scene image is needed:
- `generation/flux-image-edit`

## Output Contract

Main outputs:
- `scene_design.json`
- scene reference image files
- `scene-board.png`
- `scene-review.json`

Recommended `scene_design.json` structure:
```json
{
  "project_title": "Project Title",
  "style": "Core style tokens",
  "scenes": [
    {
      "scene_no": 1,
      "scene_base": {
        "location": "Old apartment corridor",
        "environment_summary": "A narrow old corridor with warm practical light, metal doors, and humid night air",
        "lighting": "warm tungsten practical light with dim spill into the hallway",
        "anchor_elements": [
          "narrow corridor",
          "metal door",
          "window grill",
          "aged wall texture"
        ],
        "atmosphere": "quiet, humid, slightly lonely"
      },
      "reference_images": [
        {
          "ref_num": 1,
          "view_type": "establishing",
          "purpose": "show full corridor layout and emotional atmosphere",
          "prompt": "Core style token, establishing view, empty scene, no people, old apartment corridor, warm tungsten light, narrow hallway, metal doors, window grill, aged wall texture, humid quiet night",
          "image_path": "scene-design/scene_01_establishing.png"
        },
        {
          "ref_num": 2,
          "view_type": "close_detail",
          "purpose": "show doorway texture, wall detail, and lamp glow for close shots",
          "prompt": "Core style token, close detail environment view, empty scene, no people, old apartment doorway, warm practical light, aged wall texture, window reflection, humid quiet night",
          "image_path": "scene-design/scene_01_close_detail.png"
        }
      ]
    }
  ]
}
```

Review contract files:
- Example: `art/scene-design/scene-review.example.json`
- Schema: `art/scene-design/scene-review.schema.json`

Scene design contract files:
- Example: `art/scene-design/scene-design.example.json`
- Schema: `art/scene-design/scene-design.schema.json`

## VLM Review

### Review Purpose

VLM review is for acceptance only.

It should check:
- whether the environment matches the intended scene setup
- whether lighting and time-of-day feel correct
- whether the style is consistent with the project
- whether the multi-view references still belong to the same scene base
- whether the different reference views are complementary rather than duplicated
- whether any unwanted people or distracting elements appear
- whether the references are clear enough for downstream use

### Standard Review Strategy

If one scene has only one reference image:
- send the single image to `generation/qwen2.5-vl`

If one scene has multiple references:
- compose a `scene board`
- then send the board to VLM

Board rules:
1. arrange references in a fixed order
2. label each sub-image, such as `establishing`, `medium_environment`, `close_detail`
3. resize proportionally if needed
4. keep environment details readable

Recommended size:
- long edge around `1600-2048px`

Recommended board output:
- `scene-design/scene_01_board.png`

### VLM Call

Call:
- `generation/qwen2.5-vl`

Recommended review prompt:
```text
Review this scene design image or scene board.
Check whether the environment matches the intended setting, lighting, time of day, and atmosphere.
Check whether all views still belong to the same scene base.
If there are multiple views, check whether each view serves a distinct purpose such as establishing, medium environment, close detail, reverse angle, or entrance view.
Check whether repeated anchor elements, lighting logic, and material cues remain consistent across all views.
Check whether the style is consistent with the project.
Check whether any unwanted people or distracting elements appear.
Return a concise structured review.
```

### Review Output

Write the review result to:
- `scene-review.json`

Recommended fields:
- `scene_no`
- `review_image`
- `review_mode`
- `reference_count`
- `pass_review`
- `setting_match`
- `lighting_match`
- `scene_base_consistency`
- `view_set_quality`
- `style_consistency_score`
- `issues`
- `strengths`
- `fix_suggestions`

## Review Standard

- `pass_review = true`: safe to continue into `director/test-shoots` and `art/keyframe-generation`
- `pass_review = false`: regenerate the most problematic reference first, then rebuild the board and review again

### Single-Reference Standard

For a single scene reference, require:
- `setting_match = true`
- `lighting_match = true`
- no unwanted subject pollution
- style and readability are good enough for downstream use

### Multi-View Standard

For a scene board or multi-view set, require:
- `setting_match = true`
- `lighting_match = true`
- `scene_base_consistency = true`
- `view_set_quality = true`
- all views clearly belong to the same environment identity
- anchor elements, material cues, and lighting logic remain stable across views
- the set includes meaningful view variation instead of near-duplicate images
- no unwanted subject pollution

If the scene uses multiple references, consistency becomes a hard review gate, not just a bonus check.

Key checks:
- environment setting match
- lighting and time match
- scene-base consistency across views
- multi-view usefulness and non-duplication
- no unwanted character subject pollution
- clarity and downstream usability
