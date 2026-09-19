# Two Worlds — Season Production & Actor-Cast — DESIGN

> Implements `requirements.md`. Describes the architecture, data schemas, notebooks,
> and gates for season-level production with a Qwen3-TTS actor cast. Arabic engine
> (VoiceTut) unchanged. Status: DRAFT for owner review — nothing executed until approved.

## 1. High-level architecture

```
[Season plan: season.json]  (10 episodes, situations, cast registry, Macal stage map)
     |
     v
(A) SCRIPTS   gen_episode.py + DeepSeek R1(beats)/V3(dialogue) via OpenRouter,
              short 5-10 min, structure+duration gates, x10  -> owner review
     |
     v
(B) CAST      derive full cast from 10 scripts
              -> Qwen3-TTS voice-design candidates (audition) -> owner picks -> cast.json LOCKED
     |
     v
(C) SYNTH     English -> Qwen3-TTS (per-character designed voice; Macal stage by episode)
              Arabic  -> VoiceTut ("Sayed" = Mahmoud, unchanged)
              -> manifest -> assemble_audio (gates) -> deliver plain audio -> owner
```

Two engines, one manifest pipeline:
- **English → Qwen3-TTS** (Apache-2.0, Alibaba). Voice = a **designed identity**
  (text description + seed), reproducible per character across episodes.
- **Arabic → VoiceTut** (unchanged). Coach voice "Sayed", character named **Mahmoud**.
- Both feed the existing **manifest** (`manifest_lib.py`), assembled by
  `assemble_audio.py` behind the **structure gate** + **duration gate**.

## 2. Engine facts to VERIFY before building (Phase B, Task B1)
> These are assumptions to confirm against Qwen3-TTS primary docs BEFORE committing.
> The audition exists precisely to de-risk them.
- V1. **Model + license:** Qwen3-TTS (0.6B / 1.7B), Apache-2.0, self-hostable. Pick the
  variant that fits a Kaggle T4 with best quality (1.7B preferred).
- V2. **Voice creation mode:** confirm **voice-design / natural-language voice control**
  (describe a voice in text) works WITHOUT a reference clip. Capture the exact API.
- V3. **Accent control:** confirm it can render **Egyptian-accented English**, **Indian
  English**, and **native American** convincingly, and how to specify each. Confirm
  whether "accent strength / fluency" is dial-able enough to express **Macal's 3-stage
  arc** (or whether we express the arc via 3 distinct descriptions).
- V4. **Voice identity method — Option B is the STANDARD (owner-decided).**
  Pure text `voice_design`+seed re-parses the description on every call and can drift
  subtly in pitch/timbre across episodes. So:
  - **Phase B (audition):** use Qwen3-TTS **VoiceDesign** to *invent* each character's
    voice from natural-language descriptions (candidates the owner picks from).
  - **Phases C & D (production):** save the approved audition output as a clean
    **~10-15s canonical reference WAV** per character (`voice_ref`), and synthesize with
    Qwen3-TTS **VoiceClone** against that ref. This **locks pitch/timbre 100% across all
    10 episodes** and is faster on the T4.
  - The reference is **self-generated** (produced by Qwen3-TTS in the audition), not
    supplied externally.
  - **Macal's 3 stages** → save **3 canonical refs** (one per stage); the episode's
    stage selects which ref to clone from.
  - Still confirm in B.1 that VoiceClone reproduces the ref faithfully run-to-run.
  - *(Option A — pure design+seed — is retained only as a documented fallback if
    VoiceClone underperforms VoiceDesign on quality.)*
- V5. **Kaggle install recipe:** exact pip/deps, GPU/VRAM needs, torch compatibility
  (validate to avoid the Chatterbox "--no-deps / silent-fail" class of problem).
- V6. **Output format/rate** for clean handoff to the existing 24 kHz mono manifest/
  assembly chain.

