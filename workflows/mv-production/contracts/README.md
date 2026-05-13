# MV Production Contracts

This directory contains JSON contracts for each stage of the `mv-production` workflow, organized by module.

## Structure

- Each module gets its own subdirectory.
- Each module should have both `*.schema.json` and `*.example.json`.
- Builtin templates and scripts live outside this directory:
  - templates: `../builtin-visual-templates/`
  - scripts: `../scripts/`

## Module Index

### Canonical Path Contracts

| Module | Stage | Description |
|--------|-------|-------------|
| `user-requirements/` | 0 | Intake document ingest: concept MV, visual style, reference images, resolution |
| `lyrics-timing/` | 1 | Line-level timestamps from `parse_lyrics.py` |
| `song-sections-llm/` | 2 | Qwen3 section segmentation with enriched per-section analysis (v2.0) |
| `segment-interpretation/` | 3 | Qwen3.5 segment interpretation: imagery, visual direction, shot planning hints |
| `shot-plan/` | 4 | Shot-level breakdown: time windows, composition, camera, motion, generation notes |
| `image-prompts/` | 5 | Image generation prompts: static keyframe prompts, negative prompts, quality checks |
| `song-structure/` | — | Legacy/reference consolidated structure (not emitted by canonical path) |
| `mv-global-visual-style/` | — | Legacy: global visual style lock (retained for reference) |
| `mv-keyframe-director/` | — | Legacy: director keyframe plan (retained for reference) |
| `keyframe-images/` | — | Legacy: keyframe image manifest (retained for reference) |

### Optional Branch Contracts

| Module | Stage | Description |
|--------|-------|-------------|
| `characters/` | C1 | Character/performer profiles (reuses `writer/character-profile/`) |
| `scene-design/` | C2 | Scene environment design (reuses `art/scene-design/`) |

### Legacy / Appendix Contracts

| Module | Stage | Description |
|--------|-------|-------------|
| `mv-treatment/` | — | Optional prose treatment (sidecar, not canonical) |
| `mv-storyboard/` | — | Beat-synced storyboard (appendix film-style chain) |

## Reading Order

If you are new to this workflow, read in this order:

1. `user-requirements/` — what the intake document provides
2. `lyrics-timing/` — the timing foundation for everything downstream
3. `song-sections-llm/` — section segmentation on the lyric timeline
4. `song-structure/` — optional reference if you consume a consolidated structure elsewhere
5. `mv-global-visual-style/` — global style lock after sections
6. `mv-keyframe-director/` — canonical director keyframe plan (with `keyframe_type`)
7. `keyframe-images/` — generated still image manifest
8. *(optional sidecar)* `mv-treatment/` if using prose treatment
9. *(appendix)* `mv-storyboard/` if using the legacy storyboard chain

## Cross-Contract Validation Rules

- Every `section_ref` in downstream artifacts (`mv-keyframe-director`) must match a `section_id` from `song-sections-llm.json`.
- Every `line_refs` aggregate across all `mv-keyframe-director` keyframes must form a partition of all `line_id`s from `lyrics-timing.json` — exactly once, in order, consecutive within each keyframe.
- Every `keyframe_id` in `keyframe-images.json` must exist in `mv-keyframe-director.json`.
- `keyframe_images.image_size` must match the `resolution` from `user_requirements.json`.

## Duration Field Naming Convention

| Artifact | Duration Field | Source |
|----------|---------------|--------|
| `lyrics-timing.json` | `duration_seconds` (line level) | Parsed from LRC |
| `lyrics-timing.json` | `audio_duration_seconds` (top-level) | From `--audio` media |
| `mv-keyframe-director.json` | `start_time`, `end_time` (per keyframe) | Injected from lyrics-timing |

## Interpretation Ownership

- Stages 1–4 contracts are interpreted by the MV workflow scripts (`parse_lyrics.py`, `infer_sections_qwen3.py`, `infer_global_visual_style_qwen3.py`, `infer_keyframe_director_qwen3.py`).
- Stage 5 contract is interpreted by `generate_keyframe_images_from_director.py`.
- The `mv-storyboard` contract is interpreted by `director/storyboard` with MV extensions (appendix only).
- Optional branch contracts reuse `writer/character-profile/` and `art/scene-design/` rules.
