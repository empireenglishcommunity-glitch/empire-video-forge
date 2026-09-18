# Two Worlds — Voice Engine Deep-Dive Report (2026-09-18)

> Full open-internet audit of every viable free/commercial-safe TTS option for the
> podcast, with primary-source evidence (model cards, benchmarks, GitHub issues).
> Goal: broadcast-grade **Egyptian Arabic Coach** + **expressive English cast**,
> free, runs on Kaggle GPU, commercial-safe license. No hype — measured facts.

---

## 0. The core problem, stated precisely (from KemeTone's model card)
Every *general* TTS reads Egyptian text with **Modern Standard Arabic (MSA)** sounds.
Real example of the failure:
- `جميل` → general model says `/gameel/`→`/ʤamiːl/` (MSA) ; Egyptian is `/gameel/` `/ɡ/`
- `دلوقتي` → MSA `/dilwaqti/` ; Cairo street `/dilwaʔti/`
- `ثلاثة` → MSA `/θalaːθa/` ; Egyptian `/talata/`

"It does not fail loudly. It fails politely — somewhere between a newsreader and a
foreigner." That is *exactly* what we heard from Chatterbox. Two root causes:
1. **No diacritics** → the model guesses vowels the MSA way.
2. **The model itself only knows MSA phonetics**, not Cairene — no amount of text
   prep fully fixes a model that was never trained on Egyptian sounds.

This is why the fix is partly *text* (diacritize) and partly *model* (must be
Egyptian-aware).

---

## 1. What we PROVED empirically this session
- **CATT diacritizer works** (ran it): `اهلا بيك` → `اهْلًا بِيكَ`. SOTA, Apache-2.0.
- **CATT + Chatterbox CONFLICT on Kaggle**: CATT pulls `numpy 2.2` + onnxruntime;
  Chatterbox needs `numpy==1.26.4`. In one kernel they break each other → our
  "FIXED" run almost certainly ran with CATT silently failing (no diacritization).
