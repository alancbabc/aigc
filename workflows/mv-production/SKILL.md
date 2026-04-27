---
name: mv-production
description: Master workflow for music video production. Orchestrates song analysis, lyrics interpretation, creative development, visual planning, asset generation, and final assembly from song input to finished MV output.
trigger: Use when the user wants an end-to-end music video, MV, or song-driven visual project rather than a single isolated task or a narrative film.
---

# MV Production

## Overview

This is the master workflow for music video production inside this repo.

It is responsible for:

- turning a song and its lyrics into staged visual production tasks
- analyzing song structure and lyrical imagery as the primary time and emotion drivers
- routing work to the correct leaf skills
- enforcing artifact contracts
- applying knowledge extraction before generation
- running review passes before downstream stages continue
- assembling final video with the original song audio track

This workflow is the orchestration entry for MV production.
It defines stage order, artifact dependencies, and hard gates.
It does not replace Writer, Art, Director, or Generation leaf-skill rules inside the master document.

## Core Difference From Other Workflows

| Dimension | Film Production | News Commentary | **MV Production** |
|-----------|----------------|-----------------|-------------------|
| Driver | Story / script | Article / evidence | **Song + lyrics** |
| Timeline | Narrative rhythm | Spoken-line duration | **Musical beat + section structure** |
| Visual logic | Causal coherence | Information delivery | **Emotion + imagery + beat sync** |
| Transition basis | Plot need | Visual-type switching | **Section boundary (verse/chorus/bridge)** |
| Audio handling | Optional dubbing | TTS-generated anchor audio | **Original song is the master audio track** |

## Inputs

- required: song audio file (mp3 / wav)
- required: lyrics text (LRC format with timestamps preferred, plain text accepted)
- required: MV type (`narrative` / `performance` / `concept` / `mixed`)
- optional: visual style reference (director style, reference MV links)
- optional: target duration (defaults to song duration)
- optional: performer description or reference images
- optional: model preferences and confirmation preferences

## Outputs

- one or more stage artifacts, depending on where the user wants to stop
- common artifacts include:
  - `project_meta.json`
  - `user_requirements.json`
  - `song-structure.json`
  - `lyrics-analysis.json`
  - `mv-treatment.json`
  - `characters.json`
  - `characters/`
  - `scene_design.json`
  - `scenes/`
  - `storyboard.json`
  - `storyboard-review.json`
  - `test-shoots.json`
  - `keyframe-prompts.json`
  - `keyframe-images.json`
  - `keyframe-review.json`
  - `keyframes/`
  - `video-prompt-drafts.json`
  - `video-ltx-prompts.json`
  - `video-plan.json`
  - `video-assets.json`
  - `video-assets/`
  - `video/final/output.mp4`

The workflow's done condition depends on the user-requested stopping stage.

## Workflow Rules

### Prompt Language Rule

In this standard workflow, all prompts sent into `generation/*` must be in English.

### Song As Master Timeline

The original song audio is the single source of truth for all timing decisions. Every downstream artifact must reference the song timeline, not invent independent timing.

### MV Type Branching

The workflow supports four MV types. The type selected at Stage 0 affects creative development (Stage 3) and visual planning (Stage 6) but does not change the overall stage sequence:

- `narrative`: story-driven, scenes map to plot beats aligned with song sections
- `performance`: performer-driven, choreography and stage presence aligned with musical energy
- `concept`: imagery-driven, abstract visual metaphors unfold with lyrical themes
- `mixed`: interleaves narrative, performance, and concept threads across song sections

### Use This Workflow When

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

### First Contact

Confirm these project-level inputs first:

- `song_file_path`
- `lyrics_source` (LRC file / plain text / embedded in audio)
- `mv_type` (`narrative` / `performance` / `concept` / `mixed`)
- `visual_style_reference`
- `director_style_reference`
- `style_intensity`
- `performance_style` (`lip_sync` / `dance` / `instrument` / `static_pose`)
- `visual_mood_keywords`
- `output_goal`
- `model_preference`
- `confirmation_mode`

Recommended stored artifacts:

- `project_meta.json`
- `user_requirements.json`

## Knowledge Dependencies

Read by stage, not all at once.

### Song Analysis And Lyrics Interpretation

- `_knowledge/Narrative/` for emotion arc and rhythm patterns
- `_knowledge/Genre/` for music-genre visual conventions

