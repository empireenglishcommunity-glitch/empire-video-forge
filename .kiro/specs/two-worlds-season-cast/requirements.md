# Two Worlds — Season Production & Actor-Cast — REQUIREMENTS

> Spec for moving "Two Worlds" to **season-level production** with a **repertory of
> designed "actor" voices**. English voice engine switches to **Qwen3-TTS** (Alibaba,
> Apache-2.0); the Arabic engine (VoiceTut) is unchanged. The Coach becomes the named
> character **"Mahmoud."**
>
> Status: DRAFT for owner review. Nothing is executed until the owner approves.

## 1. Background & motivation
Two Worlds is a short (5-10 min) bilingual English-learning drama podcast for
Arabic speakers (see the base spec `.kiro/specs/eec-podcast-automation/`). Episode 1
was produced, but the owner's review found the cast voices weak/unnatural (except the
Arabic Coach) and not realistic. The owner wants to work like a **creator/showrunner**:
build a cast of distinct, consistent *actors* — each with its own voice identity — and
plan the show **by season** (all scripts + all casting decided together) rather than
episode by episode.

## 2. Goals
- G1. Replace the English TTS engine with **Qwen3-TTS** and use its **voice-design**
  to create distinct, reusable, consistent actor voices (no reference clips required).
- G2. **Cast every character** in Season 1 deliberately, for **realism** and
  **pedagogy** (defined below), and lock a season cast registry.
- G3. Give **Macal** (the learner-hero) an **evolving voice across 3 stages** so his
  English audibly improves over the season.
- G4. Produce Season 1 (10 short episodes) against the locked cast, keeping the
  existing structure + duration quality gates.
- G4b. Raise **writing quality** by authoring scripts with **DeepSeek (R1 + V3)** on the
  existing free LLM backend (better dramatic, serialized storytelling).
- G5. Keep everything **$0 recurring** (self-hosted on free Kaggle GPU) and
  **commercial-safe** (Apache-2.0 engines only).
- G6. Rename the Coach to **Mahmoud** — he introduces himself by name, not "Coach".

## 3. Casting philosophy (the two principles)
Every casting decision must satisfy both:
- **P1 — Realism.** A character sounds like a real person who would actually hold that
  role in Dubai (correct origin, accent, age, register). Examples: Dubai taxi drivers
  are typically **Indian/Pakistani** (→ Indian English), not Emirati.
- **P2 — Pedagogy.** The **target accent taught is American**. Native/fluent characters
  (e.g. Nour) model **pure American English**. The **learner journey** is embodied by
  **Macal**, who starts where the audience is (Egyptian-accented, imperfect English) and
  **improves across the season**, so learners see themselves in him and grow with him.

## 4. Functional requirements

### R1 — Season-level planning
- R1.1 Season 1 = **10 short episodes** (~5-10 min each; default ~7).
- R1.2 The **full set of 10 scripts** is generated and owner-approved **before** final
  casting, so the complete cast list is known and cast once.
- R1.3 A season plan + cast registry lives in `season.json` (episode list, situations,
  cast, Macal stage map, continuity/story-so-far).

### R1b — Scriptwriting engine (dramatic quality)
- R1b.1 Scripts are written with **DeepSeek (R1 + V3)** via the existing OpenRouter
  free tier — for stronger long-form, dramatic, soap-opera-style writing.
- R1b.2 Two-pass authoring (recommended): **R1 (reasoning)** plans the episode's story
  beats/structure; **V3** writes the natural spoken dialogue **and a short per-line
  acting `direction`** (emotional/delivery note) fed to Qwen3-TTS. Fallbacks (other free
  models) remain configured so a rate-limit never blocks a run.
- R1b.5 **Per-line `direction` field:** each line may carry a natural-language acting
  note (e.g. "angry, rapid" / "calm, reassuring"). It drives Qwen3-TTS emotional
  delivery for English lines, is never spoken/shown, and does not affect the gates.
  Voice **identity** stays fixed per character (voice-design + seed, Option A — no
  cloning); `direction` only varies **emotion** per line.
- R1b.3 This is a **configuration** of the existing `llm_backend.py` (model + fallback
  env vars) — no new engine dependency, still commercial-safe (DeepSeek = MIT/open) and
  $0 on the free tier.
- R1b.4 Every generated script still passes the **structure** and **duration** gates.

