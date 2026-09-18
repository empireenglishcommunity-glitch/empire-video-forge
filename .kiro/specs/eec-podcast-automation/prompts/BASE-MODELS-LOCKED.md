# Two Worlds — Base Models LOCKED (the foundation to fine-tune)

> Decision: pick ONE professional base model for Arabic + ONE for English, chosen
> specifically as the best FOUNDATION TO FINE-TUNE to Gemini-quality (not best
> zero-shot). Then train them. No shortcuts, no paid APIs — open-source studio
> quality via fine-tuning. Evidence-grounded (Arabic TTS Arena + a real F5-vs-
> StyleTTS2 fine-tune trade-off study + all prior tests).

## Why zero-shot failed (and why that's fine)
Chatterbox + VoiceTut both fell short of Kore ZERO-SHOT. Expected: Kore is a
frontier Google model. The plan was always to FINE-TUNE. Zero-shot quality is NOT
the selection criterion — fine-tune-ability is.

## Evidence that drove the pick
- **F5-vs-StyleTTS2 fine-tune study (real data):** F5 commits HARD to accent/voice
  character (what we want for distinct cast identities) but can truncate on tiny
  data; StyleTTS2 is phonetically rock-stable but softer on accent. CRUCIAL: with a
  corpus that fully specifies the target (>~100h, or strong Egyptian pretrain), the
  trade-off COLLAPSES — F5 gives both accent + stability.
- **Arabic TTS Arena thesis (Navid AI, after listening to 100s of Arabic outputs):**
  the winning design = VOICE IDENTITY (real reference speakers) + natural-language
  PERFORMANCE direction, on flow-matching (F5-family). Maps perfectly to our huge
  multi-dialect/multi-age cast: build a LIBRARY OF VOICE IDENTITIES.
- **Egyptian F5 ecosystem already exists:** Habibi-TTS EGY, SILMA (F5, Apache-2.0,
  bilingual AR+EN, has CATT+NeMo built in), 334h diacritized Egyptian corpus, an
  academic Egyptian-XTTS fine-tune paper. The Arabic groundwork is F5-shaped.
- **English:** Chatterbox beat ElevenLabs in blind tests, MIT, emotion control,
  LoRA finetune toolkits exist.

## 🔒 LOCKED BASE MODELS

### Arabic (all dialects) = **F5-TTS family**, specifically **SILMA-TTS** as the base
- Why SILMA: it IS F5 (so all F5 tooling/finetune scripts apply), **Apache-2.0**
  (commercial-safe), **bilingual Arabic+English** (native code-switch — our exact
  need), ships **CATT diacritization + NeMo normalization built in** (the front-end
  we needed), voice cloning from ~8s, 24kHz, F5-v1.1.7-compatible training.
- Base is MSA-leaning -> we FINE-TUNE it to Egyptian (then Gulf/Levantine) using the
  Egyptian corpora + our target voice(s). F5 commits to accent -> exactly the lever
  to lock a dialect + a specific Coach voice identity.
- Fallback base if SILMA underperforms after finetune: Habibi-TTS EGY (F5, already
  Egyptian) — same toolchain, so switching is cheap.

### English (all accents) = **Chatterbox** (Multilingual v3 / Turbo)
- Best expressive English, MIT, emotion control ([laugh], exaggeration), cloning,
  LoRA finetune toolkit (gokhaneraslan/chatterbox-finetuning). Fine-tune per lead
  voice; clone for minor/guest voices. Add American/British/etc. as voice identities.

## The cast model = "voice identity library" (the Arena thesis, applied)
Not "dialect labels." A registry of REAL reference voices, each cloned/fine-tuned:
- Arabic voices (Coach, Egyptian leads, Gulf, Levantine, kids, old) -> SILMA/F5
- English voices (Macal accented, Nour, guests by accent/age) -> Chatterbox
Each character = {engine, voice-identity ref/finetune, dialect, default performance}.
Adding a character = add a voice identity. Scales to the whole production.

## How we hit Gemini-quality (the pipeline, per engine)
1. Front-end: dialect-correct diacritization (CATT, built into SILMA) + Egyptian
   normalization + code-switch handling.
2. FINE-TUNE (the core): LoRA/full on clean Egyptian data + the target voice, using
   listening-loop checkpoint selection (loss is NOT a reliable signal — pick by ear
   at the sweet-spot epoch, per the study).
3. Generation controls: performance direction, chunking, VAD trailing-trim.
4. Post: loudnorm.

## Immediate next steps (I drive; owner hears the gates)
1. Stand up SILMA-TTS on Kaggle; baseline the SAME Coach line (know our start point).
2. Prep the Egyptian fine-tune dataset (real Egyptian corpora + our chosen voice
   identity; the 150-line + growing corpus feeds text; audio from clean sources).
3. LoRA fine-tune SILMA -> Egyptian Coach; listen-loop checkpoints -> owner gate.
4. In parallel, lock Chatterbox English cast voices.

_Evidence: Arabic TTS Arena (Navid AI), F5-vs-StyleTTS2 fine-tune study, SILMA +
Habibi + Chatterbox model cards. Verified Sep 2026._
