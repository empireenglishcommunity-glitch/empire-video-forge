# Two Worlds — Voice Casting Brief

> Maps each character to a target voice profile matching their personality from the
> series bible. The pipeline clones each voice from a short (~10s) reference clip via
> Chatterbox (English cast) so voices are CONSISTENT across every episode. The Coach
> stays on Gemini TTS (Kore, Arabic). This brief is the source of truth for casting.

## Engine assignment (split-engine, locked)
- **English cast (Macal, Nour, guests):** Chatterbox (Resemble AI) on GPU (Kaggle
  batch). Beats ElevenLabs in ~65% blind tests; MIT-licensed. Voice = cloned from a
  reference clip per character -> consistent + natural + native American.
- **Coach (Arabic):** Gemini TTS, voice "Kore" (warm Egyptian), controllable style.

## Character voice profiles

### Macal — the learner-hero (male, native American English)
- Personality: smart, warm, a little nervous early, genuine, relatable; his English
  is confident/native (per owner's "all English = pure native American" rule).
- Voice target: **male, 25-35, warm, friendly, medium pitch, natural conversational
  cadence** — approachable "guy next to you", not a news anchor. Slightly upbeat.
- Chatterbox settings: exaggeration ~0.5, cfg_weight ~0.5.

### Nour — the confident guide (female, native American English)
- Personality: confident, kind, encouraging, "I believe in you" energy; the supportive
  friend who already made it. MUST sound motivated/warm (owner's earlier note).
- Voice target: **female, 25-35, warm, bright, encouraging, clear** — mentor-friend,
  not corporate. Expressive, positive.
- Chatterbox settings: exaggeration ~0.55-0.6 (a touch more expressive), cfg_weight ~0.5.

### The Coach — the teacher (Egyptian Arabic) [Gemini Kore, LOCKED]
- Personality: warm, honest, encouraging coach; the EEC brand voice. Egyptian Arabic.
- Voice: Gemini "Kore" + style prompt "warm, encouraging Egyptian coach". Not cloned.

### Guests (rotating, per episode)
- The interviewer, barista, landlord, boss, etc. — 1-2 per episode.
- Voice target: **distinct from the leads**; pick by role:
  - Authority roles (interviewer, boss): firmer/older male or female.
  - Service roles (barista, taxi): casual, younger.
- Approach: a small library of 3-4 cloned guest voices (2 male, 2 female) reused by
  role, so the world feels populated without infinite refs.

## Casting rules (so it stays consistent + smart)
1. Every recurring character has ONE locked reference clip -> same voice every episode.
2. The script generator tags each line with a speaker; the synth step maps
   speaker -> reference clip (English) or Gemini voice (Coach).
3. Guests are assigned from the guest voice library by role type.
4. Reference clips: clean, ~7-10s, single speaker, no music, native American English
   (for the English cast). Stored as a Kaggle Dataset + backed up in the repo/Drive.
5. Voice choices reviewed at the Phase-1 gate; can be swapped by replacing a ref clip
   (no code change) — voices are data, not hardcode.

## Reference clip sourcing (task 2)
- v1: royalty-free / public-domain American voice clips matching the profiles above
  (e.g. LibriVox public-domain narration, CC0 voice samples), trimmed to ~10s clean.
- Later upgrade: owner may record or choose exact voices; swap the ref clip to change.

## Integration into the pipeline (task 6 -> spec)
- `voices/refs/{macal,nour,guest_m1,guest_f1,...}.wav` — locked reference clips.
- `kaggle/synth_episode_en.py` (Kaggle/GPU batch): script.json + refs -> per-line
  WAV via Chatterbox voice cloning.
- `kaggle/synth_episode_ar.py` (Kaggle/GPU batch): Arabic lines -> VoiceTut through
  the shared Egyptian lexicon (Coach = "Sayed"). (Replaced the earlier Gemini-Kore
  coach step.)
- Speaker->voice map lives in `cast.json` so casting is data-driven + consistent.