### R2 — Cast & voices
- R2.1 **Mahmoud (Coach)** — Arabic, VoiceTut voice "Sayed" (unchanged). Named Mahmoud
  in-script; introduces himself by name.
- R2.2 **Macal** — Egyptian-accented English, **3 evolving stages**:
  - Stage 1: learner-level, clear Egyptian accent, a little hesitant.
  - Stage 2: more fluent, accent softening, more confident.
  - Stage 3: confident, near-American (the season payoff).
  Warm, earnest throughout. Default stage→episode map: **S1=Eps1-3, S2=Eps4-7,
  S3=Eps8-10** (tunable).
- R2.3 **Nour** — **native American-born**, warm/clear/confident **pure American**
  English (a model of the target accent). Not British.
- R2.4 **TaxiDriver** — **Indian English**, middle-aged, friendly working-man warmth.
- R2.5 **Other guests** (Barista, Landlord, Interviewer, Official, Friends, etc.) —
  derived from the 10 scripts, each cast by **realism** (the accent/origin of who would
  truly hold that role in Dubai: American, Indian, Filipino, Arab, etc.).
- R2.6 Each English voice is a **Qwen3-TTS voice-design spec** (a text description +
  reproducibility params) stored in `cast.json`, so the same actor voice regenerates
  identically every episode.

### R3 — Audition & selection
- R3.1 An audition produces **3-4 candidate voices per character** (for Macal, **3 arc
  stages**), each reading **real Season 1 lines**, as labeled audio clips.
- R3.2 The **owner selects** one voice per character (and approves Macal's 3-stage
  arc); iteration on descriptions is supported until approved.
- R3.3 Selected voices are locked into `cast.json`.

### R4 — Production
- R4.1 English lines synthesized on **Qwen3-TTS** against the locked cast; **Macal's
  stage is chosen by the episode's position** in the season.
- R4.2 Arabic (Mahmoud/Coach) synthesized on VoiceTut as today.
- R4.3 Every episode passes the existing **structure gate** (story/teaching separation,
  series-bible §10) and **duration gate** (5-10 min).
- R4.4 Assembly + delivery use the existing manifest-driven pipeline unchanged.
- R4.5 **Ep1 is re-synthesized** on the new cast (Macal Stage 1) to match the season.

## 5. Non-functional requirements
- N1. **Commercial-safe:** only permissively-licensed engines — Qwen3-TTS (Apache-2.0),
  VoiceTut (Apache-2.0), DeepSeek R1/V3 (MIT/open, via OpenRouter). **No
  non-commercial-licensed models** — e.g. Breeze TTS 2 and Fish Audio S2 Pro (both
  research/non-commercial self-host licenses) and XTTS are explicitly excluded.
- N2. **$0 recurring:** self-hosted on free Kaggle GPU (T4); no paid API dependency.
- N3. **Consistency:** an actor's voice is reproducible across episodes (seed +
  fixed voice-design).
- N4. **Never disrupt** the 12 live server containers; heavy synth stays off-server.
- N5. **Reviewable:** short scripts + labeled audition clips so the owner can review
  everything without special tooling.
- N6. **Reversible:** the retired Chatterbox path is archived, not deleted, until the
  new cast is proven.

## 6. Constraints
- C1. Owner provides **no reference voice clips** — voices come from Qwen3-TTS
  voice-design (text-described), not cloning.
- C2. Arabic engine (VoiceTut) is **not to be touched**.
- C3. The agent **cannot run GPU** — all Kaggle synth/audition steps are owner-run.
- C4. Qwen3-TTS on Kaggle is **new to this project**; its exact voice-design/accent
  capabilities must be validated before commitments (see design risks).

## 7. Out of scope (for this spec)
- The "second issue" the owner deferred (story/writing changes beyond what season
  scripting covers) — handled separately after the cast is locked.
- Music, video, cover art, publishing — owner-owned, downstream, unchanged.
- Seasons beyond Season 1.

## 8. Acceptance criteria
- A1. 10 Season-1 short scripts generated, gate-passing, owner-approved.
- A2. `cast.json` locked with a Qwen3-TTS voice-design per character + Macal's 3 stages,
  every voice owner-approved via audition.
- A3. Coach renamed to Mahmoud across scripts/cast/lexicon.
- A4. Ep1 re-synthesized on the new cast, re-assembled (5-10 min, gate-passing),
  delivered, and owner-approved on listen.
- A5. All engines commercial-safe; 12 containers untouched; work committed via PR.