- **Chatterbox multilingual has documented Arabic problems** (official GitHub issue
  #287): mispronunciation, random noise/breathing chunks, skipped words, runaway
  length; a user reports the *same with Arabic*, fixed ~80% only by chunking +
  trailing-silence trim + repetition-penalty. So the base model is weak at Arabic
  even with clean text.

---

## 2. Candidate models — measured, with licenses (the load-bearing column)

### English-cast engines
| Model | English quality | Cloning | Emotion control | License | Verdict |
|---|---|---|---|---|---|
| **Chatterbox (Multilingual v3)** | **Best** — beat ElevenLabs 65.3% vs 24.5% in blind test | ✅ ~5s | ✅ exaggeration knob + `[laugh]`/`[chuckle]` (Turbo) | **MIT** ✅ | **KEEP for English cast** |
| F5-TTS (base) | Good, but "copies the reference's mood" — flat, no emotion dial | ✅ | ❌ mirrors ref only | code MIT / **weights CC-BY-NC** ✗ | English weights non-commercial |
| Orpheus 3B | Expressive, emotion tags | ✅ | ✅ | Apache-2.0 ✅ | heavier (8-12GB); backup |
| XTTS v2 | Good, 17 langs | ✅ | limited | **non-commercial** ✗ | disqualified (license) |

### Arabic Coach engines (the hard part)
| Model | Egyptian? | Code-switch AR↔EN | Cloning | Quality (measured) | License | Verdict |
|---|---|---|---|---|---|---|
| **VoiceTut-TTS** | **✅ Egyptian-first** (380h Egyptian podcasts) | **✅ native** ("عندي meeting بكرة") | ✅ zero-shot + 17 built-in voices | WER **0.40 AR / 0.07 EN**, UTMOS 3.47, runs on **T4 (2.9GB)** | **Apache-2.0** ✅ | **TOP Arabic candidate** |
| SILMA-TTS (F5) | ✗ **Fusha/MSA only** | ✅ bilingual | ✅ ~8s | high-fidelity, has CATT+NeMo built in | **Apache-2.0** ✅ | great engine, wrong dialect |
| Masri Higgs v3 | ✅ Egyptian (98h) | ✅ | ✅ | **best numbers** (WER 0.10, clean long-form) | **NON-COMMERCIAL** (Higgs) ✗ | disqualified (license) |
| KemeTone | ✅ Cairene (best phonetics) | ✗ no EN, no numbers | ❌ single fixed female voice | natural, CPU-run | Apache-2.0 ✅ | no cloning/EN → can't be our flexible Coach |
| MAdel121 F5-EGY | drifts to MSA | — | ✅ | UTMOS **2.63**, 20% WER, "research artifact, not production" | CC-BY-NC ✗ | disqualified (quality+license) |
| Chatterbox (Arabic) | ✗ MSA-ish + unstable | ✗ (we bolt on) | ✅ | documented noise/mispronounce | MIT ✅ | not good enough alone for AR |

### Ruled out entirely
- **CosyVoice** — no Arabic at all (Chinese/EN/JP/KO + European). Benchmarked 2.1/5
  naturalness. Not for us.
- **Fish Speech** — non-commercial open weights.

---

## 3. The three honest architecture options

### Option A — UNIFY on Chatterbox (what we tried)
- English: excellent. Arabic: weak even with a proper front-end (model is MSA-only,
  documented instability). Would need a full Egyptian LoRA fine-tune to be viable.
- **Verdict:** only works if we invest in fine-tuning Chatterbox on Egyptian audio
  (Tier-2 effort, needs a dataset). Highest effort, uncertain Arabic ceiling.

### Option B — UNIFY on an Egyptian model (VoiceTut) for everything
- VoiceTut does Egyptian + code-switch + English (WER 0.07 EN is excellent) + cloning,
  Apache-2.0, on T4. One engine, one notebook — the *simple* dream you want.
- Risk: is its **English expressive enough for drama**, and is its **cloned-voice
  quality** as characterful as Chatterbox for the cast? Unknown until we hear it.

### Option C — SPLIT: Chatterbox (English cast) + VoiceTut (Arabic Coach) ⭐
- Each language on its proven best tool. Both free, both on Kaggle, both Apache/MIT.
- "Harder" is overstated: it's one notebook loading two models; per-line we already
  tag lang, so routing is trivial. Maintenance cost ~ tiny; quality ceiling highest.

---

## 4. RECOMMENDATION (evidence-based)
1. **Immediately test VoiceTut-TTS** — it is the single most promising find: purpose-
   built Egyptian, native code-switching, commercial-safe, T4-ready, with cloning +
   built-in studio voices. It could satisfy BOTH your "one engine" wish (Option B)
   AND the Arabic-quality bar.
2. **Hear it decide the architecture:**
   - If VoiceTut's English + cloning is drama-grade → **unify on VoiceTut (Option B)** —
     simplest, your preference.
   - If VoiceTut nails Arabic but English is flat → **split: Chatterbox EN + VoiceTut
     AR (Option C)** — highest quality.
3. **Keep Chatterbox** either way (English cast or full) — it's genuinely best-in-class
   English and MIT.
4. **Fine-tune later (optional Tier-2):** whichever Arabic engine we pick, a LoRA on
   a few hours of the target Egyptian voice pushes it to bespoke, nobody-else-has-it
   quality. VoiceTut and SILMA are both fine-tunable (F5/OmniVoice toolchains).

**We drop:** CosyVoice (no Arabic), Masri-Higgs & F5-EGY & XTTS & Fish (license/quality),
raw-Chatterbox-for-Arabic (insufficient alone).

---

## 5. Next concrete step
Build ONE Kaggle test that generates the SAME content three ways so the ears decide:
- **VoiceTut** → Egyptian Coach line (dialect + code-switch) → is the Arabic right?
- **VoiceTut** → an English cast line (cloned) → is English expressive enough?
- **Chatterbox** → same English line (same ref voice) → A/B the English.
Then the architecture (B vs C) is obvious from listening, not theory.

_All license facts checked against HF model cards / project docs, Sep 2026._
