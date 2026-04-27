News Commentary Clip Planning: LTX three-template flow

- This repository's LTX render planning now uses a fixed three-template system (Opening, Middle, Closing).
- Clips are mapped deterministically by position: first clip = Opening, last clip = Closing, others = Middle.
- Middle template adapts to clip context: solo close-up vs duo close-up based on image_mode and speaker_focus.
- The actual prompt bodies live in workflows/news-commentary/scripts/build_render_plan.py as OPENING_TEMPLATE, MIDDLE_TEMPLATE_SOLO, MIDDLE_TEMPLATE_DUO, and CLOSING_TEMPLATE.
