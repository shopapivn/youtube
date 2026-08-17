# DIVIDE THE SRT INTO SCENES BY MEANING, THEN WRITE PROMPTS

Read the SRT below, **divide it into scenes by MEANING**, and write an image
prompt and a video prompt for each scene.

Do not cut on a fixed clock. Cut where the thought changes. One scene = one
idea the narrator is landing.

## Channel style — applies to scene, background, props, and any secondary figure
<<IMAGE_STYLE>>

Palette: <<PALETTE>>
Motion style: <<VIDEO_STYLE>>
Never include: <<NEGATIVE_PROMPT>>

## The main character
The reference image is the ONE fixed identity of this channel. In **every**
prompt, refer to the character only as `nv1 (nv1.png)` — never re-describe their
face, hair, clothes or colour. Re-describing is how the character drifts.

Identity lock: <<REFERENCE_LOCK>>

## Audience
Language of the narration: <<AUDIENCE_LANGUAGE>>
<<AUDIENCE_CULTURE_NOTE>>

Preferred props: <<CULTURAL_PROPS>>
Visual metaphors already established for this channel: <<CULTURAL_METAPHORS>>

## SRT (each line is `index | start → end | text`)
<<SRT>>

## RETENTION — the rule that decides whether anyone watches

Every second has to earn the next one. A prompt that describes a room while the
narration lands a point is a wasted scene.

R1. **Scene 1 is the HOOK** — the single most arresting, curiosity-triggering
    image of the whole video.

R2. **Every scene needs ONE clear visual hook**: a transformation, a reveal, or
    an exaggerated **visual METAPHOR of what is being said** — swirling clocks,
    cracking glass, tangled threads, a shadow growing, drowning in letters, a
    door closing on light. **NEVER the character merely sitting or standing
    while the narration plays.** If your prompt would still make sense with a
    different line of narration, it is the wrong prompt.

R3. **Vary shot size and angle hard** between consecutive scenes: extreme
    close-up on eyes → wide → top-down → over-the-shoulder. Never two similar
    framings in a row.

R4. **Video prompt = a change from the start of the clip to its end**, clearly
    visible. Something moves, turns, opens, breaks, fills, empties, or the
    camera travels. **Forbidden words: `subtle`, `slight`, `gentle`, `slowly`,
    `barely`.** Calm is a matter of *pace*, not of *nothing happening*: a slow
    push-in that ends somewhere new is calm; a static shot is dead air.

R5. **Exaggerate the emotion** the way a good animated short does — readable
    posture, readable face, readable gesture.

## Rules

1. **Each prompt sticks closely to the exact words of that scene's narration.**
   If the line is about a phone call that never came, the image shows that —
   not a generic mood shot.
2. Every scene lasts between **<<MIN_SEC>> and <<MAX_SEC>> seconds**. Merge
   short neighbouring lines that belong to one thought; split a long line where
   the thought turns.
3. Cover **every** SRT line exactly once, in order. No gaps, no overlaps.
   `srt_from` of a scene = `srt_to` of the previous scene + 1.
4. Let the content drive a **varied** setting. Consecutive scenes must not
   repeat the same room, pose and framing — vary distance (close / medium /
   wide), angle, and location as the story moves.
5. **Image prompt (English):** the setting, then `nv1 (nv1.png)` with a specific
   pose and expression, then the props that carry the meaning. Concrete, not
   abstract. No text anywhere in the image.
6. **Video prompt (English):** motion only — what moves, in what direction, and
   **what is different by the end of the clip**. Obey R4: this channel is calm,
   so nothing snaps or whips — but something must actually happen.
7. Every image prompt and every video prompt must be **unique**. No copy-paste
   between scenes.

## Return JSON only, no commentary

```json
{"scenes": [
  {"srt_from": 1, "srt_to": 3,
   "img_prompt": "...", "video_prompt": "...",
   "characters_used": "nv1",
   "primary_subject": "...", "primary_action": "...",
   "visual_anchor": "...", "must_not_show": ""}
]}
```
