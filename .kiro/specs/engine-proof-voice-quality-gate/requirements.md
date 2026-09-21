# Engine Proof / Voice-Quality Gate — Requirements

> **Origin:** owner GATE-C listen verdict ("it's shit and we are getting far") triggered a
> full pipeline audit + a series of root-cause fixes (FIX-006 through FIX-009). Those fixes
> proved individual bugs, but the owner correctly stopped further episode work to demand
> something stronger: **prove the MODELS themselves — independent of any specific episode
> script — can produce sustained, multi-character, human-sounding audio before we spend any
> more effort writing/producing episodes on top of them.**
>
> **Owner's own words (verbatim, the north star for this spec):**
> *"the most important are our models... i want to prove they are working fine before we use
> them to generate our podcast... the voice tut we have to work on it to generate 5 minutes
> of egyptian arabic without problem thats a success criteria and also qwen to generate 5
> minutes of english american accent... for every 5 minutes we use 3+ characters mix of male
> and female... the voice has to be human and natural and competes elevenlabs... script has
> to be human."*
>
> This is a **gate**, not a feature. Nothing in Phase D (batch-producing Episodes 2-10) may
> proceed until this gate passes. See `design.md` for the verified technical approach and
> `tasks.md` for the execution plan.

## Vision
Before any more episode content is produced, prove — with objective diagnostics AND the
owner's own ear — that our two production language-pairs (script-writing engines, voice
-synthesis engines) can each sustain 5 continuous minutes of natural, multi-character,
non-robotic audio. This is the foundation every future episode stands on; get it right once,
here, deliberately, rather than discovering it's wrong episode-by-episode.

## Background — what's already true (do not re-litigate)
- **VoiceTut** is the sole, locked Arabic engine (Qwen3-TTS has no Arabic in its codec
  vocabulary; MOSS-TTSD's docs list Arabic but that is an unverified, unaudited, OPEN
  QUESTION — not in scope for this gate).
- **Mahmoud's voice is already re-cast and diagnostically verified**: `Essam` @
  `guidance_scale=1.5` (FIX-008) scores UTMOS 3.62 in-episode (was 3.03), zero flagged lines
  on the full Ep1 re-diagnose. This is the CURRENT best VoiceTut configuration and this
  gate's Arabic stress test should confirm it holds over a full 5-minute, multi-character
  sample — not re-run the voice audition from scratch.
- **Qwen3-TTS VoiceClone** is the locked, production English engine (Nour + 6 guests + Ravi,
  all frozen `voice-refs/*.wav`).
- **MOSS-TTSD** is an audited English CANDIDATE (Apache-2.0, native multi-speaker turn-taking
  in one generation, verified working on Kaggle T4×2 after a device_map fix) — not yet
  routed in production. This gate is the first fair, controlled comparison against Qwen3-TTS.
- **Two engines exist for scripting too**: DeepSeek (primary writer) and Qwen-text via
  OpenRouter (adversarial dialogue-polish critic, already wired and verified in
  `dialogue_polish.py`). This gate's scripts MUST be produced through that same two-engine
  pipeline — not a one-off hand-written test script — because the scripting pipeline is
  itself part of what's being proven.
- **The Diagnostic Pipeline** (`kaggle/diagnose_episode.py`: WhisperX + Parselmouth + UTMOS →
  DeepSeek report) is built and has already been run for real (Ep1 re-diagnose). This gate
  reuses it as the objective half of the pass/fail bar.

## Success criteria (the gate — ALL must hold)

### G1 — Two proof clips, not one episode
- G1.1 **Arabic proof clip:** ~5 continuous minutes, VoiceTut only, **3+ distinct
  characters, mixed gender** (at least one male + one female voice from the VoiceTut pool).
- G1.2 **English proof clip:** ~5 continuous minutes, **3+ distinct characters, mixed
  gender**, produced twice — once with Qwen3-TTS (production engine) and once with
  MOSS-TTSD (candidate) — from the SAME script, for a fair head-to-head.
- G1.3 Both clips are throwaway STRESS TESTS, not polished lesson content: they must
  deliberately exercise the boundaries each engine is known (or suspected) to struggle with
  — see G4.

### G2 — Script quality (proven, not assumed)
- G2.1 Every proof-clip script is generated through the real two-engine scripting pipeline:
  DeepSeek writes, Qwen-text (`dialogue_polish.py`) adversarially polishes. The polish
  report (reviewed/flagged/applied counts) is captured as evidence.
