# YOUTUBE VIDEO SEO

Title: **<<TITLE>>**
Thumbnail text: **<<THUMB>>**
Channel keywords: <<CHANNEL_KEYWORDS>>

Script excerpt:
<<SCRIPT_OPENING>>

Chapters (from the finished subtitle file; may be empty if not available yet):
<<CHAPTERS>>

---

Work in **<<LANGUAGE>>**.

**Identify the MAIN KEYWORD** from the title and thumbnail text — the 2–4 word phrase a viewer would type to find this video.

Then output the following. Use these exact labels:

DESCRIPTION:
Build it in EXACTLY this order — each block separated by a blank line:

1. **Hook** (1–2 sentences, first sentence ≤150 chars and contains the MAIN
   KEYWORD — this is what shows in search results). Speak to the viewer's
   feeling, not about the video.
2. **What the video covers** (2–4 sentences): name the concrete psychological
   concepts the script actually uses, ending with an emotional promise
   ("きっと途中で…" style).
3. **目次 block** — only if Chapters above is non-empty. Wrap it between two
   `━━━━━━━━━━━━━━` lines, first line `📌 目次`, then one `MM:SS label` per
   chapter, copied from the Chapters input verbatim (never invent or shift
   timestamps; if Chapters is empty, omit this whole block including the
   separator lines).
4. **One warm reframing sentence** (the video's core consolation).
5. **Channel block**: `🕊 このチャンネルについて` + 1–2 sentences about the
   channel (rest for overthinkers, psychology + neuroscience, gentle tone).
6. **Comment CTA**: `💬 コメントで教えてください` + restate the script's OWN
   closing comment question (low-friction, choose-a-scene style if the script
   has one).
7. Last line: 3–5 hashtags, main keyword hashtag first.

The MAIN KEYWORD must appear naturally 3–5 times across blocks 1–2.

HASHTAGS:
Same 3–5 hashtags, space-separated. Main keyword hashtag first.

KEYWORDS:
Comma-separated, under 500 characters, 12–20 phrases, ordered in tiers:
(a) exact-topic phrases from title + thumbnail, (b) the psychological concepts
named in the video, (c) bridge keywords shared with the channel's other videos
(from Channel keywords), (d) the channel name last.

**FORBIDDEN in KEYWORDS:** any token that is not a natural search phrase in
<<LANGUAGE>> — file names, style/asset keys, underscore_tokens (e.g.
`blank_white_figure_warm_peach`), English words, hex codes. If such a token
appears in the inputs, it is production metadata that leaked — never copy it.
