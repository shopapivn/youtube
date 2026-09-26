# WRITE 3 THUMBNAIL IMAGE PROMPTS — AMERICAN LUXURY DRAMA, NO TEXT

You write image prompts for thumbnails of an American "unaware of who he truly
was" drama channel (billionaires, CEOs, waitresses, ex-wives, fiancées). The
thumbnail is ONLY a picture — no text at all — so the picture alone must make
people click.

## What this video is about
Title: **<<TITLE>>**

Opening of the script:
<<SCRIPT_OPENING>>

## Channel look
<<THUMBNAIL_STYLE>>

Palette: <<PALETTE>>
Never include: <<NEGATIVE_PROMPT>>

## What wins in this niche (study of the top channel)

- A glossy, photorealistic, bright still of the exact moment BEFORE the tables
  turn: the arrogant person mocking, the underestimated hero calm or about to
  reveal the truth, onlookers laughing or gasping.
- Glamorous places: upscale restaurants with candles and flowers, gala
  ballrooms with chandeliers, hotel lobbies, glass offices with a city skyline
  at blue hour.
- Attractive people in jewel-tone clothes (royal blue dress, emerald dress,
  burgundy suit), faces sharp and readable: smug smirk, laughter behind a hand,
  wide-eyed shock, a frozen man mid-gesture.
- One story object that makes the viewer curious: a black card, a card machine
  showing a decline (screen turned away), a bill folder, a contract, a cheque.
- Warm golden light on the people, cooler city lights behind — lots of depth.

## Write 3 prompts, each a DIFFERENT reason to click

Named exactly: `portrait_main`, `dramatic_scene`, `youtube_ctr`.

- `portrait_main` — the hero close, calm confident face, the mockers behind.
- `dramatic_scene` — the whole room at the peak moment, everyone reacting.
- `youtube_ctr` — the story object big in front, the shocked mocker behind.

## Rules

1. Refer to the characters as **the people in the attached reference images**
   (by role). Never describe their faces, hair or clothes.
2. Every prompt: photorealistic, bright, glossy, 16:9, fill the whole frame.
3. NO text, NO letters, NO numbers, NO signs, NO logo anywhere in the image.

## Return JSON only, no commentary

```json
{"thumbnails": [
  {"version_desc": "portrait_main", "img_prompt": "..."},
  {"version_desc": "dramatic_scene", "img_prompt": "..."},
  {"version_desc": "youtube_ctr", "img_prompt": "..."}
]}
```