### Creative Development

- `_knowledge/Genre/` for genre-appropriate visual language
- `_knowledge/Narrative/` for story structure (narrative MV type)
- `_knowledge/FamousDirectors/` when a style reference exists
- `_knowledge/Actor/` for performance references

### Character And Performer Design

- `_knowledge/Genre/`
- `_knowledge/Actor/`
- `_knowledge/FamousDirectors/` when a style reference exists

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

### Before Song Structure Analysis

Extract:

- `song_genre`
- `tempo_feel`
- `energy_arc`
- `section_pattern` (verse-chorus-bridge layout)

### Before Lyrics Analysis

Extract:

- `lyrical_themes`
- `dominant_imagery`
- `emotion_trajectory`
- `narrative_potential`

### Before MV Treatment

Extract:

- `visual_style`
- `color_strategy`
- `performance_choreography` (performance type)
- `narrative_thread` (narrative type)
- `metaphor_sequence` (concept type)
- `director_style_reference`
- `style_intensity`

### Before Character / Performer Package

Extract:

- `role_archetype`
- `body_language`
- `costume_anchor`
- `performance_persona`

### Before Storyboard

Extract:

- `shot_function`
- `beat_structure`
- `transition_need`
- `environment_anchor_plan`
- `beat_sync_strategy`

These extraction results may live inside stage artifacts or intermediate planning notes, but they must exist before downstream production.

## Workflow Stages

### Stage 0: Requirement Intake

Goal:

- lock project scope, MV type, song reference, and creative direction

Dependencies:

- `_knowledge/Genre/`
- `_knowledge/Narrative/`
- `_knowledge/FamousDirectors/` when needed

Outputs:

- `project_meta.json`
- `user_requirements.json`

MV-specific fields in `project_meta.json`:

- `mv_type`: `narrative` / `performance` / `concept` / `mixed`
- `song_file_path`: path to the song audio file
- `lyrics_source`: lyrics input type (LRC / plain text / embedded)
- `performance_style`: `lip_sync` / `dance` / `instrument` / `static_pose`
- `visual_mood_keywords`: user-supplied mood keywords

### Stage 1: Song Structure Analysis

This stage is unique to the MV workflow. No other workflow has it.

Goal:

- decompose the song into labeled time sections that drive all downstream visual planning

Execution:

- if LRC timestamps are available, parse section boundaries from lyric timing gaps and repetition patterns
- if only plain text lyrics are available, infer section structure from lyric repetition, stanza breaks, and content shifts
- future: audio analysis tools (librosa / essentia) can auto-detect BPM and section boundaries

Executors:

Step 1 — parse lyrics into structured line data:

- `python workflows/mv-production/scripts/parse_lyrics.py --input <lyrics-file> --output <project>/parsed-lyrics.json --infer-sections`

Step 2 — build `song-structure.json` scaffold from parsed lyrics:

- `python workflows/mv-production/scripts/build_song_structure.py --parsed-lyrics <project>/parsed-lyrics.json --song-title "<title>" --artist "<artist>" --total-duration <seconds> --bpm <bpm> --output <project>/song-structure.json`

Step 3 — LLM enrichment of scaffold fields:

- read the scaffold `song-structure.json`
- for each section, fill in `mood`, `energy_level`, `visual_suggestion`, `transition_to_next`, and `lyrics_summary` based on lyrical content and musical context
- optionally write enrichment as a separate JSON and merge via `--enrich`: `python workflows/mv-production/scripts/build_song_structure.py --parsed-lyrics <project>/parsed-lyrics.json --enrich <project>/song-structure-enrichment.json --output <project>/song-structure.json`
- if BPM is unknown, estimate from verse pacing or genre conventions and supply via `--bpm`

Primary artifact:

- `song-structure.json`

Contracts:

- `contracts/song-structure/song-structure.schema.json`
- `contracts/song-structure/song-structure.example.json`

Key fields:

- `song_title`, `artist`, `total_duration_seconds`
- `bpm`, `time_signature`
- `mood_arc`: ordered list of mood labels across the song
- `sections[]`: each entry contains `section_id`, `section_type` (intro / verse / pre_chorus / chorus / bridge / outro / instrumental), `start_time`, `end_time`, `duration_seconds`, `mood`, `energy_level`, `lyrics_lines` or `lyrics_summary`, `visual_suggestion`

### Stage 2: Lyrics Imagery Analysis

