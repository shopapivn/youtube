You direct the voice actor for part <<KHUC>> of a narrated American story (ElevenLabs v3 voice).
The sentences are numbered below. Choose where an audio tag goes — before a sentence where the feeling clearly changes (a blow, a discovery, a quiet moment, the payoff), about one tag every 6–10 sentences. The listener should feel the story, not hear a performer: breathing sounds (sighs, exhales, inhales deeply, gulps) are rare — at most one in this whole part, only at its biggest blow — and vary the tags instead of repeating the same one.

Allowed tags (use the name without brackets): sad, angry, crying, whispers, sighs, exhales, inhales deeply, thoughtful, curious, surprised, annoyed, sarcastic, happy, excited, chuckles, laughs, gulps, short pause, long pause

If the story jumps to a new time or place, you may also mark ONE sentence that starts a new section (a pause is put before it).

Trả về NGUYÊN VĂN JSON — không tạo file, không mô tả việc đã làm, không ghi chú (no notes, no code fences).

<story>
<<DRAFT>>
</story>

Return JSON only, in this exact shape:
{"the": [[<sentence number>, "<tag>"], ...], "ngan": [<sentence number>]}
