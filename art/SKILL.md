---
name: Art
description: Art-domain entrance for character sheets, scene references, and keyframe image generation.
trigger: Use when the task is primarily visual design, scene design, or keyframe-image generation.
---

# Art Domain

## Purpose

`Art` is the aggregation-layer entrance for visual design work.

It is responsible for:

- choosing the correct art leaf skill
- defining upstream/downstream dependencies for visual artifacts
- clarifying the boundary between the Art layer and specific art skills

It is not responsible for:

- repeating detailed prompt rules in the aggregation document
- replacing Director shot decisions
- replacing Generation execution logic

## Shared Rules

1. Prompts are in English unless a leaf skill explicitly states otherwise.
2. Style tokens come from `_prompts/PromptTemplates/Style/`.
3. Prompts stay concise.

## Skill Index

### `character-three-view`

- input: character descriptions (`characters.json`)
- output: front / side / back character-sheet images + review JSON
- downstream: `director/storyboard`

### `scene-design`

- input: `storyboard.json`
- output: scene reference images + review JSON
- downstream: `director/test-shoots`

### `keyframe-generation`

- input: `test-shoots.json` + character sheets + scene references
- output: keyframe images (`first` / `intermediate` / `last`)
- downstream: `generation/flux-image-edit` or other downstream video tooling

## Collaboration Map

| Skill | Input | Output | Downstream |
|------|------|------|----------|
| `character-three-view` | character package | character-sheet images | `director/storyboard` |
| `scene-design` | storyboard | scene reference images | `director/test-shoots` |
| `keyframe-generation` | `test-shoots.json` + references | keyframe images | `generation/*` |

## Workflow Chain

```text
writer/character-profile
→ art/character-three-view
→ writer/script-writing
→ director/storyboard
→ art/scene-design
→ director/test-shoots
→ art/keyframe-generation
→ generation/*
```

## Cross References

- Character three-view: `art/character-three-view/SKILL.md`
- Scene design: `art/scene-design/SKILL.md`
- Keyframe generation: `art/keyframe-generation/SKILL.md`
