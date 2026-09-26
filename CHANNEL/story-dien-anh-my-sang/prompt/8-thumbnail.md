# WRITE 3 THUMBNAIL IMAGE PROMPTS — AMERICAN ROMANCE-DRAMA MOVIE POSTER, NO TEXT

You write image prompts for thumbnails of an American "unaware of who he truly
was" drama channel (billionaires, CEOs, waitresses, bakers, flower girls). The
thumbnail is ONLY a picture — no text at all — so the picture alone must make
people click. It must look like the POSTER of a glossy romance movie: two
beautiful people, big in the frame, a charged look between them.

## What this video is about
Title: **<<TITLE>>**

Opening of the script:
<<SCRIPT_OPENING>>

## Channel look
<<THUMBNAIL_STYLE>>

Palette: <<PALETTE>>
Never include: <<NEGATIVE_PROMPT>>

## What wins in this niche (12 top thumbnails of the leading channel, 26/09/2026)

- THE PEOPLE ARE THE PICTURE. The two leads fill 70-85% of the frame, framed
  from the chest or waist up, close to the camera; each lead's head is about
  a quarter to a third of the frame height. Never a wide room with small people.
- The man: handsome, sharp jaw, perfectly tailored suit (navy, black, emerald).
  The woman: very pretty, glossy long hair, soft makeup, a bright feminine
  outfit (pink, lavender, sky-blue or red dress, or a neat work uniform with an
  apron) — the brightest colour patch in the image.
- A clear emotional charge readable at phone size: he stares at her, stunned or
  tender; she has a hand on her heart, tears in her eyes, a shy smile or a
  shocked face. Side characters (mocking guests, a laughing rival, a stern
  parent) are smaller, behind, slightly soft — they react, they do not compete.
- Bright, high-key, saturated light: sunny café terraces, flower-filled
  bakeries, gala halls with chandeliers, sea-view restaurants; at night the
  faces are still lit warm and bright, city lights as glowing bokeh behind.
- One story object in the foreground between them: a gift bag, an open ring
  or jewel box, a bouquet, a coffee cup, a folder, a basket of roses.
- Crisp focus on faces, background softly blurred, rich colour grading, no
  dark or empty areas anywhere.

## Write 3 prompts, all poster-framed, each a DIFFERENT reason to click

Named exactly: `portrait_main`, `dramatic_scene`, `youtube_ctr`.

- `portrait_main` — the two leads facing each other across the frame (man one
  side, woman the other), the charged look between them, the story object in
  the middle.
- `dramatic_scene` — the woman in front, hurt or humiliated, one or two
  mockers just behind her laughing; the man a step behind watching, about to
  step in. Still medium close — all faces big.
- `youtube_ctr` — both leads looking toward the camera side by side like a
  movie poster, her emotional, him composed, the glamorous place glowing
  behind them.

## Rules

1. Start every prompt with the framing sentence: "Movie-poster medium close-up,
   the two main characters fill most of the frame, framed from the chest up,
   faces large and sharp."
2. Refer to the characters as **the people in the attached reference images**
   (by role). Never describe their faces or hair.
3. Every prompt: photorealistic, bright, glossy, saturated, 16:9, fill the
   whole frame edge to edge.
4. NO text, NO letters, NO numbers, NO signs, NO logo anywhere in the image.

## Return JSON only, no commentary

```json
{"thumbnails": [
  {"version_desc": "portrait_main", "img_prompt": "..."},
  {"version_desc": "dramatic_scene", "img_prompt": "..."},
  {"version_desc": "youtube_ctr", "img_prompt": "..."}
]}
```
