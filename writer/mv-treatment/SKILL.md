---
name: mv-treatment
description: Generates a creative treatment for a music video, mapping song structure and lyrics into a unified visual concept with per-section plans, aligned with mv-global-visual-style.
trigger: Use when the user needs an MV concept, treatment, or creative direction document based on a song, section timeline, and global visual lock.
---

# MV Treatment

## Overview

This skill turns song structure (line timings + sections) and global visual style lock into a creative treatment document that defines the overall MV concept, visual style, color strategy, and per-section visual plans. Lyrical imagery is read directly from lyric lines grouped by sections (no standalone `lyrics-analysis.json`).

It is responsible for:

- deciding the MV concept type (narrative, performance, concept, or mixed)
- establishing a unified visual style and color palette
- mapping each song section to a visual world with specific content plans
- defining cross-cutting rules when multiple visual threads coexist
- providing enough creative direction for downstream storyboard and scene design

It is not responsible for:

- analyzing the song structure (that belongs to Stage 1 of the workflow)
- authoring a standalone lyrics-imagery JSON artifact (workflow uses lyric lines + `mv-global-visual-style.json` instead)
- detailed shot-level planning (that belongs to `director/storyboard`)
- scene reference image generation (that belongs to `art/scene-design`)
- character visual design (that belongs to `art/character-three-view`)

## Inputs

- Required: **`lyrics-timing.json`** + **`song-sections-llm.json`** from Stage 1 (section timeline; derive windows from **`line_refs`** + line timings)
- Required: **`mv-global-visual-style.json`** from Stage 2
- Required: `user_requirements.json` with `mv_type` and style preferences
- Optional: **`mv-keyframe-director.json`** (director keyframe / I2V prompt plan — align treatment with established beats when present)
- Optional: legacy consolidated **`song-structure.json`** where the pipeline still emits it (same fields consumed as before where applicable)
- Optional: user-provided visual references, mood boards, or reference MV links
- Optional: `project_meta.json` with director style reference

## Outputs

- Primary output: `mv-treatment.json`
- Done condition: a treatment document that covers every song section with actionable visual direction

## Dependencies

### Knowledge Dependencies

Read before generating the treatment:

- `_knowledge/Genre/` — map the musical genre to visual conventions
- `_knowledge/Narrative/` — story structure patterns for narrative MVs
- `_knowledge/FamousDirectors/` — when a director style reference exists
- `_knowledge/Actor/` — performance archetypes and blocking patterns
- `_knowledge/VisualEnvironment/` — environment and atmosphere vocabulary

### Prompt Dependencies

Read during treatment writing:

- `_prompts/PromptTemplates/Style/` — vetted English style tokens for visual_style field

### Tools

No external API calls. This skill produces a planning document only.

## Rules

1. The treatment must reference every **`section_id`** from **`song-sections-llm.json`**. No section may be left without a visual plan.
2. The `concept_type` must align with `user_requirements.json`. If the user specified `narrative`, do not produce a pure performance treatment.
3. All style keywords in `visual_style.style_keywords` must be in English, aligned with `_prompts/PromptTemplates/Style/`.
4. For narrative MVs, the `narrative_thread` must have a clear premise, protagonist, conflict, and resolution.
5. For performance MVs, the `performance_plan` must specify the performance style and camera strategy.
6. For mixed MVs, `cross_cutting_rules` must define how narrative and performance threads interleave.
7. The treatment must respect the song's energy arc: high-energy sections get visually dynamic plans, low-energy sections get intimate or still plans.
8. Color palette shifts must be motivated by emotional changes in the song, not arbitrary.
9. Do not over-prescribe shot-level details. Keep visual descriptions at the section level. Shot-level decisions belong to `director/storyboard`.
10. Each `section_plan` must include a `transition_strategy` that explains how it connects to the next section.

## Workflow

### For Narrative MV

1. Read **`lyrics-timing.json`**, **`song-sections-llm.json`**, and **`mv-global-visual-style.json`**. Optionally read **`mv-keyframe-director.json`** if present.
2. From lyric lines grouped by **`line_refs`** per section, infer narrative potential / dominant imagery (themes, metaphors).
3. Read `_knowledge/Narrative/` for story structure patterns.
4. Read `_knowledge/Genre/` for the musical genre's visual conventions.
5. Draft the `narrative_thread` (premise, protagonist, conflict, resolution, timeline structure).
6. Decide `visual_style` using `_prompts/PromptTemplates/Style/` tokens.
7. Assign each song section to a visual world and primary content type.
8. Define `cross_cutting_rules` if the MV intercuts between timelines or worlds.
9. Write `color_palette` with a clear shift strategy that follows the emotion arc.
10. Produce `mv-treatment.json`.

### For Performance MV

1. Read **`lyrics-timing.json`**, **`song-sections-llm.json`**, **`mv-global-visual-style.json`**.
2. Read `_knowledge/Actor/` for performance archetypes and blocking.
3. Draft `performance_plan` with style, stage description, and camera strategy.
4. Decide `visual_style` and `color_palette`.
5. Assign each song section to a visual world focused on performance staging.
6. Produce `mv-treatment.json` with `narrative_thread` set to null.

### For Concept MV

1. Read **`lyrics-timing.json`**, **`song-sections-llm.json`**, **`mv-global-visual-style.json`**.
2. Treat recurring lyric images and **`core_visual_motifs`** from `mv-global-visual-style` as the primary creative material.
3. Build a visual metaphor sequence that evolves across the song.
4. Each section plan uses `concept_imagery` as the primary content type.
5. Produce `mv-treatment.json` with both `narrative_thread` and `performance_plan` set to null.

### For Mixed MV

1. Follow the narrative flow but add a `performance_plan` for performance segments.
2. Define `cross_cutting_rules` that govern when to cut between narrative, performance, and concept footage.
3. Typically: verses carry narrative, choruses carry performance or visual climax, bridge carries concept imagery or turning point.

## Contracts

- Primary artifact: `mv-treatment.json`
- Schema: `workflows/mv-production/contracts/mv-treatment/mv-treatment.schema.json`
- Example: `workflows/mv-production/contracts/mv-treatment/mv-treatment.example.json`

## Example

```text
Input:
  - lyrics-timing + song-sections-llm: "夜曲" by 周杰伦, 245s, 8 sections (line-level times)
  - mv-global-visual-style.json: motifs + verse/chorus structural rules
  - user_requirements.json: mv_type = narrative, style = neo-noir cinematic

Processing:
  1. Extract narrative thread from grouped lyric text + motifs
  2. Map visual worlds to song sections (rain city → warm apartment → dawn rooftop)
  3. Define color shift strategy (cool blue → warm amber → golden dawn)
  4. Set cross-cutting rules for memory/present interleaving

Output:
  - mv-treatment.json with complete visual plan per section
```

## Changelog

- 2026-04-22: Created as a new leaf skill for MV production workflow.
