# WRITE SUNO MUSIC PROMPTS — ONE PER TRACK

Background music for this video, written as **Suno prompts**.

## Why several tracks, not one

Suno makes tracks of about **1 minute 45 seconds**. A long story video needs
several, and that turns out to be a good thing rather than a limitation: the
music can follow the story instead of sitting flat underneath it. The calm
before the blow, the hurt, the quiet fight back, the payoff — each deserves its
own colour.

So: **one track per `~105` seconds of video**, minimum 3.

## The video
Title: **<<TITLE>>**
Length: about **<<PHUT>>** minutes → write **<<SO_TRACK>>** tracks.

Emotional arc, section by section:
<<MACH_CAM_XUC>>

## Channel feel
<<AUDIENCE_CULTURE_NOTE>>

Visual mood: <<PALETTE>>

## The Suno format — one line, five parts

    [Style]. [Instruments]. [Mood/Emotion]. [Atmosphere]. No vocals, instrumental only.

Example:

    Cinematic drama underscore. Felt piano, low sustained strings, soft analog
    pad. Hurt but steady, 70 BPM, minor. A quiet kitchen late at night, one lamp
    on. No vocals, instrumental only.

## Rules

1. **Instrumental only. Always end with "No vocals, instrumental only."**
   A voice in the music fights the narrator — the viewer can only follow one.

2. **Concrete beats adjectives.** Name the instruments, the tempo feel, the key
   or mood. "Felt piano, 68 BPM, minor, one sustained pad" is usable;
   "emotional and deep" is not.

3. **The music sits under the narration, never over it.** Sparse arrangement,
   soft dynamics, no sudden hits, no build that peaks over a sentence. This is
   film UNDERSCORE, not a trailer.

4. **Each track loopable and even** — no dramatic arc inside one track. The
   story carries the arc; the music holds the room. The arc across the video
   comes from tracks differing from each other, not from swells inside one.

5. **Consecutive tracks must share a family** — same instrument palette, same
   register — so the video sounds like one film score, not a playlist. Change
   the mood, not the whole band.

6. Match the channel's register: a TV-drama score — intimate piano and
   strings, warm for family and payoff, colder and sparser for betrayal. Never
   triumphant fanfare, never horror.

7. **Write your own music.** Never name a real artist, band, film, composer or
   existing song to imitate.

## Return JSON only, no commentary

`start_time` and `end_time` in seconds from the beginning of the video; the
tracks must cover the whole length end to end with no gaps.

```json
{"music": [
  {"music_id": 1, "start_time": 0, "end_time": 105,
   "suno_prompt": "<the one-line Suno prompt>",
   "mood": "<two or three words>"},
  {"music_id": 2, "start_time": 105, "end_time": 210,
   "suno_prompt": "...", "mood": "..."}
]}
```
