---
name: character-three-view
description: Generate front, side, and back character sheets, then run a concrete VLM review focused on view correctness, white background, and appearance consistency.
trigger: Call when the user needs a character three-view sheet, unified character appearance design, or a review of front/side/back consistency.
---

# Character Three View

## Knowledge Dependencies

Prioritize:
- `_knowledge/Actor/`: character temperament, body language, silhouette cues
- `_knowledge/Genre/`: costume logic, era fit, and genre-appropriate styling
- `_knowledge/FamousDirectors/`: optional global style tone when the project specifies a director reference
- `_prompts/PromptTemplates/Style/`: reusable style prompt tokens

Use rules:
1. Stay faithful to `characters.json` first, then add style reinforcement.
2. Style references can strengthen visual tone, but must not change the core character setup.
3. Front, side, and back views must describe the same hairstyle, costume set, accessories, and shoes.

## Inputs

Workflow mode:
- `characters.json`
- optional `outline.json` or `visual_style`

Standalone mode:
- a character description from the user
- project type, such as `wuxia`, `fantasy`, `sci-fi`, or `modern`
- optional image size requirements

## Output Contract

Main outputs:
- `front`
- `side`
- `back`
- `review_sheet.png`
- `three-view-review.json`

Review contract files:
- Example: `art/character-three-view/three-view-review.example.json`
- Schema: `art/character-three-view/three-view-review.schema.json`

## Prompt Rules

- All prompts sent into `generation/*` must be in English.
- Always use `full body shot`.
- Always state `front view`, `side view`, or `back view` explicitly.
- Always require `pure white background`.
- Do not use `character sheet` inside the generation prompt.
- Do not rely on stacked negative prompts to force the background.

Prompt template:
```text
[Core Token], full body shot, [view], pure white background, clean white studio background, [subject description], portrait style
```

## Generation Flow

### Step 1: Confirm Style

1. Read `visual_style` if available.
2. Scan `_prompts/PromptTemplates/Style/`.
3. Build one shared Core Token for all three views.

### Step 2: Generate Prompts

Generate prompts first, before image creation.

Hard consistency targets:
- same hairstyle
- same face shape and age impression
- same costume structure
- same accessory placement
- same shoes
- same body proportion
- only the view changes

### Step 3: User Prompt Check

Show the three prompts and wait for confirmation before generating images.

### Step 4: Generate Images

- `front`: `generation/flux-text-to-image`
- `side`: `generation/flux-image-edit`
- `back`: `generation/flux-image-edit`

Recommended naming:
- `characters/[character_name]_[state_num]_front.png`
- `characters/[character_name]_[state_num]_side.png`
- `characters/[character_name]_[state_num]_back.png`

## VLM Review

### Review Purpose

VLM review is for acceptance, not creation.

The review must answer these concrete questions:
- Are all three required views present?
- Are the panels truly front, side, and back?
- Is the background pure white in all three panels?
- Is the hairstyle consistent across all three views?
- Is the clothing design consistent across all three views?
- Are the shoes consistent across all three views?
- Are accessories and body proportions stable enough for downstream use?

### Standard Review Strategy

Because the standard repo usage currently prefers one uploaded image at a time, three-view review must use a composed contact sheet:
1. Combine `front`, `side`, and `back` into one sheet.
2. Fix the order as `front | side | back`.
3. Add visible labels: `front`, `side`, `back`.
4. If the sheet is too large, resize proportionally.
5. Keep the character body and costume details readable after resize.

Recommended size:
- long edge around `1600-2048px`
- keep the white background and full body visible

Recommended output:
- `characters/[character_name]_[state_num]_sheet.png`

### VLM Call

Call:
- `generation/qwen2.5-vl`

Recommended review prompt:
```text
Review this character three-view sheet.
Check:
1. whether the three panels are complete and correctly labeled as front, side, and back,
2. whether every panel uses a pure white background,
3. whether hairstyle is consistent across all three views,
4. whether clothing design is consistent across all three views,
5. whether shoes are consistent across all three views,
6. whether accessories and body proportions remain stable enough for production use.

Return a concise structured review with pass/fail, concrete issues, and fix suggestions.
```

### Review Output

Write the result to:
- `three-view-review.json`

Recommended fields:
- `pass_review`
- `view_coverage`
- `background_check`
- `consistency_score`
- `consistency_checks`
- `issues`
- `strengths`
- `fix_suggestions`

## Review Standard

`pass_review = true` only if all of the following are satisfied:
- front, side, and back are complete
- background is pure white in all three panels
- hairstyle is consistent
- clothing is consistent
- shoes are consistent
- no major accessory drift
- no major body proportion drift

`pass_review = false` if any hard requirement fails.

Priority of regeneration:
1. wrong view
2. non-white background
3. hairstyle drift
4. clothing drift
5. shoe drift
6. accessory or proportion drift

If review fails, regenerate the most problematic panel first, then rebuild the sheet and review again.