This stage is unique to the MV workflow. No other workflow has it.

Goal:

- extract visual imagery, emotional arcs, and narrative potential from lyrics to inform creative development

Dependencies:

- `_knowledge/Narrative/`
- `_knowledge/Genre/`

Primary artifact:

- `lyrics-analysis.json`

Contracts:

- `contracts/lyrics-analysis/lyrics-analysis.schema.json`
- `contracts/lyrics-analysis/lyrics-analysis.example.json`

Key fields:

- `themes`: extracted lyrical themes (love, departure, freedom, etc.)
- `imagery_map`: per-section core visual imagery
- `emotion_arc`: per-section emotion curve, cross-validated with `song-structure.json` mood_arc
- `narrative_potential`: assessment of whether lyrics support storytelling vs. pure imagery
- `visual_metaphors`: list of metaphors convertible to screen imagery
- `color_mood_suggestions`: color palette suggestions based on lyrical mood
- `performance_cues`: suggested performer actions, expressions, and body language per section

### Stage 3: MV Creative Treatment

Goal:

- define the overall creative direction and per-section visual strategy for the MV

This stage branches by MV type:

| MV Type | Treatment Focus | Skill Routing |
|---------|----------------|---------------|
| `narrative` | story outline mapped to song sections | reuse `writer/story-outline` with `song-structure.json` as input constraint, then produce `mv-treatment.json` |
| `performance` | choreography plan + stage/location switching | `writer/mv-treatment` |
| `concept` | imagery sequence + visual metaphor unfolding | `writer/mv-treatment` |
| `mixed` | interleaved narrative + performance thread planning | combination of both |

Primary skill:

- `writer/mv-treatment`

Dependencies:

- `_knowledge/Genre/`
- `_knowledge/Narrative/`
- `_knowledge/FamousDirectors/`
- `_knowledge/Actor/`
- `_prompts/PromptTemplates/Style/`

Primary artifact:

- `mv-treatment.json`

Contracts:

- `contracts/mv-treatment/mv-treatment.schema.json`
- `contracts/mv-treatment/mv-treatment.example.json`

Key fields:

- `concept_type`: MV type
- `visual_style`: locked visual style including style tokens from `_prompts/PromptTemplates/Style/`
- `color_palette`: color scheme for the MV
- `section_plans[]`: per-song-section visual plan (scene, characters, action, mood, camera intent)
- `narrative_thread`: story arc (for narrative type)
- `performance_plan`: choreography and staging plan (for performance type)
- `imagery_sequence`: ordered visual metaphor plan (for concept type)
- `cross_cutting_rules`: rules for interleaving narrative/performance/imagery threads (for mixed type)

### Stage 4: Character And Performer Design

Primary skills:

- `writer/character-profile`
- `art/character-three-view`

Goal:

- define characters or performers visually and produce usable character references
- for performance-type MVs, "characters" are the performers/singers with locked visual identity

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

### Stage 4A: Character Review

Primary review skill path:

- `art/character-three-view`
- `generation/qwen2.5-vl` as review support

Goal:

- verify three-view completeness and character/performer consistency before downstream stages depend on them

Review artifact:

- `art/character-three-view/three-view-review.example.json`
- `art/character-three-view/three-view-review.schema.json`

### Stage 5: Scene Design

Primary skill:

- `art/scene-design`

Goal:

- create scene bases and multi-view sets for each visual world in the MV
- MVs often use 3-5 completely different visual worlds (e.g. reality + memory + stage + fantasy), and strong visual contrast between scenes is an important MV technique

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

### Stage 5A: Scene Review

Goal:

- verify environment identity, lighting logic, anchor consistency, and multi-view stability
- verify visual contrast between different MV worlds is strong enough

Review artifact:

- `art/scene-design/scene-review.example.json`
- `art/scene-design/scene-review.schema.json`

### Stage 6: MV Storyboard

Primary skills:

- `director/storyboard`
- `director/transition` when a boundary needs explicit transition design

Goal:

- convert the MV treatment into beat-synchronized shots with camera language, environment logic, and transition planning
- every shot must align with `song-structure.json` time windows

Dependencies:

- `_knowledge/Camera/`
- `_knowledge/Narrative/`
- `_knowledge/Transition/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`

Inputs:

