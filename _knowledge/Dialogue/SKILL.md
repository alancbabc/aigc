---
name: Dialogue
description: Shared dialogue knowledge for script writing and dialogue-heavy storyboard planning. Covers rhythm, subtext, reaction priority, and dialogue-to-visual conversion.
trigger: Use when a skill needs to improve lines, scene dialogue rhythm, listener reaction design, or dialogue scene shot logic.
---

# Dialogue

## Use For

- `writer/script-writing`
- `writer/polish`
- `director/storyboard`

## Common Use Cases

- improving dialogue rhythm
- designing pauses and interruptions
- strengthening subtext
- planning reaction shots in dialogue scenes
- turning spoken lines into visual beats

## Output Impact

- `script.json -> scenes[].dialogue`
- `script.json -> scenes[].duration`
- `storyboard.json -> scenes[].shots[].dialogue`
- `storyboard.json -> scenes[].shots[].description`

## AI Usage Principles

1. Dialogue is not only what is said, but also what is avoided, delayed, or redirected.
2. Listener reaction is often more valuable than repeating the speaker visually.
3. A dialogue scene should have rhythm changes, not just line-by-line alternation.
4. Spoken content, subtext, and physical action should support each other.
5. If dialogue carries no conflict, concealment, pressure, or shift, it is likely too flat.

## Core Rules

### Rule 1: Every Important Line Needs a Function

A line should usually do at least one of these:

- reveal information
- hide information
- change power balance
- trigger emotion
- delay or resist a question
- push the scene toward a choice

### Rule 2: Reaction Matters

- the most important moment may be the listener's reaction, not the line itself
- if a line lands emotionally, consider holding on the receiver
- if a line is dishonest, the reaction shot is often stronger than the speaker shot

### Rule 3: Dialogue Needs Physical Anchors

Avoid scenes where characters only stand and exchange text. Pair dialogue with:

- walking
- cooking
- packing
- driving
- searching
- cleaning
- handling an object

Physical action helps pacing and subtext.

### Rule 4: Pause Design Creates Meaning

- comma-like pause -> small emotional beat
- sentence-ending pause -> aftertaste, discomfort, silence, judgment
- unfinished line -> interruption, hesitation, concealment, emotional overflow

## Dialogue Rhythm Heuristics

- short lines -> speed, tension, conflict
- long lines -> persuasion, confession, explanation, emotional overflow
- interruption -> dominance, panic, urgency
- silence after key information -> stronger than immediate reply
- repeated wording -> obsession, sarcasm, emotional fixation

## Subtext Heuristics

Common useful patterns:

- saying something polite while meaning the opposite
- answering a different question to avoid exposure
- talking about an object to avoid talking about feelings
- speaking calmly while body language reveals stress
- using jokes to hide vulnerability

## Dialogue-to-Visual Conversion

When a scene is dialogue-heavy, convert it into visual beats:

- speaker beat
- listener beat
- silent reaction beat
- object or environment beat

Do not mechanically alternate speaker and listener every line.

## Shot Design Heuristics For Dialogue Scenes

- use `medium shot` or over-the-shoulder as the stable base
- use `close-up` when emotional reading becomes more important than information clarity
- hold on the listener when subtext or emotional impact matters
- use shared framing when relationship tension matters
- vary angle or distance only when power, emotion, or relation changes

## Pattern Library

### Conflict Dialogue

- shorter lines
- more interruption
- faster turn-taking
- more reaction shots
- less decorative camera movement

### Confession Dialogue

- slower rhythm
- longer pauses
- close-ups gain value
- silence becomes part of the scene

### Flirtation Or Tension Dialogue

- indirect wording
- unstable eye contact
- delayed answers
- reaction beats often matter more than the literal text

### Exposition Dialogue

- break information across action
- avoid long uninterrupted explanation blocks
- let one character resist or challenge the explanation

## Anti-Patterns

- line-by-line flat alternation with no change in power or emotion
- characters saying exactly what they feel with no tension
- long exposition with no action support
- repeating the same meaning in multiple lines
- showing only the speaker when the listener is where the scene actually changes

## Suggested Extraction Targets

Before writing or revising a dialogue scene, extract:

- `dialogue_goal`
- `power_balance`
- `subtext_pattern`
- `reaction_priority`
- `rhythm_mode`
- `physical_anchor`

## Suggested Questions

- What is the line really trying to achieve?
- What is the speaker not saying directly?
- Who changes after this exchange?
- Should the camera stay on the speaker or the listener?
- Does the scene have physical action, silence, or reaction to break repetition?
