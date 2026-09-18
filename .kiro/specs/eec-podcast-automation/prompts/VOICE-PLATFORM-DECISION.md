# Two Worlds — Voice PLATFORM Decision (the strategic call)

> This is a MULTI-YEAR production platform, not a podcast voice. It must scale to a
> big cast: kids/young/old, men/women, Egyptian + Gulf + Levantine + all-Arab, and
> English in multiple accents — all HUMAN-feeling, emotional, reactive (laughs,
> surprise, warmth) because the mission is "learn with fun." The model choice now
> decides how easy everything is for years. I (Kiro) own this decision.

## The hard constraint that eliminates most "best" models
The show is **bilingual with heavy Arabic**. That single requirement rules out the
most expressive models on the market:
- **DramaBox** (Resemble) — the BEST emotional/"direct-a-scene" model (laughs, sighs,
  whispers from a plain-language prompt). But **English-ONLY by design.** ❌ Arabic.
- **MOSS-TTSD** — 60-min multi-speaker dialogue, cloning, Apache-2.0, beat Gemini-2.5
  in subjective tests. But **English + Chinese only.** ❌ Arabic.
- **Maya 1 / Parler-Expresso / StyleTTS2** — strong emotion, but English/EU-centric,
  no real Arabic. ❌
- **XTTS v2 / F5 base / Fish** — non-commercial licenses. ❌ (paid channel)

So the field that is BOTH great-at-Arabic AND commercial-safe AND fine-tunable is
small. That's why this needs a deliberate platform pick, not a vibe.

## The decision: a TWO-ENGINE platform, each fine-tunable, split by language
No single open model is simultaneously best at expressive Egyptian/Arab-dialect
Arabic AND expressive multi-accent English under a commercial license. Forcing one
model to do both = mediocre at both. The professional answer is a clean split, and
BOTH halves are chosen to be **fine-tune-able** so we reach Kore-quality and beyond:

### 🎙️ ARABIC half (all dialects) -> VoiceTut / OmniVoice family, fine-tuned
- Egyptian-first, native AR<->EN code-switch, cloning, built-in Egyptian text
  normalizer, Apache-2.0, runs on T4. Owner already likes it (just below Kore).
- **Fine-tunable** on the OmniVoice/F5 toolchains -> we train it to Kore-level and
  add Gulf/Levantine/kids/old voices over time by adding data per voice.
- SILMA-TTS (also F5, Apache-2.0, bilingual, has CATT+NeMo built in) is the sister
  option / fallback and is explicitly F5-finetune-compatible.

### 🎙️ ENGLISH half (all accents) -> Chatterbox family, fine-tuned
- Best-in-class expressive English (beat ElevenLabs), MIT, emotion control
  (exaggeration + [laugh]/[chuckle] on Turbo), cloning, **fine-tune toolkits exist
  (LoRA)**. Add American/British/etc. voices as cloned refs or light finetunes.
- Chatterbox Nano/Flash (just announced) give edge/speed variants if needed.

### Why split is EASIER long-term (not harder)
- Each engine stays best-in-class for its language; we never fight a model to do a
  language it's weak at.
- Adding a new character = add a reference clip (cloning) or a small LoRA — on
  whichever engine matches the language. Scales cleanly to a big cast.
- One Kaggle batch can load both; the script already tags each line's language, so
  routing to the right engine is automatic.

## How we reach "Kore quality and better" — the pipeline, not just the model
Owner is right: it's the PIPELINE. For EACH engine we apply the full stack:
1. **Text front-end**: dialect-correct diacritization + Egyptian/Gulf normalization
   (numbers, clock, names) + code-switch segmentation. (VoiceTut has much of this;
   we extend per dialect.)
2. **Fine-tune** on the target voice(s): LoRA on clean Egyptian/target audio ->
   bakes in dialect + timbre + Kore-level naturalness. Repeatable per new voice.
3. **Generation controls**: per-line emotion/exaggeration, cfg tuning, sentence
   chunking + VAD trailing-trim (kills the noise/hallucination artifacts).
4. **Post**: loudnorm, light polish.

## Where the training data comes from (the clever, honest part)
- **Kore recreation:** we still have Gemini Kore access. Generate a clean Egyptian
  dataset with Kore, then fine-tune the Arabic engine to BECOME that voice ->
  unlimited, free, self-owned "Kore" forever. (Owner loved Kore; this captures it.)
- **New cast voices:** clean reference clips (voice actors / licensed samples /
  recordings). Cloning first; LoRA fine-tune for the recurring lead voices.
- Kids/old/dialect voices added incrementally as the production grows.

## Decisions LOCKED (so we stop re-deciding)
- Platform = **two fine-tunable engines, split by language**: Arabic = VoiceTut/
  OmniVoice (SILMA fallback); English = Chatterbox. Both Apache/MIT, both on Kaggle.
- Quality path = **front-end + fine-tune + generation-controls pipeline**, per engine.
- First proof = **fine-tune the Arabic engine to Kore-level** (Kore-recreation data).
- Emotion/"fun": Chatterbox emotion tags for English now; evaluate DramaBox for
  English drama later (English-only, so it CAN slot into the English half if we want
  maximum drama); for Arabic, expressiveness comes via reference style + fine-tune.

_All license/capability facts verified against model cards + papers, Sep 2026._
