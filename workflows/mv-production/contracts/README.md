# MV Production Contracts

This directory contains JSON contracts for each stage of the `mv-production` workflow, organized by module.

## Structure

- Each module gets its own subdirectory
- Each module should have both `*.schema.json` and `*.example.json`
- Builtin templates and scripts live outside this directory

## Module Index

### MV-Specific Contracts

- `song-structure/` — Song section breakdown with timing, mood, and energy metadata
- `lyrics-analysis/` — Lyrics imagery, themes, emotion arc, and visual metaphor extraction
- `mv-treatment/` — MV creative concept, visual style, and per-section visual plan
- `mv-storyboard/` — Beat-synced storyboard with time windows and lyrics alignment
- `mv-video-plan/` — Timeline-aware video generation plan with song-synced segments

### Reused From film-production

- Video prompt drafts and LTX prompt optimization reuse the contracts defined in `workflows/film-production/contracts/`

## Reading Order

If you are new to this workflow, read in this order:

1. `song-structure/`
2. `lyrics-analysis/`
3. `mv-treatment/`
4. `mv-storyboard/`
5. `mv-video-plan/`

## Interpretation Ownership

- Stages 1-3 contracts are interpreted by the workflow and `writer/mv-treatment`
- Stage 6 storyboard contract is interpreted by `director/storyboard` with MV extensions
- Stage 9-11 video contracts follow the same interpretation rules as `workflows/film-production`
