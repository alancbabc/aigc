# AIGC Skills Index

This repo is a composable AIGC skill system for film, short-drama, and visual-storytelling workflows.

It supports both:

- single-point leaf skill usage
- multi-stage workflow orchestration

## Main Entrances

### Workflows

- [film-production](../workflows/film-production/)
- [short-drama-production](../workflows/short-drama-production/)
- [news-commentary](../workflows/news-commentary/)

### Core Skill Groups

- [writer](../writer/)
- [art](../art/)
- [director](../director/)
- [generation](../generation/)

### Shared Layers

- [_knowledge](../_knowledge/)
- [_prompts](../_prompts/)
- [ROUTING.md](../ROUTING.md)

## System Structure

```text
workflows/
|- film-production/
|- short-drama-production/
`- news-commentary/

writer/
|- story-outline/
|- character-profile/
|- script-writing/
`- news-commentary-writing/

art/
|- character-three-view/
|- scene-design/
`- keyframe-generation/

director/
|- storyboard/
|- transition/
|- test-shoots/
`- news-commentary-clip-planning/

generation/
|- flux-text-to-image/
|- flux-image-edit/
|- qwen-image-2512/
|- qwen2.5-vl/
|- qwen3-tts/
|- mineru25-ocr/
`- ltx23-video/

_knowledge/
|- Genre/
|- Narrative/
|- Actor/
|- Dialogue/
|- Camera/
|- Transition/
|- VisualEnvironment/
|- FamousDirectors/
|- Sound/
`- ShortDrama/

_prompts/
|- PromptTemplates/
`- ModelGuides/
```

## Workflow Backbone

The standard production backbone is:

1. requirement intake
2. story outline
3. character package
4. script writing
5. storyboard
6. scene design
7. test shoots
8. keyframe generation
9. generation assets

`short-drama-production` reuses this backbone and injects `ShortDrama` knowledge in the writing and pacing stages.

`news-commentary` uses a separate broadcast-style backbone for news analysis, dual-anchor writing, TTS, clip planning, and render planning.

## Skill Roles

### Writer

- develops premise, outline, characters, scripts, and news commentary writing

### Art

- develops character views, scenes, and keyframes

### Director

- develops storyboard, transitions, test-shoot planning, and news clip planning

### Generation

- executes image generation, editing, video generation, TTS, and document parsing

### Knowledge

- provides reusable rules, patterns, and reference logic

### Prompts

- provides prompt templates and model-specific phrasing support

## Key Rules

1. In standard workflows, prompts entering `generation/*` are in English unless the leaf skill explicitly states otherwise.
2. Use leaf skills for isolated tasks.
3. Use workflows for multi-stage projects.
4. Read `_knowledge` before generating important artifacts.
5. Use `_prompts` after knowledge extraction, not before.

## Reading Order

1. [`../SKILL.md`](../SKILL.md)
2. [`../README.md`](../README.md)
3. [`../ROUTING.md`](../ROUTING.md)
4. the target workflow or domain `SKILL.md`
