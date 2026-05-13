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
| 2 | song section segmentation (enriched) | `song-sections-llm.json` (v2.0) | workflow |
| 3 | segment interpretation | `segment-interpretation.json` | workflow |
| 4 | shot plan | `shot-plan.json` | workflow |
| 5 | image prompts | `image-prompts.json` | workflow |
| 5d | generation queue | `image-generation-queue.json` | workflow (programmatic) |
| 6 | asset manifest | `asset-manifest.json` | workflow (programmatic) |
| 6a | image selection review | `image-selection-review.json` | manual / VLM review template |
| 6b | selected asset manifest | `selected-asset-manifest.json` | workflow (programmatic from review) |
| 7 | video prompts | `video-prompts.json` | workflow (Qwen3.5) |
| 8 | timeline | `timeline.json` | workflow (programmatic assembly) |

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

1. The workflow must advance in the direction `lyrics parsing → section segmentation → segment interpretation → shot plan → image prompts`.
2. The **original song audio** is the single source of truth for all timing decisions. Every downstream artifact must reference the song timeline, not invent independent timing.
3. `song-sections-llm.json` must cover every lyric `line_id` exactly once in order. Instrumental-only lines (`is_instrumental=true`) must also be covered.
4. Every `section_ref` in downstream artifacts must match `section_id` from `song-sections-llm.json`.
5. Every `segment_id` in `shot-plan.json` must exist in `segment-interpretation.json`.
6. Every shot's `time_range` must fall within its `parent_segment_id` time window, and segments must be fully tiled by their shots.
7. **Imagery-type MV**: no narrative character acting; visual language limited to silhouettes, light threads, reflections, distant views, semi-transparent elements.
8. **Instrumental segments**: receive `ambient_hold` entries with `generate_new_image: false`, reuse previous shot's image.
9. All prompts sent into `generation/*` must be in English.
10. `global_prompt_prefix` is data-driven from S3 segment data, not song-specific hardcoded.
11. Ambient hold shots reuse previous image, no new generation.

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

## Stage 3: Segment Interpretation

**Goal**: upgrade each visual segment from `song-sections-llm.json` (v2.0) from a "lyric-time block" to a "generation-ready semantic block". Interpret what the lyrics mean, extract visual imagery, set visual direction, plan shot count, and define generation constraints.

**Input**: `song-sections-llm.json` (v2.0) + `lyrics-timing.json`

**Output**: `segment-interpretation.json` (schema `1.0`)

**Contract**: `contracts/segment-interpretation/segment-interpretation.schema.json`

