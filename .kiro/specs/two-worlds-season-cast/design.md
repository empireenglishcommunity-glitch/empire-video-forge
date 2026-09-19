# Two Worlds — Season Production & Actor-Cast — DESIGN

> Implements `requirements.md`. Describes the architecture, data schemas, notebooks,
> and gates for season-level production with a Qwen3-TTS actor cast. Arabic engine
> (VoiceTut) unchanged. Status: DRAFT for owner review — nothing executed until approved.

## 1. High-level architecture

```
[Season plan: season.json]  (10 episodes, situations, cast registry, Macal stage map)
     |
     v
(A) SCRIPTS   gen_episode.py (short 5-10 min, structure+duration gates) x10  -> owner review
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
- V4. **Reproducibility:** confirm a voice is stable across runs via a **seed** and/or a
  fixed voice-design spec (so an actor sounds the same every episode).
- V5. **Kaggle install recipe:** exact pip/deps, GPU/VRAM needs, torch compatibility
  (validate to avoid the Chatterbox "--no-deps / silent-fail" class of problem).
- V6. **Output format/rate** for clean handoff to the existing 24 kHz mono manifest/
  assembly chain.

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
        "1": { "voice_design": "Egyptian young man, late 20s, learner-level English, clear Egyptian accent, a little hesitant, warm/earnest", "seed": 0 },
        "2": { "voice_design": "same man, more fluent, accent softening, more confident", "seed": 0 },
        "3": { "voice_design": "same man, confident, near-native American English, warm", "seed": 0 }
      },
      "stage_map": { "1": [1,2,3], "2": [4,5,6,7], "3": [8,9,10] },   // episode -> stage
      "status": "pending-audition"
    },
    "Nour": {
      "engine": "qwen3tts", "lang": "en", "role": "guide/friend",
      "voice_design": "native American-born woman, warm, clear, confident, pure American accent",
      "seed": 0, "status": "pending-audition"
    },
    "TaxiDriver": {
      "engine": "qwen3tts", "lang": "en", "role": "Dubai taxi driver",
      "voice_design": "middle-aged Indian man, Indian English accent, friendly, easygoing",
      "seed": 0, "status": "pending-audition"
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
- `voice_design` is the exact field name Qwen3-TTS uses (confirmed in V2); `seed`
  ensures reproducibility (V4).
- **Macal** resolves to a concrete voice per episode via `stage_map` (episode → stage
  → that stage's `voice_design`+`seed`).
- Non-Macal English characters have a single fixed `voice_design`+`seed`.

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

## 4. Notebooks (Kaggle, owner-run)
- `kaggle/audition_qwen.py` — NEW. For each character, generate 3-4 candidate
  voice-designs (Macal: the 3 arc stages) reading real Season-1 lines; emit labeled
  clips + a zip. Pure audition; writes no cast state.
- `kaggle/synth_episode_en_qwen.py` — NEW (replaces `synth_episode_en.py`). Reads
  `cast.json`, routes each English line to its character's designed voice; for Macal,
  picks the stage from `stage_map` given the episode number. Writes `lineNNN_*.wav` +
  a pass manifest, same contract as today.
- `kaggle/synth_episode_ar.py` — UNCHANGED (VoiceTut; Coach lines).

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
| Qwen3-TTS accent fidelity (Egyptian/Indian/American) uncertain | Audition proves each accent before commit; iterate descriptions; accept closest good option |
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
