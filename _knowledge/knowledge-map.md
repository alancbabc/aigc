# Knowledge Map

This file turns `_knowledge` from a loose reference folder into a shared dependency layer for the whole skill system.

Use it to answer two questions:

1. Which knowledge libraries should this skill read first?
2. Which knowledge libraries influence the output fields I am producing?

## Role-Based Routing

### Writer

Use these first:

- `_knowledge/Genre/`
- `_knowledge/Narrative/`
- `_knowledge/Dialogue/`
- `_knowledge/Actor/`
- `_knowledge/FamousDirectors/` when the user gives a director-style reference
- `_knowledge/ShortDrama/` when the project is episodic or platform-first

Typical impact:

- story tone
- structure pattern
- character archetypes
- dialogue rhythm
- subtext

### Director

Use these first:

- `_knowledge/Camera/`
- `_knowledge/Narrative/`
- `_knowledge/Transition/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`
- `_knowledge/Sound/` when the scene needs sound-effect emphasis, off-screen cues, or silence design

Typical impact:

- shot design
- rhythm and beat splitting
- transition selection
- performance framing
- scene atmosphere
- sound cue planning

### Art

Use these first:

- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/Genre/`
- `_knowledge/FamousDirectors/`

Typical impact:

- character appearance
- posture and body language
- scene mood
- visual anchors
- art direction style

## Output-Based Routing

### `outline.json`

Read first:

- `_knowledge/Genre/`
- `_knowledge/Narrative/`
- `_knowledge/FamousDirectors/` if style reference exists
- `_knowledge/ShortDrama/` if the project is an episodic short drama

Main impact:

- `genre`
- `tone`
- `core_theme`
- `structure_pattern`
- `director_style_reference`

### `characters.json`

Read first:

- `_knowledge/Actor/`
- `_knowledge/Genre/`
- `_knowledge/FamousDirectors/` if style reference exists

Main impact:

- `role_archetype`
- `personality`
- `body_language`
- `relationship_signal`
- `costume_anchor`

### `script.json`

Read first:

- `_knowledge/Narrative/`
- `_knowledge/Dialogue/`
- `_knowledge/Actor/`
- `_knowledge/ShortDrama/` for episodic hook and cliffhanger logic

Main impact:

- scene progression
- conflict pattern
- dialogue rhythm
- subtext
- emotional escalation

### `storyboard.json`

Read first:

- `_knowledge/Camera/`
- `_knowledge/Narrative/`
- `_knowledge/Transition/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`
- `_knowledge/Sound/` when sound-effect design helps the beat or reveal

Main impact:

- `shot_function`
- `shot_type`
- `camera_angle`
- `camera_movement`
- `composition`
- `transition_to_next`
- `transition_notes`
- `sound_design`

### `test-shoots.json`

Read first:

- `_knowledge/Camera/`
- `_knowledge/Transition/`
- `_knowledge/Actor/`
- `_knowledge/VisualEnvironment/`
- `_knowledge/FamousDirectors/`
- `_knowledge/Sound/` when a shot depends on sound cues, off-screen attention, or silence emphasis

Main impact:

- `shot_prompt`
- `frame_plan`
- `transition_context`
- `reference_images`
- `sound_cues`

## Priority Rules

1. Start from the task and output contract, not from the biggest knowledge folder.
2. Use knowledge libraries to extract rules and decisions, not to copy text directly into final output.
3. When multiple libraries apply, lock structure first, then add style.
4. If libraries conflict, prefer:
   - current skill contract
   - upstream artifacts
   - workflow rules
5. If the user supplies a director-style reference, route `_knowledge/FamousDirectors/` earlier than usual.

## Recommended Reading Order

For most tasks:

1. read the current skill contract
2. read the most relevant knowledge libraries from this map
3. extract decision fields
4. generate the artifact
5. review against the contract
