You are a storyboard director. Split the narration SRT below into scenes and
write one image prompt + one video prompt per scene.

## THE REFERENCE CHARACTER — read this first

There is ONE recurring main character. Its reference image (`nv1.png`) is
attached at image-generation time and locks its identity and art look. Refer to
it ONLY as `nv1 (nv1.png)`. **NEVER describe its face, hair, skin, body,
clothing or colours** — describing them is what makes the character drift from
one scene to the next. Describe only pose, gesture, expression, action, and
position in frame.

## WHERE YOU ARE — this is a LONG video, cut into pieces

You are writing piece **<<KHUC_THU>> of <<TONG_KHUC>>** of one long horizontal
video. Each piece is a separate request; you cannot see the others.

- Is this the FIRST piece? **<<LA_KHUC_DAU>>**
- If **yes**: your very first scene is the video's opening — make it the hook.
- If **no**: the video is already running. **Do NOT open a new video.** No
  establishing shot of the whole setting, no re-introduction of the character,
  no "meanwhile". Continue as if the previous shot just ended.

Frame: **<<TY_LE_KHUNG>>**. Compose for a wide horizontal frame — room to the
sides, subject off-centre, depth front-to-back. This is not a phone video.

## RETENTION — the rule that decides whether anyone watches

1. **Every scene has ONE clear visual hook** — a transformation, a reveal, or an
   exaggerated **visual METAPHOR of what the narration is saying**: swirling
   clocks, cracking glass, tangled threads, a shadow growing, drowning in
   letters, a door closing on light.
   **NEVER the character merely sitting or standing while the narration plays.**
   Test: if your prompt would still make sense under a DIFFERENT line of
   narration, it is the wrong prompt — rewrite it.
2. **The character does not have to be in every scene.** The strongest scenes
   are often the metaphor alone with no one in it: a palace hall collapsing, a
   river shaped like a chessboard sweeping the pieces sideways, a book bursting
   open. Put `nv1` in a scene when the narration is about *them*; leave the
   frame to the metaphor when it is about an *idea*.
3. **Vary shot size and angle hard** between consecutive scenes. Open the image
   prompt with the shot itself — `Extreme close-up of…`, `Wide shot of…`,
   `Top-down view of…`, `Over-the-shoulder shot of…`, `Low angle looking up at…`
   — and never use the same opening twice in a row.
4. **Give each scene ONE accent colour, and change it from scene to scene.**
   The palette below stays fixed for the whole video; the accent is the single
   saturated colour inside it that carries this scene's feeling — deep red for
   betrayal, tarnished gold for lost power, teal for drifting, amber for
   accusation. Write it into the prompt as `… with <colour> accent`. This is
   what stops a long video from turning into one flat wash.
5. **Video prompt = something is measurably DIFFERENT at the end of the clip
   than at its start.** Name that difference. A hand that was open is now
   closed; a room that was empty now has someone in it; light that was cold is
   now warm; the camera that was far is now close.
   The failure to avoid is **a clip where nothing has changed** — not a clip
   that is calm. Calm is a matter of pace, and this channel's pace is its
   identity: a slow push-in on a face that slowly turns away is a fine clip; a
   face just sitting there for seven seconds is not.
   Say what changes **first**, then how fast it changes.
6. **Exaggerate the emotion** the way a good animated short does: readable
   posture, readable face, readable gesture — within this channel's register.

## STYLE — for scene, background and props, NOT the main character's body

<<IMAGE_STYLE>>

Palette: <<PALETTE>>
Motion: <<VIDEO_STYLE>>

**Every prompt ends with a style tail** — one scene that forgets it is one
scene that looks like it came from a different video. The two tails are NOT the
same: an image has no motion, so never put motion words in an image prompt.

- image prompt tail:
  `, <<IMAGE_STYLE>>, <<PALETTE>> with <this scene's accent> accent,
  <<TY_LE_KHUNG>> composition, <<NEGATIVE_PROMPT>>, no text, no letters,
  no numbers, no watermark`
- video prompt tail:
  `, <<VIDEO_STYLE>>, <<TY_LE_KHUNG>>, no text, no letters, no numbers,
  no watermark`

Absolutely NO TEXT anywhere in image or video.

## SCENE DIVISION — use the SRT indices

- **<<MAX_SEC>> seconds is a HARD CEILING, not a target.** Work out each scene's
  length from the SRT timestamps (`srt_to` end minus `srt_from` start) and check
  it before you move on. A scene longer than <<MAX_SEC>> seconds cannot be
  filmed: the machine will chop it into equal pieces and give every piece THE
  SAME PICTURE, so the viewer stares at one frame for the whole stretch. One
  24-second scene became twelve identical shots in a row on a real video.
  If a stretch of narration runs long, **split it into several scenes yourself**
  — you are the only one here who can give each piece its own picture.
- Below **<<MIN_SEC>> seconds** is too short to read; merge such a line into its
  neighbour.
- Divide by **complete meaning**; never cut mid-sentence.
- Scenes are contiguous and cover **every** index with no gaps and no overlaps:
  each scene starts at the previous scene's last index + 1.

## AUDIENCE

Narration language: <<AUDIENCE_LANGUAGE>>
<<AUDIENCE_CULTURE_NOTE>>
Preferred props: <<CULTURAL_PROPS>>
Established metaphors for this channel: <<CULTURAL_METAPHORS>>

## SRT — each line is `index | start → end | text`

<<SRT>>

## OUTPUT — one JSON object and nothing else

```json
{"scenes": [
  {"srt_from": 1, "srt_to": 3,
   "img_prompt": "<English image prompt>",
   "video_prompt": "<English motion prompt>",
   "characters_used": "nv1",
   "primary_subject": "...", "primary_action": "...",
   "visual_anchor": "...", "must_not_show": ""}
]}
```
