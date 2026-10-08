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
- She is stunning like a movie star: radiant skin, striking eyes, flattering
  makeup, an elegant hairstyle, fine jewellery, an elegant neckline — you
  choose the styling that suits her and this story.
- Expression: calm, confident, a quiet knowing look or a faint smile straight
  into the lens — the woman who already knows how this ends.
- Background: a soft, warm, blurred hint of an elegant place that fits the
  story — it never competes with her.

## Write 3 portraits, each a DIFFERENT setting and pose

Named exactly: `portrait_main`, `dramatic_scene`, `youtube_ctr`.

Choose three clearly different looks yourself — different outfit, outfit
colour, hairstyle, setting and expression in each — all glamorous and fitting
this story's winning moment. Never give two portraits the same outfit colour.

- `portrait_main` — the most iconic image of her victory, a calm knowing look
  into the lens.
- `dramatic_scene` — a second look in a different place, a faint confident
  smile.
- `youtube_ctr` — the most eye-catching of the three at phone size, chin
  slightly lifted, composed and radiant.

## Rules

1. The woman is **the woman in the attached reference image** — never
   describe her face or hair. Dress her in a glamorous, elegant outfit that
   fits a winning moment (you choose it), flawless soft makeup, glossy hair.
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
