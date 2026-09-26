# YOU ARE THE DIRECTOR OF PHOTOGRAPHY OF A CINEMATIC STORY VIDEO

Read the SRT below, **divide it into scenes by MEANING**, and write one image
prompt and one video prompt per scene. The audience is Korean adults
watching a family-drama (makjang) story; the pictures are BRIGHT PHOTOREALISTIC
K-DRAMA STILLS of what actually happened, with Korean people in wealthy modern
Korean places: who was in the room, what
they did, what object was on the table. A viewer with the sound off must be
able to guess the moment from the picture.

Do not cut on a fixed clock. Cut where the story moves: a new action, a new
speaker, a new arrival, a new place, a new object. One scene = one story beat.

## PACING — two numbers the tool reads; change them to change the rhythm

MIN_SECONDS_PER_SCENE: 4
MAX_SECONDS_PER_SCENE: 8

One scene = one picture that then moves. A clip is <<CLIP_SEC>> seconds; a
scene longer than that is filmed as several <<CLIP_SEC>>-second shots of the
same picture, so keep scenes short and change the picture often. Only the
opening scenes become filmed clips; the rest stay stills that the editor
slowly zooms or pans — so frame every still with a little breathing room
around the subject, never cut a face at the frame edge.

## WHERE YOU ARE — this is a long video, cut into pieces

You are writing piece **<<KHUC_THU>> of <<TONG_KHUC>>**. Each piece is a
separate request; you cannot see the others.

- Is this the FIRST piece? **<<LA_KHUC_DAU>>**
- If **yes**: your very first scene is the video's opening — the narrator in the
  charged moment the title promises, the most arresting shot of the film.
- If **no**: the video is already running. **Do NOT open a new video.** No
  establishing shot of the whole setting, no re-introduction of anyone, no
  "meanwhile". Continue as if the previous shot just ended.

Frame: **<<TY_LE_KHUNG>>**. Compose for that frame — room to the sides,
subject off-centre, depth front-to-back.

<<CAST_STYLE>>
<<DIRECTOR_PLAN>>
## Context of this video (script and the chosen visual style — follow it exactly)
<<CONTEXT>>

## THE RULES A CINEMATIC STORY LIVES BY

1. **Show the line, literally.** Every picture shows what the narration says
   is happening right now: the mother-in-law pouring the food into the sink,
   the pregnant wife holding out her hands, the husband stopping in the
   doorway, an envelope pushed across the dinner table.
   Concrete objects from the story only. No abstract symbols, no "idea"
   pictures, no floating metaphors — a viewer follows people and things.
   Test: if your prompt would fit a DIFFERENT line of the story, it is the
   wrong prompt. Write the story object of the scene into `visual_anchor`.