- required: `song-structure.json` (authoritative timeline)
- required: `mv-treatment.json` (per-section visual plan)
- required: `characters.json` (character text profiles; image refs optional at this stage)
- optional: `scene_design.json` (scene text descriptions; image refs optional at this stage)
- optional: `lyrics-analysis.json` (for performance cues and visual metaphors)

Outputs:

- `storyboard.json`

Contracts:

- `contracts/mv-storyboard/mv-storyboard.schema.json`
- `contracts/mv-storyboard/mv-storyboard.example.json`

MV storyboard extends the standard storyboard with beat-sync fields. Each shot entry must include:

- `section_ref`: reference to the song section from `song-structure.json`
- `beat_sync`: `start_beat`, `end_beat`, `cut_on_beat` (whether the cut falls on a musical beat)
- `lyrics_line_refs`: which lyrics lines this shot covers
- `performance_type`: `lip_sync` / `dance` / `reaction` / `b_roll` / `narrative_action` / `concept_imagery`
- `time_window`: precise `start_time` and `end_time` from the song timeline
- `render_mode_hint`: `audio_to_video` / `text_image_to_video_high_quality` / `image_audio_ffmpeg`

#### Stage 6 Execution Guidance

Stage 6 reuses the base `director/storyboard` skill rules (beat extraction, merge vs split, duration support, scene-level review) and extends them for MV. The following steps define the MV storyboard execution flow.

##### Step 1: Load and validate upstream artifacts

1. Read `song-structure.json`. Extract the full section list with `section_id`, `start_time`, `end_time`, `bpm`, and `energy_level`.
2. Read `mv-treatment.json`. Map each `section_plans[]` entry to its `section_ref`.
3. Read `characters.json`. Collect character IDs for `character_refs`.
4. If `scene_design.json` exists, collect scene IDs for `scene_id` / `visual_world`. Otherwise infer scene descriptions from `mv-treatment.json` `section_plans[].visual_world`.

##### Step 2: Generate scenes from sections

Create one storyboard `scene` per song section. Each scene maps 1:1 to a section in `song-structure.json`:

- `scene_id`: a readable identifier (e.g. `scene_intro_city`, `scene_verse1_streets`)
- `section_ref`: must exactly match `section_id` from `song-structure.json`
- `scene_description`: from `mv-treatment.json` `section_plans[].visual_world` or scene design
- `visual_world`: from treatment

When a single song section spans two distinct visual worlds (e.g. present + memory in a chorus), the section still maps to one storyboard scene, but the shots within it switch visual worlds via different `character_refs` and `action_description`.

##### Step 3: Plan shots within each scene

For each scene, use the treatment's `key_visual_moments`, `camera_approach`, and `energy_match` to determine shot count and pacing:

**Shot density by energy level:**

| Energy Level | Typical Shot Duration | Shots per 30s |
|-------------|----------------------|---------------|
| low | 6–10s | 3–5 |
| medium_low | 5–8s | 4–6 |
| medium | 4–7s | 5–8 |
| medium_high | 3–5s | 6–10 |
| high / peak | 2–4s | 8–15 |

These are guidelines, not hard rules. Duration support rules from `director/storyboard` still apply: every shot must be justified by action, dialogue, emotion, or camera movement.

**Time window allocation:**

1. Each shot's `time_window.start_time` and `time_window.end_time` must fall within the parent section's time range.
2. Shots within a scene must tile the section's time range without gaps or overlaps.
3. Compute `duration_seconds = end_time - start_time`.

**Beat sync computation:**

1. `start_beat = ceil(start_time * bpm / 60)` (1-based)
2. `end_beat = ceil(end_time * bpm / 60)`
3. `cut_on_beat`: set to `true` when the shot's entry point aligns with a musical downbeat. Section-boundary cuts and high-energy chorus cuts should prefer `cut_on_beat=true`.
4. `beat_emphasis`: `downbeat` for strong entries, `upbeat` for anticipatory entries, `offbeat` for syncopated moments, `none` for continuous flow shots.

**Lyrics line refs:**

- Map `lyrics_line_refs` from `song-structure.json` sections to individual shots based on timing.
- A shot that covers lines 3–4 of verse 1 should list `["line_03", "line_04"]`.
- Instrumental or b-roll shots have empty `lyrics_line_refs`.

##### Step 4: Assign performance type and render mode hint

**Performance type decision tree:**

