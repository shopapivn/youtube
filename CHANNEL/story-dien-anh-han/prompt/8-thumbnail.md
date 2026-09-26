# WRITE 3 THUMBNAIL IMAGE PROMPTS — KOREAN FAMILY DRAMA, NO TEXT

You write image prompts for thumbnails of a Korean family-drama (노후사연)
channel. The goal is **STOPPING THE SCROLL**: a Korean viewer must see, in one
second, who is wronging whom and feel "what happens next?!".

The image carries NO text. Our tool adds two lines of Korean text afterwards —
one along the TOP edge, one along the BOTTOM edge — so keep faces out of those
two bands.

## What this video is about
Title: **<<TITLE>>**
Thumbnail text (added later, for your understanding only): **<<THUMB>>**

Opening of the script:
<<SCRIPT_OPENING>>

## Channel look
<<THUMBNAIL_STYLE>>

Palette: <<PALETTE>>
Never include: <<NEGATIVE_PROMPT>>

## What wins in this niche (study of the top Korean channels)

- A bright, glossy, photorealistic K-drama still in a WEALTHY modern Korean
  place: luxury apartment with marble kitchen, penthouse living room, funeral
  hall with white chrysanthemums, hospital VIP room, company lobby.
- THREE or FOUR people in the frame at the peak of the clash: the wronged wife
  (often pregnant, crying or pleading), the cruel mother-in-law (elegant,
  pearls, cold or furious face), the husband (dark suit, pointing, rushing in or
  frozen in shock), sometimes the other woman or a delivery man.
- Big readable emotions: tears streaming, mouths open shouting, fingers
  pointing, a hand grabbing an arm, someone pulling a wrist.
- One story object visible and large: courier boxes, an envelope of money, a
  phone with evidence (screen turned away), a luxury handbag, a card statement,
  a funeral portrait frame.

## Write 3 prompts, each a DIFFERENT moment

Named exactly: `portrait_main`, `dramatic_scene`, `youtube_ctr`.

- `portrait_main` — the wronged wife close in the foreground (tearful or
  stunned), the mother-in-law and husband reacting right behind her.
- `dramatic_scene` — the whole confrontation, all characters in the room,
  the most shocking second of the story.
- `youtube_ctr` — the story object big in the foreground, the characters'
  shocked faces behind it.

## Rules

1. Refer to the characters as **the people in the attached reference images**
   (by role: the wife, the mother-in-law, the husband). Never describe their
   faces, hair or clothes — the reference images carry them.
2. Every prompt: photorealistic, bright daylight, 16:9, faces in the MIDDLE
   band of the frame, top 20% and bottom 22% free of faces.
3. NO text, NO letters, NO numbers, NO signs, NO logo anywhere in the image.

## Return JSON only, no commentary

```json
{"thumbnails": [
  {"version_desc": "portrait_main", "img_prompt": "..."},
  {"version_desc": "dramatic_scene", "img_prompt": "..."},
  {"version_desc": "youtube_ctr", "img_prompt": "..."}
]}
```
