---
name: news-commentary-clip-planning
description: Directing subskill for Stage 9 clip planning in the news-commentary workflow. Owns visual binding, anchor/source routing, and document-image clip planning.
trigger: Use when the task is to organize commentary audio/script into `clip-plan.json` and decide how anchor shots and source images divide visual responsibility.
---

# News Commentary Clip Planning

## Purpose

This subskill owns the Director-side work inside the `news-commentary` workflow:

- clip-level visual binding
- `ltx` vs `image_audio_ffmpeg` routing
- visual strategy for opening / closing / headline / discussion / summary beats
- explicit declaration of `anchor_binding`, `character_bindings`, and `visual_asset_paths`

It is not responsible for:

- article-analysis writing judgments
- dual-anchor script generation
- final render-parameter details after render-plan assembly

## Inputs

- `script.json`
- `audio/timeline.json`; if unavailable, use `audio/tts-plan.json`
- `source-assets/source-visual-assets.json`
- anchor visual asset paths

## Outputs

- `video/clip-plan.json`

## Director-Side Execution Ownership

For `workflows/news-commentary`, this skill is the primary rule source for Stage 9.

- the workflow enforces that clip-plan must exist before render-plan begins
- this skill explains how script/audio/source visuals become executable `video/clip-plan.json`
- render-plan may consume only validated clip-plan structure; it must not patch Stage 9 backward

## Director-Side Contract Ownership

This skill owns the interpretation of:

- `contracts/source-visual-assets/`
- `contracts/audio-timeline/`
- `contracts/clip-plan/`
- `contracts/render-plan/`

Read order:

1. `audio-timeline/` (or fallback `tts-plan/`)
2. `source-visual-assets/`
3. `clip-plan/`
4. `render-plan/`

Director-side concerns:

- which audio units can map stably to anchor-led clips
- which source visuals can support document-led clips
- how `clip-plan.json` explicitly declares anchor binding and source-image binding
- how `render-plan.json` maps already-chosen anchor-led LTX clips into the fixed program templates

## Core Visual Routing Rules

### 1. Default Shot Strategy

- opening / closing / short dialogue: use `duo_frame`
- long single-speaker explanation: use the matching anchor's solo image
- dense data, process, model, chart, release-site, or source-heavy moments: use source images
- when a clip finally uses `render_mode=ltx`, render-plan must map that anchor-led clip into the opening / middle / closing template system
- only the first opening duo LTX clip may receive the dedicated opening push-in treatment; later opening duo clips must align with middle-duo reference-image strategy and prompt body behavior
- clip planning decides whether a clip is anchor-led or document-led; it does not write final LTX prompt bodies
- anchor-led templates are the fallback path for clips that are genuinely anchor-led; they must not absorb the entire program when usable provided news images exist

#### Duo / Solo Switching Rule (Mandatory)

- do not cut to a solo shot just because one host/guest line is short
- if an anchor-led exchange is still a short back-and-forth dialogue, the frame must remain `duo_frame`
- switch to `solo` only when the same speaker exceeds **15 seconds** of cumulative duration across **continuous anchor-led clips**
- “continuous” means there is no intervening anchor-led clip from the other speaker and no intervening `document` source-image clip
- if cumulative same-speaker duration stays **at or below 15 seconds**, keep `duo_frame` even if the line itself is spoken by one person
- the opening beat may still begin with `duo_frame` to establish the program shape

### 2. When To Use Source Images

When a usable provided source image carries the information better than a talking-head anchor shot, route directly to:

- `anchor_binding=document`
- `render_mode=image_audio_ffmpeg`
- `image_mode=document_image`

This especially applies to:

- data-dense explanation
- charts / pipelines / model-structure explanation
- cluster, training, compute, or performance explanation
- moments where the news fact is better established by the source image itself

If `source-assets/source-visual-assets.json` contains usable provided images, the clip plan must include at least one document-led clip that uses them explicitly.

- each source image may appear only once in the whole program
- if a source image is chosen, it may continue across multiple consecutive audio units as one uninterrupted document-led block
- once the program cuts away from that source image, it must not return to the same image later

If script-stage `visual_hint` names a provided image, release-site image, signing image, chart, or cluster image, the planner should treat that as a binding obligation unless the image is clearly unusable for video.

### 3. Markdown Image Manifest Usage

- `标题` in the markdown manifest acts as `caption`
- `说明` acts as `context_hint`
- `说明` is not passive metadata; it must participate in clip image selection
- when the manifest and sibling image files clearly define visual intent, those source visuals must be consumed
- if source visuals were extracted successfully and at least one is usable for video, failing to bind any of them is a routing error, not an acceptable stylistic alternative

### 4. Render-Plan Consumption Boundary

- `clip-plan` decides whether a clip is `anchor-led` or `document-led`
- `render-plan` decides which selected `ltx` clips use the opening / middle / closing template
- template selection belongs to render planning, but clip planning must define clear anchor-led boundaries first
- clip planning does not hardcode final LTX prompt bodies, appended spoken-text format, or negative prompt policy; it outputs clear binding and routing structure only

## Explicit Binding Rules

Every clip must declare explicit visual binding.

- `anchor_binding=solo`
  - `character_bindings` must contain exactly one role
  - `visual_asset_paths` must contain exactly one matching anchor asset
- `anchor_binding=duo`
  - `character_bindings` must contain exactly two roles
  - `visual_asset_paths` must explicitly include two single-anchor assets
  - `composite_visual_asset_path=duo_frame` may be added
- `anchor_binding=document`
  - no anchor visual asset is used
  - `source_image_ids` / `source_image_paths` must be declared explicitly
  - use this path whenever the clip is primarily carrying a provided image, release-site photo, chart, pipeline figure, screenshot, or document-derived visual

## Timing And Splitting Constraints

- when `render_mode=ltx`, each clip should map to exactly one audio unit
- if any clip's `estimated_duration_seconds` exceeds `15.0`, the split must be pushed upstream; Stage 9 does not perform the first structural split
- if one explanation must span multiple audio units, split it into multiple LTX clips or route it into source-image clips
- `duo_frame` / `solo` switching depends on cumulative same-speaker anchor-led duration, not one isolated line duration
- if upstream `script.json` already preserves line-level split and traceability fields, Stage 9 must consume those fields rather than reinventing splitting logic
- document-led blocks may merge multiple consecutive audio units when one source image should be shown once as a continuous run, but any resulting clip must still stay within the `15.0s` limit

## Stage 9 Hard-Fail Conditions

Clip planning fails immediately if:

- explicit visual binding is missing
- role count and visual asset count do not match
- the plan references audio with `needs_resynthesis=true`
- any clip exceeds `15.0s`
- usable provided source images exist, but the plan produces no `anchor_binding=document` clip at all

## Collaboration Boundaries

- workflow: owns orchestration, contracts, and artifact flow
- `writer/news-commentary-writing`: owns spoken writing quality and commentary translation
- `news-commentary-clip-planning`: owns clip visual routing and document-image planning
- render-plan: consumes validated clip-plan and maps anchor-led LTX clips into opening / middle / closing templates; it does not repair Stage 9 failures

## Boundaries With Writer / Workflow

- Writer decides how content becomes spoken lines; Director decides how those lines bind to visuals
- workflow keeps only stage dependencies, hard-fail conditions, and entry constraints; it does not restate clip-plan / render-plan field-level semantics
- if the problem is really evidence, line density, or line splitting, send it back to Writer; if the problem is duo/solo routing, source-image matching, or anchor binding, fix it here

## Required Invocation Stages

`workflows/news-commentary` must load this skill at:

- Stage 9 — Clip Planning