| Condition | performance_type | render_mode_hint |
|-----------|-----------------|-----------------|
| Shot shows character singing / mouthing lyrics | `lip_sync` | `audio_to_video` |
| Shot shows dance or choreography | `dance` | `audio_to_video` |
| Shot shows musician playing instrument | `instrument` | `audio_to_video` |
| Shot shows character reacting (not singing) | `reaction` | `text_image_to_video_high_quality` |
| Shot is environmental / establishing / b-roll | `b_roll` | `text_image_to_video_high_quality` |
| Shot drives narrative action (walking, running, etc.) | `narrative_action` | `text_image_to_video_high_quality` |
| Shot is abstract visual metaphor | `concept_imagery` | `text_image_to_video_high_quality` |
| Shot is static visual (photo, document, still) | `b_roll` | `image_audio_ffmpeg` |

The `render_mode_hint` is advisory. Stage 9 (video prompt drafts) makes the final render mode decision.

##### Step 5: Plan transitions

MV transition rules:

- **section boundary** (verse → chorus, chorus → bridge): strong transition (style switch, energy jump, scene change, dissolve, or smash cut). Call `director/transition` when the boundary is complex.
- **within-section shot change**: weak transition (cut / match cut, aligned to beat)
- **bridge section entry**: dramatic visual shift — sudden stillness, color temperature reversal, or single long take
- **intro first shot**: establishing shot, slow reveal, fade from black
- **outro last shot**: resolution, wide pullback, fade to black or freeze frame
- **same-world consecutive shots**: prefer straight cut on beat
- **cross-world cuts** (present ↔ memory): prefer dissolve or match cut

For each shot, set `transition_in` and `transition_out` accordingly.

##### Step 6: Scene-level review pass

After generating all shots for a scene, run the base `director/storyboard` review checklist plus MV-specific checks:

1. **Beat coverage**: do the shots tile the section's time range completely?
2. **Lyrics coverage**: is every `lyrics_line_ref` in the section assigned to at least one shot?
3. **Energy match**: does shot density match the section's `energy_level`?
4. **Transition strength**: are section-boundary transitions visually stronger than within-section cuts?
5. **Performance plausibility**: do lip-sync shots cover enough duration for the assigned lyrics lines?
6. **Redundancy check**: adjacent shots with the same subject, angle, and emotional function should be merged.
7. **Duration support**: every shot's duration must be justified per `director/storyboard` rules.

##### Fast-path: text-only storyboard without generated images

When Stage 4/5 image generation is not yet available, Stage 6 can still produce a complete `storyboard.json`:

- Use `character_refs` with text IDs (e.g. `["protagonist"]`) instead of image paths.
- Use `visual_world` text descriptions instead of `scene_id` image references.
- The storyboard contract does not require image file paths. All image-dependent fields (`source_image_paths`, etc.) belong to later stages (Stage 7+).
- This produces a structurally valid, review-ready storyboard that can immediately drive Stage 7 (test shoots) and Stage 8 (keyframe planning) once image generation becomes available.

### Stage 6A: Storyboard Review

Goal:

- verify beat alignment accuracy
- verify section-boundary transitions are strong enough
- verify shot density matches musical energy
- remove redundant shots and fix unsupported durations

Review artifact:

- `director/storyboard/storyboard-review.example.json`
- `director/storyboard/storyboard-review.schema.json`

### Stage 7: Test Shoots And Frame Planning

Primary skills:

- `director/test-shoots`
- `director/transition` when frame planning depends on transition complexity

Goal:

- convert the MV storyboard into shot prompts, frame plans, and transition-aware boundary planning

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

- generate frame prompts and frame images that preserve progression, character consistency, scene consistency, and emotional arc

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

- verify frame progression matches emotional arc
- verify intent alignment with MV treatment
- verify character and performer consistency
- verify scene consistency

Review artifact:

- `art/keyframe-generation/keyframe-review.example.json`
- `art/keyframe-generation/keyframe-review.schema.json`

### Stage 9: Video Prompt Drafts

Goal:

- convert reviewed keyframe outputs into raw video prompt drafts

MV-specific render mode routing:

| Scene Type | Render Mode | Reason |
|-----------|-------------|--------|
| Performance / lip sync | `audio_to_video` | audio drives lip and body movement |
| Narrative / imagery shots | `text_image_to_video_high_quality` | keyframe + text prompt is sufficient |
| Static imagery | `image_audio_ffmpeg` | static image + Ken Burns / slow pan effect |

