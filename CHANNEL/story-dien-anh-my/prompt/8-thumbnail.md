# WRITE 3 VERTICAL PORTRAIT PROMPTS — THE HEROINE, NO TEXT

The thumbnail of this channel is a text panel on the left (our tool writes the
story hook there) and ONE vertical portrait of the main character on the right.
You write the prompts for that portrait.

The portrait is the woman the audience roots for — the narrator AT HER WINNING
MOMENT: stunning, composed, quietly confident, the kind of woman viewers want
to be. Not a victim picture: she has already won. SHE IS THE REASON TO CLICK:
the viewer must see her face clearly and be drawn to her at phone size.

## What this video is about
Title: **<<TITLE>>**

Opening of the script:
<<SCRIPT_OPENING>>

## Channel look
<<THUMBNAIL_STYLE>>

Palette: <<PALETTE>>
Never include: <<NEGATIVE_PROMPT>>

## Framing — a close movie-star portrait (12 winning thumbnails of the niche)

- A CLOSE head-and-shoulders portrait: her face is the picture, filling most
  of the frame height's upper half; framed from mid-chest up, camera close.
  Never full body, never a small figure in a room.
- She is stunning like a movie star: radiant skin, striking eyes with soft
  smoky makeup, rosy-nude lips, an elegant hairstyle (a soft chignon with
  loose face-framing strands, or long glossy waves), delicate drop earrings
  and a fine necklace, an elegant neckline (emerald or black gown, ivory silk
  blouse, cream knit).
- Expression: calm, confident, a quiet knowing look or a faint smile straight
  into the lens — the woman who already knows how this ends.
- Background: a soft, warm, blurred hint of an elegant place (a lit ballroom,
  a city street at golden hour, a luxurious room) — it never competes with her.

## Write 3 portraits, each a DIFFERENT setting and pose

Named exactly: `portrait_main`, `dramatic_scene`, `youtube_ctr`.

- `portrait_main` — in an emerald or black evening gown with drop earrings,
  soft chignon, warm ballroom bokeh behind, a calm knowing look into the lens.
- `dramatic_scene` — in an ivory silk blouse with a fine necklace, long glossy
  waves, a golden-hour city street softly blurred behind, a faint confident
  smile.
- `youtube_ctr` — in a soft cream knit or elegant blazer, hair in loose
  glossy waves, a warm luxurious room blurred behind, chin slightly lifted,
  composed and radiant.

## Rules

1. The woman is **the woman in the attached reference image** — never
   describe her face or hair. Dress her in a glamorous, elegant outfit that
   fits a winning moment (a deep navy, emerald or ruby dress, a silk blouse,
   fine jewellery), flawless soft makeup, glossy hair.
2. Start every prompt with: "Vertical 9:16 close head-and-shoulders portrait,
   her face fills most of the frame, large, sharp and radiant."
3. One person only, photorealistic, bright, glossy, eye contact with the
   camera.
4. NO text, NO letters, NO numbers, NO signs, NO logo anywhere in the image.

## Return JSON only, no commentary

```json
{"thumbnails": [
  {"version_desc": "portrait_main", "img_prompt": "..."},
  {"version_desc": "dramatic_scene", "img_prompt": "..."},
  {"version_desc": "youtube_ctr", "img_prompt": "..."}
]}
```
