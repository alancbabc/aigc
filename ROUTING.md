# Routing Guide

This file defines how OpenClaw or any orchestrator should choose between:

- leaf skills
- workflow skills
- `_knowledge`
- `_prompts`

## Skill Layers

### 1. Leaf Skills

Leaf skills solve a single local task.

Use them when the user:

- only wants one step done
- already has an upstream artifact
- wants a revision, extension, or focused output

Common leaf skills:

- `writer/story-outline`
- `writer/character-profile`
- `writer/script-writing`
- `writer/mv-treatment`
- `art/character-three-view`
- `art/scene-design`
- `art/keyframe-generation`
- `director/storyboard`
- `director/transition`
- `director/test-shoots`
- `generation/flux-text-to-image`
- `generation/flux-image-edit`
- `generation/qwen-image-2512`
- `generation/qwen2.5-vl`

### 2. Workflow Skills

Workflow skills orchestrate multiple leaf skills across a larger project.

Current workflows:

- `workflows/film-production`
- `workflows/short-drama-production`
- `workflows/mv-production`

Future examples:

- `workflows/ad-production`
- `workflows/education-video-production`

### 3. Shared Layers

These layers should usually not be the direct first match for a user request.

- `_knowledge/` provides rules, concepts, and decision support
- `_prompts/` provides prompt templates and model-facing phrasing

They are support layers for skills, not default end-user task targets.

## Primary Routing Rule

### Prefer A Leaf Skill When

Prefer a leaf skill if the user:

- provides an intermediate artifact
- asks for one local outcome
- wants to revise one stage only
- does not need end-to-end orchestration

Examples:

- user gives an outline and only wants character profiles -> `writer/character-profile`
- user gives character text and only wants three-view art -> `art/character-three-view`
- user gives a storyboard and only wants scene references -> `art/scene-design`
- user gives a script and only wants storyboard -> `director/storyboard`
- user gives an image and only wants visual analysis -> `generation/qwen2.5-vl`

### Prefer A Workflow When

Prefer a workflow if the user:

- wants an end-to-end project
- has no useful intermediate artifact yet
- needs multiple stages across writing, art, directing, and generation

Examples:

- "make me a wuxia short film" -> `workflows/film-production`
- "make me a 20-episode vertical short drama" -> `workflows/short-drama-production`

## Intermediate Artifact Recovery

If the user provides an intermediate artifact, resume from the nearest valid downstream stage instead of restarting from the beginning.

Recovery rules:

- `outline.json` -> continue to `writer/character-profile` or `writer/script-writing`
- `characters.json` -> continue to `writer/script-writing`, `art/character-three-view`, or `director/storyboard`
- `script.json` -> continue to `director/storyboard`
- `episodes/episode_01.json` -> continue to `director/storyboard`
- `storyboard.json` -> continue to `art/scene-design` or `director/test-shoots`
- `test-shoots.json` -> continue to `art/keyframe-generation` or `generation/*`
- `song-structure.json` -> continue to `writer/mv-treatment` or `director/storyboard`
- `mv-treatment.json` -> continue to `writer/character-profile` or `art/scene-design`

## Shared Layer Access Rule

Do not route user requests directly to `_knowledge` or `_prompts` unless the user explicitly asks to inspect the knowledge base or prompt assets themselves.

Default rule:

1. choose a leaf skill or workflow
2. let that skill read `_knowledge` and `_prompts` through its own dependencies

## Routing By Request Type

### Writing Requests

- "write an outline" -> `writer/story-outline`
- "build character profiles" -> `writer/character-profile`
- "turn this outline into a script" -> `writer/script-writing`

### Visual Design Requests

- "make a three-view sheet" -> `art/character-three-view`
- "design a set of scene references" -> `art/scene-design`
- "generate keyframes" -> `art/keyframe-generation`

### Directing Requests

- "turn this script into storyboard" -> `director/storyboard`
- "design the transition between these two segments" -> `director/transition`
- "turn storyboard into shot and frame prompts" -> `director/test-shoots`

### Generation Requests

- "generate an image from prompt" -> `generation/flux-text-to-image`
- "edit an image based on another image" -> `generation/flux-image-edit`
- "analyze this image" -> `generation/qwen2.5-vl`

### End-To-End Project Requests

- "go from idea to keyframes for a short film" -> `workflows/film-production`
- "go from idea to episodic scripts and keyframes for a short drama" -> `workflows/short-drama-production`
- "make a music video for this song" -> `workflows/mv-production`
- "turn this song into an MV" -> `workflows/mv-production`

## ShortDrama Routing Rule

If the project is episodic, platform-first, or retention-driven:

- still prefer the same main backbone as `film-production`
- inject `_knowledge/ShortDrama/` as a modifier layer in outline, character, and script stages
- do not treat `ShortDrama` as a replacement for the shared knowledge stack

## Decision Priority

When multiple skills might match, decide in this order:

1. Is the user asking for a local goal only?
2. Has the user already provided an intermediate artifact?
3. Is there a nearby leaf skill that can solve the task directly?
4. If not, enter a workflow.

## Done Conditions

### Leaf Skill

A leaf skill is done when it produces the artifact defined by its own contract.

### Workflow

A workflow is done when it reaches the stage the user actually asked for.

Examples:

- user says "stop after character package" -> finish at `characters.json`
- user says "stop after keyframes" -> finish at reviewed `keyframes/`
- user says "just polish this paragraph" -> do not enter a workflow at all
