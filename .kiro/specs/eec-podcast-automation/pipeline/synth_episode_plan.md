# Two Worlds — Unified Episode Synthesis (design, before code)

## What it does
Turns one episode `script.json` into per-line audio + a timeline, routing each
line to the right voice via the cast registry, with Arabic running through the
shared pronunciation brain. This is the production synthesizer for the platform.

## Where each part runs (honest architecture)
- **Arabic lines (VoiceTut)** — GPU, so on **Kaggle** (batch). Uses cast.json +
  egyptian_lexicon.json (shared brain) + ASR-QA.
- **English lines (Chatterbox)** — GPU, also **Kaggle** (batch).
- Both are GPU/Kaggle work; the **server** orchestrates (script, assembly,
  delivery) — never runs the heavy models (3.7GB RAM box, protect the 12 containers).

So the unified synth is a **Kaggle notebook** that:
1. reads episodes/epNN/script.json (from the repo, raw GitHub)
2. reads cast.json (voice-identity map) + egyptian_lexicon.json (shared brain)
3. for each line:
   - look up character -> engine + voice + settings
   - if Arabic: prepare_text (shared lexicon + auto-diacritize) -> VoiceTut -> ASR-QA
   - if English: Chatterbox with the character's ref + exaggeration/cfg
   - write lineNNN_<speaker>.wav + record duration, flagged-words
4. emit timeline.json + a QA report (any word to add to the lexicon)
5. owner downloads the ep folder -> server assembles plain audio -> raw-audio

## Why one notebook loads both engines
Per-line language tag routes to the right engine; both fit on a T4 (VoiceTut
~3GB, Chatterbox ~4-6GB — load sequentially if VRAM tight: do all AR lines, free,
then all EN lines). The script already tags lang, so routing is trivial.

## Build order (DONE — implemented as the split notebooks)
The unified `synth_episode.py` sketch was superseded by the two manifest-driven
Kaggle notebooks (VoiceTut and Chatterbox clash in one kernel, so the passes are
split): `kaggle/synth_episode_ar.py` + `kaggle/synth_episode_en.py`, with
`kaggle/synth_arabic_qa.py` for the ASR-QA proof. Both were run for real on Ep1.
Server-side `assemble_audio.py --plain` stitches the merged output.

## Self-improving pronunciation (locked)
Every Arabic line: shared lexicon + auto-diacritize + ASR-QA. Flagged words ->
egyptian_lexicon.json (one fix, whole cast, forever). The pipeline gets more
accurate every episode; no manual hunting, no blind regeneration.
