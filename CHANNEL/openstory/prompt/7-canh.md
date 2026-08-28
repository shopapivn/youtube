# YOU ARE THE STORYBOARD DIRECTOR OF A CHILDREN'S 3D ANIMATED FILM

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

---

## 0. THE EXAMPLES BELOW ARE NOT YOUR STORY

Every example and every "Measured …" note in this document comes from a
**different film that is already finished**. They are here to show what went
wrong and how the rule was found — a healer and a grandmother, a cat and a
basket-boat, a cat in boots and a king, a wolf and a flock of goats.

**None of that belongs in the film you are writing now.** Never carry a
character, an animal, an object, a place or a line of action from an example
into your scenes. Your material is the script and the cast list above, and
nothing else. If your story has no cat, no cat appears — no matter how many
times the word "cat" appears below.

The rules are general. The examples are not.

---

# PART ONE — THE IMAGE PROMPT (the starting frame)

## 1. Identity comes from the reference image, never from your words

A reference image is attached at generation time for every character and every
place listed above. It carries the whole look. **Do NOT describe face, hair,
fur, skin, build, body type, clothes, props or colours.** Name the character
by its id (`nv4`, `nv7b`) and give only:

- the pose, gesture and expression of this exact moment;
- the costume detail only where the cast list itself already fixed it (never
  invent, never restate).

Every word you write about appearance competes with the reference image, and
the model resolves that fight by inventing a *new* character from your words.
That is the single most expensive mistake in this file.

**Put the id immediately after the role-noun, at its first natural mention** —
`the boy (nv4) crouches by the doorway`, `the cat (nv7) lifts the sack`, `the
mill yard (loc2) stretches behind them`. That is what tells the model which
reference image drives which thing in the frame.

Use the id of the right STAGE when a character changes look during the story
(the cast list says when). Put every id you used into `characters_used`, and
the place id into `location_used`.

## 1b. Everyone in the picture must have a reference

The picture is drawn from the attached reference images and nothing else. A
creature nobody named has no reference, so the machine invents it — and it comes
out a different animal every time.

- **Name every character you put in the frame** in `characters_used`, even one
  that is only half seen: a paw at the door, a shadow on the wall, a silhouette
  behind a window, one leg entering frame.
- **Never write "and the others", "the siblings", "the rest of them", "a few
  villagers".** If a group is on screen, use the group character's own id — the
  machine draws all of them from that one reference. Unnamed extras come out as
  plain animals with no clothes.
- **Never dress a character in something its reference does not wear** — no
  disguise, cloak, hood, bonnet, costume. A character that changes look during
  the story has its own id for that stage (the cast list says which); use that
  id. If there is no such id, say what is actually different (floured white
  paws, a hidden face, a changed voice), never "disguised as the mother".
- **Everyone the line puts in the room is in the picture, and everyone in the
  picture carries their own reference.** There is no quota to meet: a scene
  with the healer, the grandmother and the boy attaches three references and
  names all three.
  What a crowded frame needs is not fewer people but a clear SUBJECT.
  **Which two? The one who acts and the one acted upon.** A character being
  examined, rescued, fed, spoken to or looked at is never the one you drop —
  the line is about them. Drop the bystander instead, and let them be a
  shoulder or a hand at the near edge of frame, or simply off-camera.
  A beat with three characters is two scenes: put the pair the line is about in
  the first, cut to the third's reaction in the second.
  **Never write a story character as an unnamed body.** Phrases like "a small
  blanketed figure", "someone lying on the cot", "a villager nearby" are how a
  named character gets drawn as a stranger: measured 28/08/2026, the scene
  "the healer comes to examine grandmother" put the healer and the boy in
  frame and left grandmother as "a blanketed figure out of focus" — she came
  out as a black-haired stranger in her own sickbed. If a character is in the
  picture at all, they are named and they carry their reference; if they
  cannot, keep them out of the frame entirely.

## 1d. Whose moment is it

Every beat belongs to somebody. Decide who before you choose the shot:

- A line of **dialogue** belongs to the SPEAKER — put the speaker in frame,
  mouth open, gesturing, and let the listener be the shoulder in the near edge
  or be out of frame entirely. Drawing the listener while someone else talks
  reads to a child as if the wrong character said it.
