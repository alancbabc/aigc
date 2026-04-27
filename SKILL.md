---
name: AIGC
description: A complete AIGC skill system for writing, art, direction, generation, and workflow orchestration.
trigger: Use when the task involves film, short-drama, news-commentary, music-video, or visual-storytelling creation with AI assistance.
---

# AIGC Skill System

## Purpose

`AIGC` is the root entry of this skill system.

It is responsible for:

- deciding which layer the task should enter: `workflows/`, `writer/`, `art/`, `director/`, or `generation/`
- defining responsibility boundaries between aggregation layers and leaf skills
- enforcing that multi-stage work goes through workflows and isolated work goes through the correct leaf skill

It is not responsible for:

- repeating detailed leaf-skill rules in the root document
- replacing workflow stage design
- replacing domain-level writing, directing, art, or generation decisions

## System Structure

```text
workflows/          # multi-stage entrances; own orchestration, stage dependencies, and artifact chains
writer/             # writing domain; owns outlines, characters, scripts, and news commentary writing
art/                # art domain; owns character sheets, scene references, and keyframe images
director/           # directing domain; owns storyboard, transition, test-shoots, and news clip planning
generation/         # execution layer; owns image, video, audio, OCR, and parsing execution
_knowledge/         # knowledge layer; provides reusable rules and decision references
_prompts/           # prompt layer; provides prompt templates and model-specific phrasing
```

## Routing Rules

### 1. Multi-stage tasks

Any task spanning two or more upstream/downstream stages must enter `workflows/`.

Primary workflows:

- `workflows/film-production`
- `workflows/short-drama-production`
- `workflows/news-commentary`
- `workflows/mv-production`

### 2. Isolated writing tasks

If the task only needs writing artifacts, enter `writer/`:

- `writer/story-outline`
- `writer/character-profile`
- `writer/script-writing`
- `writer/mv-treatment`
- `writer/news-commentary-writing`

### 3. Isolated art tasks

If the task only needs visual design artifacts, enter `art/`:

- `art/character-three-view`
- `art/scene-design`
- `art/keyframe-generation`

### 4. Isolated directing tasks

If the task only needs shot or clip planning, enter `director/`:

- `director/storyboard`
- `director/transition`
- `director/test-shoots`
- `director/news-commentary-clip-planning`

### 5. Isolated execution tasks

If the task only needs model execution and does not need new creative structure decisions, enter `generation/`.

## Aggregation-Layer Boundaries

- `AIGC`: decides which layer to use; does not invent local process details.
- `workflows/`: owns stage order, artifact dependencies, and hard-fail gates.
- `writer/`: owns what gets written, how it gets written, and what stays in text.
- `art/`: owns visual reference generation and keyframe image formation.
- `director/`: owns shot logic, visual binding, and routing decisions.
- `generation/`: executes already-approved prompts, references, and inputs; it does not replace upstream creative decisions.
- `_knowledge/`: provides reusable rules and references; it is not the final output layer.
- `_prompts/`: provides phrasing assets; it is not a high-level decision layer.

## Global Rules

1. Multi-stage tasks must use workflows. Do not manually stitch stages together at the root layer.
2. Isolated tasks must enter the correct domain or leaf skill. Do not treat aggregation layers as final execution layers.
3. In standard workflows, prompts sent into `generation/*` must be in English unless a leaf skill explicitly states otherwise.
4. Read relevant `_knowledge/` before generating important artifacts. Read `_prompts/` during prompt-writing stages, not before knowledge extraction.
5. Aggregation-layer documents define routing, boundaries, and entry points only. They do not duplicate detailed leaf-skill rules.

## Usage

### Isolated tasks

```bash
skill("AIGC", "writer/story-outline")
skill("AIGC", "art/scene-design")
skill("AIGC", "generation/qwen3-tts")
```

### Multi-stage tasks

```bash
skill("AIGC", "workflows/film-production")
skill("AIGC", "workflows/short-drama-production")
skill("AIGC", "workflows/news-commentary")
skill("AIGC", "workflows/mv-production")
```

## Cross References

- Writing domain entrance: `writer/SKILL.md`
- Art domain entrance: `art/SKILL.md`
- Directing domain entrance: `director/SKILL.md`
- Generation domain entrance: `generation/SKILL.md`
- News commentary workflow: `workflows/news-commentary/SKILL.md`
- MV production workflow: `workflows/mv-production/SKILL.md`

## Changelog

- 2026-04-01: Tightened aggregation-layer wording and aligned the root skill with routing/boundary semantics.
- 2026-03-25: Created as the OpenCode AIGC skill system root.
- 2026-03-24: Standardized the first skill batch and added schema/example conventions.
- 2026-03-12: Consolidated existing model skills and added rate-limit guidance.
