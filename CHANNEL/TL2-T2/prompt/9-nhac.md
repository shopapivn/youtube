# WRITE THE BACKGROUND MUSIC PROMPT

Write one prompt for an instrumental background track for this video.

## The video
Title: **<<TITLE>>**
Length: about **<<PHUT>>** minutes.

Opening of the script, so you can feel where it starts:
<<SCRIPT_OPENING>>

## Channel feel
<<AUDIENCE_CULTURE_NOTE>>

Visual mood of this channel: <<PALETTE>>

## Rules

1. **Instrumental only. No vocals, no lyrics, no spoken word.** A voice in the
   music fights the narrator — the viewer can only follow one.
2. **The music sits under the narration, never over it.** Sparse arrangement,
   soft dynamics, no sudden hits, no build that peaks over a sentence.
3. Name the instruments, the tempo in BPM, and the key or mood. Concrete beats
   adjectives: "felt piano, 68 BPM, minor, one sustained pad" is usable;
   "emotional and deep" is not.
4. Keep it **loopable and even** — no dramatic arc. The story carries the arc;
   the music holds the room.
5. Match the channel's emotional register. This is a psychology channel: calm,
   warm, a little wistful. Not cinematic, not triumphant, not tense.
6. Write your own music — do not name a real artist, band, or existing song to
   imitate, and do not reference a specific commercial track.

## Return JSON only, no commentary

```json
{"music": {
  "prompt": "<the full music prompt, English>",
  "bpm": 68,
  "mood": "<two or three words>",
  "instruments": "<comma separated>"
}}
```