- G2.2 The script-writing prompt must be **engine-aware** (see `design.md` §"Performance
  cues, engine-specific") — it must NOT rely on generic bracketed cues like `[sigh]` that
  our verified engine capabilities show neither engine actually consumes as a modifier.
- G2.3 Coach/Arabic diacritized text is never touched by the adversarial critic beyond an
  optional delivery-note suggestion (protects FIX-004/FIX-009 — this is already enforced in
  `dialogue_polish.py` and must not regress).

### G3 — Objective diagnostic bar
- G3.1 Every proof clip is run through `diagnose_episode.py` (WhisperX + Parselmouth +
  UTMOS). Per-clip **mean UTMOS ≥ 3.7** (the target the owner and the diagnostic pipeline
  already converged on for Mahmoud/FIX-008) and **zero lines flagged** `low_naturalness_mos`
  or `monotone_low_pitch_variation`.
- G3.2 CER/pronunciation sanity via the ASR-QA path (ratio ≥ 0.5 after brand/orthography
  normalization, per FIX-006/FIX-009) — catches script-spelling regressions like
  هنعيش/دبي before they reach the owner's ear.
- G3.3 The diagnostic numbers are evidence FOR the owner's ear-test, never a substitute for
  it (see G5). A clip that passes G3 but fails G5 still fails the gate.

### G4 — Stress-test coverage (per engine, so the test actually finds boundaries)
- G4.1 **VoiceTut (Arabic) stress test must include:** rapid style/energy shifts between
  consecutive lines (calm↔energetic), heavy Arabic↔English code-switching mid-sentence
  (Egyptian colloquial pattern, e.g. "عندي meeting بكرة"), and at least one drill/imperative
  exchange (the pattern that produced FIX-008's worst-scoring lines historically).
- G4.2 **Qwen3-TTS / MOSS-TTSD (English) stress test must include:** rapid pace/register
  shifts (calm conversational → excited/loud), written-in emotion via text semantics rather
  than bracket tags (e.g. "Wait — no way..." not "[shocked] No way"), overlapping/interrupted
  turns between 3+ speakers, and genuine questions/reactions (not declarative monologue).
- G4.3 Both stress tests are designed to `design.md`'s engine-capability findings — cues that
  the verified API surface can actually act on, not cues borrowed from ElevenLabs-style docs
  that don't apply to our engines.

### G5 — The owner's ear is the final verdict
- G5.1 Bar (owner's own framing, locked): **"5 minutes of frictionless, non-robotic
  listening"** — NOT literal ElevenLabs-parity on theatrical acting (crying, heavy sighs,
  whispering); WE compete on **authenticity** (real Egyptian code-switching, real regional
  English accents) rather than dramatic range.
- G5.2 Each proof clip gets an explicit owner verdict: pass / fail / conditional, with
  specific timestamped notes on anything that breaks immersion — fed back into the fix loop
  exactly like FIX-001 through FIX-009 (root-cause, permanent, logged in
  `episode-fixes-log.md`), never a one-off patch.
- G5.3 For the English head-to-head, the owner's verdict also decides whether MOSS-TTSD
  becomes a routed production engine, stays a documented candidate, or is dropped — this
  spec does not pre-decide that outcome.

### G6 — Cast audition coverage
- G6.1 Before generating the proof clips, confirm (or re-confirm) which VoiceTut voices
  (male + female) and which Qwen3-TTS characters best serve a MIXED-GENDER 3+ cast — reusing
  the audition methodology from FIX-008 (UTMOS-scored, ranked, owner ear-confirmed) rather
  than picking voices by assumption.
- G6.2 If a female VoiceTut voice hasn't yet been diagnostically scored (all FIX-008
  auditions were male), this gate is the first opportunity to do so — do not assume parity.

## Non-goals (for this gate)
- Auditioning MOSS-TTSD (or anything else) for ARABIC. VoiceTut stays the sole Arabic
  engine for this gate; the Arabic-support listing on MOSS-TTSD's docs is logged as an open
  question for a future, separate decision.
- Producing new episode content. The proof clips are throwaway stress tests; they do not
  become Episode 1 material and are not required to follow the series bible's story
  structure (cold_open/coach_break/etc.) — only its VOICE/brand rules where relevant.
- Video, music, mastering, or any Phase-C.5/Virtual-Studio concern. This gate is audio-only,
  voice-only.
- Re-deciding Best-of-N seed sampling (already tested and dropped — VoiceTut's
  `synthesize()` has no seed parameter; see `episode-fixes-log.md` FIX-009 section) or
  VoiceTut style tags (already tested and found cosmetic-only; see the capability-probe
  findings in `design.md`).

## Definition of done
This gate is DONE when both proof clips exist, both have passed G3's objective diagnostic
bar, and the owner has given an explicit pass verdict on G5 for both the Arabic clip and
(at least) one English engine. Only then may Phase D (batch Episodes 2-10) resume.