- A line of **reaction** belongs to the LISTENER — hold on the face that is
  taking the news, not on the mouth that delivered it.
- A line of **action** belongs to whoever acts.

Write that person first in `primary_subject`, and open the prompt with them.
This is the difference between a picture of a conversation and a picture that
tells you who is talking.

## 2. Spend the words you saved on the world

Because identity is handled by the reference, **about 60% of the prompt should
be the world**: light and its texture, depth of field, what is in the
foreground, what is far behind, weather, dust, the time of day, the colour the
light carries. That is what makes two scenes in the same room look like two
different shots instead of the same picture twice.

Do not re-describe the PLACE either — it has its own reference image. Say only
which *part* of it we are seeing, what is in the foreground, and what the light
is doing right now.

## 3. Write the STARTING FRAME — and the action must already be HAPPENING

This still is the exact first frame the video model will animate from, so it
must carry motion: weight already shifted, arm already lifting, mouth opening,
eyes already turned towards the thing that matters. A frozen posed portrait
animates into nothing.

But "about to" is not enough. **The picture must show the narrated action
underway, at the moment a child could name it.** If the line says the cat
leaps into the basket, draw the cat IN THE AIR, paws over the rim, tail
streaming — not a cat standing beside a basket looking at it. If the line says
the healer examines the grandmother, draw his fingers ON her wrist and his
eyes on her face — not a man kneeling nearby.

Measured 27/08/2026: with only "the moment the action begins", the leap scene
came out as a cat standing on the mud next to an empty basket, and a viewer
reading the picture alone would never guess the line. Pick the instant that is
unmistakably this action and no other.

## 3b. A character who is lying, covered or turned away still needs a face

The reference is a standing portrait. When a scene hides most of a character —
asleep under a blanket, seen from behind, deep in water, tiny in a wide shot —
the machine has almost nothing to match and it invents a stranger.

So whenever a character is not plainly visible head to foot, name the ONE
feature that still identifies them in that pose: her silver hair-bun on the
pillow, his orange sleeve on the rim, the tabby stripes of the tail. One
anchor, not a description — you are pointing at the reference, not replacing
it.

Measured 27/08/2026: the grandmother lying ill under a blanket, with only her
head showing, was drawn as a bald old man in brown — and the scoring pass gave
that picture 4/5 because the OTHER character in frame matched perfectly. A
half-hidden character is where identity breaks and where checking fails.

## 3c. Two characters of the same kind in one frame — name a feature for EACH

Two old people, two children, two cats, two soldiers: the machine sees several
reference portraits of the same kind and gives one of them the other's design.
It does not merely confuse them — it deletes one and paints the other twice.

So when a frame holds two characters of the same obvious kind, give **each of
them** one feature word straight from their own reference, right beside the id:
`nv4 (Image 2), the white-bearded healer in his indigo robe` and `nv2 (Image
3), her silver hair-bun on the mat`. One feature each. This is the same anchor
as 3b, applied for a different reason: there, the character was hidden; here,
the character has a twin.

**One feature, never a portrait.** Rule 1 still governs: the reference owns the
face. You are pointing at the right reference, not describing it. Two features
for one character is already too many.

Measured 28/08/2026, film 0008 scene 7. The healer is an old man with a white
beard, indigo robe and black head-cloth; the grandmother is an old woman with a
silver bun and a brown blouse. The prompt named the healer with no feature at
all — `nv4 (Image 2) who lifts one hand in a solemn instructing gesture` —
while the grandmother carried her anchor. The picture came back with **the
grandmother standing in the healer's place**, brown blouse and all, and no
healer anywhere. 2/5.

## 3d. A posture belongs to a character — say WHY they are in it

Three people and one bed: the machine will lay somebody on the bed. Which
somebody is a coin toss unless the sentence gives it a reason. Naming the right
reference is not enough — the references were all correct in the picture that
failed; what moved was **who was doing what**.

So write the reason into the same breath as the posture, in two or three words
the story already supplies: `nv2 (Image 3), ill, lies curled on the reed mat`,
`nv1 (Image 1), unhurt, stands at the foot of the cot`. And no two characters
in one frame may share a posture phrase — if one lies down, nobody else lies
down.