## 2b. Scriptwriting engine — DeepSeek (R1 + V3)
Scripts are authored with **DeepSeek** via the existing OpenRouter free tier — a
**config change to `llm_backend.py`, not a new dependency**. That module already selects
models by env (`EEC_LLM_MODEL`), supports a comma-separated fallback list
(`EEC_LLM_FALLBACKS`), and has a `reasoning.enabled` toggle for reasoning models.
- **Two-pass authoring (recommended):**
  - **R1 (reasoning)** → plan the episode: story beats, the scene→coach structure, the
    2-3 target phrases, the cliffhanger. (`reasoning.enabled = true` for this pass.)
  - **V3** → write the natural spoken dialogue from R1's plan (fast, fluent), and emit a
    short **per-line `direction`** (acting note, e.g. "calm, reassuring" / "anxious,
    rapid") that Qwen3-TTS consumes for emotional delivery (see §3.3).
- **Config (illustrative; exact model strings confirmed at adoption):**
  `EEC_LLM_MODEL=deepseek/deepseek-r1:free`,
  `EEC_LLM_FALLBACKS=deepseek/deepseek-chat-v3:free, meta-llama/llama-3.3-70b-instruct:free, qwen/qwen-2.5-72b-instruct:free`.
- **Free-tier resilience (REQUIRED):** OpenRouter free DeepSeek endpoints hit strict
  concurrency/429s and queue timeouts. `gen_episode.py` must have robust **retry with
  exponential backoff + jitter** (≥5 attempts) AND rotate across the fallback list of
  **high-capacity** free models (Llama-3.3-70B, Qwen-2.5-72B) so a rate-limit never
  blocks a run. Verify the current backoff/rotation meets this (it has rotation; add
  jitter/backoff if missing).
- **Optional paid escape hatch (documented, not default):** a direct DeepSeek API key
  (~$0.001/script; ~$0.01 for a 10-episode run) if free-tier reliability is
  insufficient. Kept optional to preserve the $0 default.
- **Commercial-safe** (DeepSeek R1/V3 are MIT/open), **$0** on the free tier, fallbacks
  keep runs unblocked. Output still passes the **structure** + **duration** gates.
- `gen_episode.py` may gain an optional two-pass mode (beats→dialogue); if not, a
  single strong model (R1 or V3) is used with the existing prompts. Decided at build.

## 3. Data schemas

### 3.1 `cast.json` (schema v2)
Adds a Qwen3-TTS voice-design model for English and a multi-stage model for Macal.
```jsonc
{
  "engines": {
    "voicetut":  { "role": "arabic",  "note": "Coach = Sayed; unchanged" },
    "qwen3tts":  { "role": "english", "model": "<verified id>", "note": "voice-design; Apache-2.0" }
  },
  "cast": {
    "Mahmoud": {                       // the Coach, renamed
      "engine": "voicetut", "voice": "Sayed", "lang": "ar",
      "role": "the teacher/host", "display_name": "Mahmoud",
      "num_step": 64, "guidance_scale": 2.5, "speed": 1.0, "status": "locked"
    },
    "Macal": {                         // EVOLVING — 3 stages
      "engine": "qwen3tts", "lang": "en", "role": "learner-hero",
      "stages": {
        "1": { "voice_design": "young adult male, native Arabic speaker from Cairo speaking English, clear Egyptian L2 accent, rolled r's, crisp T sounds, slightly slow deliberate pacing, earnest", "voice_ref": "voice-refs/macal_s1.wav", "seed": 0 },
        "2": { "voice_design": "same man, more fluent, Egyptian accent softening, more confident", "voice_ref": "voice-refs/macal_s2.wav", "seed": 0 },
        "3": { "voice_design": "same man, confident, near-native American English, warm", "voice_ref": "voice-refs/macal_s3.wav", "seed": 0 }
      },
      "stage_map": { "1": [1,2,3], "2": [4,5,6,7], "3": [8,9,10] },   // episode -> stage
      "status": "pending-audition"
    },
    "Nour": {
      "engine": "qwen3tts", "lang": "en", "role": "guide/friend",
      "voice_design": "native American-born woman, warm, clear, confident, pure American accent",
      "voice_ref": "voice-refs/nour.wav", "seed": 0, "status": "pending-audition"
    },
    "TaxiDriver": {
      "engine": "qwen3tts", "lang": "en", "role": "Dubai taxi driver",
      "voice_design": "middle-aged Indian man, Indian English accent, friendly, easygoing",
      "voice_ref": "voice-refs/taxidriver.wav", "seed": 0, "status": "pending-audition"
    }
    // ... + full season roster derived from the 10 scripts, each cast by realism
  },
  "casting_principles": {
    "realism": "cast by who realistically holds the role in Dubai (origin/accent/age)",
    "pedagogy": "American is the taught target; natives model it; Macal is the learner arc"
  }
}
```
Notes:
- **Two fields per English character:** `voice_design` (the natural-language
  description used at AUDITION to invent the voice) and `voice_ref` (the canonical
  ~10-15s WAV, self-generated from the approved audition, used in PRODUCTION via
  VoiceClone — see V4 / Option B). `seed` is retained for the fallback design path.
- **Production synth uses `voice_ref`** (VoiceClone) for pitch/timbre locking; the
  per-line `direction` still drives emotion on top of the cloned identity.
- **Macal** has **3 stage refs**: each stage stores its own `voice_design` + `voice_ref`;
  the episode resolves the stage via `stage_map`, then clones that stage's `voice_ref`.
- Non-Macal English characters have one fixed `voice_design` + `voice_ref`.
- `voice_ref` paths live under `voice-refs/` in the repo (self-generated; committed so
  Kaggle can fetch them), replacing the retired Chatterbox refs.

### 3.2 `season.json` (extended)
```jsonc
{
  "season": 1,
  "current_episode": 2,                // Ep1 already generated; reconciled in Phase A
  "episodes": [                        // the season plan (situations from series-bible)
    { "n": 1,  "title": "The Arrival",        "level": "A2", "situation": "airport + taxi" },
    { "n": 2,  "title": "The Apartment",      "level": "A2", "situation": "the landlord" },
    // ... through 10 ...
  ],
  "cast_registry": ["Mahmoud","Macal","Nour","TaxiDriver", "..."],  // filled after scripts
  "macal_stage_map": { "1":[1,2,3], "2":[4,5,6,7], "3":[8,9,10] },
  "story_so_far": "...",
  "phrases_taught": []
}
```

### 3.3 Script line schema (adds per-line acting `direction`)
Each script line gains an optional **`direction`** — a short natural-language acting note
that V3 (the scriptwriter) writes per line and that Qwen3-TTS consumes as an emotional/
delivery instruction. This turns every line into a directed performance.
```jsonc
{
  "section": "act1",
  "speaker": "Macal",
  "lang": "en",
  "text": "Wait — tonight? Like, an interview? Now?",
  "direction": "anxious, rising panic, speaking quickly"   // NEW — optional per line
}
```
Rules:
- `direction` is **optional**; if absent, the character's base `voice_design` (calm
  default) is used. If present, it is combined with the voice_design at synth time
  (identity from voice_design + emotion from direction).