Outputs:

- `video-prompt-drafts.json`

Contracts:

- `workflows/film-production/contracts/video-prompt-drafts/video-prompt-drafts.schema.json`
- `workflows/film-production/contracts/video-prompt-drafts/video-prompt-drafts.example.json`

### Stage 10: LTX Prompt Optimization

Goal:

- optimize raw video prompts using the LTX prompt guide for LTX-2 compatibility

Primary reference:

- `_prompts/ModelGuides/LTX-Video/SKILL.md`

Outputs:

- `video-ltx-prompts.json`

Contracts:

- `workflows/film-production/contracts/video-ltx-prompts/video-ltx-prompts.schema.json`
- `workflows/film-production/contracts/video-ltx-prompts/video-ltx-prompts.example.json`

Rules:

- do not overwrite the raw prompt drafts; keep both artifacts as first-class outputs
- before any `ltx23-video` request is finalized, pass the raw prompt through the LTX prompt guide

### Stage 11: Video Generation Plan

Goal:

- create a minimal, executable video generation plan from optimized prompts

Primary skill:

- `generation/ltx23-video`

Outputs:

- `video-plan.json`

Contracts:

- `contracts/mv-video-plan/mv-video-plan.schema.json`
- `contracts/mv-video-plan/mv-video-plan.example.json`

MV-specific requirements:

- every render item must carry precise `start_time` and `end_time` matching the song timeline
- every render item must reference its `section_ref` from `song-structure.json`
- render items are ordered by song timeline position
- `video-plan.json` must reference the optimized prompt entries from `video-ltx-prompts.json`

Routing rules:

- prefer `text_image_to_video_high_quality` for imagery and narrative shots
- prefer `audio_to_video` only when the project has valid audio inputs for performance shots
- prefer `image_audio_ffmpeg` for static imagery segments
- for non-CUT section boundaries, call `director/transition` and persist a separate transition clip entry

### Stage 12: Video Asset Generation

Primary skill:

- `generation/ltx23-video`

Goal:

- execute the per-shot LTX requests defined in `video-plan.json`
- generate reusable video assets

Outputs:

- `video-assets.json`
- `video-assets/`

Asset expectations:

- each video asset maps back to a specific `section_ref`, `shot_id`, or equivalent stable upstream identifier
- each asset entry records the chosen LTX mode, input image paths, output video path, and generation status
- each asset entry preserves references to both the raw prompt draft and the optimized LTX prompt used for execution
- output paths stay inside the project memory tree (e.g. `video-assets/verse1_shot_03.mp4`)

### Stage 12A: Video Asset Review

Goal:

- verify that generated video assets preserve keyframe intent, scene identity, and shot-level motion direction
- verify beat-sync alignment for performance shots
- catch obvious failures before downstream assembly

Review focus:

- motion should extend the approved keyframe progression
- character identity, costume anchor, and environment anchor should remain consistent
- performance timing should match musical rhythm
- if a generated clip materially breaks shot intent, revise the raw prompt draft and regenerate

### Stage 13: Timeline Assembly

This stage is unique to the MV workflow. It is analogous to Stage 12 in news-commentary but with a critical difference: the original song audio replaces all segment audio tracks.

Goal:

- assemble all video segments in song-timeline order
- replace all segment audio with the original song audio track
- produce the final MV output

Execution steps:

1. sort all video segments by `start_time` from `video-plan.json`
2. trim each segment to its precise time window
3. concatenate segments using FFmpeg
4. overlay the original song audio track, replacing any per-segment audio
5. optionally add fade-in/fade-out transitions at MV boundaries
6. optionally burn lyrics subtitles (from LRC or aligned timestamps)

Executor:

- `scripts/assemble_mv.py`

Outputs:

- `video/segments/` (trimmed individual segments)
- `video/final/output.mp4` (final assembled MV)

Optional variants:

- lyrics-subtitled version
- vertical-crop version for mobile platforms

### Stage 14: Final Output

Goal:

- deliver the finished MV file and optional variants

Outputs:

- `video/final/output.mp4`
- optional: `video/final/output_subtitled.mp4`
- optional: `video/final/output_vertical.mp4`

## Hard Constraints

These constraints stay at the orchestration layer and must not be delegated away:

