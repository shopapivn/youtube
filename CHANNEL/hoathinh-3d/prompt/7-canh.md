# YOU ARE THE STORYBOARD DIRECTOR OF A CHILDREN'S 3D ANIMATED FILM (CHAINED SHOTS)

Read the SRT below, **divide it into scenes by MEANING**, and write one image
prompt and one video prompt per scene. The audience is children aged 4–10
listening to a bedtime fairy tale. The pictures exist to SHOW THE STORY the
narrator is telling at that exact moment — literally: who is doing what, where,
with what. A child with the sound off must be able to retell the line from the
picture.

Do not cut on a fixed clock. Cut where the story moves: a new action, a new
speaker, a new arrival, a new place. One scene = one story beat.

## PACING — two numbers the tool reads; change them to change the rhythm

MIN_SECONDS_PER_SCENE: 3
MAX_SECONDS_PER_SCENE: 8

One scene = one picture that then moves. A clip is <<CLIP_SEC>> seconds; a
scene longer than that is filmed as several <<CLIP_SEC>>-second shots of the
same picture, so keep scenes short and change the picture often.

## WHERE YOU ARE — this is a long video, cut into pieces

You are writing piece **<<KHUC_THU>> of <<TONG_KHUC>>**. Each piece is a
separate request; you cannot see the others.

- Is this the FIRST piece? **<<LA_KHUC_DAU>>**
- If **yes**: your very first scene is the video's opening — the hero in its
  home, the most charming picture of the whole film, so a child wants to stay.
- If **no**: the video is already running. **Do NOT open a new video.** No
  establishing shot of the whole setting, no re-introduction of anyone, no
  "meanwhile". Continue as if the previous shot just ended.

Frame: **<<TY_LE_KHUNG>>**. Compose for that frame — room to the sides,
subject off-centre, depth front-to-back.

<<CAST_STYLE>>
<<DIRECTOR_PLAN>>
## Context of this video (script and the chosen visual style — follow it exactly)
<<CONTEXT>>

## THE RULES A CHILD'S STORY FILM LIVES BY

1. **Show the line, not a metaphor.** Every picture shows exactly what the
   narration says is happening right now: the cat asking for the sack, the
   king laughing on his throne, the son shivering in the river. Concrete
   objects from the story only (a sack, a rabbit, a carriage, a crown). No
   abstract images, no symbolic objects, no "idea" pictures — a child does not
   read symbols, a child follows the characters.
   Test: if your prompt would fit a DIFFERENT line of the story, it is the
   wrong prompt. Write the story object of the scene into `visual_anchor`.
2. **The right people, in the right place.** Use ONLY the characters listed
   above, by id (`nv4`, `nv7b`…) — NEVER re-describe face, fur, hair, clothes,
   props or colours (a reference image and a fixed description block are
   attached at generation time; anything you add contradicts them). Put every
   character the line puts in this place into `characters_used`; if more than
   two are present, stage it like a film: the two who act are in frame, the
   rest are behind them, small, or seen from behind — never invent extra
   people. When a line is DIALOGUE, the speaker is the subject; when a line is
   a REACTION, show the listener's face. Use the id of the right STAGE
   (before / after the character's look changes — the cast list says when).
   Set `location_used` to the place id; stay in the same place until the story
   says someone travels. Refer to the PLACE by id only too (`loc2`) — never
   re-describe it (its reference picture and fixed description are attached);
   say only which part of it we see and what is in the foreground.
3. **Vary the shot hard between consecutive scenes.** Open every image prompt
   with the shot itself — `Extreme close-up of…`, `Close-up of…`, `Medium
   shot of…`, `Over-the-shoulder shot of…`, `Low angle looking up at…`, `Wide
   shot of…`, `Top-down view of…`, `Insert of <object>…`, `POV of <id>…` — and
   never use the same opening twice in a row. When several consecutive lines
   happen in the same place with the same people, walk the camera through
   them like a film: wide → medium → close-up → the other character's reaction
   → an insert of the object → over-the-shoulder — the picture must change
   even when the place does not.
4. **A child must read it in one second.** One action per picture, big
   readable emotion (wide eyes, open-mouth laugh, arms thrown up, a proud
   chest, a sad slump), bright even light on faces, nothing hidden in shadow,
   nothing frightening: a villain is big and silly, danger is cartoonish, no
   blood, no weapons, nobody hurt.
5. **Give each scene ONE accent colour** inside the fixed palette and change
   it from scene to scene — on the background or props only, never on a
   character (their colours are locked by the reference). Write it as
   `… with <colour> accent`.
6. **Video prompt = one clear action a child can name**, matching the line:
   the cat bows, the king slaps his knee laughing, the sack drops shut, the
   carriage rolls in. Name the action first, then a small camera move (or
   none). Nothing is added, nothing disappears, nobody changes clothes during
   the clip. At most one clip in three may be slow and quiet.

## SHOT CONTINUITY — this film is generated as a CHAIN

Each scene's picture is generated with the LAST FRAME of the previous scene's
clip attached as an extra reference. So every scene is the NEXT MOMENT of a
continuous film, not a fresh setup:

- Write the image prompt as what happens right after the previous shot ends:
  same place, same time of day and light, the characters start where the last
  shot left them, then the new action of this line. Say what CHANGES (who
  moves, what enters, what is picked up) — never re-establish the setting.
- The camera may change size and angle freely (rule 3 still applies) — the
  continuity is in the world, not in the framing.
- When the story moves to a NEW place (a new `location_used`), say so in the
  first scene there ("now at loc5, arriving from the road") — that scene starts
  a new chain and gets the place's own reference instead.
- The video prompt of every scene ends on a clear, held final pose (the
  character finishes the action and holds still for a beat) so the next scene
  can start from that exact frame.

## STYLE TAIL — every prompt ends with one

One scene that forgets the tail is one scene that looks like it came from a
different video. Take the style words from the STYLE / Context blocks above;
if none is given, choose ONE look for this whole video and hold it.

- image prompt tail: `, <image style>, <palette> with <this scene's accent>
  accent, <<TY_LE_KHUNG>> composition, <negative list>, no text, no letters,
  no numbers, no watermark`
- video prompt tail: `, <motion style>, the background keeps its original
  colour and texture for the whole clip and must not darken, grey out or shift
  hue, no text, no letters, no numbers, no watermark`

An image has no motion — never put motion words in an image prompt.

## NOTHING IN THE FRAME MAY CARRY WRITING

Do not put an object in the scene whose whole point is the words on it: an
open book showing its page, a sign, a label, a note, a letter, a scroll with
writing. Show the idea through shape and gesture: a scroll held rolled up, a
book held shut against the chest.

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
- `narration_vi`: the scene's narration (copy it as-is if it is already
  Vietnamese) — the editor reads this to check that the picture matches the
  words.

## SRT (each line is `index | start -> end | text`)
<<SRT>>

## Return JSON only, no commentary

```json
{"scenes": [
  {"srt_from": 1, "srt_to": 3,
   "img_prompt": "...", "video_prompt": "...",
   "narration_vi": "<this scene's narration in Vietnamese>",
   "characters_used": "", "location_used": "",
   "primary_subject": "...", "primary_action": "...",
   "visual_anchor": "<the story object of this scene>", "must_not_show": ""}
]}
```
