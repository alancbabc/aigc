---
name: transition
description: Design the transition between two scenes, segments, or shots, and output a structured result that can be mapped directly into storyboard, test-shoots, and downstream transition-clip planning.
trigger: Call when the user wants to design a transition between two segments, or when storyboard/test-shoots needs a concrete transition decision.
---

# Transition

## Use This When

- the user already has two segments and only wants help choosing how to transition between them
- `director/storyboard` is ready, but a scene boundary still lacks a clear transition
- `director/test-shoots` needs to decide whether an extra `intermediate` or `last` frame is necessary
- a transition idea must be turned into structured downstream fields
- a non-cut transition must be turned into a standalone downstream transition clip design

## Knowledge Dependencies

Prioritize:
- `_knowledge/Transition/`
- `_knowledge/Camera/`
- `_knowledge/Narrative/`
- `_knowledge/FamousDirectors/`

Use rules:
1. understand the relationship between the two segments first, then choose a transition type
2. default to `CUT` unless there is a clear reason to escalate
3. always explain the bridge, the reason, the execution, and whether extra frames are needed
4. only design a standalone transition clip when the transition type is not `CUT`
5. for advanced transitions, treat the previous tail frame and next head frame as the required boundary anchors

## Inputs

Supported modes:
- standalone:
  - `from_segment`
  - `to_segment`
  - `goal`
  - optional `style_reference`
- workflow:
  - `current_scene` or `current_shot`
  - `next_scene` or `next_shot`
  - optional `storyboard_context`
  - optional `rhythm_goal`

Optional VLM-assisted inputs:
- `last_frame_image`
- `first_frame_image`
- `last_frame_analysis`
- `first_frame_analysis`

## Outputs

- `transition_type`
- `transition_goal`
- `visual_bridge`
- `reason`
- `execution_notes`
- `frame_requirement`
- `prompt_hint`
- `transition_clip_needed`
- optional `transition_clip`

Main output file:
- `transition.json`

Optional analysis artifacts:
- `last-frame-analysis.json`
- `first-frame-analysis.json`

Contracts:
- Example: `director/transition/transition.example.json`
- Schema: `director/transition/transition.schema.json`
- Frame-analysis example: `director/transition/frame-analysis.example.json`
- Frame-analysis schema: `director/transition/frame-analysis.schema.json`

## Downstream Field Mapping

- `storyboard.scenes[].transition_to_next` <- `transition_type`
- `storyboard.scenes[].transition_notes.visual_bridge` <- `visual_bridge`
- `storyboard.scenes[].transition_notes.reason` <- `reason`
- `storyboard.scenes[].transition_notes.execution_notes` <- `execution_notes`
- `test-shoots.shots[].transition_to_next` <- `transition_type`
- `test-shoots.shots[].transition_context.visual_bridge` <- `visual_bridge`
- `test-shoots.shots[].transition_context.prompt_hint` <- `prompt_hint`
- `test-shoots.shots[].transition_context.frame_requirement` <- `frame_requirement`
- `film-production/video-prompt-drafts.json` transition entries <- `transition_clip.raw_prompt`
- `film-production/video-ltx-prompts.json` transition entries <- `transition_clip.optimized_prompt`
- `film-production/video-plan.json` transition entries <- `transition_clip.ltx_request_stub`

## Decision Rules

Prefer:
- `CUT` for direct, fast, clear progression
- `DISSOLVE` for soft emotional continuity or time flow
- `MATCH CUT` when a real visual bridge exists
- `SMASH CUT` for shock, contrast, or forceful rhythm
- `AERIAL MATCH CUT` or `SKY TRANSITION` when the bridge is built through sky or upward motion

Do not use a complex transition just because it feels more cinematic.

## VLM Assist

When frame images are available, use `generation/qwen2.5-vl` as a frame analysis helper.

Role boundary:
- `qwen2.5-vl` provides visual evidence
- `director/transition` makes the final decision

Recommended flow:
1. analyze the previous segment's `last_frame_image`
2. write `last-frame-analysis.json`
3. analyze the next segment's `first_frame_image`
4. write `first-frame-analysis.json`
5. compare both inside `director/transition`
6. decide `transition_type`, `visual_bridge`, `frame_requirement`, and `prompt_hint`

## Standalone Transition Clip Rule

If `transition_type = CUT`:

- do not design a standalone transition clip
- let downstream video stages connect the two neighboring shot clips directly

If `transition_type != CUT`:

- design a standalone `transition_clip`
- use the previous segment's tail frame and the next segment's head frame as the required image anchors
- write a raw prompt that describes the bridge in direct downstream-ready terms
- write an optimized LTX prompt that converts the bridge into a model-ready motion description
- keep this transition clip separate from both the previous and next normal shot clip

Required transition clip design fields:

- `clip_id`
- `clip_type = transition`
- `from_shot_id`
- `to_shot_id`
- `from_last_frame`
- `to_first_frame`
- `transition_type`
- `visual_bridge`
- `bridge_logic`
- `raw_prompt`
- `optimized_prompt`
- `ltx_request_stub`

Use VLM mainly to inspect:
- main subject
- subject position
- motion direction
- camera angle
- composition focus
- lighting continuity
- mood continuity
- bridge candidates
- continuity risks

Suggested VLM prompt:

```text
Analyze this frame for transition planning. Identify the main subject, subject position, motion direction, camera angle, composition focus, lighting, mood, possible visual bridge elements, and any continuity risks. Return a concise structured analysis.
```

## Persistence Examples

### Storyboard

```json
{
  "transition_to_next": "AERIAL MATCH CUT",
  "transition_notes": {
    "visual_bridge": "Paper airplane rises into the sky -> sky reveals the next scene",
    "reason": "Both segments share a sky-based bridge and the emotion stays continuous, so an aerial match cut is the most natural transition choice.",
    "execution_notes": [
      "End the first segment with the paper airplane moving away in a clear direction",
      "Preserve the upward motion direction into the next scene reveal"
    ]
  }
}
```

### Test Shoots

```json
{
  "transition_to_next": "AERIAL MATCH CUT",
  "transition_context": {
    "visual_bridge": "Paper airplane rises into the sky -> sky reveals the next scene",
    "prompt_hint": "aerial match cut, camera follows the paper airplane upward into the sky, sky bridge into the next scene",
    "frame_requirement": {
      "needs_extra_frames": true,
      "recommended_frames": ["first", "intermediate", "last"]
    }
  }
}
```

## Done When

- a clear `transition_type` is chosen
- the reason is explained, not just the label
- the bridge element is identified
- extra frame need is judged
- the output matches `transition.schema.json`
- the result can be mapped cleanly into both storyboard and test-shoots
- if the transition is not `CUT`, the result also contains a usable standalone `transition_clip` design for downstream video generation