- `direction` is a performance note only — it is **stripped from any on-screen text**
  and never spoken. The audio-cleaner already removes bracketed/parenthetical stage
  directions from `text`; `direction` lives in its own field so it's never read aloud.
- **VERIFY (safety):** the text-cleaner, **text_hash / manifest** builder, subtitle/
  timeline generator, and the structure+duration gates must read ONLY `text`/`speaker`/
  `section` and **ignore `direction` entirely**. A leak of `direction` into `text` would
  corrupt manifest alignment or gate checks. Add an explicit test asserting `direction`
  never reaches the synthesized `text` or the hash input.
- Arabic (Coach/Mahmoud, VoiceTut) currently ignores `direction` (VoiceTut has no
  natural-language emotion control); it applies only to Qwen3-TTS English lines.
- The structure + duration gates operate on `text`/`speaker`/`section` as before —
  `direction` does not affect them.

## 4. Notebooks (Kaggle, owner-run)
- `kaggle/audition_qwen.py` — NEW. For each character, generate 3-4 candidate
  voice-designs (Macal: the 3 arc stages) reading real Season-1 lines; emit labeled
  clips + a zip. Pure audition; writes no cast state. (Uses a neutral direction so
  candidates are compared on voice identity, not performance.)
- `kaggle/synth_episode_en_qwen.py` — NEW (replaces `synth_episode_en.py`). Reads
  `cast.json`, routes each English line to its character's designed voice; for Macal,
  picks the stage from `stage_map` given the episode number; passes the line's
  **`direction`** (if any) to Qwen3-TTS as the delivery instruction. Writes
  `lineNNN_*.wav` + a pass manifest, same contract as today.
