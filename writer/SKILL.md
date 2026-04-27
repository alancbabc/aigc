---
name: Writer
description: Writing-domain entrance for outlines, character packages, scripts, MV treatments, and dual-anchor news commentary writing.
trigger: Use when the task is primarily story writing, character writing, script writing, MV treatment writing, or commentary-script writing.
---

# Writer Domain

## Purpose

`Writer` is the aggregation-layer entrance for writing work.

It is responsible for:

- choosing the correct writing leaf skill
- defining upstream/downstream writing dependencies
- clarifying the boundary between the Writer layer and specific writing skills

It is not responsible for:

- repeating detailed leaf-skill rules in the aggregation document
- replacing `news-commentary-writing` or `script-writing` with local stage logic

## Skill Index

### 1. `story-outline`

- purpose: expands a raw idea into a structured story outline
- input: genre, duration target, raw premise
- output: `outline.json`
- downstream: `character-profile` → `script-writing`

### 2. `character-profile`

- purpose: builds character packages from an outline
- input: `outline.json`
- output: `characters.json`
- downstream: `art/character-three-view`, `script-writing`

### 3. `script-writing`

- purpose: writes a full narrative script from an outline and character package
- input: `outline.json`, `characters.json`
- output: `script.json`
- downstream: `director/storyboard`

### 4. `mv-treatment`

- purpose: generates a creative treatment for a music video based on song structure and lyrics analysis
- input: `song-structure.json`, `lyrics-analysis.json`, `user_requirements.json`
- output: `mv-treatment.json`
- downstream: `character-profile`, `art/scene-design`, `director/storyboard`
- applies to: `workflows/mv-production`
- detailed rules: `writer/mv-treatment/SKILL.md`

### 5. `news-commentary-writing`

- purpose: transforms article analysis into a dual-anchor commentary script and owns script-review writing rules
- input: `article-analysis.json` and optional review/anchor context
- output: `script.json`, `script-review.json`
- applies to: `workflows/news-commentary`, `/news-broadcast`
- detailed rules: `writer/news-commentary-writing/SKILL.md`

## Invocation Boundaries

- Use `story-outline`, `character-profile`, or `script-writing` for general narrative writing tasks.
- Use `mv-treatment` for music video concept and creative treatment.
- Use `news-commentary-writing` for dual-anchor news commentary writing.
- When the task is already inside Stage 5 / 6 of `workflows/news-commentary`, `news-commentary-writing` is the only valid writing executor.
- The top-level `Writer` document does not restate Stage 5 / 6 commentary-writing details.

## Collaboration Map

| Skill | Input | Output | Downstream |
|---|---|---|---|
| `story-outline` | raw idea | `outline.json` | `character-profile` → `script-writing` |
| `character-profile` | `outline.json` | `characters.json` | `art/character-three-view` → `script-writing` |
| `script-writing` | outline + characters | `script.json` | `director/storyboard` |
| `mv-treatment` | song structure + lyrics analysis | `mv-treatment.json` | `character-profile` → `art/scene-design` → `director/storyboard` |
| `news-commentary-writing` | analysis + review context | `script.json` / `script-review.json` | `workflows/news-commentary` |

## Knowledge Dependencies

- `_knowledge/Genre/`
- `_knowledge/Narrative/`
- `_knowledge/Dialogue/`

## Cross References

- MV production workflow: `workflows/mv-production/SKILL.md`
- MV treatment writing rules: `writer/mv-treatment/SKILL.md`
- News commentary workflow: `workflows/news-commentary/SKILL.md`
- News commentary writing rules: `writer/news-commentary-writing/SKILL.md`