1. The workflow must advance in the direction `song analysis → lyrics analysis → treatment → character → scene → storyboard → keyframe → video → assembly`.
2. Every shot in the storyboard must reference a valid `section_ref` from `song-structure.json`.
3. Every shot's `time_window` must fall within its referenced section's time range.
4. Stage 6 (storyboard) cannot start before Stage 1 (song structure) and Stage 3 (treatment) succeed.
5. Stage 13 (assembly) must use the original song audio as the master track. No generated or synthetic audio may replace the song.
6. Render items in `video-plan.json` must be ordered by song timeline. Gaps or overlaps in coverage must be resolved before generation.
7. Section-boundary transitions must be visually stronger than within-section shot changes.

## Related Skills

- MV creative treatment: `writer/mv-treatment`
- character profiles: `writer/character-profile`
- story outline (narrative MV): `writer/story-outline`
- character three-view: `art/character-three-view`
- scene design: `art/scene-design`
- storyboard: `director/storyboard`
- transition design: `director/transition`
- test shoots: `director/test-shoots`
- keyframe generation: `art/keyframe-generation`
- LTX video generation: `generation/ltx23-video`
- LTX prompt guide: `_prompts/ModelGuides/LTX-Video/`

## Contracts

Full index: `contracts/README.md`

### New Contracts (MV-specific)

- `contracts/song-structure/` — song section decomposition
- `contracts/lyrics-analysis/` — lyrics imagery and emotion analysis
- `contracts/mv-treatment/` — MV creative treatment
- `contracts/mv-storyboard/` — beat-synchronized storyboard (extends standard storyboard)
- `contracts/mv-video-plan/` — video plan with song-timeline alignment

### Reused Contracts

- `writer/character-profile/` — character profiles
- `art/character-three-view/` — character three-view sheets
- `art/scene-design/` — scene design
- `director/storyboard/` — base storyboard structure
- `director/test-shoots/` — test shoot plans
- `art/keyframe-generation/` — keyframe prompts and images
- `workflows/film-production/contracts/video-prompt-drafts/` — video prompt drafts
- `workflows/film-production/contracts/video-ltx-prompts/` — optimized LTX prompts

## VLM Assist Points

Use `generation/qwen2.5-vl` as a review and analysis helper at these points:

- character/performer sheet review (Stage 4A)
- scene board review (Stage 5A)
- boundary-frame analysis for transition decisions (Stage 6)
- keyframe review support (Stage 8A)
- video asset review for beat-sync and motion quality (Stage 12A)

## Early Exit Rules

This workflow does not need to run to the end if the user only wants a partial result.

Valid completion points:

- after `song-structure.json`
- after `lyrics-analysis.json`
- after `mv-treatment.json`
- after `characters.json` and character views
- after `scene_design.json`
- after `storyboard.json`
- after `test-shoots.json`
- after reviewed `keyframes/`
- after `video-prompt-drafts.json`
- after `video-ltx-prompts.json`
- after `video-plan.json`
- after reviewed `video-assets/`
- after `video/final/output.mp4`

## Intermediate Artifact Recovery

If the user provides an existing artifact, resume from the nearest valid stage:

- `song-structure.json` → continue to lyrics analysis or treatment
- `lyrics-analysis.json` → continue to treatment
- `mv-treatment.json` → continue to character package or scene design
- `characters.json` → continue to scene design, storyboard, or character views
- `storyboard.json` → continue to scene design or test shoots
- `test-shoots.json` → continue to keyframe generation
- `keyframe-images.json` → continue to video prompt drafting, prompt optimization, video planning, or video asset generation
- `video-prompt-drafts.json` → continue to LTX prompt optimization or video planning
- `video-ltx-prompts.json` → continue to video planning or video asset generation
- `video-plan.json` → continue to video asset generation
- `video-assets.json` → continue to timeline assembly

Do not rerun earlier stages unless the user asks for revision.

## Artifact Layout

```text
memory/[date]/[project-name]/v[version]/
├── project_meta.json
├── user_requirements.json
├── song-structure.json
├── lyrics-analysis.json
├── mv-treatment.json
├── characters.json
├── characters/
├── scene_design.json
├── scenes/
├── storyboard.json
├── storyboard-review.json
├── test-shoots.json
├── keyframe-prompts.json
├── keyframe-images.json
├── keyframe-review.json
├── keyframes/
├── video-prompt-drafts.json
├── video-ltx-prompts.json
├── video-plan.json
├── video-assets.json
├── video-assets/
└── video/
    ├── segments/
    └── final/
        └── output.mp4
```

