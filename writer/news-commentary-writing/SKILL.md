---
name: news-commentary-writing
description: Writing subskill for transforming article analysis into a dual-anchor commentary script, with evidence-first scripting, spoken-language translation, promo-tone neutralization, and visual-offloading rules.
trigger: Use when the task is to turn news articles, links, or analysis into a dual-anchor commentary script rather than a plain summary or compressed restatement.
---

# News Commentary Writing

## Purpose

This subskill owns the Writer-side work inside the `news-commentary` workflow:

- converting article analysis into commentary form
- generating a dual-anchor spoken script
- defining writing-side script-review rules
- deciding which information should stay in spoken lines and which should be offloaded to visuals

Inside `workflows/news-commentary`, this skill is the required writer executor for Stage 5 / 6.

It is not responsible for:

- anchor visual asset generation
- clip-level shot or image routing
- render-plan assembly or final video stitching

Those belong to the workflow itself or Director-side subskills.

The workflow owns orchestration only and must not bypass this skill to inline-generate or rewrite `script.json`.

## Inputs

- `article-analysis.json`
- optional `article-review.json`
- optional `anchors.json`
- workflow constraints such as target duration, language, and show style

## Outputs

- `script-skeleton.json`
- `script-segments/*.json`
- `script.json`
- `script-review.json`

## Stage 5 / 6 Ownership

For `workflows/news-commentary`, this skill is not advisory. It is the only valid writing execution path for Stage 5 / 6.

- Stage 5 converts analysis into the commentary-ready script artifact chain
- Stage 6 performs script review
- the workflow must not bypass this skill by generating, stitching, or rewriting `script.json` locally

The execution model should be treated as a smaller operational model such as OpenClaw + minimax 2.5. Stage 5 therefore uses a file-splitting writing chain by default.

### Stage 5 Artifact Chain

Write files in this order:

1. `script-skeleton.json`
2. `script-segments/seg01.json`, `seg02.json`, ...
3. `script.json`

### Stage 5a — Skeleton

Stage 5a locks the structural skeleton before segment drafting begins.

At root level, define when available:

- `title`
- `duration_estimate`
- `series_mode`
- `anchors`

At minimum, define:

- segment order with explicit `segment_no`
- each segment's contract-valid `type`
- each segment's `segment_goal`
- each segment's `takeaway`
- `host_function` / `guest_function`
- required `must_keep_evidence`
- `source_refs`
- `visual_hint`

For stronger explanation quality, it is recommended to also lock:

- `explanation_target`
- `commentary_target`

Full dialogue generation cannot start until the skeleton is stable.

### Stage 5b — Segment Drafting

When generating `script-segments/*.json`:

- process one segment at a time
- carry only the current segment's evidence, role split, and goal
- do not inject the full-script context back into each segment pass
- each segment must first satisfy speakability and clear host/guest role separation before any full-script polish

`script-segment` should carry:

- `segment_no`
- contract-valid `type`
- `segment_goal`
- `takeaway`
- segment-level writing realization
- `lines[]` with speaker / text / estimated_duration_seconds
- pre-splitting of oversized explanation lines
- line-level structure that stays traceable into TTS and clip planning

Each line must include at minimum:

- `line_no`
- `speaker`
- `text`

Stage 5 segment drafts must remain valid JSON files. Spoken text that contains quoted phrases must be escaped correctly.

### Stage 5c — Merge and Length Normalization

When merging `script-skeleton.json` + `script-segments/*.json` into `script.json`:

- keep segment order consistent with the skeleton
- preserve line-level traceability fields
- keep skeleton and segment drafts aligned on `segment_no`
- keep segment `type` aligned between skeleton and draft
- split clearly oversized spoken lines during the script stage
- do not leave the first structural split to TTS, clip-plan, or render-plan

If root-level fields such as `title`, `duration_estimate`, `series_mode`, or `anchors` are known during Stage 5a, they should be carried into `script.json` rather than left null.

Executor:

- `python workflows/news-commentary/scripts/merge_script_stage5.py --skeleton <project>/script-skeleton.json --segments-dir <project>/script-segments --output <project>/script.json`

This merge step is an explicit Stage 5 action.
If the skeleton and `script-segments/*.json` disagree on segment structure, Stage 5 fails and the relevant segment must be regenerated.

### Stage 6 — Script Review

Script review happens only after the full `script.json` exists. Full-script self-review cannot be interleaved with segment drafting.

Review checks:

