# Yalla Fluent — canonical voice references (Phase B.7)

Frozen reference clips for the locked cast. Production **VoiceClones** from these so
each character's voice is 100% consistent across all episodes (Option B — no drift).

| File | Character | Source | License |
|------|-----------|--------|---------|
| `nour_ref.wav` | Nour | Qwen3-TTS VoiceDesign winning take (audition cand2) | Apache-2.0 (Qwen output) |
| `tarek_ref.wav` | Tarek | Qwen3-TTS VoiceDesign (cand3) | Apache-2.0 |
| `farida_ref.wav` | Interviewer / Farida | Qwen3-TTS VoiceDesign (cand1) | Apache-2.0 |
| `aisha_ref.wav` | Barista / Aisha | Qwen3-TTS VoiceDesign (cand2) | Apache-2.0 |
| `qureshi_ref.wav` | Landlord / Qureshi | Qwen3-TTS VoiceDesign (cand1) | Apache-2.0 |
| `friendf_ref.wav` | Friend_F | Qwen3-TTS VoiceDesign (cand1) | Apache-2.0 |
| `official_ref.wav` | Official | Qwen3-TTS VoiceDesign (cand2) | Apache-2.0 |
| `friendm_ref.wav` | Friend_M | Qwen3-TTS VoiceDesign (cand1) | Apache-2.0 |
| `ravi_ref1.wav` | TaxiDriver / Ravi | **Mozilla Common Voice** (`fixie-ai/common_voice_17_0`, en, accent "India and South Asia") | **CC0 public domain** (commercial-safe; attribution kept for provenance) |

**Not here (by design):**
- **Mahmoud (Coach)** = VoiceTut voice **Omar** — generated from voice name + Arabic text, no ref clip.
- **Macal** = VoiceTut voice **Abdullah** reading **raw English** — no ref clip, no transliteration.

All clips are 24 kHz-family mono WAV; the assembly chain normalizes to 24 kHz regardless.