**Key fields per segment**:
- `interpretation`: `literal_meaning_zh` (direct translation), `deep_meaning_zh` (deeper meaning in song's narrative arc), `emotional_state_zh[]` (keywords), `emotional_intensity` (0.0-1.0 float)
- `imagery[]`: extracted visual imagery with `image_zh`, `image_en`, `type` (natural/atmosphere/symbolic_creature/character/object/action), `visual_priority` (0.0-1.0), `symbolic_meaning_zh`
- `visual_direction`: `scene_type`, `setting_zh`, `color_palette[]`, `lighting`, `composition_zh`, `camera_mood`
- `shot_planning_hint`: `keyframe_count` (≥1, used as lower bound by Stage 5 director), `motion_intensity` (none/low/medium/high), `transition_in`, `transition_out`
- `generation_constraints`: `must_include[]`, `avoid[]` — both feed into downstream prompt construction

**Instrumental segments**: segments where ALL `line_refs` are `is_instrumental=true` get placeholder entries with `is_instrumental: true` and `keyframe_count: 0`. No Qwen3 analysis is performed for these. Their visuals extend the preceding segment's imagery.

**Executor**:
```
python workflows/mv-production/scripts/infer_segment_interpretation_qwen3.py \
    --song-sections-llm <project>/song-sections-llm.json \
    --lyrics-timing <project>/lyrics-timing.json \
    --out <project>/segment-interpretation.json
```

**Hard rules**:
- Non-instrumental segments are sent to Qwen3.5 for full interpretation. Instrumental segments receive placeholder entries.
- `time_range` is injected from `lyrics-timing.json` by the script for accuracy.
- `lyrics_text` is copied from the source `song-sections-llm.json`.
- `visual_priority = 1.0` marks the segment's core imagery; `emotional_intensity` guides downstream mood.

## Stage 4: Shot Plan

**Goal**: split each segment-interpretation segment into executable shots with precise time windows, composition, camera movement, emotion, and generation notes. This is the bridge from semantic interpretation to actionable prompts.

**Input**: `segment-interpretation.json` (Stage 3)

**Output**: `shot-plan.json` (schema `1.0`)

**Contract**: `contracts/shot-plan/shot-plan.schema.json`

**Key fields per shot**:
- `shot_id` (`shot_{segment_id}_{NN}`), `parent_segment_id`, `parent_section_id`
- `time_range` (must fall within parent segment window)
- `shot_role` (enum: establishing_image, symbolic_detail, emotional_peak, transition_image, motif_development, ambient_hold, memory_echo, climax_image, resolution_image)
- `visual_concept_zh` / `deep_function_zh`: what this shot shows and why
- `key_imagery[]` / `secondary_imagery[]`: imagery from Stage 3, assigned per-shot
- `composition` (enums: shot_size, camera_angle, foreground/midground/background, focal_point, depth)
- `camera` (enums: camera_motion, movement_speed, lens_feeling, stability)
- `motion_design` (subject_motion, environment_motion, motion_intensity)
- `visual_style` (scene_type, color_palette, lighting, texture — inherited from Stage 3)
- `emotion` (primary, secondary, intensity — inherited from Stage 3)
- `transition` (transition_in, transition_out, transition_duration)
- `generation_notes` (image_prompt_focus, video_prompt_focus, avoid — ready for downstream prompt stages)

**Instrumental segments** receive `ambient_hold` entries with `generate_new_image: false` and `reuse_from_shot_id` pointing to the previous segment's last shot.

**Executor**:
```
python workflows/mv-production/scripts/infer_shot_plan_qwen3.py \
    --segment-interpretation <project>/segment-interpretation.json \
    --out <project>/shot-plan.json
```

**Hard rules**:
- Each shot's time window must fall within its parent segment.
- Each segment's shots must tile its full time window.
- Each shot has one primary visual motion (one camera move + one subject move).
- Imagery-type MV constraints apply: silhouettes, light threads, reflections, distant views, no narrative acting.
- `composition`, `camera`, `motion_design` fields use predefined enums only.
- `ambient_hold` shots reuse previous shot's image without generating new ones.

## Stage 5: Image Prompts

**Goal**: convert each shot from `shot-plan.json` into a stable, unified English prompt for static keyframe image generation. Ambient hold shots reuse previous images without generating new ones.

**Input**: `shot-plan.json` (Stage 4) + `segment-interpretation.json` (Stage 3)

**Output**: `image-prompts.json` (schema `1.0`)

**Contract**: `contracts/image-prompts/image-prompts.schema.json`

**Method**: Programmatic assembly + Qwen3.5 batch translation.
- `global_style` is induced from S3 segment data: top-3 colors (CN→EN mapped), top-3 camera moods (CN→EN mapped), dominant lighting, dominant scene type
- `global_prompt_prefix` is a fixed template filled with data-induced values: `"A poetic symbolic music video keyframe, {color_phrase} atmosphere, cinematic composition, {mood_phrase}, elegant and emotional visual storytelling"`
- `visual_concept_zh` from each shot is batch-translated to English by Qwen3.5
- Composition/emotion/lighting are mapped via fixed CN→EN lookup tables

**Key fields per prompt**:
- `render_strategy.generate_new_image`: `false` for ambient_hold shots with `reuse_from_shot_id`
- `image_prompt`: full English prompt = `global_prompt_prefix + visual_concept_en + composition_hint + lighting_hint + emotion_hint + 16:9`
- `negative_prompt`: fixed global template + shot-specific avoid list
- `prompt_components`: structured breakdown (main_subject, environment, composition, lighting, emotion, style_keywords)
- `generation_parameters`: aspect_ratio (16:9), resolution, num_candidates
- `quality_check`: must_include, must_avoid, continuity_tags

**Executor**:
```
python workflows/mv-production/scripts/build_image_prompts.py \
    --shot-plan <project>/shot-plan.json \
    --segment-interpretation <project>/segment-interpretation.json \
    --out <project>/image-prompts.json
```

**Hard rules**:
- `global_prompt_prefix` is data-driven (not song-specific hardcoded): colors and moods are aggregated from S3 segment data via fixed CN→EN maps.
- Ambient hold shots do not generate new images; they reuse the previous shot's image.
- All prompts are in English.
- `image_prompt` describes only the static keyframe — no camera motion, no video action.

## Stage 5d: Generation Queue

**Goal**: build an executable task queue from image-prompts. Filters `generate_new_image=true` shots and maps each to candidate output paths.

**Input**: `image-prompts.json` (Stage 5)

**Output**: `image-generation-queue.json`

**Executor**:
```
python workflows/mv-production/scripts/build_generation_queue.py \
    --image-prompts <project>/image-prompts.json \
    --out <project>/image-generation-queue.json
```

**Hard rules**:
- Critical shots (`establishing_image`, `emotional_peak`, `climax_image`, `resolution_image`) get 3 candidates; others get 2.
- Reuse tasks record `reuse_from_shot_id` and `reuse_after_selection` status.

## Stage 6: Asset Manifest (post-generation)

**Goal**: scan generated images on disk and build a manifest recording per-shot candidacy.

**Input**: `image-generation-queue.json` (Stage 5d) + actual generated files on disk

**Output**: `asset-manifest.json`

**Executor**:
```
python workflows/mv-production/scripts/build_asset_manifest.py \
    --generation-queue <project>/image-generation-queue.json \
    --out <project>/asset-manifest.json
```

## Stage 6a: Image Selection Review

**Goal**: review candidate images per shot with 5-score rubric. Currently manual; VLM integration planned.

**Input**: `asset-manifest.json` (Stage 6)

**Output**: `image-selection-review.json`

**Executor**:
```
python workflows/mv-production/scripts/build_selection_review_template.py \
    --asset-manifest <project>/asset-manifest.json \
    --out <project>/image-selection-review.json
```
*Scoring is manual — fill in scores, then proceed to S6b.*

**Scoring dimensions**:
- `prompt_alignment`: does it match the prompt and must_include? (0-1)
- `style_consistency`: does it match the global visual style? (0-1)
- `composition_quality`: clear composition with defined depth? (0-1)
- `symbolic_strength`: powerful and evocative imagery? (0-1)
- `video_readiness`: suitable for image-to-video generation? (0-1)

## Stage 6b: Selected Asset Manifest

**Goal**: select the highest-scoring candidate per shot and resolve reuse dependencies.

**Input**: `asset-manifest.json` (Stage 6) + `image-selection-review.json` (Stage 6a)

**Output**: `selected-asset-manifest.json`

**Executor**:
```
python workflows/mv-production/scripts/build_selected_manifest.py \
    --asset-manifest <project>/asset-manifest.json \
    --selection-review <project>/image-selection-review.json \
    --out <project>/selected-asset-manifest.json
```

## Stage 7: Video Prompts

**Goal**: convert each selected keyframe image into an image-to-video motion prompt. Uses Qwen3.5 to generate camera-aware video prompts from shot-plan camera/motion data.

**Input**: `shot-plan.json` (Stage 4) + `image-prompts.json` (Stage 5) + `selected-asset-manifest.json` (Stage 6b, optional)

**Output**: `video-prompts.json`

**Executor**:
```
python workflows/mv-production/scripts/build_video_prompts.py \
    --shot-plan <project>/shot-plan.json \
    --image-prompts <project>/image-prompts.json \
    [--selected-manifest <project>/selected-asset-manifest.json] \
    --out <project>/video-prompts.json
```

## Stage 8: Timeline

**Goal**: assemble a sequential timeline of video segments for final MV production. Aligns with lyrics-timing for subtitle synchronization and builds FFmpeg concat reference.

**Input**: `shot-plan.json` (S4) + `video-prompts.json` (S7) + `selected-asset-manifest.json` (S6b) + `lyrics-timing.json` (S1)

**Output**: `timeline.json`

**Executor**:
```
python workflows/mv-production/scripts/build_timeline.py \
    --shot-plan <project>/shot-plan.json \
    --video-prompts <project>/video-prompts.json \
    --selected-manifest <project>/selected-asset-manifest.json \
    --lyrics-timing <project>/lyrics-timing.json \
    [--song-audio <original-song>] \
    --out <project>/timeline.json
```

## Appendix: Legacy Storyboard Chain

The film-style path (`storyboard.json` → `test-shoots.json` → `keyframe-prompts.json` → `keyframe-images.json` via `art/keyframe-generation`) is **not** part of the canonical MV orchestration. Use it only for film-style shot granularity or legacy compatibility.

When running this chain without `mv-treatment.json`, anchor each section's creative intent with `mv-global-visual-style.json`, `user_requirements.json`, `project_meta.json`, and `mv-keyframe-director.json`.

Contracts and guidance for these stages remain in:
- `contracts/mv-storyboard/`
- `contracts/mv-treatment/`
- Leaf skills: `director/storyboard`, `director/test-shoots`, `art/keyframe-generation`

## Hard Constraints Recap

1. Canonical direction: `lyrics → sections → segment interpretation → shot plan`.
2. Song audio is the master timeline for all timing decisions.
3. Stage 2 sections cover every `line_id` exactly once, including instrumental lines.
4. Every `segment_id` in shot-plan must exist in segment-interpretation.
5. Every shot's time window falls within parent segment and all shots tile the segment.
6. Imagery-type MV constraints: no narrative acting; silhouettes, light threads, reflections.
7. Instrumental segments use ambient_hold, reuse previous shot's image.
8. All `generation/*` prompts in English.
9. `composition`, `camera`, `motion_design` use predefined enums only.

## Core Dependencies

### Contracts

Full index: `contracts/README.md`

Priority directories:
- `contracts/user-requirements/`
- `contracts/lyrics-timing/`
- `contracts/song-sections-llm/`
- `contracts/segment-interpretation/`
- `contracts/shot-plan/`
- `contracts/mv-treatment/` (optional sidecar)
- `contracts/mv-storyboard/` (legacy appendix)

## Collaboration Boundaries

- **workflow**: owns stage orchestration, artifact dependencies, hard constraints, entry behavior
- **`writer/mv-treatment`**: owns optional treatment prose and creative concept development
- **`director/storyboard`** (appendix): owns shot-level beat-sync planning

## Early Exit Rules

Valid completion points:
- after `lyrics-timing.json` + `song-sections-llm.json` (Stage 2)
- after `segment-interpretation.json` (Stage 3)
- after `shot-plan.json` (Stage 4)
- after `image-prompts.json` (Stage 5)

## Intermediate Artifact Recovery

If the user provides an existing artifact, resume from the nearest valid stage:

| Existing Artifact | Resume at |
|------------------|-----------|
| `lyrics-timing.json` + `song-sections-llm.json` | Stage 3 (segment interpretation) |
| `segment-interpretation.json` | Stage 4 (shot plan) |
| `shot-plan.json` | Stage 5 (image prompts) |
| `image-prompts.json` | Done — image prompts is the current terminal stage |

Do not rerun earlier stages unless the user asks for revision.

## Artifact Layout

```
<project_root>/
├── project_meta.json
├── user_requirements.json
├── lyrics-timing.json
├── song-sections-llm.json
├── segment-interpretation.json
├── shot-plan.json
├── image-prompts.json
├── image-generation-queue.json
├── asset-manifest.json
├── image-selection-review.json
├── selected-asset-manifest.json
├── video-prompts.json
├── timeline.json
├── assets/
│   ├── images/
│   │   ├── candidates/        (generated, one per gen task)
│   │   └── selected/           (post-review picks)
│   └── videos/
│       ├── candidates/         (generated video clips)
│       └── selected/           (post-review picks)
├── characters.json              (optional)
├── characters/                  (optional)
├── scene_design.json            (optional)
└── scenes/                      (optional)
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