- whether evidence is preserved
- whether claims cross the source boundary
- whether lines are too dense or too close to written prose
- whether content that should be visual remains overloaded into spoken lines
- whether line-level duration risks were already handled during scripting

## Writer-Side Contract Ownership

This skill owns the interpretation and writing usage of:

- `contracts/article-analysis/`
- `contracts/script-skeleton/`
- `contracts/script-segment/`
- `contracts/script/`
- `contracts/script-review/`

Read order:

1. `article-analysis/`
2. `script-skeleton/`
3. `script-segment/`
4. `script/`
5. `script-review/`

Writer-side concerns:

- which analysis fields define speakable content and evidence boundaries
- how skeleton and segment artifacts form the Stage 5 intermediate chain
- which downstream-traceability fields must stay in `script.json`
- how review artifacts mark writing problems rather than visual-routing problems

## Core Writing Rules

### 1. Evidence-first

- use `must_keep_evidence` and `speakable_facts` to select what is actually worth saying before drafting lines
- every major judgment must map back to source evidence
- if the source is promotional, neutralize it before allowing it into script text

### 2. Speakable-first

- do not compress a dense source paragraph into a slightly shorter but denser guest monologue
- translate content into spoken layers:
  - fact lines
  - explanation lines
  - judgment lines
- the host translates, asks, and guides; the guest explains, compares, and judges
- every segment should contain at least a fact layer and an explanation layer; key segments should preferably also contain meaning or comparison
- avoid host lines that only perform low-information acknowledgment, generic praise, or empty bridging
- in key segments, the guest should explain why the claim matters, why the problem is hard, or how it compares with prior practice

### 3. Visual Offloading

- move `visual_only_details` into cards, subtitles, source images, or later `image_audio_ffmpeg` clips
- do not overload a single guest line with charts, pipelines, and dense numbers
- decide visual offloading during script writing rather than discovering the problem for the first time in clip planning
- `visual_hint` may suggest later source-image support, but it must not hardcode final shot binding
- for `opening` and `closing` segments, Writer must not instruct the program to begin on a source image or a solo anchor shot; those beats stay under Director-side duo-frame policy unless downstream routing rules explicitly say otherwise

### 4. Anti-promo Handling

- use `promo_phrases_to_neutralize` to cool down source-level marketing tone
- use `commentary_claim_boundaries` to prevent claims from drifting beyond source evidence
- do not translate “technical breakthrough” directly into “commercial success” or “overall leadership”

## Script Generation Rules

- `script.json` is a commentary-ready dual-anchor script, not a restated news article
- each segment must contain at least two of:
  - fact layer
  - explanation layer
  - meaning layer
- merge overlapping claims across multiple sources rather than repeating them source by source

### Spoken-Length Control

- estimate spoken length during script generation
- if a single-speaker explanation line is clearly beyond the practical ~`8–15s` range, split it during the script stage into consecutive spoken lines
- do not leave the first structural split to TTS, clip-plan, or render-plan

## Script Review Rules

After generation, review must verify:

- whether the script is still too close to a compressed news article
- whether all major judgments remain source-grounded
- whether promotional or inflated wording remains
- which details should stay in spoken lines and which should move to visual handling
- whether rhythm, role separation, and meaning-layer clarity are preserved
- whether Stage 5 artifacts were explanation-rich enough rather than merely mergeable
- whether host lines carry real translation, guidance, or synthesis value
- whether key segments are missing explanation or meaning/comparison layers
- whether merge-shape drift or invalid-JSON risk is visible in the Stage 5 chain

## Collaboration Boundaries

- workflow: owns stage order, contracts, and artifact handoff
- `news-commentary-writing`: owns Stage 5 / 6 writing quality
- `director/news-commentary-clip-planning`: owns Stage 9 visual routing and clip binding
- within `workflows/news-commentary`, Stage 5 / 6 must invoke this skill as the only writing executor

## Boundaries With Workflow / Director

- this skill decides what should be said, how it should be said, and how spoken content is split into line structure
- this skill may annotate `visual_hint`, but it does not perform final clip binding
- `visual_hint` must stay advisory; it cannot override the Director rule that opening / closing beats use `duo_frame`
- whether lines finally use `duo`, `solo`, or `document` is decided by `director/news-commentary-clip-planning`
- the three-template render prompts are not defined here; Writer only leaves structure and visual hints that Director can consume

## Required Invocation Stages

`workflows/news-commentary` must load this skill at:

- Stage 5 — Script Generation
- Stage 6 — Script Review