Measured 28/08/2026, film 0008 scene 7, second attempt. Every character matched
their reference exactly and the scoring pass gave it 4/5 — but **the grandmother
was standing and talking while the boy slept on the sickbed**, the exact reverse
of the story. A picture can pass every identity check and still tell the wrong
story; the check cannot see roles, only faces.

## 4. ONE SHOT — one continuous camera take

Each scene is **exactly one shot**: one camera setup, no cuts inside it.

Split into two scenes when the line contains:

- "then we see", "cut to", "meanwhile", "back at…";
- two camera framings in a row ("wide shot of the yard. close-up of his face");
- a time jump inside the action ("he walks to the door. Later he arrives…").

Keep as one scene: a camera that tracks, pans, dollies or pushes in through the
whole beat; a character entering, crossing and sitting down in one take.

## 5. ZERO MEMORY

The image model is given this prompt and nothing else — no previous scene, no
memory of what was just on screen. Re-state the place, the light and who is
present in **every** scene. Never write "the same room as before", "he is still
holding it", "continuing from the previous shot".

This is not a contradiction of "do not re-describe the place": say *which* part
of `loc2` we see and how it is lit right now, not what `loc2` looks like.

## 6. Vary the shot hard between consecutive scenes

Open every image prompt with the shot itself — `Extreme close-up of…`,
`Close-up of…`, `Medium shot of…`, `Low angle looking up at…`, `High angle
looking down at…`, `Wide shot of…`, `Top-down view of…`, `Two-shot of…`,
`Insert of <object>…` — and never use the same opening twice in a row. When
several consecutive lines happen in the same place with the same people, walk
the camera through them like a film: wide → medium → close-up → the other
character's reaction → an insert of the object → a low angle. The picture must
change even when the place does not.

**No over-the-shoulder shot, and no POV shot.** Both spend the nearest, largest
part of the frame on a person whose face the camera cannot see, and the
reference is a front-facing portrait — so the machine has nothing to match
there and fills the space with a stranger.

Measured 28/08/2026, film 0008 scene 7: `Over-the-shoulder shot from just
behind nv1's shoulder in soft blur… looking across to nv4` came back with the
boy gone from the picture entirely, an invented middle-aged woman standing in
the middle of the room, and the healer reduced to a blue back. It scored 2/5,
was redrawn four times, and every redraw failed the same way — because the
fault was in the framing, not in the luck.

To show one character looking at another, put them both in the frame facing
each other and let the shot size carry the intimacy: `Medium two-shot of nv1
turning to look up at nv4…`.

## 7. A child must read it in one second

One action per picture, big readable emotion (wide eyes, open-mouth laugh, arms
thrown up, a proud chest, a sad slump), bright even light on faces, nothing
hidden in shadow, nothing frightening: a villain is big and silly, danger is
cartoonish, no blood, no weapons, nobody hurt.

Show the line, not a metaphor. Concrete story objects only (a sack, a rabbit, a
carriage, a crown). Write that object into `visual_anchor`.
**Test: if your prompt would fit a DIFFERENT line of the story, it is the wrong
prompt.**

## 8. One accent colour per scene

Give each scene ONE accent colour inside the fixed palette and change it from
scene to scene — on the background or props only, never on a character (their
colours are locked by the reference). Write it as `… with <colour> accent`.

## 9. Sentence shape

Flatten everything into ONE paragraph in this order:

`[shot size] + [character id and what it is doing] + [the story object] +
[the part of the place we see, foreground to background] + [light] +
[camera angle / lens feel]`

Plain, grammatical English. Short clauses. Ordinary word pairs. Do not stack
four adjectives on one noun and do not invent compound words — an image model
that cannot parse a prompt rejects its own output, and the rejection message
looks like censorship when it is really broken grammar.

---

# PART TWO — THE VIDEO PROMPT (how that frame moves)

The rendered still IS the first frame. The video model can see it. Everything
that is already visible in it is wasted breath.

## 10. Never repeat what the picture already shows

No hair colour, no clothes, no room decor, no character description. Write only
**what moves or changes**.

