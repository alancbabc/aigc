# News Commentary Workflow

资讯解说类双人播报视频自动化生成 workflow。

入口：`/news-broadcast`

适合：

- 单条新闻快速解说
- 多链接汇总后的深度解说
- 固定栏目 / 固定主播嘉宾的系列化生产
- 使用内置双主播模板快速生成新闻节目
- 用户提供固定人物图后的视频生成

## Quick Start

Contract 文件已整理到 `contracts/` 目录；阶段说明看本文件，字段细节看 `contracts/README.md`。

### Start

```text
/news-broadcast
```

启动后，默认直接使用内置人物与音色。用户通常只需要再提供：

```text
文档链接或本地文档路径
```

workflow 应默认直接进入自动流程，不再先询问是否使用内置人物与音色。只有当用户主动提出要自定义人物、图片、名字或音色时，才切换到自定义资产路径。

### Input

```text
/news-broadcast
文档地址： [文章链接或本地文件路径]
```

### Local source format for article visuals

When the user wants article images to appear at suitable positions in the final clips, use this local package shape:

```text
news1/
├── news1.md
├── news_img_1.png
└── news_img_2.png
```

The markdown file places an image manifest before the article body, for example:

```markdown
# 标题

## 图片清单
1. 文件名：news_img_1.png
   标题：发布现场照片
   说明：适合在开头介绍联合发布时使用

2. 文件名：news_img_2.png
   标题：模型与集群流程技术图
   说明：适合在讲模型结构、训练流程或千卡集群时使用

## 正文
...
```

The extractor tolerates small formatting drift such as `说明。` instead of `说明：`, and minor filename differences such as hyphen vs underscore when matching files in the same folder.

### Output

```text
memory/[date]/[project-name]/v[version]/
├── user_requirements.json
├── article-analysis.json
├── article-review.json
├── series-profile.json
├── anchors.json
├── script.json
├── script-review.json
├── source-assets/
│   ├── source-visual-assets.json
│   └── images/
├── audio/
├── visuals/
│   └── anchors/
│       ├── female_solo.png
│       ├── male_solo.png
│       ├── duo_far.png
│       └── duo_close.png
└── video/
    ├── clip-plan.json
    ├── render-plan.json
    ├── segments/
    └── final/
```

## Stages

