---
name: Generation
description: Execution-layer entrance for image, video, audio, OCR, and parsing tasks.
trigger: Use when the task is primarily model execution rather than creative structure design.
---

# Generation Domain

## Purpose

`Generation` is the aggregation-layer entrance for execution work.

It is responsible for:

- receiving already-approved prompts, references, audio, or documents
- routing execution to the correct generation leaf skill
- enforcing execution-layer delivery rules, decoding rules, and rate-limit expectations

It is not responsible for:

- redesigning style, story, or shot logic at the aggregation layer
- replacing Writer, Art, or Director decisions
- mixing too many leaf-specific exceptions into the aggregation document

## Inputs

- structured prompts from upstream skills
- reference images, editable images, or analyzable images
- explicit generation / editing / analysis goals
- optional execution parameters such as size, voice, and model preference

## Outputs

- images, videos, audio, or analysis text
- execution artifacts ready for downstream review or selection
- decoded image files when an API returns `b64_json` payloads

## Execution Rules

1. Execute upstream-approved prompts and references without rewriting creative intent.
2. If extra knowledge is needed, restrict it to terminology completion and consistency checks.
3. High-level style, story, and shot design decisions remain upstream in Writer / Art / Director.
4. Model-specific behavior belongs in leaf skills, not in the aggregation document.
5. Batched execution must respect rate limits.

## Skill Index

### `qwen-image-2512`
- text-to-image
- input: prompt + size
- output: image files

### `qwen-image-local`
- local-service image generation / editing
- input: prompt + optional reference images
- output: image files

### `flux-text-to-image`
- text-to-image
- input: English prompt + size
- output: image files

### `flux-image-edit`
- image-to-image editing
- input: 1–3 reference images + English prompt
- output: image files

### `qwen2.5-vl`
- image understanding
- input: images + questions
- output: text answers

### `qwen3-tts`
- text-to-speech
- input: text + `speaker` + `language`
- output: audio files

### `qwen-tts-local`
- local-service text-to-speech
- input: text + optional `speaker` / `instruct` / `language`
- output: audio files

### `mineru25-ocr`
- OCR / document parsing
- input: local document paths + optional OCR/table/formula/layout settings
- output: Markdown and optional status JSON

### `ltx23-video`
- video generation
- input: audio + prompt + optional reference image, or image + prompt
- output: video files

## Collaboration Map

| Skill | Input | Output | Use Case |
|------|------|------|----------|
| `qwen-image-2512` | prompt + size | images | text-to-image |
| `qwen-image-local` | prompt + optional reference images | images | local text-to-image / image edit |
| `flux-text-to-image` | English prompt + size | images | text-to-image |
| `flux-image-edit` | references + prompt | images | image editing, three-view generation |
| `qwen2.5-vl` | images + questions | text | analysis and review |
| `qwen3-tts` | text + speaker + language | audio | TTS and spoken drafts |
| `qwen-tts-local` | text + optional speaker/instruct/language | audio | local-service TTS |
| `mineru25-ocr` | documents + OCR settings | Markdown | OCR and document extraction |
| `ltx23-video` | audio/image + prompt | videos | audio-driven or image-driven video generation |

## Contracts And Artifacts

- The `generation/` aggregation layer defines execution-level expectations only; it does not own one shared artifact contract.
- New generation leaf skills must include input/output definitions, env vars, rate-limit rules, and local `.example.json` / `.schema.json` files.
- Image-generation leaf skills must define decode behavior when an API returns `b64_json` payloads.
- Validation entry: `npm run validate:skills`

## Rate Limits

⚠️ Gitee API requests cannot be sent in large bursts.

- send requests one by one
- wait 3–5 seconds between requests

## Cross References

- Video generation: `generation/ltx23-video/SKILL.md`
- Local image generation: `generation/qwen-image-local/SKILL.md`
- Text to speech: `generation/qwen3-tts/SKILL.md`
- Local text to speech: `generation/qwen-tts-local/SKILL.md`
- OCR / parsing: `generation/mineru25-ocr/SKILL.md`
