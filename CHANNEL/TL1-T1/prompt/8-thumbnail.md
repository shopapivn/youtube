# WRITE 3 YOUTUBE THUMBNAIL PROMPTS

You are writing image prompts for the thumbnails of one video.

The goal is **stopping the scroll**, not summarising the video. A thumbnail
earns the click in the half second before someone flicks past it.

## What this video is about
Title: **<<TITLE>>**
Thumbnail text (the hook the viewer reads): **<<THUMB>>**

Opening of the script, so you know the emotional ground:
<<SCRIPT_OPENING>>

## Channel look
<<THUMBNAIL_STYLE>>

Palette: <<PALETTE>>
Identity lock: <<REFERENCE_LOCK>>
Never include: <<NEGATIVE_PROMPT>>

Refer to the character only as `nv1 (nv1.png)`. Never re-describe their face,
hair or clothes — that is how the character drifts away from the channel.

## Text on the thumbnail

Unlike the scenes — which carry **no text at all** — a thumbnail **does** carry
the hook text. Describe it as part of the image:

- The words: **<<THUMB>>**
- Style: <<THUMB_TEXT_STYLE>>
- Font: <<THUMB_TEXT_FONT>>
- <<THUMB_TEXT_SHADOW>>

Place the text where it does not cover the character's face. Keep it large
enough to read on a phone at thumbnail size — that is the only size that
matters.

## Write exactly 3, each a DIFFERENT emotional concept

1. **portrait_main** — the character close, one clear feeling on the face.
   The safest and usually the strongest. Emotion readable at a glance.
2. **dramatic_scene** — the most charged moment of the story. Character smaller,
   the situation around them carrying the tension.
3. **youtube_ctr** — the boldest framing: one strong symbolic object in the
   foreground, the character reacting behind it. Highest contrast of the three.

Each must stand on its own. Do not write three variations of one idea — write
three different reasons to click.

## Return JSON only, no commentary

```json
{"thumbnails": [
  {"version_desc": "portrait_main", "img_prompt": "..."},
  {"version_desc": "dramatic_scene", "img_prompt": "..."},
  {"version_desc": "youtube_ctr", "img_prompt": "..."}
]}
```