| Stage | Input | Output | Description |
|-------|-------|--------|-------------|
| 0 | User brief | user_requirements.json | Confirm default builtin path and any override intent |
| 1 | Article | article-analysis.json | Parse key points, meaning, uncertainty |
| 2 | Analysis | article-review.json | Verify commentary readiness |
| 3 | Source doc/images | source-assets/source-visual-assets.json | Extract source images plus caption/context metadata for still-image segments |
| 4 | Series settings | series-profile.json | Lock recurring show identity |
| 5 | Analysis + anchor context | script-skeleton.json → script-segments/*.json → script.json | Generate commentary dialogue through skeleton → segment drafting → `merge_script_stage5.py` |
| 6 | Script | script-review.json | Review depth, role function, and spoken-length control |
| 7 | Script | audio/tts-plan.json + audio/*.mp3 + audio/timeline.json | Split long lines before TTS, synthesize audio, and mark any overlimit audio for targeted re-synthesis |
| 8 | Audio | — | Spoken readability check |
| 9 | Audio timeline + Script + Refs | video/clip-plan.json | Group lines into mixed-render video clips |
| 10 | Clip plan + Refs | video/render-plan.json | Store final render requests for LTX or image+audio+ffmpeg |
| 11 | Render plan | video/segments/*.mp4 | Render segments via LTX or image+audio+ffmpeg |
| 12 | Segments | video/final/output.mp4 | Final assembly |

## Core Rules

1. Do not stop at article restatement.
2. Each discussion segment contains at least two of:
   - fact layer
   - explanation layer
   - meaning layer
3. Host translates and guides.
4. Guest interprets and judges.
5. Promotional articles include uncertainty or counterpoint when possible.
6. When multiple source links are provided, merge overlapping claims once and use extra links to deepen context.
7. In recurring mode, keep anchor identity and show cadence stable unless the user requests a reset.
8. Do not write oversized single-speaker paragraphs. If one speaker needs a long explanation, split it into multiple consecutive spoken lines during script generation.
9. Stage 5 must use a staged script flow: skeleton first, then segment drafting, then merge, then review.

## Content Quality Policy

For this workflow, "good content" does not mean preserving every source sentence. It means preserving the **right evidence**, translating it into **speakable commentary**, and avoiding the common failure mode of turning a dense source article into a slightly shorter but still overloaded spoken script.

Use this quality policy:

- **Evidence first**: major commentary claims are backed by source evidence, not just tone or summary.
- **Speakable first**: keep only the facts that a host or guest can naturally say aloud; move dense enumerations and stacked metrics to visuals.
- **Translation, not compression**: do not compress a long technical paragraph into one guest monologue. Re-express it as short spoken units with clear function.
- **Neutralize promo tone**: if the source sounds like a press release, lower the temperature before it becomes script text.
- **Separate layers**: facts, explanations, and judgments stay related, but do not get jammed into a single overloaded line.

## Stage 5 policy

This workflow runs on smaller execution models such as OpenClaw + minimax 2.5. Stage 5 must use the segmented writing flow below.

Execution order:

1. **Stage 5a — Script skeleton**
   - Decide segment list, segment goals, host/guest role split, and must-keep evidence per segment.
   - Write this to `script-skeleton.json`.
2. **Stage 5b — Segment drafting**
   - Generate each segment independently.
   - Keep the model focused only on the evidence and function of the current segment.
   - Write each drafted segment to `script-segments/segXX.json`.
3. **Stage 5c — Merge and length normalization**
   - Merge `script-skeleton.json` plus `script-segments/*.json` into `script.json`.
   - Split oversized lines before entering TTS.
   - Executor: `python workflows/news-commentary/scripts/merge_script_stage5.py --skeleton <project>/script-skeleton.json --segments-dir <project>/script-segments --output <project>/script.json`
4. **Stage 6 — Script review**
   - Review the merged script for evidence, tone, rhythm, role separation, and spoken-length control.

File chain:

- `memory/.../script-skeleton.json`
- `memory/.../script-segments/seg01.json`, `seg02.json`, `seg03.json`, ...
- `memory/.../script.json`

Explicit Stage 5 command chain:

```text
python workflows/news-commentary/scripts/merge_script_stage5.py --skeleton <project>/script-skeleton.json --segments-dir <project>/script-segments --output <project>/script.json
node workflows/news-commentary/scripts/build_tts_plan.mjs --script <project>/script.json --series-profile <project>/series-profile.json --output <project>/audio/tts-plan.json
node workflows/news-commentary/scripts/generate_local_tts_from_plan.mjs --tts-plan <project>/audio/tts-plan.json
python workflows/news-commentary/scripts/build_audio_timeline.py --tts-plan <project>/audio/tts-plan.json --series-profile <project>/series-profile.json --audio-dir <project>/audio --audio-format mp3 --output <project>/audio/timeline.json
```

## Visual Input Rule

Default path for this workflow is **builtin anchor templates**, with user-supplied assets as optional overrides.

For `/news-broadcast`, the common path is:

1. Start with builtin anchors and builtin voices by default.
2. Ask only for the document URL or local document path.
3. Run the workflow automatically.
4. Switch to custom anchor assets only if the user explicitly requests customization.

Automatic execution order for the common local-document path:

1. Stage 1 parses the article into `article-analysis.json`.
2. Stage 3 runs `extract_source_visual_assets.py`.
   - If the input is markdown with a top image manifest and sibling image files, use that declared manifest path first.
3. Stage 7 builds `audio/tts-plan.json`, then TTS output, then `audio/timeline.json` from the actually generated audio files.
4. Stage 9 runs `build_clip_plan.py` so source images can be routed into suitable clips before render packaging.
5. Stage 10 runs `build_render_plan.py` from the validated clip plan.

Before Stage 1, the workflow checks whether the user wants to override the defaults with their own:

- anchor images
- anchor names
- anchor TTS voices

If the user does not request overrides, the workflow continues with builtin assets directly. If the user does request overrides, the workflow must either:

- ask the user to provide them, or
- apply a builtin anchor template as fallback

This decision is stored in `user_requirements.json`, not guessed later during downstream clip planning.

Builtin anchor assets are no longer treated as a standalone main-flow stage. In the default path, they are preloaded defaults that the workflow carries forward automatically. Only when the user explicitly requests custom人物/图片/名字/音色 does the workflow expand into an override path for anchor assets.

Three-image package:

- `female_solo.png`
- `male_solo.png`
- `duo_far.png`
- `duo_close.png`

Use cases:

- female single speaking shot → `female_solo`
- male single speaking shot → `male_solo`
- intro / outro / same-frame moments → `duo_frame` planning state, rendered from `duo_close`
- opening first duo LTX clip only → `duo_close` as the sole reference image, using the fixed two-anchor prompt behavior
- opening later duo LTX clips → same as middle duo: `duo_close` as start frame only
- middle duo LTX path → `duo_close` as start frame only
- closing LTX path → `duo_close` as start frame only, with sign-off motion carried by prompt/action rather than an explicit ending frame

News-video policy:

- Use solo image for most spoken lines, especially explanation-heavy and lip-sync-critical lines.
- Use `duo_frame` as the planning-state label for opening, closing, and short same-frame transitions or mutual reaction beats; Stage 10 should resolve that state to the concrete `duo_close` render reference instead of a standalone duo image asset.
- During script drafting, treat opening/closing visual guidance as advisory only; do not tell the program to start on a source image or a solo anchor shot.
- Do not use long duo-frame explanation clips.
- If one speaker clearly owns the line, use that speaker's solo image even inside a two-anchor segment.
- Use `image_audio_ffmpeg` for data-heavy, factual, chart-like, or source-figure moments when extracted document images add more value than a generated talking-head shot.
- If a markdown source provides an image manifest plus sibling image files, treat those declared images as first-class source visuals rather than waiting for embedded-doc extraction.
- Use `ltx` for anchor-led intros, reactions, emphasis, and moments where on-camera persona matters more than source imagery.
- In Stage 10 render planning, the very first opening duo LTX clip should also reuse the same `duo_close`-only reference-image strategy and fixed two-anchor prompt behavior as middle duo clips, rather than using a separate opening push-in treatment.
- Derive clip duration from `audio/timeline.json`, including pauses, and keep the audio-side LTX clip within a practical ~15s limit.
- For Stage 10 LTX requests, use only `audio_to_video`, leave `width` / `height` unspecified so the model service uses its default resolution, set `a2v_audio_start_time=0.0`, set `a2v_audio_insert_video_time=0.5` so audio begins 0.5 second after video start, and set request `duration_seconds = audio duration + 1.0` second.
- For Stage 10 LTX prompt assembly, build the positive prompt from the fixed template system and insert both the speaking role and the spoken Chinese line inside the speaking-action sentence, instead of appending dialogue as a final trailing sentence. In duo scenes use explicit role pairs: `speaker_focus=host` => `left female speaker` + `right male listener`, `speaker_focus=guest` => `right male speaker` + `left female listener`; in solo scenes use `speaker_focus=host` => `female anchor`, `speaker_focus=guest` => `male anchor`.
- Move negative constraints such as dramatic motion, shaky framing, text/logo/watermark, subtitles/captions/on-screen text, exaggerated gestures, wandering eyes, weak mouth motion, frozen lips, and unwanted listener motion into `ltx_request.negative_prompt` instead of mixing them into the positive prompt paragraph.
- During script generation, estimate spoken length per line and split long single-speaker explanations early so each spoken unit stays within a practical ~8-15s range.
- Treat `audio/tts-plan.json` as a fallback safety layer, not the primary place where oversized script lines are discovered for the first time.
- After TTS, use real audio duration as the hard gate. If any single audio entry exceeds `15s`, trace it back through `script_line_id` / `split_group_id`, split only that script line further, and regenerate only the affected audio entries.
- After TTS completes, always measure `duration_seconds` from the generated audio file itself when materializing `audio/timeline.json`; do not copy `estimated_duration_seconds` forward as if it were real audio length.
- For builtin anchor templates, local TTS speaker / instruction settings should come from `builtin-anchor-templates/<template_id>.json`, get copied into `audio/tts-plan.json`, and be consumed by `generate_local_tts_from_plan.mjs` during Stage 7 execution.
- For `render_mode=ltx`, Stage 9 may merge consecutive anchor-led entries when they keep the same reference image and the merged audio duration stays within the practical LTX limit (`<=16s` in the current workflow).
- Each extracted source image must be used exactly once in the whole program; when it is chosen, keep it as one continuous document-led visual block, but cap that single image block at `6s`, then cut back to duo/solo anchor shots.
- For `image_audio_ffmpeg`, Stage 9 should keep a source image only while its continuous document-led block remains within `6s`. Stage 11 then merges any multi-audio clip into one WAV with `1s` of silence between adjacent clips before rendering against the still image.
- Keep pre-TTS duration estimates in `script.json` / `audio/tts-plan.json` as `estimated_duration_seconds`, but use `computed_duration_seconds` in `video/clip-plan.json` and `video/render-plan.json` because those durations are derived from either `audio/timeline.json` or an explicit clip-planning fallback source rather than raw script estimation.
- Use `must_keep_evidence` to decide what survives into spoken lines.
- Use `visual_only_details` to move dense numeric or process-heavy details out of dialogue and into cards, captions, or source-image segments.
- Use `promo_phrases_to_neutralize` and `commentary_claim_boundaries` to keep the script from drifting into unsupported celebration or hollow rhetoric.
- For `render_mode=ltx`, allow the model service default output size. For `render_mode=image_audio_ffmpeg`, match output video size to the selected image dimensions.
- When a source image aspect ratio differs from the target frame, use proportional scaling plus pad rather than stretching.

Contract cross-check rule:

- every `audio_entry_id` used in `video/clip-plan.json` must exist in `audio/timeline.json`
- every `clip_id` in `video/clip-plan.json` must appear in `video/render-plan.json`

## Dependencies

### Skills

- `writer/character-profile` - Anchor-role design reference
- `writer/script-writing` - Script structure reference
- `generation/qwen3-tts` - TTS generation
- `generation/ltx23-video` - LTX-2 audio-to-video generation for anchor-led segments
- `_prompts/ModelGuides/LTX-Video/` - Final prompt optimization before LTX generation
- `generation/flux-text-to-image` - Reference image generation

### Stage 4 Helper Script

- Build a pre-TTS split plan with: `node workflows/news-commentary/scripts/build_tts_plan.mjs --script /path/to/project/script.json --series-profile /path/to/project/series-profile.json --output /path/to/project/audio/tts-plan.json`
- For local TTS execution, use: `node workflows/news-commentary/scripts/generate_local_tts_from_plan.mjs --tts-plan /path/to/project/audio/tts-plan.json`
- Use `audio/tts-plan.json` as the synthesis unit list for TTS generation rather than feeding raw long lines directly into TTS
- The script must already be split well enough that this helper only makes small corrective splits, not major structural repairs
- After TTS generation, materialize actual timeline data with: `python workflows/news-commentary/scripts/build_audio_timeline.py --tts-plan /path/to/project/audio/tts-plan.json --series-profile /path/to/project/series-profile.json --audio-dir /path/to/project/audio --audio-format mp3 --output /path/to/project/audio/timeline.json`
- After TTS synthesis, if any `audio/timeline.json` entry exceeds `15s`, do not continue downstream unchanged. Re-split the corresponding script line and re-generate only the affected audio entries until all audio entries are within limit.

### Knowledge

- `_knowledge/Actor/` - Role archetypes, expression
- `_knowledge/Dialogue/` - Turn-taking, Q&A rhythm
- `_knowledge/Narrative/` - Commentary pacing

### Models

- LTX-2 A2VidTwoStage - Audio-to-video generation path used for all workflow LTX clips

## Render Routing Summary

1. Start from builtin anchor assets unless the user overrides them.
2. Opening / closing / short dialogue beats use `duo_frame`.
3. Longer single-speaker explanation beats use the role-matched solo image.
4. If a usable source image from the article carries the information better than an anchor shot, route the clip to `image_audio_ffmpeg`.
5. Otherwise route the clip to `ltx` using the anchor reference image path chosen by Stage 9, one or more audio clips when merge rules allow, and an English prompt optimized with `_prompts/ModelGuides/LTX-Video/`.

## Configuration

```json
{
  "style": "professional | casual | humorous",
  "target_duration": "3min | 5min | 10min",
  "series_mode": "one_off | recurring",
  "language": "zh-CN | en-US",
  "anchor_asset_mode": "user_provided | builtin_template | mixed",
  "builtin_anchor_template_id": "optional-template-id",
  "missing_anchor_assets_policy": "ask | auto_fill",
  "anchor_name_inputs": {
    "host_name": "optional",
    "guest_name": "optional"
  },
  "anchor_voice_inputs": {
    "host_tts_voice_id": "optional",
    "guest_tts_voice_id": "optional",
    "host_voice_reference_audio": "optional wav path",
    "guest_voice_reference_audio": "optional wav path"
  },
  "anchor_image_inputs": {
    "female_solo": "optional",
    "male_solo": "optional",
    "duo_frame": "optional"
  },
  "anchor_preference": {
    "host_gender": "female",
    "guest_gender": "male",
    "style": "news | talkshow | educational"
  }
}
```

## Recurring Series Notes

For repeated news稿 production, add a `series-profile.json` that stores:

- show title
- tagline
- tone
- anchor defaults
- builtin template defaults for names, voices, and visual assets
- repetition guardrails
- intro cadence

This prevents every new episode from being generated as if it were a one-off script.

## Contracts

- 合同索引：`contracts/README.md`
- 所有 contract 按模块分目录，完整列表：
  - `contracts/user-requirements/`
  - `contracts/article-analysis/`
  - `contracts/article-review/`
  - `contracts/source-visual-assets/`
  - `contracts/series-profile/`
  - `contracts/anchors/`
  - `contracts/script/`
  - `contracts/script-segment/`
  - `contracts/script-skeleton/`
  - `contracts/script-review/`
  - `contracts/tts-plan/`
  - `contracts/audio-timeline/`
  - `contracts/clip-plan/`
  - `contracts/render-plan/`
  - `contracts/ltx-prompt-package/`
  - `contracts/visual-assets/`
- builtin 主播模板仍保留在：`builtin-anchor-templates/default-news-duo-v1.json`

## Notes

- TTS stage defaults to `mp3` clips, but the workflow may convert them to `wav` before LTX if the deployment requires it.
- Stage 3 executor example: `python workflows/news-commentary/scripts/extract_source_visual_assets.py --inputs /path/to/news1.docx --output-dir /path/to/project/source-assets`
- Markdown path example: `python workflows/news-commentary/scripts/extract_source_visual_assets.py --inputs /path/to/news1.md --output-dir /path/to/project/source-assets`
- Stage 3 tries to populate `images[].caption` and `images[].context_hint` from image-adjacent title/caption text and nearby paragraphs in the source doc/docx.
- For markdown sources, Stage 3 first parses the image manifest at the top of the document, then matches sibling image files by filename with tolerant normalization, and uses the declared 标题/说明 as `caption` / `context_hint`.
- Stage 9 executor example: `python workflows/news-commentary/scripts/build_clip_plan.py --script /path/to/project/script.json --audio-timeline /path/to/project/audio/timeline.json --source-visual-assets /path/to/project/source-assets/source-visual-assets.json --output /path/to/project/video/clip-plan.json`
- If `audio/timeline.json` is not available yet, Stage 9 temporarily falls back to `audio/tts-plan.json`, but final routing uses real `audio/timeline.json`.
- Stage 9 routes a clip to `image_audio_ffmpeg` when a declared source image strongly matches the line text, segment takeaway, or segment goal better than an anchor shot.
- Opening / closing segments should still begin as duo-frame at Stage 9 even if Stage 5 left an over-eager visual note about later source-image usage.
- If consecutive Stage 9 entries keep the same chosen source image, merge them into one document-led clip only while the accumulated real audio duration stays within `6s`; after that, cut back to anchor-led clips and do not reuse that image later in the program.
- Stage 10 executor example: `python workflows/news-commentary/scripts/build_render_plan.py --audio-timeline /path/to/project/audio/timeline.json --clip-plan /path/to/project/video/clip-plan.json --source-visual-assets /path/to/project/source-assets/source-visual-assets.json --output /path/to/project/video/render-plan.json`
- Stage 11 executor example: `python workflows/news-commentary/scripts/stage11_render_segments.py --render-plan /path/to/project/video/render-plan.json`
- Stage 11 merges any multi-audio render item into one WAV with `1s` of silence between adjacent source clips before handing that audio to LTX or ffmpeg.
- For actual rendering, `image_audio_ffmpeg` items render once only. `ltx` items fan out into four parallel variants by default and save sibling outputs as `_v1`, `_v2`, `_v3`, `_v4` under the same target segment directory.
- Stage 12 executor example: `python workflows/news-commentary/scripts/stage12_final_assembly.py --render-plan /path/to/project/video/render-plan.json`
- Example ffmpeg command for an `image_audio_ffmpeg` render item: `ffmpeg -y -loop 1 -i /path/to/project/source-assets/images/doc01_img01.png -i /path/to/project/audio/guest/line_005.mp3 -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1" -r 30 -c:v libx264 -preset veryfast -crf 23 -tune stillimage -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart -shortest /path/to/project/video/segments/seg03_clip03.mp4`
- Example Stage 12 concat list file at `/path/to/project/video/final/segments.txt`:

```text
file '../segments/seg01_clip01.mp4'
file '../segments/seg02_clip01.mp4'
file '../segments/seg03_clip03.mp4'
```

- Example final assembly command when segment streams already match and have been explicitly verified as identical: `ffmpeg -y -f concat -safe 0 -i /path/to/project/video/final/segments.txt -c copy /path/to/project/video/final/output.mp4`
- Default final assembly command for this workflow: `ffmpeg -y -f concat -safe 0 -i /path/to/project/video/final/segments.txt -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart /path/to/project/video/final/output.mp4`
- Prefer Stage 12 re-encode by default because Stage 11 may mix LTX-rendered clips with ffmpeg-rendered clips, and those outputs are not guaranteed to be stream-identical enough for safe `-c copy` concatenation.
- If no video generation model is configured, the workflow may validly stop after Stage 7 or Stage 8.
- Use hyphenated artifact names consistently: `article-analysis.json`, not `article_analysis.json`.
