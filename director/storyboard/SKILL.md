---
name: storyboard
description: Design scene-level and shot-level visual storytelling from script and character inputs, while controlling shot count, duration support, transition design, and downstream handoff quality.
trigger: Call when the project needs storyboard design, shot planning, or scene-level camera language.
---

# Storyboard

## What This Skill Does

This skill turns story material into:
- scene breakdown
- shot planning
- camera language
- transition planning
- downstream-ready storyboard contracts

It is responsible for:
- deciding shot structure scene by scene
- describing each shot clearly enough for downstream art and generation
- controlling redundant shots
- making sure shot duration is supported by real content

It is not responsible for:
- redesigning character appearance
- replacing scene-design references
- directly generating images

## Knowledge Dependencies

Prioritize:
- `_knowledge/Camera/`
- `_knowledge/Narrative/`
- `_knowledge/Transition/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`
- `_knowledge/Sound/` when scene-level sound-effect planning helps the beat, reveal, or tension

Use rules:
1. determine scene function first, then choose camera language
2. let Camera, Actor, and Environment define structure
3. use FamousDirectors only as style reinforcement, not as a replacement for narrative logic
4. use Sound only for sound effects, ambience, off-screen cues, and silence design
5. let knowledge affect `environment`, `narrative_type`, `shots[]`, `transition_to_next`, and optional sound fields

## Inputs

- `script.json`
- `characters.json`
- optional style references from upstream workflow

## Outputs

Main output:
- `storyboard.json`

Review output:
- `storyboard-review.json`

Contracts:
- Example: `director/storyboard/storyboard.example.json`
- Schema: `director/storyboard/storyboard.schema.json`
- Review example: `director/storyboard/storyboard-review.example.json`
- Review schema: `director/storyboard/storyboard-review.schema.json`

## Transition Skill Routing

Use `director/transition` when a scene boundary needs an explicit transition decision instead of a default cut.

Trigger it when:
- there is a visible time jump, space jump, or emotion shift between adjacent scenes
- the transition may be `MATCH CUT`, `SMASH CUT`, `AERIAL MATCH CUT`, or `SKY TRANSITION`
- the storyboard needs a clear `visual_bridge`, `reason`, or `execution_notes`
- the user asks to optimize the transition between two specific segments

Integration rule:
1. finish current scene-level shot design first
2. extract `current_scene` and `next_scene`
3. call `director/transition`
4. map the result back into `transition_to_next`
5. persist extra notes into `transition_notes` when needed

## Scene Design Routing

Use `art/scene-design` after the scene-level shot plan is stable.

Trigger `art/scene-design` for a **single main reference** when:
- the scene has only one shot
- multiple shots stay close in angle and scale
- the scene mainly needs one broad environment mood reference

Trigger `art/scene-design` for a **multi-view set** when:
- the same scene contains both wide or medium shots and close shots
- downstream work needs both layout readability and local detail
- the scene includes reverse angles, entrance views, or large perspective shifts
- the scene will be reused across multiple shots and visual continuity matters

Typical mapping:
- wide or long shot presence -> `establishing`
- medium shot presence -> `medium_environment`
- close-up or insert on environment detail -> `close_detail`
- reverse angle coverage -> `reverse_angle`
- doorway or arrival shot -> `entrance_view`

Integration rule:
1. finish `environment` and `shots[]` for the current scene first
2. inspect shot scale and angle spread
3. decide whether the scene needs one main reference or a multi-view set
4. call `art/scene-design`
5. keep all returned references under one shared scene base

## Sound Routing

Use `_knowledge/Sound/` when sound effects help define the scene beat more clearly.

Typical triggers:
- an off-screen sound reveals danger, arrival, or attention shift
- a silence moment should land shock, realization, or emotional collapse
- the scene depends on concrete environmental sound such as rain, fluorescent buzz, traffic, or footsteps
- object interaction sound is important enough to support the shot beat

Persistence rule:
- put scene-level sound planning in `sound_design`
- put shot-level sound emphasis in `shots[].sound_cues`
- keep this layer focused on sound effects rather than music

## Core Principle

Shots are narrative units first, camera units second.

This means:
- do not create a new shot only because another angle is possible
- every shot must justify its own existence with new information, new emotion, new action phase, or a necessary rhythm change
- if two adjacent shots carry the same narrative value, prefer merging them