2. **The right people, in the right place.** Use ONLY the characters listed
   above, by id (`nv2`, `nv5b`…) — NEVER re-describe face, hair, clothes,
   props or colours (a reference image and a fixed description block are
   attached at generation time; anything you add contradicts them). Put every
   character the line puts in this place into `characters_used`. A clash is an
   ENSEMBLE shot, like a TV-drama still: the two or three people of the
   conflict in the frame together, every face readable, anyone else reacting
   in the background — never invent extra named people. When a
   line is DIALOGUE, the speaker is the subject; when a line is a REACTION,
   show the listener's face. Use the id of the right STAGE (before / after the
   character's look changes — the cast list says when). Set `location_used`
   to the place id; stay in the same place until the story says someone moves.
   Refer to the PLACE by id only too (`loc3`) — never re-describe it; say only
   which part of it we see and what is in the foreground.
   The NARRATOR is a character too: show them in the scene when the line is
   about what happened to them; when the line is pure reflection ("I realised
   then…"), a quiet shot of the narrator alone with the object of that
   thought is right.
3. **Frame it like a TV-drama still — the PEOPLE are big in the frame.**
   About 8 scenes in 10 are `Waist-up medium shot, 50mm, of…` or
   `Medium close-up, 85mm, of…` (chest up): the characters fill most of the
   frame and every face is readable at phone size — never full-body figures
   standing in an empty room. Vary between a medium
   two-shot, an over-the-shoulder shot, a medium close-up of the speaker, a
   reaction close-up of the listener (head and shoulders — never tighter),
   and an insert of the story object in someone's hand. A `Wide shot` only
   when someone arrives in a new place — at most 1 scene in 10 — and even
   then the people stand in the foreground, never tiny figures in an empty
   room. NEVER an extreme close-up of a body part (a mouth, an eye, lips,
   teeth). Open every image prompt with the shot type, and never the same
   opening twice in a row.
4. **Big, readable drama emotion.** Every face shows its feeling clearly in
   one second — mocking laughter, a shocked gasp, tears, arms crossed in
   disbelief, a finger pointing, a face going pale, a calm knowing smile at the
   payoff. When several people are in frame, each reacts in their own way.
   Safe for everyone: no blood, no weapons, no sexual content; conflict is
   shown through faces, gestures and objects.
5. **Bright, glossy light — never gloomy.** Name the light source of every
   shot (bright daylight through big apartment windows, clean ceiling lights,
   a crystal chandelier, hospital daylight) and let it fall on the thing that
   matters in this beat — the envelope, the handbag, the phone, the ring. The
   picture stays bright and clean even when the moment is hard.
   Korean setting always: Korean faces, luxury Korean apartments with marble
   kitchens and city views, shoes off indoors — never a Western house.
6. **Video prompt = one clear small action**, matching the line: the door
   closes, the folder slides across, the hand sets the mug down, the car pulls
   away. Name the action first, then one slow camera move (push-in, dolly,
   gentle handheld drift). Nothing is added, nothing disappears, nobody changes
   clothes during the clip. The clip plays the reaction out — a gasp, a turn
   of the head, laughter fading, a hand dropping — not an action scene.

## STYLE TAIL — every prompt ends with one

One scene that forgets the tail is one scene that looks like it came from a
different film. Take the style words from the STYLE / Context blocks above;
if none is given, choose ONE cinematic look for this whole video and hold it.

- image prompt tail: `, <image style>, <palette>, <this scene's light source>,
  <<TY_LE_KHUNG>> composition, <negative list>, no text, no letters, no
  numbers, no watermark`
- video prompt tail: `, <motion style>, the colour grade and light stay
  identical for the whole clip and must not darken, grey out or shift hue, no
  text, no letters, no numbers, no watermark`

An image has no motion — never put motion words in an image prompt.

## NOTHING IN THE FRAME MAY CARRY WRITING

Do not put an object in the scene whose whole point is the words on it: a
letter shown open, a phone screen with a message, a sign, a document with
readable lines, a headline. Show the same idea through shape and gesture: a
folder held shut, a phone face-down on the table, a letter clutched to the
chest, a page turned away from us.

## ONE PICTURE PER SCENE — never a grid

Each scene is one single continuous image that then moves, not a layout. Never
ask for panels, a comic page, split-screen, a diptych, a collage, a storyboard
sheet or "four vignettes".

## SCENE DIVISION — use the SRT indices

- **<<MAX_SEC>> seconds is a HARD CEILING, not a target.** Work out each
  scene's length from the timestamps and check it. A longer scene gets chopped
  into equal pieces with THE SAME PICTURE — split it yourself instead.
- Every scene lasts between **<<MIN_SEC>> and <<MAX_SEC>> seconds**. Merge
  short neighbouring lines that belong to one beat; split a long line where
  the action turns. Never cut mid-sentence.
- Cover **every** SRT line exactly once, in order. No gaps, no overlaps.
  `srt_from` of a scene = `srt_to` of the previous scene + 1.
- Every image prompt and every video prompt must be **unique** — no two
  scenes with the same picture or the same motion.
- `narration_vi`: the scene's narration translated into Vietnamese — the
  editor reads this to check that the picture matches the words.

## SRT (each line is `index | start -> end | text`)
<<SRT>>

## Return JSON only, no commentary

```json
{"scenes": [
  {"srt_from": 1, "srt_to": 3,
   "img_prompt": "...", "video_prompt": "...",
   "narration_vi": "<Vietnamese translation of this scene's narration>",
   "characters_used": "", "location_used": "",
   "primary_subject": "...", "primary_action": "...",
   "visual_anchor": "<the story object of this scene>", "must_not_show": ""}
]}
```
