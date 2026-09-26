You direct the voice actor for part <<KHUC>> of a narrated American story (ElevenLabs v3 voice).
The sentences are numbered below. Choose where an audio tag goes — before a sentence where the feeling clearly changes (a blow, a discovery, a quiet moment, the payoff), about one tag every 4–6 sentences.

Allowed tags (use the name without brackets): sad, angry, crying, whispers, sighs, exhales, inhales deeply, thoughtful, curious, surprised, annoyed, sarcastic, happy, excited, chuckles, laughs, gulps, short pause, long pause

If the story jumps to a new time or place, you may also mark ONE sentence that starts a new section (a pause is put before it).

Trả về NGUYÊN VĂN JSON — không tạo file, không mô tả việc đã làm, không ghi chú (no notes, no code fences).

<story>
<<DRAFT>>
</story>

Return JSON only, in this exact shape:
{"the": [[<sentence number>, "<tag>"], ...], "ngan": [<sentence number>]}
