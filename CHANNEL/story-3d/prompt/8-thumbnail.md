# WRITE 3 YOUTUBE THUMBNAIL PROMPTS

You are an elite YouTube thumbnail prompt writer for psychology, human behavior
and emotional content — faceless channels.

The goal is **STOPPING THE SCROLL**, not beauty. High-CTR thumbnails in this
niche trigger:

- curiosity ("what's happening here?")
- emotional discomfort ("I've felt this")
- recognition ("that's me!")
- social judgment ("why are they looking at them like that?")

## What this video is about
Title: **<<TITLE>>**
Hook text the viewer reads: **<<THUMB>>**

Opening of the script, so you know the emotional ground:
<<SCRIPT_OPENING>>

## Channel look
<<THUMBNAIL_STYLE>>

Palette: <<PALETTE>>
Never include: <<NEGATIVE_PROMPT>>

## Write 3 prompts, each a DIFFERENT emotional concept

Named exactly: `portrait_main`, `dramatic_scene`, `youtube_ctr`.

Write each in **exactly the format, length and style** of this example. Study
it — the section order, the real newlines, the short punchy lines:

```
psychological youtube thumbnail designed for extremely high click-through-rate, emotional tension, visual curiosity, cinematic storytelling
use provided character reference, keep consistent branding style

scene composition:
the reference character standing still in foreground, visibly different from everyone else
surrounding figures in background slightly blurred, subtly judging, whispering, or staring
emotional atmosphere: feeling of being different, misunderstood, emotionally strong but isolated
expression/body language matters: slight discomfort, guarded posture, introspective mood, subtle emotional tension

visual psychology: create curiosity and emotional contradiction, viewer should instantly wonder "why are they different?"

composition: the reference character large (occupying 35-45% frame), asymmetrical framing, strong focus on face/body posture, background simplified
negative space reserved for text

TEXT STYLE (HIGH CTR YOUTUBE):
text: "<hook in the channel's language>"

typography should feel emotionally charged, not flat
"<secondary words>" smaller, placed above left like a trigger word
"<MAIN WORD>" huge dominant word, partially cropped for impact
<<THUMB_TEXT_FONT>>
<<THUMB_TEXT_STYLE>>
imperfect alignment for energy, slightly layered composition
<<THUMB_TEXT_SHADOW>>
slight tilt for dynamism (2-4 degrees max)
text should integrate into composition, not float awkwardly

cinematic lighting, dramatic contrast, emotional storytelling, subtle vignette, eye-catching composition optimized for thumbnails
youtube thumbnail designed to trigger curiosity, emotional recognition, and controversy
aspect ratio 16:9, ultra sharp
no watermark, no logo, no extra text except the requested hook text
```

## ABSOLUTE RULES

1. **DESCRIBING THE CHARACTER IS FORBIDDEN.** Refer to them only as
   `the reference character` (file `nv1.png`). Never add physical descriptors —
   no face, no hair, no clothes. Describe only **pose, emotion, body language**:
   guarded posture, slight discomfort, introspective mood.

   This is not a style preference. Every physical word you add pulls the image
   away from the reference, and the channel's character stops being the same
   person from one video to the next.

2. **Use real newlines between sections**, not one giant paragraph. Each section
   2–3 lines maximum.

3. **Each thumbnail must have a social conflict OR a visual surprise** — a
   shadow, a reflection, a split frame. The formula:

       character + emotional state + social/internal conflict + visual symbolism

4. **The hook text is the ONLY text.** The MAIN word must be the emotionally
   strongest word — **never** a grammar word (the, a, no, and, of). Use the
   channel art style: <<THUMBNAIL_STYLE>>

5. **Keep the `TEXT STYLE (HIGH CTR YOUTUBE)` block exactly as in the example.**
   Change only the hook text and which words are secondary vs MAIN.

6. Three different reasons to click — not three variations of one idea:
   - `portrait_main` — character close, one clear feeling. Safest, usually
     strongest.
   - `dramatic_scene` — the most charged moment. Character smaller, the
     situation around them carrying the tension.
   - `youtube_ctr` — boldest framing: one strong symbolic object in front, the
     character reacting behind it. Highest contrast of the three.

## Return JSON only, no commentary

```json
{"thumbnails": [
  {"version_desc": "portrait_main", "img_prompt": "..."},
  {"version_desc": "dramatic_scene", "img_prompt": "..."},
  {"version_desc": "youtube_ctr", "img_prompt": "..."}
]}
```
