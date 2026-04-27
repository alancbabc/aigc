---
name: news-commentary
description: Master workflow for turning one or more news sources into a dual-anchor commentary package with analysis, script, TTS audio, clip planning, render planning, and optional mixed video generation.
trigger: Use when the user provides one or more articles, URLs, or local source packages and wants a dual-anchor commentary format rather than a single-narrator summary.
---

# News Commentary Workflow

## Overview

This workflow turns news articles, URLs, or local news-source packages into a dual-anchor commentary program.

It owns orchestration only:

- entry and intake order
- stage dependencies
- artifact flow
- which child skill owns which stage
- which hard constraints must be satisfied before the next stage begins

It does not replace detailed Writer or Director skill rules.

## Related Skills

- writing rules: `writer/news-commentary-writing`
- clip planning and visual routing: `director/news-commentary-clip-planning`
- stage walkthrough: `README.md`
- contract index: `contracts/README.md`

## Slash Entry

- user-facing entry: `/news-broadcast`
- `/news-broadcast` maps to this `news-commentary` workflow

Builtin anchor visuals and builtin voices are the default path. In the common case, the user only needs to provide:

- one or more article URLs, or
- local document paths

## Use This Workflow When

Use this workflow when the task needs:

- fast commentary for a single news item
- deeper commentary across multiple links
- recurring series production with stable anchor identity
- dual-anchor interaction instead of single-narrator voice-over
- mixed rendering across anchor-led shots and source-image-led clips

Do not use this workflow when the task only needs:

- text analysis with no media production
- standalone TTS or video generation from an already-finished script
- single-anchor or pure narration output

## Default Input Paths

`/news-broadcast` follows this fixed path:

1. use builtin anchor assets and builtin voices
2. collect article URLs or local document paths
3. enter the workflow automatically
4. switch to a custom-asset path only if the user explicitly requests custom people, images, names, or voices

For a local markdown article package, use this path:

1. read the markdown body
2. parse the top-of-document image manifest at Stage 3
3. treat sibling images as first-class source visuals
4. route matched source images into `image_audio_ffmpeg` clips during clip planning

## Stage Map

| Stage | Goal | Primary Artifact | Rule Owner |
|---|---|---|---|
| 0 | intake / preflight | `user_requirements.json` | workflow |
| 1 | article analysis | `article-analysis.json` | workflow |
| 2 | analysis review | `article-review.json` | workflow |
| 3 | source-visual extraction | `source-assets/source-visual-assets.json` | workflow |
| 4 | recurring-show setup | `series-profile.json` | workflow |
| 5 | commentary script generation | `script-skeleton.json` → `script-segments/*.json` → `script.json` | `writer/news-commentary-writing` |
| 6 | script review | `script-review.json` | `writer/news-commentary-writing` |
| 7 | TTS planning and audio generation | `audio/tts-plan.json` / `audio/timeline.json` | workflow |
| 8 | spoken-audio check | review result | workflow |
| 9 | clip planning | `video/clip-plan.json` | `director/news-commentary-clip-planning` |
| 10 | render planning | `video/render-plan.json` | workflow |
| 11 | segment rendering | `video/segments/*.mp4` | workflow |
| 12 | final assembly | `video/final/output.mp4` | workflow |

## Hard Constraints Owned By This Workflow

These constraints stay at the orchestration layer and must not be delegated away:

1. The workflow must advance in the direction `analysis → script → audio → clip-plan → render-plan`.
2. Every clip in `video/clip-plan.json` must declare explicit visual binding.
3. Stage 10 cannot start before Stage 9 succeeds.
4. Stage 10 cannot repair structural Stage 9 failures.
5. Every TTS unit, audio timeline entry, and final clip must stay `<= 15.0` seconds. Any overflow must be fixed upstream first.
6. Any audio entry with `needs_resynthesis=true` cannot flow into clip-plan or render-plan.
7. Output video dimensions follow the selected image dimensions. Aspect mismatches may only use scale + pad, never stretch.

## Minimal Stage Responsibilities

### Stage 1 / 2

