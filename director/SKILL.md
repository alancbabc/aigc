---
name: Director
description: Directing-domain entrance for storyboard, transition, test-shoot planning, and news commentary clip planning.
trigger: Use when the task is primarily shot design, transition design, shot-planning, or clip routing.
---

# Director Domain

## Purpose

`Director` is the aggregation-layer entrance for directing work.

It is responsible for:

- choosing the correct directing leaf skill
- defining upstream/downstream directing dependencies
- clarifying the boundary between the Director layer and specific directing skills

It is not responsible for:

- repeating detailed shot rules in the aggregation document
- replacing `news-commentary-clip-planning` with local routing logic

## Skill Index

### 1. `storyboard`

- purpose: designs shots, framing, motion, and transition intent from narrative inputs
- input: full script, character package
- output: `storyboard.json`
- downstream: `art/scene-design`, `test-shoots`

### 2. `test-shoots`

- purpose: turns storyboard outputs into shot-level prompt plans and frame-level keyframe prompt plans
- input: `storyboard.json`
- output: `test-shoots.json`
- downstream: `art/keyframe-generation`, `generation/*`
- core rule: prompts are in English and each shot produces 1–3 frames

### 3. `news-commentary-clip-planning`

- purpose: generates `clip-plan.json` for dual-anchor news commentary and owns explicit visual binding plus anchor/source routing decisions
- input: `script.json`, `audio/timeline.json` or `audio/tts-plan.json`, `source-visual-assets.json`
- output: `video/clip-plan.json`
- applies to: `workflows/news-commentary`, `/news-broadcast`
- detailed rules: `director/news-commentary-clip-planning/SKILL.md`

## Invocation Boundaries

- Use `storyboard` for long-form shot design.
- Use `test-shoots` after storyboard exists and the task is keyframe-planning oriented.
- Use `news-commentary-clip-planning` for dual-anchor commentary clip planning.
- News commentary duo / solo / document routing rules live only in `news-commentary-clip-planning`.

## Collaboration Map

| Skill | Input | Output | Downstream |
|---|---|---|---|
| `storyboard` | full script | `storyboard.json` | `art/scene-design` → `test-shoots` |
| `test-shoots` | `storyboard.json` | `test-shoots.json` | `art/keyframe-generation` / `generation/*` |
| `news-commentary-clip-planning` | script + audio + source visuals | `clip-plan.json` | render-plan |

## Shared Rule Entrances

- Camera / shot language: consumed by `storyboard` and `test-shoots`
- Transition rules: consumed by `storyboard`
- News commentary duo / solo / document routing: consumed by `news-commentary-clip-planning`

## Cross References

- News commentary workflow: `workflows/news-commentary/SKILL.md`
- News commentary clip rules: `director/news-commentary-clip-planning/SKILL.md`
