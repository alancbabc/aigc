---
name: LTX-2-prompt-guide
description: Write and optimize English prompts for LTX-2 text-to-video generation.
trigger: Use when generating or revising prompts for LTX-2 video.
---

# LTX-2 Prompt Guide

> **Rule:** LTX-2 prompts must be written in **English only**.

## Goal

Turn a scene idea into a **single flowing English video prompt** that LTX-2 can execute reliably.

## Instructions

When invoked:
- output **one English prompt only**
- write **one single paragraph**
- write **4–8 sentences**
- use **present tense**
- keep **one clear visual sequence from start to end**
- make the result **ready to paste into LTX-2**

## Prompt Structure

Build the prompt in this order:

1. **Shot** — establish the shot type and style
2. **Scene** — lighting, atmosphere, color, texture, time of day
3. **Character** — age, appearance, clothing, distinguishing details
4. **Action** — one clear action sequence in present tense
5. **Camera** — describe camera movement relative to the subject
6. **Audio** — ambient sound, dialogue, music if needed

## Writing Rules

- Write as **one flowing paragraph**, not a keyword list.
- Use **present tense** verbs.
- Match detail to shot scale.
- Express emotion through **visible behavior**, not labels.
- Use **specific lighting cues** instead of vague mood words.
- Keep the scene readable and physically simple.
- Prefer **one main subject** and **one main action**.

## Prompt Formula

```text
[STYLE / SHOT]. [SCENE with lighting, atmosphere, texture, time of day]. [CHARACTER details]. [ACTION unfolds from beginning to end in present tense]. [CAMERA movement relative to subject]. [AUDIO details]. [Emotion shown through posture, gesture, or facial expression].
```

## Use

### Shot / Camera
- cinematic wide shot
- wide establishing shot
- medium close-up
- extreme close-up
- over-the-shoulder
- static frame
- handheld tracking
- pushes in
- pulls back
- pans across
- circles around
- crane shot
- overhead view

### Lighting / Atmosphere
- warm golden hour light
- soft studio lighting
- neon glow
- dramatic shadows
- cold blue light
- fog
- rain
- dust
- smoke
- reflections
- worn pavement
- glossy surfaces

### Style
- cinematic
- film noir
- painterly
- surreal
- cyberpunk
- comic-book
- documentary
- stop-motion
- hand-drawn
- pixelated animation

## Avoid

- emotion labels without visual cues
  - bad: `a sad woman`
  - better: `a woman sits hunched forward, eyes wet, hands trembling`
- text, logos, signage, brand names
- overloaded scenes with too many characters or actions
- chaotic physics or fast nonlinear motion
- conflicting lighting logic unless intentionally motivated
- stacked camera instructions like:
  - bad: `zoom while panning while rotating while tilting`

## Validation

Before returning the prompt, verify:

- Is the prompt fully in English?
- Is it one paragraph?
- Is it 4–8 sentences?
- Does it clearly establish shot, scene, character, action, camera, and audio?
- Are emotions shown visually instead of named?
- Is the camera movement readable?
- Is the lighting concrete?
- Is the action simple enough to render clearly?

## Output Pattern

Return only the final prompt unless the caller explicitly asks for analysis, options, or revision notes.

## Example

```text
Cinematic medium close-up of a woman in her 30s standing alone on a wet city street at night. Cold blue neon reflections shimmer across the pavement while dim storefront light catches the edge of her dark coat and loose hair. She stands slightly hunched, jaw tight, eyes glossy, then slowly begins walking forward while glancing down at the ground. The camera tracks backward with her, keeping her face centered as blurred headlights drift behind her. Distant traffic hum, light rain, and soft footsteps echo through the street. She exhales shakily and whispers, "I thought you would come back."
```

## Reference

Official guide:
https://ltx.io/model/model-blog/prompting-guide-for-ltx-2#key-aspects-to-include
