# WRITE 3 VERTICAL PORTRAIT PROMPTS — THE HEROINE, NO TEXT

The thumbnail of this channel is a text panel on the left (our tool writes the
story hook there) and ONE vertical portrait of the main character on the right.
You write the prompts for that portrait.

The portrait is the woman the audience roots for — the narrator AT HER WINNING
MOMENT: beautiful, composed, quietly confident, the kind of woman viewers want
to be. Not a victim picture: she has already won.

## What this video is about
Title: **<<TITLE>>**

Opening of the script:
<<SCRIPT_OPENING>>

## Channel look
<<THUMBNAIL_STYLE>>

Palette: <<PALETTE>>
Never include: <<NEGATIVE_PROMPT>>

## Write 3 portraits, each a DIFFERENT setting and pose

Named exactly: `portrait_main`, `dramatic_scene`, `youtube_ctr`.

- `portrait_main` — seated on a cream sofa in a bright elegant living room,
  legs crossed, hands resting, a calm small smile at the camera, soft window
  light, a teacup and an open book on the table beside her.
- `dramatic_scene` — standing tall in the doorway of a sunlit beautiful house
  (or on its porch), arms relaxed, a serene knowing look.
- `youtube_ctr` — seated at a table in a warm upscale restaurant or garden,
  golden light behind her, relaxed and radiant.

## Rules

1. The woman is **the woman in the attached reference image** — never
   describe her face or hair. You may choose an elegant outfit (a deep navy or
   emerald dress, a cream blouse) that fits a winning moment.
2. VERTICAL 9:16 portrait, one person only, her body filling the frame height
   (head near the top, framed down to the knees), photorealistic, bright,
   glossy, shallow depth of field, eye contact with the camera.
3. NO text, NO letters, NO numbers, NO signs, NO logo anywhere in the image.

## Return JSON only, no commentary

```json
{"thumbnails": [
  {"version_desc": "portrait_main", "img_prompt": "..."},
  {"version_desc": "dramatic_scene", "img_prompt": "..."},
  {"version_desc": "youtube_ctr", "img_prompt": "..."}
]}
```