- `kaggle/synth_episode_ar.py` — UNCHANGED (VoiceTut; Coach lines; ignores `direction`).

## 5. Gates (unchanged, applied every episode)
- **Structure gate** (`structure_check.py`, series-bible §10): cold_open pure story;
  Coach only in coach sections; canonical order. Enforced in generation + assembly.
- **Duration gate**: 5-10 min band, enforced at generation (`gen_episode.py`).
- **Manifest completeness gate**: assembly refuses unless every line rendered.

## 6. The Coach → Mahmoud rename (design)
- `cast.json`: key/display becomes **Mahmoud** (voice still "Sayed").
- Scripts: the Coach's self-introduction lines use the name Mahmoud (Arabic). The
  speaker id in scripts may stay `Coach` (role) with `display_name: Mahmoud`, OR switch
  to `Mahmoud` — decided at implementation to minimize churn in `structure_check`
  (which treats "Coach" as the teaching speaker). **Chosen approach:** keep speaker id
  `Coach` (so gates/pipeline are untouched) and add `display_name: "Mahmoud"`; only the
  spoken Arabic text introduces him as Mahmoud. This isolates the change to text + cast
  metadata.

## 7. Migration / retirement
- Chatterbox English path (`synth_episode_en.py`, `voice-refs/*.wav`) → archived
  (server `_abandoned_*` + kept in git history), removed from the active pipeline only
  AFTER the Qwen3-TTS cast is locked and Ep1 is re-synthesized + owner-approved.
- Ep1's current short audio (Chatterbox English) is superseded by the Qwen3-TTS re-synth.

## 8. Risks & mitigations
| Risk | Mitigation |
|---|---|
| **Macal's Egyptian L2 English accent** — "Egyptian man speaking English" may render as plain American (L2 transfer accents aren't native dialect profiles) | **Primary audition risk.** Use explicit **acoustic-marker** prompts (rolled r's, crisp T's, deliberate pacing, earnest tone) AND **script-level L2 reinforcement** (DeepSeek V3 writes slight L2 phrasing/hesitation — "Um, yeah... tonight?" — in Stage-1 lines). Validate early; if unachievable, decide a fallback with the owner |
| Qwen3-TTS accent fidelity (Indian/American) uncertain | Audition proves each accent before commit; iterate descriptions; accept closest good option |
| Macal's arc may be stepped, not smooth | Express arc as **3 distinct designed voices**, not a gradient; owner approves all 3 |
| Voice consistency across episodes | Lock `voice_design` + `seed`; audition verifies same-voice reproducibility |
| Kaggle setup for a new engine (install/VRAM) | Validate recipe against primary docs (V5) before owner runs; provide paste-safe cells |
| Scope (10 scripts + full cast) is large | Phased: scripts → cast → prove on Ep1 → then batch the rest; gates catch regressions |
| Owner GPU-only steps (audition/synth) | Clear cell-by-cell handoffs; agent verifies outputs after each |

## 9. Definition of done (design-level)
Matches requirements §8: 10 gate-passing scripts approved; `cast.json` locked with
approved Qwen3-TTS voices + Macal's 3 stages; Coach = Mahmoud; Ep1 re-synthesized on the
new cast, assembled in-band, delivered, owner-approved; commercial-safe; containers
untouched; shipped via PR.
