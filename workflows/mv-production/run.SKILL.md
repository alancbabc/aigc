---
name: mv-production (orchestrator)
description: Single-entry orchestrator for the mv-production workflow. Accepts an intake document, auto-resolves all artifact paths, tracks stage completion, and supports resume/retry.
trigger: Use when the user wants to run the full MV pipeline from intake to final video, or a contiguous range of stages, without manually invoking each script.
---

# MV Production Orchestrator (`run.py`)

## Overview

`run.py` is a workflow orchestrator that drives the entire mv-production stage pipeline from a single entry point. It manages:

- **Stage ordering**: executes stages in dependency order
- **Path resolution**: auto-derives all input/output file paths per stage
- **State tracking**: records completed stages in `.mv_workflow_state.json` at the project root
- **Resume**: skips already-completed stages; supports `--from` / `--to` for partial runs
- **Fallback**: auto-detects whether to use `assemble_final.py` (videos) or `assemble_still_mv.py` (still images)

## Usage

```bash
python workflows/mv-production/run.py \
    --intake <intake.json> \
    --project-root <project-dir> \
    [--from <stage>] \
    [--to <stage>] \
    [--force] \
    [--dry-run] \
    [--continue-on-error] \
    [--no-annotate]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--intake` | Path | yes | Intake document JSON (same format as Stage 0 intake) |
| `--project-root` | Path | yes | Project output directory |
| `--from` | str | no | Stage name to start from (inclusive) |
| `--to` | str | no | Stage name to end at (inclusive) |
| `--force` | flag | no | Re-run all selected stages even if already completed |
| `--dry-run` | flag | no | Print commands without executing |
| `--continue-on-error` | flag | no | Continue to next stage if current stage fails |
| `--no-annotate` | flag | no | Skip the final image annotation stage |

## Stage Names

| Stage Name | Corresponding Script | Artifacts |
|------------|---------------------|-----------|
| `init` | `init_project.py` | `project_meta.json`, `user_requirements.json` |
| `parse_lyrics` | `parse_lyrics.py` | `lyrics-timing.json` |
| `infer_sections` | `infer_sections_qwen3.py` | `song-sections-llm.json` |
| `interpret_segments` | `infer_segment_interpretation_qwen3.py` | `segment-interpretation.json` |
| `shot_plan` | `infer_shot_plan_qwen3.py` | `shot-plan.json` |
| `build_prompts` | `build_image_video_prompts.py` | `image-video-prompts.json` |
| `build_queue` | `build_generation_queue.py` | `image-generation-queue.json` |
| `generate_images` | `generate_images.py` | `image-generation-results.json` |
| `asset_manifest` | `build_asset_manifest.py` | `asset-manifest.json` |
| `apply_overrides` | `apply_shot_overrides.py` | *(overrides selected images)* |
| `select_manifest` | `build_selected_manifest.py` | `selected-asset-manifest.json` |
| `generate_videos` | `generate_videos.py` | `video-generation-results.json` |
| `build_timeline` | `build_timeline.py` | `timeline.json` |
| `assemble` | `assemble_final.py` / `assemble_still_mv.py` | `assets/videos/final/output.mp4` |
| `annotate` | `annotate_selected.py` | `assets/images/labeled/*.png` |

## Examples

### Full pipeline from intake to final video

```bash
python workflows/mv-production/run.py \
    --intake my_project/intake.json \
    --project-root my_project
```

### From shot plan to prompts only (useful for prompt engineering)

```bash
python workflows/mv-production/run.py \
    --intake my_project/intake.json \
    --project-root my_project \
    --from shot_plan --to build_prompts
```

### Re-run only the assemble step

```bash
python workflows/mv-production/run.py \
    --intake my_project/intake.json \
    --project-root my_project \
    --from assemble --to assemble
```

### Retry after a failure (skips completed stages)

```bash
python workflows/mv-production/run.py \
    --intake my_project/intake.json \
    --project-root my_project \
    --continue-on-error
```

### Force re-run everything

```bash
python workflows/mv-production/run.py \
    --intake my_project/intake.json \
    --project-root my_project \
    --force
```

## State File

The orchestrator maintains `.mv_workflow_state.json` in the project root:

```json
{
  "schema_version": "1.0",
  "project_root": "C:/path/to/project",
  "started_at": "2026-05-15T10:00:00",
  "stages": {
    "init": {
      "status": "completed",
      "started_at": "2026-05-15T10:00:00",
      "completed_at": "2026-05-15T10:00:05"
    },
    "parse_lyrics": {
      "status": "completed",
      "started_at": "2026-05-15T10:00:05",
      "completed_at": "2026-05-15T10:00:06"
    }
  }
}
```

Key behaviors:
- Stage completion is verified by **both** the state file entry **and** actual artifact file existence on disk
- If artifact files are missing but state says "completed", the stage is re-run
- If a stage fails, subsequent stages are skipped (unless `--continue-on-error`)
- Delete the state file or individual entries to reset completion status

## Path Resolution

All intermediate file paths are auto-derived from `--project-root`. The orchestrator reads:
- `intake.json` for initial paths (lyrics LRC, song audio)
- `project_meta.json` for the resolved song audio path (for final assembly)
- `user_requirements.json` for target resolution

## Design

The orchestrator's stage pipeline is defined in `STAGE_REGISTRY` — each entry specifies:
- **name**: CLI-visible stage name
- **builder**: function that returns the CLI command list for that stage
- **artifacts**: list of expected output files (relative to project root)

Architecture follows a simple sequential loop:

```
for each stage in [from:to]:
    if completed and not force → skip
    build command via stage builder function
    subprocess.run(command)
    if success → mark completed
    if failure → stop (or continue if --continue-on-error)
```
