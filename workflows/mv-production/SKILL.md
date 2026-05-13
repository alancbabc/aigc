---
name: mv-production
description: Master workflow for music video production. Orchestrates song analysis, lyrics interpretation, visual style lock, keyframe planning, and keyframe image generation from song input to finished keyframe assets.
trigger: Use when the user wants an end-to-end music video, MV, or song-driven visual project rather than a single isolated task or a narrative film.
---

# MV Production

## Overview

This workflow owns orchestration only:

- entry and intake order
- stage dependencies and artifact flow
- which child skill owns which stage
- which hard constraints must be satisfied before the next stage begins

It does not replace `writer/mv-treatment`, `art/character-three-view`, `art/scene-design`, `director/storyboard`, or `generation/*` leaf-skill rules.

## Related Skills

- creative development: `writer/mv-treatment` (optional sidecar)
- character design: `writer/character-profile` + `art/character-three-view`
- scene design: `art/scene-design`
- storyboard (legacy appendix): `director/storyboard` + `director/transition`
- keyframe generation: `generation/qwen-image-local`
- contract index: `contracts/README.md`

## Slash Entry

- user-facing entry: `/mv-production`
- `/mv-production` maps to this `mv-production` workflow

The intake document is a JSON file with the following shape:

```json
{
  "song_audio_path": "C:/path/to/song.flac",
  "lyrics_lrc_path": "C:/path/to/lyrics.lrc",
  "song_background": "The song is the theme of ...",
  "visual_style": "anime",
  "reference_images": ["C:/path/to/artist_photo.png"],
  "resolution": {"width": 1280, "height": 720}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `song_audio_path` | string | yes | Path to song audio file (mp3/flac/wav) |
| `lyrics_lrc_path` | string | yes | Path to LRC lyrics file with timestamps |
| `song_background` | string | no | Background knowledge: movie/game context, artist info, thematic intent |
| `visual_style` | string | no | Non-realistic style: `anime` (default) / `cartoon` or user-specified |
| `reference_images` | array[string] | no | Paths to user-provided artist/singer reference images for character keyframes |
| `resolution` | object | no | Output resolution `{"width": 1280, "height": 720}` (default: API capability) |
| `notes` | string | no | Free-form notes |

## Use This Workflow When

Use this workflow when:

- the user wants an end-to-end music video pipeline
- the primary input is a song with lyrics
- the visual output must synchronize with musical structure and rhythm
- the task spans multiple stages across analysis, writing, art, directing, and generation

Do not use this workflow when:

- the user only wants one isolated task
- the user already has a valid intermediate artifact and only wants to continue from there
- the project is a narrative film without a song-driven timeline (use `workflows/film-production`)
- the project is a news commentary package (use `workflows/news-commentary`)

## Core Difference From Other Workflows

| Dimension | Film Production | News Commentary | **MV Production** |
|-----------|----------------|-----------------|-------------------|
| Driver | Story / script | Article / evidence | **Song + lyrics** |
| Timeline | Narrative rhythm | Spoken-line duration | **Musical beat + section structure** |
| Visual logic | Causal coherence | Information delivery | **Emotion + imagery + beat sync** |
| Transition basis | Plot need | Visual-type switching | **Section boundary (verse/chorus/bridge)** |
| Audio handling | Optional dubbing | TTS-generated anchor audio | **Original song is the master audio track** |

## Fixed Design Rules

### MV Type: Concept Only

The workflow **only** produces **concept** MV type. No other MV type is supported. The concept MV approach:

- **Lyric-imagery keyframes**: for lyrics with clear visual entities, metaphors, or concrete imagery → the director extracts imagery from the lyrics and generates text-to-image keyframes.
- **Character-singing keyframes**: for lyrics that are abstract, emotional, or lack concrete visual anchors → the director routes these to character-singing keyframes, which use user-provided reference images of the artist/singer as visual input for image-to-image generation.

This decision is made per-keyframe by the director (Stage 4) and encoded in the `keyframe_type` field.

### Visual Style: Non-Realistic

All keyframe and video output must be **non-realistic** (illustrated / animated). The user specifies which flavor:

| Style | Description |
|-------|-------------|
| `anime` | Cel-shaded, vibrant palettes, clean lines, anime aesthetic |
| `cartoon` | Bold outlines, saturated colors, illustrated/cartoon look |
| *(custom)* | Any non-photorealistic style string |

The `visual_style` field from the intake document flows into Stage 3 (`animation_art_style_en`), Stage 4 (director prompts), and Stage 5 (style prefix for image generation). Realistic / photographic styles are not allowed.

### Resolution

Output resolution is set at intake and propagates through all downstream stages. Defaults to the project's available API capability (1280x720).

## Inputs

The workflow accepts a single intake document at Stage 0. See [Slash Entry](#slash-entry) for the document shape.

## Builtin Visual Template Entry

Builtin style templates are retained in `builtin-visual-templates/` as a reference asset library. They are **not used** in the canonical concept-MV intake path (which always derives style from the user's `visual_style` field). They serve:

- **Legacy reference** for the deprecated narrative/performance/ mixed MV modes
- **Future expansion** if concept-MV adds template-based baseline overrides
- **Knowledge base** for Qwen3 prompt engineering patterns

## Stage Map

| Stage | Goal | Primary Artifact | Rule Owner |
|-------|------|-----------------|------------|
| 0 | intake / preflight | `project_meta.json` + `user_requirements.json` | workflow (`init_project.py`) |
| 1 | lyrics parsing | `lyrics-timing.json` | workflow |
| 2 | song section segmentation | `song-sections-llm.json` | workflow |
| 3 | global visual style lock | `mv-global-visual-style.json` | workflow |
| 4 | director keyframe plan | `mv-keyframe-director.json` (with `keyframe_type` per keyframe) | workflow |
| 5 | keyframe image generation | `keyframes/*.png` + `keyframe-images.json` | workflow |

## Stage 0: Intake / Preflight

**Goal**: accept the intake document, validate inputs, and create the project scaffold.

**Input**: intake document (see [Slash Entry](#slash-entry))

**Output**: `project_meta.json` + `user_requirements.json` (schema `2.0`)

**Contract**: `contracts/user-requirements/user-requirements.schema.json`

**Key fields in `project_meta.json`**:
- `song_file_path`, `lyrics_file_path`, `lyrics_source`
- `mv_type`: always `"concept"`
- `visual_style`: non-realistic style (`anime` / `cartoon` / custom)
- `reference_images[]`: user-provided artist/singer reference image paths
- `resolution`: output image/video dimensions

**Key fields in `user_requirements.json`**:
- `keyframe_style_prefix`: derived English style prefix from `visual_style`
- `mv_type`: `"concept"`
- `reference_images[]`: forwarded from intake
- `resolution`: forwarded from intake
- `song_background`: background knowledge for downstream creative stages

**Executor**:
```bash
python workflows/mv-production/scripts/init_project.py \
    --doc <intake-document.json> \
    --project-root <project-dir>
```

**Hard rules**:
- The intake document must contain at least `song_audio_path` and `lyrics_lrc_path`.
- The audio file and LRC file must exist at the specified paths.
- `mv_type` is always `"concept"`; this field is set automatically and cannot be overridden.
- `resolution` defaults to 1280x720 (the project's available API capability) when not specified.
- `visual_style` defaults to `"anime"` when not specified.

### Optional Branch: Character + Scene Design

After Stage 5 (keyframes exist), character and scene design may be inserted:

| Stage | Goal | Primary Artifact |
|-------|------|-----------------|
| C1 | character / performer design | `characters.json` + `characters/` |
| C1R | character review | `three-view-review.json` |
| C2 | scene design | `scene_design.json` + `scenes/` |
| C2R | scene review | `scene-review.json` |

### Legacy Appendix: Storyboard Chain

The film-style storyboard chain (`storyboard.json` → `test-shoots.json` → `keyframe-prompts.json`) is **not** part of this canonical path. See [Appendix](#appendix-legacy-storyboard-chain).

## Hard Constraints Owned By This Workflow

These constraints stay at the orchestration layer and must not be delegated away:

1. The workflow must advance in the direction `lyrics parsing → section segmentation → visual style → director plan → keyframe images`.
2. The **original song audio** is the single source of truth for all timing decisions. Every downstream artifact must reference the song timeline, not invent independent timing.
3. Stage 4 keyframes must form a **partition** of all lyric `line_id`s into consecutive blocks. No line may be skipped or duplicated.
4. `song-sections-llm.json` must cover every lyric `line_id` exactly once in order. Instrumental-only lines (`is_instrumental=true`) must also be covered.
5. Every `section_ref` in downstream artifacts must match `section_id` from `song-sections-llm.json`.
6. The `global_style_suffix` from Stage 3 must be present in every downstream image prompt; it must not be silently dropped.
7. All prompts sent into `generation/*` must be in English.
8. **Concept MV rule**: Every keyframe in Stage 4 must carry a `keyframe_type` of either `lyric_imagery` or `character_singing`. The director (Qwen3) decides based on lyric content: concrete visual entities → `lyric_imagery`; abstract / emotional / non-visual → `character_singing`.
9. **Character-singing routing**: Keyframes with `keyframe_type: "character_singing"` must use image-to-image generation with the user's reference images as visual input. Keyframes with `keyframe_type: "lyric_imagery"` use standard text-to-image.
10. **Non-realistic enforcement**: The `animation_art_style_en` in Stage 3 must reflect the user's `visual_style` setting (anime/cartoon). Photorealistic or cinematic-realistic style is not permitted.
11. **Resolution propagation**: `resolution` from Stage 0 must flow unchanged through Stage 5 image generation. All keyframe images must share the same resolution.

## Prompt Language Rule

In this standard workflow, all prompts sent into `generation/*` must be in English.

## Section Timeline (without `song-structure.json`)

Workflow Stage 2 does **not** materialize `song-structure.json`. Treat `lyrics-timing.json` (line-level `start_time` / `end_time`) plus `song-sections-llm.json` (per-section `section_id`, `section_type`, `line_refs`) as the section timeline:

- `section_ref` in downstream artifacts must equal `section_id` from `song-sections-llm.json`.
- A section's `start_time` / `end_time` window is the `start_time` of the first line and `end_time` of the last line in `line_refs`, looked up in `lyrics-timing.json` `lines[]`.
- `audio_duration_seconds` on `lyrics-timing.json` (from `--audio`) establishes total length; BPM for beat math comes from `user_requirements.json` / project notes.

## Stage 1: Lyrics Parsing

**Goal**: decompose the song into line-level timing entries with start/end timestamps.

**Input**: LRC file or plain text lyrics. When LRC with timestamps is available, use it as the primary timing source.

**Output**: `lyrics-timing.json` (schema `1.1`)

**Contract**: `contracts/lyrics-timing/lyrics-timing.schema.json`

**Key fields**:
- `lines[]`: `line_id`, `text`, `start_time`, `end_time`, `duration_seconds`, `is_instrumental`
- `audio_duration_seconds` (when `--audio` is passed)

**Executor**:
```
python workflows/mv-production/scripts/parse_lyrics.py \
    --input <lyrics-file> \
    --output <project>/lyrics-timing.json \
    [--audio <media-file>]
```

**Hard rule**: after parsing, every line must have a valid `start_time`. Lines at the tail with `end_time: null` must be resolved using `--audio` to supply `audio_duration_seconds`.

## Stage 2: Song Section Segmentation

**Goal**: segment lyrics-timing lines into musical sections (verse, chorus, bridge, ...) using Qwen3.

**Input**: `lyrics-timing.json`

**Output**: `song-sections-llm.json` (schema `1.0`)

**Contract**: `contracts/song-sections-llm/song-sections-llm.schema.json`

**Key fields**:
- `sections[]`: `section_id` (snake_case), `section_type` (enum: intro/verse/pre_chorus/chorus/bridge/instrumental/outro/interlude), `line_refs[]`, `notes`

**Hard rule**: all `line_refs` from all sections, when concatenated in order, must equal the full `line_order` from `lyrics-timing.json`. Instrumental lines must not be skipped.

**Executor**:
```
python workflows/mv-production/scripts/infer_sections_qwen3.py \
    --lyrics-timing <project>/lyrics-timing.json \
    --out <project>/song-sections-llm.json
```

**Validation**: the script validates line coverage and rejects responses that skip or duplicate lines. If validation fails, the model may be retried.

## Stage 3: Global Visual Style Lock

**Goal**: lock global English style suffix, core visual motifs, and per-section-role structural rules so downstream keyframes share one art direction.

**Input**: `lyrics-timing.json` + `song-sections-llm.json`. May also consume a builtin visual template or user style references.

**Output**: `mv-global-visual-style.json` (schema `1.1`)

**Contract**: `contracts/mv-global-visual-style/mv-global-visual-style.schema.json`

**Key fields**:
- `global_style_suffix`: English clause appended to every downstream MV image prompt
- `structural_visual_rules[]`: per `section_roles` (verse / chorus / bridge …) rules for `visual_tension_en`, `camera_framing_en`, `cut_motion_tempo_en`, `contrast_vs_other_sections_en`. Validator ensures verse and chorus are covered when those `section_type`s appear in `song-sections-llm.json`.
- `core_visual_motifs[]`: recurring `entities / environments / symbols` with `prompt_anchor_en`, `recurrence`, optional `lyrics_line_refs`. Must have 3–10 items.
- `animation_art_style_en`, `color_palette_en`, `lighting_mood_en`, `texture_material_en`, `motion_camera_en`, `negative_style_hints_en`

**Builtin template merge rule**: when the user selects a builtin template at Stage 0:
1. Read `builtin-visual-templates/<template_id>.json`.
2. Qwen3 receives the template values as context alongside lyrics + sections.
3. The model may override or extend template fields to create a song-specific style, but the general aesthetic direction should remain aligned with the template.
4. When the user provides custom style references, the builtin template becomes advisory only.

**Executor (default path)**:
```
python workflows/mv-production/scripts/infer_global_visual_style_qwen3.py \
    --lyrics-timing <project>/lyrics-timing.json \
    --song-sections-llm <project>/song-sections-llm.json \
    --out <project>/mv-global-visual-style.json \
    [--builtin-template-id <template_id>]
```

**Executor (legacy `song-structure.json` path, still requires `lyrics-timing.json`)**:
```
python workflows/mv-production/scripts/infer_global_visual_style_qwen3.py \
    --lyrics-timing <project>/lyrics-timing.json \
    --song-structure <project>/song-structure.json \
    --out <project>/mv-global-visual-style.json
```

## Stage 4: Director Keyframe + I2V Prompt Plan (Concept MV)

**Goal**: produce non-line-by-line keyframe coverage with concept-MV routing. Consecutive lyric lines are grouped into keyframe beats. Each keyframe carries a `keyframe_type` (`lyric_imagery` or `character_singing`), a still-image prompt (16:9), and an image-to-video prompt, all anchored on canonical timestamps from `lyrics-timing.json`.

**Input**: `lyrics-timing.json` + `song-sections-llm.json` + `mv-global-visual-style.json` + `user_requirements.json` (for `reference_images` and `visual_style`)

**Output**: `mv-keyframe-director.json` (schema `1.0`) with `keyframe_type` on each keyframe

**Contract**: `contracts/mv-keyframe-director/mv-keyframe-director.schema.json`

**Key fields**:
- `keyframes[]`: `keyframe_id`, `primary_section_ref`, `section_type_focus`, `line_refs[]`, `start_time`, `end_time`, `lines[]`, `keyframe_type`, `keyframe_image_prompt_en`, `video_from_keyframe_prompt_en`
- `instrumental_bookends[]`: optional segments without lyric `line_refs` (intro before first LRC line, outro tail)

**Concept MV routing logic** (per keyframe):
| Condition | `keyframe_type` | Generation Path |
|-----------|----------------|-----------------|
| Lyrics contain concrete visual entities (sea, fish, sky, etc.) | `lyric_imagery` | Text-to-image from `keyframe_image_prompt_en` |
| Lyrics are abstract / emotional / lack concrete visual anchors | `character_singing` | Image-to-image using user's reference images of the singer |

The director (Qwen3) analyzes each group of lyrics and decides the `keyframe_type` based on visual concreteness.

**Hard rules**:
- Keyframes must form a **partition** of all `line_id`s into **consecutive** blocks.
- One line per keyframe is rejected when keyframe count is excessive (must be fewer than total lines).
- `start_time` / `end_time` / `lines[]` are filled by the script from timings after model return.
- `keyframe_image_prompt_en` must incorporate `global_style_suffix` and `core_visual_motifs` prompt anchors.
- `video_from_keyframe_prompt_en` must describe motion/camera/action starting from the still frame.
- Every keyframe must have a non-null `keyframe_type`. Instrumental bookends default to `lyric_imagery`.

**Executor**:
```
python workflows/mv-production/scripts/infer_keyframe_director_qwen3.py \
    --lyrics-timing <project>/lyrics-timing.json \
    --song-sections-llm <project>/song-sections-llm.json \
    --mv-global-visual-style <project>/mv-global-visual-style.json \
    --out <project>/mv-keyframe-director.json
```

## Stage 5: Keyframe Image Generation

**Goal**: generate still images for each keyframe in the director plan, routing by `keyframe_type`. Produces raw images and labeled versions with lyric overlays.

**Input**: `mv-keyframe-director.json` + `mv-global-visual-style.json` + `user_requirements.json` (for style prefix, reference images, resolution)

**Output**: `keyframes/<keyframe_id>.png`, `keyframes/<keyframe_id>_labeled.png`, `keyframe-images.json` (manifest with paths, timing, and generation status)

**Contract**: `contracts/keyframe-images/keyframe-images.schema.json`

### Concept MV Routing

Each keyframe's `keyframe_type` determines the generation method:

| `keyframe_type` | Method | Input | Description |
|----------------|--------|-------|-------------|
| `lyric_imagery` | Text-to-image | `keyframe_image_prompt_en` | Standard text-to-image generation from the director's English prompt |
| `character_singing` | Image-to-image | Reference images + prompt | Uses user-provided reference images of the singer as visual input, with the director's prompt as text guidance |

For `character_singing` keyframes:
- Reference images come from `user_requirements.json` → `reference_images[]`.
- The first available reference image is used as the visual input.
- The director's `keyframe_image_prompt_en` becomes the text prompt for image-to-image.
- If no reference images are available, falls back to `lyric_imagery` method and logs a warning.

**Render backends**:
| Backend | Service | Resolution Constraints | Fallback |
|---------|---------|------------------------|----------|
| `qwen_local` | Local Qwen Image `POST /submit` | Any (default 1280×720) | placeholder PNG |
| `gitee_kolors` | Gitee `/v1/images/generations` (kolors model) | Only 1024×576, 1024×768, 1024×1024, 512×512 | placeholder PNG |
| `dry_run` | No API | Any | placeholder PNG |

**Executor** (local Qwen backend):
```
python workflows/mv-production/scripts/generate_keyframe_images_from_director.py \
    --director <project>/mv-keyframe-director.json \
    --global-style <project>/mv-global-visual-style.json \
    --user-requirements <project>/user_requirements.json \
    --project-root <project> \
    --out-dir <project>/keyframes
```

**Executor** (Gitee Kolors backend):
```
python workflows/mv-production/scripts/generate_keyframe_images_flux.py \
    --director <project>/mv-keyframe-director.json \
    --global-style <project>/mv-global-visual-style.json \
    --user-requirements <project>/user_requirements.json \
    --project-root <project> \
    --out-dir <project>/keyframes \
    --width 1024 --height 576
```

**Hard rules**:
- Each `keyframe_id` produces one `*.png` and one `*_labeled.png`.
- `keyframe-images.json` must record per-keyframe `generation_ok` status and `keyframe_type`.
- Image prompts must incorporate `global_style_suffix` from Stage 3 and the user's `keyframe_style_prefix` from `user_requirements.json`. The director's `keyframe_image_prompt_en` already includes `global_style_suffix`; the script adds `texture_material_en` + `lighting_mood_en` but does NOT re-append `global_style_suffix` to avoid duplication.
- Resolution is read from `user_requirements.json` → `resolution`. The Kolors backend validates against its supported sizes and falls back to 1024×576 on mismatch.
- For `character_singing` keyframes: if the image-to-image API is unavailable, fall back to text-to-image with a character description prompt.
- Placeholder images (solid-color PNGs) replace failed generations only in non-strict mode.

## Appendix: Legacy Storyboard Chain

The film-style path (`storyboard.json` → `test-shoots.json` → `keyframe-prompts.json` → `keyframe-images.json` via `art/keyframe-generation`) is **not** part of the canonical MV orchestration. Use it only for film-style shot granularity or legacy compatibility.

When running this chain without `mv-treatment.json`, anchor each section's creative intent with `mv-global-visual-style.json`, `user_requirements.json`, `project_meta.json`, and `mv-keyframe-director.json`.

Contracts and guidance for these stages remain in:
- `contracts/mv-storyboard/`
- `contracts/mv-treatment/`
- Leaf skills: `director/storyboard`, `director/test-shoots`, `art/keyframe-generation`

## Hard Constraints Recap

1. Canonical direction: `lyrics → sections → style → director → keyframes`.
2. Song audio is the master timeline for all timing decisions.
3. Stage 4 keyframes form a partition of all `line_id`s into consecutive blocks.
4. Stage 2 sections cover every `line_id` exactly once, including instrumental lines.
5. Every `section_ref` downstream matches `section_id` from `song-sections-llm.json`.
6. `global_style_suffix` must flow into every downstream image prompt.
7. All `generation/*` prompts in English.
8. Every keyframe has `keyframe_type`: `lyric_imagery` or `character_singing`.
9. `character_singing` keyframes route to image-to-image with user reference images.
10. Non-realistic style enforced; `animation_art_style_en` reflects `visual_style` from intake.
11. Resolution from Stage 0 propagates unchanged through Stage 5.

## Core Dependencies

### Skills
- `writer/mv-treatment` (optional sidecar)
- `writer/character-profile` + `art/character-three-view` (optional branch)
- `art/scene-design` (optional branch)
- `generation/qwen-image-local` → keyframe stills

### Contracts

Full index: `contracts/README.md`

Priority directories:
- `contracts/user-requirements/`
- `contracts/project-meta/`
- `contracts/lyrics-timing/`
- `contracts/song-sections-llm/`
- `contracts/song-structure/` (legacy reference)
- `contracts/mv-global-visual-style/`
- `contracts/mv-keyframe-director/`
- `contracts/keyframe-images/`
- `contracts/mv-treatment/` (optional sidecar)
- `contracts/mv-storyboard/` (legacy appendix)

## Collaboration Boundaries

- **workflow**: owns stage orchestration, artifact dependencies, hard constraints, entry behavior
- **`writer/mv-treatment`**: owns optional treatment prose and creative concept development
- **`art/character-three-view` + `art/scene-design`**: owns optional visual world building
- **`director/storyboard`** (appendix): owns shot-level beat-sync planning
- **`generation/qwen-image-local`**: owns keyframe image generation rules

## Early Exit Rules

Valid completion points:
- after `lyrics-timing.json` + `song-sections-llm.json` (Stage 2)
- after `mv-global-visual-style.json` (Stage 3)
- after `mv-keyframe-director.json` (Stage 4)
- after `keyframes/*.png` + `keyframe-images.json` (Stage 5)

## Intermediate Artifact Recovery

If the user provides an existing artifact, resume from the nearest valid stage:

| Existing Artifact | Resume at |
|------------------|-----------|
| `lyrics-timing.json` + `song-sections-llm.json` | Stage 3 (global style) or Stage 4 (director plan) |
| `mv-global-visual-style.json` | Stage 4 (director plan) |
| `mv-keyframe-director.json` | Stage 5 (keyframe images) |
| `keyframe-images.json` | Done — keyframe generation is the terminal stage |

Do not rerun earlier stages unless the user asks for revision.

## Artifact Layout

```
<project_root>/
├── project_meta.json
├── user_requirements.json
├── lyrics-timing.json
├── song-sections-llm.json
├── mv-global-visual-style.json
├── mv-keyframe-director.json
├── keyframes/
│   ├── kf_01.png
│   ├── kf_01_labeled.png
│   └── ...
├── keyframe-images.json
├── characters.json              (optional)
├── characters/                  (optional)
├── scene_design.json            (optional)
└── scenes/                      (optional)
```

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

Before downstream artifact generation, extract the decision layer first:

### Before Song Section Analysis (Stage 2)
Extract: `song_genre`, `tempo_feel`, `energy_arc`, `section_pattern`

### Before Global Style (Stage 3)
Extract and record in `user_requirements.json` or planning notes:
`visual_style` intent, `color_strategy`, `performance_choreography`, `narrative_thread`, `metaphor_sequence`, `director_style_reference`, `style_intensity`

### Before Keyframe Director Plan (Stage 4)
Extract: `lyrical_themes`, `dominant_imagery`, `emotion_trajectory`, `narrative_potential`

### Before Character / Performer Package (optional branch)
Extract: `role_archetype`, `body_language`, `costume_anchor`, `performance_persona`

## VLM Assist Points

Use `generation/qwen2.5-vl` as a review and analysis helper at:
- keyframe image review (Stage 5)

## Missing Capabilities (Future)

| Capability | Purpose | Future Module |
|-----------|---------|---------------|
| Audio structure analysis | auto-detect BPM, section boundaries, energy curves | `generation/audio-analysis` |
| Lyrics timestamp alignment | align plain-text lyrics to audio timestamps | `generation/lyrics-alignment` |

## Changelog

- 2026-05-11: Removed video-generation stages (6–11). Workflow now terminates after keyframe image generation (Stage 5). Future video stages will be designed in a separate workflow or appended when the image-to-video pipeline is stabilized.
- 2026-05-11: Added concept-MV-only design: `keyframe_type` routing (lyric_imagery vs character_singing), non-realistic visual style enforcement, resolution propagation through all stages, and slash-entry intake format.
- 2026-05-11: Standardized stage numbering (0–5). Added keyframe-images contract. Moved character/scene design to optional branch.
- 2026-05-11: Earlier version dropped `mv-treatment` from canonical path.
- 2026-04-22: Created MV production workflow with initial stage definitions.