- produce commentary-ready analysis rather than a restated article summary
- preserve evidence, boundaries, uncertainty, and promo-tone neutralization needs

### Stage 3

- extract source visuals from doc / docx / markdown inputs
- treat a top-of-document markdown image list as an explicit manifest
- map `标题` to `images[].caption`
- map `说明` to `images[].context_hint`
- resolve image files from the markdown sibling directory with tolerant name matching

Executor:

- `python workflows/news-commentary/scripts/extract_source_visual_assets.py --inputs <doc/docx/md paths...> --output-dir <project>/source-assets`

### Builtin Anchor Assets / Override Path

- anchor assets are not a standalone main-flow stage in the default path
- `female_solo.png`, `male_solo.png`, `duo_far.png`, and `duo_close.png` are builtin defaults supplied by Stage 0 configuration
- custom anchor assets are only introduced when the user explicitly requests overrides
- whether builtin or custom, clip-plan must still receive directly bindable anchor assets
- `duo_frame` remains an explicit clip-planning state, but Stage 10 must resolve that state to concrete render references such as `duo_far.png` and `duo_close.png`

### Stage 5 / 6

The workflow keeps only orchestration rules here:

- `script.json` must be a commentary-ready dual-anchor script
- it must stay aligned with `article-analysis.json` evidence and boundaries
- Stage 5 / 6 must execute through `writer/news-commentary-writing`
- the workflow must not inline-generate, patch, or rewrite `script.json` directly
- detailed Stage 5 artifact chaining, merge rules, length handling, and review rules live in `writer/news-commentary-writing`
- Stage 5 must use the staged Writer-defined flow; one-shot full-script generation is not allowed here
- before Stage 5 is considered successful, `script-skeleton.json` and `script-segments/*.json` must be compatible with `merge_script_stage5.py`
- Stage 5 artifact generation must prefer `segment_no` as the primary segment key; do not rely on `segment_id` for merge identity
- Stage 5 artifacts must remain valid JSON; spoken text may contain quoted phrases, but any embedded double quotes must be escaped correctly during JSON generation
- Stage 6 should not pass a script that is structurally mergeable but still too summary-like or explanation-thin
- script-stage `visual_hint` stays advisory only; it may suggest later source-image support, but it must not override Director-side binding rules
- `opening` / `closing` segment drafting must not tell the program to start on a source image or a solo anchor shot; those beats remain duo-frame at the clip-planning layer

Executor:

- `python workflows/news-commentary/scripts/merge_script_stage5.py --skeleton <project>/script-skeleton.json --segments-dir <project>/script-segments --output <project>/script.json`

### Stage 7 / 8

- consume script-stage spoken-line splitting rather than inventing a first split at audio time
- if any real audio entry exceeds `15s`, resplit upstream by `script_line_id` / `split_group_id` and regenerate only affected artifacts
- no `duration_seconds > 15` entry may remain after Stage 8
- Stage 7 produces `audio/tts-plan.json` as a pre-synthesis plan only; it does not carry realized `audio_path` fields
- after actual TTS generation, Stage 8 must materialize `audio/timeline.json` with real `audio_path` and `duration_seconds` values before any render planning

Executor:

- `node workflows/news-commentary/scripts/build_tts_plan.mjs --script <project>/script.json --series-profile <project>/series-profile.json --output <project>/audio/tts-plan.json`
- local TTS generation may be executed directly from the plan with: `node workflows/news-commentary/scripts/generate_local_tts_from_plan.mjs --tts-plan <project>/audio/tts-plan.json`
- after TTS files are actually generated, materialize `audio/timeline.json` from the real audio files: `python workflows/news-commentary/scripts/build_audio_timeline.py --tts-plan <project>/audio/tts-plan.json --series-profile <project>/series-profile.json --audio-dir <project>/audio --audio-format mp3 --output <project>/audio/timeline.json`
- when `series-profile.json` points to a builtin anchor template, Stage 7 should read local TTS speaker / instruction settings from `builtin-anchor-templates/<template_id>.json` through the generated `audio/tts-plan.json` entries rather than hardcoding them at execution time

### Stage 9

