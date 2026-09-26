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

## Framing — she dominates the portrait

- Close portrait from the HIPS or WAIST UP, camera near her. Never full body,
  never a doorway or room with a small figure in it.
- Her head and shoulders take the upper half of the frame; her face is large,
  sharp and well lit (about a fifth of the frame height); her body fills
  80-90% of the frame width.
- The setting is only a soft, bright, blurred background behind her (shallow
  depth of field) — it adds colour and luxury, it never competes with her.

## Write 3 portraits, each a DIFFERENT setting and pose

Named exactly: `portrait_main`, `dramatic_scene`, `youtube_ctr`.

- `portrait_main` — seated close to the camera on a cream sofa in a bright
  elegant living room, leaning slightly forward, a calm small smile at the
  camera, soft window light behind her.
- `dramatic_scene` — standing close to the camera in front of a sunlit
  beautiful house (blurred behind her), arms folded or one hand at her
  necklace, a serene knowing look straight into the lens.
- `youtube_ctr` — seated at a table in a warm upscale restaurant or garden,
  chin resting lightly on her hand, golden bokeh behind, relaxed and radiant.

## Rules

1. The woman is **the woman in the attached reference image** — never
   describe her face or hair. Dress her in a glamorous, elegant outfit that
   fits a winning moment (a deep navy, emerald or ruby dress, a silk blouse,
   fine jewellery), flawless soft makeup, glossy hair.
2. Start every prompt with: "Vertical 9:16 close portrait from the waist up,
   the woman fills most of the frame, her face large, sharp and radiant."
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
