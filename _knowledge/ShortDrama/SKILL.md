---
name: ShortDrama
description: Specialized short-drama knowledge layer for episodic short-form storytelling. Adds platform rhythm, hook design, cliffhanger pacing, and episode-level payoff rules on top of the shared film-production foundation.
trigger: Use when the project is an episodic short drama, vertical drama, platform-first serial, or any production that needs short-form hook and cliffhanger logic.
---

# ShortDrama

## Role In The System

`_knowledge/ShortDrama/` is not a replacement for the shared film-production knowledge stack.

It acts as a modifier layer on top of:

- `_knowledge/Genre/`
- `_knowledge/Narrative/`
- `_knowledge/Dialogue/`
- `_knowledge/Actor/`

Its purpose is to strengthen:

- episode hooks
- cliffhanger design
- short-form pacing
- payoff density
- platform-fit storytelling

## Use For

- `workflows/short-drama-production`
- `writer/story-outline`
- `writer/character-profile`
- `writer/script-writing`
- `director/storyboard` when hook density or episode-end emphasis matters

## Applies To Stages

Read this knowledge layer earlier than usual in these stages:

- requirement intake
- story outline
- character package
- episode script writing

Use it selectively in:

- storyboard
- test shoots

It should influence later stages indirectly through upstream artifacts rather than replacing camera or environment knowledge.

## Override Scope

When `ShortDrama` conflicts with the shared knowledge stack:

- for hook design, cliffhanger pacing, platform rhythm, and episode payoff density:
  - prefer `_knowledge/ShortDrama/`
- for basic narrative logic, character plausibility, camera language, and environment design:
  - keep the shared knowledge libraries as the base layer

## Core Questions

Before using this layer, answer:

- what is the platform expectation?
- how fast should the hook arrive?
- what is the episode-end retention device?
- how dense should reversals and emotional spikes be?
- what is the minimum payoff each episode must deliver?

## Output Impact

- `outline.json -> structure_pattern`
- `outline.json -> hook_strategy`
- `outline.json -> cliffhanger_pattern`
- `characters.json -> relationship_signal`
- `episodes/episode_XX.json -> opening_hook`
- `episodes/episode_XX.json -> payoff_beats`
- `episodes/episode_XX.json -> ending_hook`
- `storyboard.json -> hook_emphasis`

## Genre Library

Current genre references live in:

- `_knowledge/ShortDrama/genre/`

Available examples include:

- `sweet-romance.md`
- `bittersweet-love.md`
- `warrior-return.md`
- `god-of-wealth.md`
- `rebirth.md`
- `office-romance.md`

## Extraction Targets

Before generating a short-drama outline or episode script, extract:

- `platform_mode`
- `hook_strategy`
- `cliffhanger_pattern`
- `payoff_schedule`
- `relationship_engine`
- `reversal_density`
- `episode_rhythm`

## Usage Principles

1. Keep the main workflow structure aligned with `film-production`.
2. Use `ShortDrama` to modify rhythm and retention logic, not to reinvent the whole pipeline.
3. Push short-drama decisions upstream so downstream stages inherit them through contracts.
4. Prefer concrete genre patterns from `_knowledge/ShortDrama/genre/` over vague "short-drama feeling" instructions.