The workflow keeps only orchestration rules here:

- `video/clip-plan.json` must declare explicit visual binding
- anchor binding or source-image binding cannot be omitted
- visual routing, duo/solo switching, source-image matching, and clip/render contract-consumption boundaries live in `director/news-commentary-clip-planning`
- `clip-plan` may temporarily fall back to `audio/tts-plan.json` only when `audio/timeline.json` is not ready yet; this fallback is for preliminary grouping only
- if `source-assets/source-visual-assets.json` contains usable provided news images, Stage 9 must produce at least one `anchor_binding=document` clip that binds those source images explicitly
- if script-stage `visual_hint` points to a provided news image or release-site image, Stage 9 must treat that as a routing requirement, not passive metadata
- each source image must appear exactly once in the finished clip-plan, and only as one continuous document-led visual block
- that single visual block may cover multiple consecutive audio units, including consecutive entries that cross segment boundaries, only while the accumulated `computed_duration_seconds` for the final document clip stays `<= 6.0`; after that, Stage 9 must cut back to anchor-led clips
- when Stage 9 groups either an anchor-led LTX block or a document-led ffmpeg block into one multi-audio clip, Stage 11 should first merge the clip-local audio paths into one WAV with `1s` of silence between adjacent source clips before video rendering continues

Executor:

- `python workflows/news-commentary/scripts/build_clip_plan.py --script <project>/script.json --audio-timeline <project>/audio/timeline.json --source-visual-assets <project>/source-assets/source-visual-assets.json --output <project>/video/clip-plan.json`
- if `audio/timeline.json` is not available yet, fallback to `--tts-plan <project>/audio/tts-plan.json`; this supports early clip grouping only, and any clip-plan produced from `tts-plan` must be refreshed once real timeline data exists

### Stage 10

- render-plan only consumes a validated clip-plan
- render-plan does not repair Stage 9 structure failures
- render-plan must consume real `audio/timeline.json`-backed audio paths and durations; `audio/tts-plan.json` is never a valid direct substitute here
- if Stage 9 had usable provided source images available but produced no document-led clip, Stage 10 must be treated as blocked rather than silently falling back to anchor-only rendering
- every `render_mode=ltx` clip must use the fixed three-template prompt system and the LTX-2 `audio_to_video` request path; consecutive anchor-led entries may share one LTX clip only when they keep the same reference image and remain within the configured LTX duration limit (`16s` in the current workflow)
- every Stage 10 LTX request must leave output `width` / `height` unspecified and rely on the model service defaults; do not force custom resolution fields in the request
- every Stage 10 LTX request must set `a2v_audio_start_time=0.0`
- every Stage 10 LTX request must set `a2v_audio_insert_video_time=0.5` so audio begins 0.5 second after the video starts
- every Stage 10 LTX request must set `duration_seconds` to `audio timeline duration + 1.0` second
- Stage 10 owns final LTX prompt assembly: positive template text, appended spoken line (`The anchor speaks in Chinese: "..."`), and negative prompt policy all belong here rather than in Stage 9 clip planning
- opening duo LTX clips, including the first one, must use the same duo-close-only reference-image strategy and fixed two-anchor prompt behavior as middle duo clips
- template-boundary assumptions and field-consumption rules live in `director/news-commentary-clip-planning`

Executor:

- `python workflows/news-commentary/scripts/build_render_plan.py --audio-timeline <project>/audio/timeline.json --clip-plan <project>/video/clip-plan.json --source-visual-assets <project>/source-assets/source-visual-assets.json --output <project>/video/render-plan.json`

FFmpeg command examples for `image_audio_ffmpeg` clips:

- still image + one audio clip → one segment mp4

```bash
ffmpeg -y -loop 1 -i <project>/source-assets/images/doc01_img01.png -i <project>/audio/guest/line_005.mp3 -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1" -r 30 -c:v libx264 -preset veryfast -crf 23 -tune stillimage -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart -shortest <project>/video/segments/seg03_clip03.mp4
```