## Workflow

### Step 1: Understand Scene Function

For each scene, determine:
- what story function it serves
- what emotional change happens
- what action phase begins or ends
- what environment information must be readable

### Step 2: Extract Beats

Before writing shots, reduce the scene into a small set of beats.

Each beat should answer:
- what new information appears here
- what emotional change happens here
- what action phase starts or ends here
- whether this beat truly needs a new camera setup

Default rule:
- one beat can map to one shot
- but multiple light beats may share one shot if one setup can carry them clearly
- do not split one simple beat into multiple shots only to increase shot count

### Step 3: Decide Merge vs Split

Merge when:
- adjacent shots share the same subject focus
- the emotional beat is the same
- there is no new visual information
- dialogue continues naturally in one setup
- a camera change does not change narrative meaning

Split when:
- a new action phase starts
- emotional power depends on a reaction or reveal
- spatial understanding would otherwise become unclear
- a change in scale or perspective carries real narrative value

Typical merge cases:
- lift object -> throw object
- pick up -> examine
- walk to mark -> stop at mark

### Step 4: Check Logic Between Adjacent Shots

Adjacent shots must preserve causal, temporal, and spatial logic.

Avoid:
- abrupt scale jumps without purpose
- character position changes without readable movement
- broken time order

### Step 4.5: Plan Scene References

After shot design, decide whether the scene should request:
- one main reference image
- or a multi-view environment set from `art/scene-design`

Use one main reference when:
- the whole scene can be understood from one stable angle
- shot changes are minor
- close detail is not important downstream

Use a multi-view set when:
- the scene needs both layout readability and local detail readability
- there is a strong jump between wide, medium, and close environmental usage
- the same environment must support both establishing shots and detail-driven shots

Do not ask `art/scene-design` to redesign the scene per shot.
Always preserve one shared environment base per scene.

### Step 5: Estimate Duration

Base duration should come from:
- dialogue content
- readable action progression
- meaningful camera movement
- emotional hold with visual tension
- environment information the audience truly needs to absorb

General heuristics:
- pure action without dialogue: around 3 seconds minimum
- dialogue shot: dialogue length x reading/speaking pace, with a reasonable floor
- emotional hold: around 4 seconds minimum
- transition empty shot: around 2-3 seconds

Upper rule:
- a single shot should rarely exceed 10 seconds without a strong reason

### Step 5.5: Duration Support Rule

Every shot duration must be supported by at least one of these:
- dialogue
- readable action progression
- meaningful camera movement
- emotional hold
- necessary environment absorption

If a shot duration is not supported, do one of these:
1. shorten the shot
2. merge it with the previous or next shot
3. enrich the shot with real action, reaction, or information

Warning signs:
- thin description but long duration
- no dialogue, no action, and no atmospheric reason
- repeated information from the previous shot
- angle change without meaning change

## Quality Rules

- never create redundant shots only to fill runtime
- every shot must have a narrative function
- when runtime pressure appears, protect clarity and narrative logic before chasing length

## Shot Review Questions

For each shot, ask:
- what is this shot doing that the previous shot did not already do
- can the previous and current shot be merged without losing clarity
- is the planned duration truly supported by action, dialogue, emotion, or environment
- if this shot were deleted, would the scene lose anything important

If the last answer is “not much”, the shot is probably redundant.

## Scene-Level Review Pass

After finishing one scene, produce a small internal review before locking the storyboard.

The review should assess:
- `redundant_shot_risk`
- `duration_support_risk`
- `merge_suggestions`
- `duration_adjustments`

Use these rules:
- `redundant_shot_risk = high` when multiple adjacent shots repeat the same function or angle change without new meaning
- `duration_support_risk = high` when one or more shots have weak `duration_basis` or thin descriptions compared with planned duration
- add `merge_suggestions` when adjacent shots can be combined without losing clarity
- add `duration_adjustments` when a shot should be shortened, merged, or enriched

## Storage

- `memory/[date]/[title]/v[version]/storyboard/storyboard.json`
- `memory/[date]/[title]/v[version]/storyboard/storyboard-review.json`
- `memory/[date]/[title]/v[version]/storyboard/storyboard-references.json`

## Downstream

- `director/test-shoots`
- later image or video generation stages
