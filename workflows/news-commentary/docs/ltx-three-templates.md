Three-template LTX render prompts for local News Commentaries

- Purpose: Provide a fixed, deterministic visual prompt system for LTX render planning. Maps each clip to one of three templates: Opening, Middle, Closing.
- Templates (top-level, mutually exclusive):
1) OPENING_TEMPLATE: Opening first duo clip now uses the same single-image `duo_close` reference strategy as middle duo clips; keep a fixed two-anchor composition, explicit speaker/listener labeling, clearly visible speaking motion, attentive silent listening behavior, and no cutaway to a solo shot.
2) MIDDLE_TEMPLATE: Fixed camera with either a single-anchor close-up or a duo close-up depending on clip image_mode and speaker_focus; keep speaking motion natural but clearly visible, with distinct mouth opening/closing, readable articulation, active jaw participation on spoken syllables, explicit eyeline stability, and a clear difference between the explicitly named speaker and explicitly named listener in duo shots.
3) CLOSING_TEMPLATE: Closing duo shot begins from a tight duo frame, then relies on subtle paper-organizing/sign-off gestures and restrained body motion rather than a forced end frame; closing delivery should keep the explicitly named duo speaker visibly speaking with active mouth articulation and syllable-timed jaw motion while the explicitly named opposite listener stays silent and composed.
- Mapping (deterministic):
  - First clip (index 0) => OPENING
  - Last clip => CLOSING
  - All intermediate clips => MIDDLE
  - Practical consequence: the first opening duo clip no longer gets a special push-in treatment; it now uses the same duo-close-only fixed two-anchor behavior as MIDDLE.
- Implementation notes:
  - The three templates are used to populate render_item['optimized_prompt'] for LTX renders.
- For MIDDLE, if image_mode is 'duo_frame' or speaker_focus is 'duo', use the duo close-up; otherwise use solo close-up.
- Opening clips, including the first one, should use the same duo-close-only reference-image strategy as MIDDLE.
  - Middle solo prompts should keep the fixed visual body generic, but the inserted dialogue sentence should still reflect the actual speaking role from clip data (`female anchor` or `male anchor`). In duo scenes, use explicit left/right speaker labels (`left female speaker` or `right male speaker`) and explicit opposite listener labels (`right male listener` or `left female listener`).
  - Across all templates, use a positive prompt structure close to: shot / scene / anchor state / spoken delivery / inserted dialogue line / restrained lip motion with small precise mouth-jaw motion / eyeline / camera movement / atmosphere-style.
  - Spoken text should be inserted inside the action / speaking section of the template, not appended as a final trailing sentence.
  - Recommended insertion points: after `The left female speaker is the only one speaking.` or `The right male speaker is the only one speaking.` in OPENING, after `The anchor is speaking directly to the camera.` in MIDDLE solo, after `Only the left female speaker speaks.` or `Only the right male speaker speaks.` in MIDDLE duo, and after `The left female speaker delivers the closing line.` or `The right male speaker delivers the closing line.` in CLOSING.
  - Future projects should fill both the speaking role and the dialogue line from clip data. In duo scenes, use `speaker_focus=host` => `left female speaker` and `right male listener`, use `speaker_focus=guest` => `right male speaker` and `left female listener`. In solo scenes, use `speaker_focus=host` => `female anchor`, `speaker_focus=guest` => `male anchor`. Then insert `The [role] says in Chinese: "..."` at the template insertion point.
  - `avoid / no / do not` constraints should move out of the positive prompt and into the LTX negative prompt field.
  - Negative prompts should explicitly suppress weak mouth motion, frozen lips, wandering eyes, eye darting, unwanted listener motion, subtitles, captions, on-screen text, and burned-in text overlays.
- Documentation: This file documents the intent and mapping rules used by build_render_plan.py.