- use this path for `render_mode=image_audio_ffmpeg` clips when Stage 10 resolved a source image plus one or more audio paths into an ffmpeg render request
- the example matches the current render-plan fields: `target_width`, `target_height`, `image_fit_mode=scale_pad`, `pad_color`, and `save_path`
- if the deployment requires exact duration control beyond `-shortest`, compute the authoritative duration from `audio/timeline.json` first and pass an explicit `-t <seconds>`

### Stage 11 / 12

- Stage 11 renders each `video/render-plan.json` item into `video/segments/*.mp4`
- `render_mode=ltx` clips are rendered only by LTX-2 `audio_to_video`
- `render_mode=image_audio_ffmpeg` clips are rendered by ffmpeg from resolved source images and audio paths
- whenever a Stage 11 item resolves to multiple audio paths, Stage 11 must merge those WAV files into one temporary WAV with `1s` of silence between adjacent source clips before handing audio to LTX or ffmpeg
- Stage 12 concatenates the already-rendered segment mp4 files into `video/final/output.mp4`

Executors:

- Stage 11: `python workflows/news-commentary/scripts/stage11_render_segments.py --render-plan <project>/video/render-plan.json`
- Stage 12: `python workflows/news-commentary/scripts/stage12_final_assembly.py --render-plan <project>/video/render-plan.json`
- Stage 12 defaults to re-encoding during concat because Stage 11 may mix LTX-rendered segments and ffmpeg-rendered segments that are not guaranteed to share identical stream layout, timebase, or audio encoding details

FFmpeg command examples for final assembly:

- opt-in concat demuxer copy path when all segment mp4 files already share compatible codec / timebase / stream layout

```bash
ffmpeg -y -f concat -safe 0 -i <project>/video/final/segments.txt -c copy <project>/video/final/output.mp4
```

- example `segments.txt`

```text
file '../segments/seg01_clip01.mp4'
file '../segments/seg02_clip01.mp4'
file '../segments/seg03_clip03.mp4'
```

- default re-encode path when segment streams are not identical or have not been explicitly verified as identical, producing a normalized H.264 / AAC output

```bash
ffmpeg -y -f concat -safe 0 -i <project>/video/final/segments.txt -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart <project>/video/final/output.mp4
```

- prefer re-encode by default for this workflow; use `-c copy` only after explicitly validating that all Stage 11 outputs are already aligned

## Render Routing Summary

- opening, closing, and short dialogue beats use anchor-led presentation
- when a usable provided news image carries the information better than a talking-head shot, the clip must use `image_audio_ffmpeg`
- provided news images are part of the primary visual package for the program, not optional decoration; anchor templates are fallback visuals for clips that are truly anchor-led
- detailed switching, explicit binding, and template-consumption rules live in `director/news-commentary-clip-planning`

## Core Dependencies

### Skills

- `writer/news-commentary-writing`
- `director/news-commentary-clip-planning`
- `generation/qwen3-tts`
- `generation/ltx23-video`
- `_prompts/ModelGuides/LTX-Video/`

### Contracts

Full index: `contracts/README.md`

Priority directories:

- `contracts/user-requirements/`
- `contracts/article-analysis/`
- `contracts/article-review/`
- `contracts/source-visual-assets/`
- `contracts/anchors/`
- `contracts/script/`
- `contracts/script-segment/`
- `contracts/script-skeleton/`
- `contracts/script-review/`
- `contracts/tts-plan/`
- `contracts/audio-timeline/`
- `contracts/clip-plan/`
- `contracts/render-plan/`

Interpretation ownership:

- Writer side owns interpretation of `article-analysis/`, `script-skeleton/`, `script-segment/`, `script/`, and `script-review/`
- Director side owns interpretation of `source-visual-assets/`, `audio-timeline/`, `clip-plan/`, and `render-plan/`

## Collaboration Boundaries

- workflow: owns stage orchestration, artifact dependencies, hard constraints, and entry behavior
- `writer/news-commentary-writing`: owns writing rules and script-review rules
- `director/news-commentary-clip-planning`: owns clip visual binding, duo/solo switching, and source-image routing
- render-plan: consumes clip-plan only; it does not replace clip planning