## 11. Name the movers by id

`nv4 turns towards the window`, `nv7 lifts the sack` — never "the boy", never
"the woman", never "the animal". The id binds the motion to the right reference
image. This does not contradict rule 10: the id says *who* moves; you still do
not describe what they look like.

## 12. EXACTLY ONE camera move, with a pacing word

One move per clip, from start to end, always paired with a pacing adverb: `slow
dolly forward`, `steady handheld drift`, `gentle push-in`, `static lock-off`,
`smooth pan right following nv4`.

**Never stack moves.** "Push in, then pan left, then orbit" makes every video
model jitter. If the beat needs two moves, it needs two scenes.

## 13. One clear action a child can name

The cat bows. The king slaps his knee laughing. The sack drops shut. The
carriage rolls in. Name the action first, then the camera move. Nothing is
added, nothing disappears, nobody changes clothes during the clip. The movement
is already under way at the first frame and still going at the last — never a
frozen pose at either end. At most one clip in three may be slow and quiet.

## 14. One or two touches of secondary motion

Fabric lifting, dust in the light, leaves turning, steam rising, a tail
flicking. It is what makes the clip read as filmed instead of warped. One or
two — not a list.

## 15. Words that ruin clips

Never write `fast`, `epic`, `amazing`, `dramatic`, `lots of movement`, or image
quality boosters (`cinematic`, `4K`, `masterpiece`, `highly detailed`) in a
video prompt — they produce chaotic, jittery output. For quick motion write
`brisk` or `quick but controlled`. Use pacing words, never technical specs: no
`24fps`, no `f/2.8`.

Keep the video prompt under about 100 words.

## 16. Sound — one short clause at the end

The clip carries its own audio. End the video prompt with one clause naming the
ambient sound of the place plus at most two sound effects tied to the action:
`ambient: mill wheel and water, birds; sfx: sack thumping shut, footsteps on
straw`.

**No music** — one music track is laid over the whole video afterwards, and a
per-clip score fights it. **No speech, no dialogue, no voices, no singing**:
the narrator's voice is a separate recording and any mouth-generated speech
would talk over it. Mouths may move as performance; nothing may be said.

---

# RULES THAT APPLY TO BOTH PROMPTS

## 17. Keep the safety filter out of your way

The image filter rejects far more than you would expect, and every rejection
costs a retry:

- No named real person and no signature look of a copyrighted character (a cat
  in a feathered musketeer hat and boots, a mouse in red shorts). Describe the
  look plainly instead — age, build, hair, wardrobe, manner — and never name a
  film, book or game.
- No body horror: nobody dissolves, melts, splits or transforms on camera. Show
  the result instead ("a tiny mouse now sits where the giant stood").
- No blood, no wounds, no weapons pointed at anyone, no undressing or bathing.
- Avoid the words that trip the filter on their own even in innocent sentences:
  `anthropomorphic`, `sly`, `seductive`, `kill`, `corpse`, and — on animals —
  `lick`, `slurp`, `swallow`, `into his mouth`.

## 18. Nothing in the frame may carry writing

Do not put an object in the scene whose whole point is the words on it: an open
book showing its page, a sign, a label, a note, a letter, a scroll with
writing. Show the idea through shape and gesture: a scroll held rolled up, a
book held shut against the chest.

## 19. One picture per scene — never a grid

Each scene is one single continuous image that then moves, not a layout. Never
ask for panels, a comic page, split-screen, a diptych, a collage, a storyboard
sheet or "four vignettes".

## 20. Style tail — every prompt ends with one

One scene that forgets the tail is one scene that looks like it came from a
different video. Take the style words from the STYLE / Context blocks above; if
none is given, choose ONE look for this whole video and hold it.

- image prompt tail: `, <image style>, <palette> with <this scene's accent>
  accent, <<TY_LE_KHUNG>> composition, <negative list>, no text, no letters,
  no numbers, no watermark`
- video prompt tail: `, <motion style>, the background keeps its original
  colour and texture for the whole clip and must not darken, grey out or shift
  hue, no text, no letters, no numbers, no watermark`

An image has no motion — never put motion words in an image prompt.

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