## Orchestration Rules

1. Read the current stage contract before generating output.
2. Run review before handing critical artifacts to the next downstream stage.
3. Move one stage at a time unless the user explicitly wants batching.
4. If the user only wants a local goal, stop at the nearest valid early-exit stage.
5. Let Writer, Art, and Director make the creative decisions; let Generation execute and review.
6. The song timeline is authoritative. Do not invent independent timing at any stage.
7. For section-boundary transitions, defer to `director/transition`; do not improvise transition logic locally.
8. When assembling the final MV, always use the original song audio. Never substitute generated or synthetic audio for the song track.

## Example Flows

### Narrative MV — Full Pipeline

1. The user provides a Chinese pop ballad (mp3 + LRC lyrics) and wants a narrative MV with Wong Kar-wai style.
2. The workflow confirms `mv_type=narrative`, `song_file_path`, `lyrics_source=lrc`, `visual_style_reference=Wong Kar-wai`, `style_intensity=high`, and `output_goal=final_video`.
3. The workflow runs:
   - Stage 0: intake, produce `project_meta.json` and `user_requirements.json`
   - Stage 1: parse LRC, produce `song-structure.json` with sections (intro, verse_1, chorus_1, verse_2, chorus_2, bridge, outro)
   - Stage 2: analyze lyrics imagery, produce `lyrics-analysis.json` with themes, metaphors, and emotion arc
   - Stage 3: create narrative treatment mapping story beats to song sections, produce `mv-treatment.json`
   - Stage 4/4A: design characters using `writer/character-profile` + `art/character-three-view`, review
   - Stage 5/5A: design scenes (3 worlds: rainy city, memory apartment, neon bar), review
   - Stage 6/6A: create beat-synced storyboard with cuts on downbeats, review
   - Stage 7: produce test-shoot plans
   - Stage 8/8A: generate keyframes, review
   - Stage 9: write video prompt drafts with `text_image_to_video_high_quality` for narrative shots
   - Stage 10: optimize prompts for LTX-2
   - Stage 11: create timeline-aligned video plan
   - Stage 12/12A: generate video assets, review
   - Stage 13: assemble segments, overlay original song audio, produce `video/final/output.mp4`
4. The workflow delivers the final MV file.

### Performance MV — Keyframe-Only Output

1. The user provides a dance track (mp3 + plain text lyrics) and wants a performance MV with keyframes only.
2. The workflow confirms `mv_type=performance`, `performance_style=dance`, and `output_goal=keyframes`.
3. The workflow runs:
   - Stage 0: intake
   - Stage 1: infer song structure from lyric patterns (no LRC timestamps)
   - Stage 2: analyze lyrics for performance cues
   - Stage 3: create performance treatment with choreography plan per section
   - Stage 4/4A: design performer visual identity, review
   - Stage 5/5A: design stage/location scenes, review
   - Stage 6/6A: create beat-synced storyboard emphasizing dance moves and camera motion, review
   - Stage 7: produce test-shoot plans
   - Stage 8/8A: generate keyframes capturing key dance poses and energy peaks, review
4. Because the requested output goal is keyframes, the workflow stops there.

### Concept MV — Treatment Only

1. The user provides an ambient electronic track and wants only a creative concept treatment.
2. The workflow confirms `mv_type=concept` and `output_goal=treatment`.
3. The workflow runs:
   - Stage 0: intake
   - Stage 1: analyze song structure
   - Stage 2: analyze abstract imagery potential
   - Stage 3: create concept treatment with visual metaphor sequence
4. Because the requested output goal is treatment, the workflow stops after `mv-treatment.json`.

## Missing Capabilities (Future)

These capabilities are not yet available but can be added later:

| Capability | Purpose | Future Module |
|-----------|---------|---------------|
| Audio structure analysis | auto-detect BPM, section boundaries, energy curves | `generation/audio-analysis` (librosa / essentia) |
| Lyrics timestamp alignment | align plain-text lyrics to audio timestamps | `generation/lyrics-alignment` (whisper forced alignment) |

When these modules become available, Stage 1 can be upgraded to use automated audio analysis instead of manual or LRC-based parsing.

## Changelog

- 2026-04-22: Created MV production workflow with full stage definitions, aligned with film-production and news-commentary patterns.
