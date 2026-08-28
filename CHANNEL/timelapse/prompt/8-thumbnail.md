# WRITE 3 YOUTUBE THUMBNAIL PROMPTS — FIXED-CAMERA TIMELAPSE

This channel has no characters and no narrator. Every video is **one place**,
seen from **one camera that never moves**, while centuries run past. The
thumbnail has to sell exactly that promise in one glance: *this place, this
much time*.

Measured on the channel this format comes from (a fixed-camera timelapse video
with 1.24 million views): what makes a viewer click is **the contrast between
two ages of the same ground** — not beauty, not a face.

## What this video is about
Title: **<<TITLE>>**
Hook text the viewer reads: **<<THUMB>>**

The place, the camera, and the milestones of this film:
<<SCRIPT_OPENING>>

## Channel look
<<THUMBNAIL_STYLE>>

Palette: <<PALETTE>>
Never include: <<NEGATIVE_PROMPT>>

## Write 3 prompts, each a DIFFERENT reason to click

Named exactly: `portrait_main`, `dramatic_scene`, `youtube_ctr`.

Write each in **exactly the format, length and style** of this example — the
section order, the real newlines, the short punchy lines:

```
photoreal cinematic youtube thumbnail for a fixed-camera history timelapse, designed for extremely high click-through-rate
one single place seen from one single viewpoint, the shape of the land identical on both sides of the frame

scene composition:
the frame split vertically down the middle, the same view of the same ground on both halves
left half: the place at its earliest year — what stood here then, the materials, the emptiness
right half: the place at its latest year — what stands here now, dense and lit
the horizon line, the river or road, and the hills continue unbroken straight across the split
a few small human figures at the same spot in both halves, for scale

visual psychology: the viewer must recognise it is ONE place, not two — the shock is that the ground is the same and everything on it is not
time depth: the eye should be able to travel from one age to the other in a single glance

composition: wide establishing view, horizon on the upper third, the split centred, negative space reserved for text along the top
cinematic golden light, deep atmospheric haze in the distance, high micro-contrast

TEXT STYLE (HIGH CTR YOUTUBE):
text: "<hook in the channel's language>"

the two years enormous and dominant, one at each side, like a scoreboard of time
"<earliest year>" on the left, "<latest year>" on the right, both partially cropped for impact
<<THUMB_TEXT_FONT>>
<<THUMB_TEXT_STYLE>>
<<THUMB_TEXT_SHADOW>>
text integrated into the sky, never floating over the subject

aspect ratio 16:9, ultra sharp
no watermark, no logo, no extra text except the requested hook text and the two years
```

## ABSOLUTE RULES

1. **It must read as ONE place.** Whatever the composition, the land itself —
   the horizon, the hill, the bend of the river, the line of the valley — has to
   be recognisably the same in every part of the image. That recognition IS the
   click. Two unrelated pretty landscapes is a dead thumbnail.

2. **No invented landmark.** Use only what the milestones above actually
   describe. A famous building that was never in this film is a lie the video
   cannot pay off, and the viewer leaves in five seconds.

3. **No people in close view, no faces, no portraits.** Human figures only small
   and distant, for scale. This channel is about ground and time, not persons.

4. **Numbers are the strongest text.** The two years — earliest and latest — do
   more work than any word. Keep them huge. If a hook phrase is used as well,
   keep it short and above them.

5. **Nothing gruesome.** Fire, ruin, siege and flood are allowed as the drama of
   a place; blood, bodies and weapons pointed at the viewer are not.

6. **Use real newlines between sections**, not one giant paragraph. Each section
   2–3 lines maximum.

7. Three different reasons to click — not three variations of one idea:
   - `portrait_main` — the split frame above: earliest age against latest age,
     the ground continuous across the seam. Safest, usually strongest.
   - `dramatic_scene` — the single most violent or startling milestone of this film
     (the fire, the siege, the flood, the demolition), shown from the same fixed
     viewpoint, with a small ghosted overlay of the same view in a calmer age.
   - `youtube_ctr` — the boldest: the place today in the foreground, and the
     oldest age of it rising behind as a translucent overlay in the exact same
     alignment, so the two ages sit inside one another.

## Return JSON only, no commentary

```json
{"thumbnails": [
  {"version_desc": "portrait_main", "img_prompt": "..."},
  {"version_desc": "dramatic_scene", "img_prompt": "..."},
  {"version_desc": "youtube_ctr", "img_prompt": "..."}
]}
```
