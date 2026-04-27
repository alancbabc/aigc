---
name: mv-lrc-workflow
description: Master workflow for music video production from LRC format. Orchestrates LRC parsing, song structure analysis, creative treatment, storyboard generation, keyframe generation, LTX video rendering, and final assembly.
trigger: Use when the user provides LRC format lyrics and wants a complete MV pipeline. Differs from mv-production by using LRC as primary input rather than manual song structure.
---

# MV-LRC-Workflow

## Overview

This workflow transforms LRC format files into complete music videos.

It differs from `mv-production`:
- **Input**: LRC file (not manual song structure)
- **Automation**: Stage 1 automatically parses LRC to song-structure.json
- **Focus**: Streamlined LRC-to-video pipeline

## Core Difference From Other Workflows

| Dimension | Film Production | News Commentary | MV-LRC-Workflow |
|-----------|----------------|-----------------|------------------|
| Driver | Story / script | Article / evidence | **LRC timestamps** |
| Timeline | Narrative rhythm | Spoken-line duration | **LRC timestamps** |
| Visual logic | Causal coherence | Information delivery | **Beat + section sync** |
| Input format | Manual | Article/URL | **LRC file** |

## Inputs

Required:
- LRC file with timestamps and section labels
- Song audio file (mp3/wav)

Optional:
- Visual style reference
- Target duration

## Outputs

| Stage | Output | Description |
|-------|-------|-------------|
| 0 | `user_requirements.json` | Project scope confirmed |
| 1 | `song-structure.json` | **Parsed from LRC** |
| 2 | `lyrics-analysis.json` | Visual imagery extraction |
| 3 | `mv-treatment.json` | Creative direction |
| 4 | `characters.json` | Character designs |
| 5 | `scene_design.json` | Scene worlds |
| 6 | `storyboard.json` | **Beat-synced shots** |
| 7 | `keyframe-prompts.json` | Keyframe prompts |
| 8 | `keyframes/` | Keyframe images |
| 9 | `video-prompt-drafts.json` | Draft prompts |
| 10 | `video-ltx-prompts.json` | Optimized prompts |
| 11 | `video-plan.json` | Render plan |
| 12 | `video-assets/` | Generated clips |
| 13 | `video/final/output.mp4` | **Final 16:9 output** |

## Workflow Stages

### Stage 0: Requirement Intake

Goal: Lock project scope, MV type, inputs

Input: LRC file + audio file

Output: `user_requirements.json`

### Stage 1: LRC Parsing & Song Structure (UNIQUE)

This stage is unique to MV-LRC-Workflow.

**Execution**:
```bash
python scripts/build_song_structure.py input.lrc -o song-structure.json -t "Song Title" -a "Artist"
```

Output: `song-structure.json`

**LRC Format Supported**:
```text
[00:00.00](Intro)
[00:15.00](Verse 1)
[00:30.50]第一句歌词
[00:34.20]第二句歌词
[01:00.00](Chorus)
```

### Stage 2: Lyrics Analysis

Goal: Extract visual imagery, emotions, metaphors

Input: `song-structure.json`

Output: `lyrics-analysis.json`

### Stage 3: MV Treatment

Goal: Creative direction per section

Input: `lyrics-analysis.json`

Output: `mv-treatment.json`

### Stage 4-5: Character & Scene Design

Goal: Define visual world

Outputs: `characters.json`, `scene_design.json`

### Stage 6: MV Storyboard Generation

**Execution**:
```bash
python scripts/build_mv_storyboard.py song-structure.json -o storyboard.json -t mixed
```

Output: `storyboard.json`

Each shot includes:
- `start_time`, `end_time` (aligned to LRC timestamps)
- `section_ref` (maps to song-structure.json)
- `camera`, `action` suggestions
- `beat_sync` metadata

### Stage 7: Keyframe Prompts Generation

**Execution**:
```bash
python scripts/generate_keyframes.py storyboard.json -o keyframe-prompts.json
```

Output: `keyframe-prompts.json`

### Stage 8: Keyframe Image Generation (via Art Skill)

Use `art/keyframe-generation` skill to generate actual images from prompts.

### Stage 9: Video Prompt Drafts

**Execution**:
```bash
python scripts/build_video_plan.py storyboard.json -o video-prompt-drafts.json -d video-assets
```

Output: `video-prompt-drafts.json`

### Stage 10: LTX Prompt Optimization

Optimize prompts using `_prompts/ModelGuides/LTX-Video/`

### Stage 11: Video Generation Plan

**Execution**:
```bash
python scripts/build_video_plan.py storyboard.json -o video-plan.json -d video-assets
```

Output: `video-plan.json`

### Stage 12: Video Asset Generation

Execute LTX video rendering via `generation/ltx23-video` skill.

Render modes:
- `text_image_to_video_high_quality` - Keyframe + text prompt
- `audio_to_video` - Audio driven (for performance MV)
- `image_audio_ffmpeg` - Static image + Ken Burns effect

### Stage 13: Timeline Assembly

**Execution**:
```bash
python scripts/assemble_mv.py --video-plan video-plan.json --song song.mp3 --output output.mp4
```

Output: `video/final/output.mp4` (16:9)

## Hard Constraints

1. All shot time windows must fall within their referenced section range
2. Song audio is the master timeline - no synthetic audio replacement
3. Stage 6 cannot start before Stage 1 succeeds
4. Stage 13 uses original song audio, not generated audio

## Usage

### Quick Start

```bash
# 1. Parse LRC to song structure
python scripts/build_song_structure.py examples/input/sample.lrc -o song-structure.json -t "Song Title" -a "Artist"

# 2. Generate storyboard
python scripts/build_mv_storyboard.py song-structure.json -o storyboard.json -t mixed

# 3. Generate keyframe prompts
python scripts/generate_keyframes.py storyboard.json -o keyframe-prompts.json

# 4. Build video plan
python scripts/build_video_plan.py storyboard.json -o video-plan.json -d video-assets
```

### Full Pipeline

```bash
# Stage 1: LRC → Song Structure
python scripts/build_song_structure.py input.lrc -o song-structure.json -t "Song Title" -a "Artist"

# Stage 2-3: Analysis & Treatment (manual or via Writer skill)

# Stage 4-5: Character & Scene (via Art skill)

# Stage 6: Storyboard
python scripts/build_mv_storyboard.py song-structure.json -o storyboard.json -t mixed

# Stage 7: Keyframe prompts
python scripts/generate_keyframes.py storyboard.json -o keyframe-prompts.json

# Stage 8: Keyframe generation (via art/keyframe-generation)

# Stage 9: Video prompts
python scripts/build_video_plan.py storyboard.json -o video-plan.json -d video-assets

# Stage 10-12: Video generation (via generation/ltx23-video)

# Stage 13: Final assembly
python scripts/assemble_mv.py --video-plan video-plan.json --song song.mp3 --output output.mp4
```

## Dependency Scripts

| Script | Purpose |
|--------|---------|
| `parse_lrc.py` | Core LRC parsing |
| `build_song_structure.py` | LRC to song-structure.json |
| `build_mv_storyboard.py` | Storyboard generation |
| `generate_keyframes.py` | Keyframe prompts |
| `build_video_plan.py` | Video render plan |
| `assemble_mv.py` | Final video assembly |

## Related Skills

- `writer/mv-treatment` - MV creative treatment
- `art/keyframe-generation` - Keyframe generation
- `generation/ltx23-video` - Video rendering

## Contracts

- `contracts/song-structure/` - Song structure schema