# WRITE 3 THUMBNAIL IMAGE PROMPTS — KOREAN FAMILY DRAMA POSTER, NO TEXT

You write image prompts for thumbnails of a Korean family-drama (노후사연)
channel. The goal is **STOPPING THE SCROLL**: a Korean viewer must see, in one
second, who is wronging whom and feel "what happens next?!". It must look like
the poster of a K-drama: the characters big in the frame, faces clear, the
clash readable at phone size.

The image carries NO text. Our tool adds two lines of Korean text afterwards —
one along the TOP edge, one along the BOTTOM edge — so keep FACES out of those
two bands (bodies, arms and objects may run under them).

## What this video is about
Title: **<<TITLE>>**
Thumbnail text (added later, for your understanding only): **<<THUMB>>**

Opening of the script:
<<SCRIPT_OPENING>>

## Channel look
<<THUMBNAIL_STYLE>>

Palette: <<PALETTE>>
Never include: <<NEGATIVE_PROMPT>>

## What wins in this niche (top Korean channels, 26/09/2026)

- THE PEOPLE ARE THE PICTURE. Three or four characters crowd the frame edge
  to edge, framed from the waist up, close to the camera, filling 75-90% of
  the picture. Never a wide room with small people in it.
- The wronged wife (often pregnant) is very pretty and the emotional centre:
  tears streaming, pleading or stunned. The mother-in-law is elegant (pearls,
  tweed or silk) with a cold or furious face. The husband, handsome in a dark
  suit, pointing, rushing in or frozen in shock.
- Big physical action: a hand grabbing an arm, a finger pointing, someone
  pulling a wrist, arms thrown out, a box or envelope being pushed away.
- One story object large and in front: courier boxes, an envelope of money,
  a phone with evidence (screen turned away), a luxury handbag, a card
  statement, a funeral portrait frame.
- Bright, glossy, high-key K-drama light in a WEALTHY modern Korean place
  (luxury apartment, marble kitchen, funeral hall with white chrysanthemums,
  hospital VIP room), softly blurred behind the people.

## Write 3 prompts, all poster-framed, each a DIFFERENT moment

Named exactly: `portrait_main`, `dramatic_scene`, `youtube_ctr`.

- `portrait_main` — the wronged wife big in the foreground (tearful or
  stunned), the mother-in-law and husband close behind her, reacting.
- `dramatic_scene` — the clash at its peak, three or four characters packed
  across the frame, the key physical action in the middle.
- `youtube_ctr` — the story object big in front, two or three shocked faces
  right behind it.

## Rules

1. Start every prompt with: "K-drama poster framing, the characters fill most
   of the frame from the waist up, faces large and sharp in the middle band."
2. Refer to the characters as **the people in the attached reference images**
   (by role: the wife, the mother-in-law, the husband). Never describe their
   faces or hair — the reference images carry them.
3. Every prompt: photorealistic, bright daylight, glossy, 16:9, fill the whole
   frame edge to edge; faces between 20% and 78% of the frame height.
4. NO text, NO letters, NO numbers, NO signs, NO logo anywhere in the image.

## Return JSON only, no commentary

```json
{"thumbnails": [
  {"version_desc": "portrait_main", "img_prompt": "..."},
  {"version_desc": "dramatic_scene", "img_prompt": "..."},
  {"version_desc": "youtube_ctr", "img_prompt": "..."}
]}
```
