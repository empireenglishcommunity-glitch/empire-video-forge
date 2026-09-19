# Two Worlds — Season Production & Actor-Cast (SPEC)

Formal spec for moving Two Worlds to **season-level production** with a repertory of
designed **Qwen3-TTS** actor voices (English) + VoiceTut (Arabic, Coach = **Mahmoud**).

**Status: DRAFT for owner review. Nothing is executed until the owner approves.**

## Read in this order
1. [`requirements.md`](./requirements.md) — goals, casting philosophy (realism +
   pedagogy), functional/non-functional requirements, constraints, acceptance criteria.
2. [`design.md`](./design.md) — architecture, engine facts to verify, `cast.json`
   schema v2 (Macal's 3-stage arc), `season.json`, notebooks, gates, risks.
3. [`tasks.md`](./tasks.md) — phased implementation plan + the live task list
   (Phases 0-E), owner-vs-agent split, and the gate checklist.

## Headline decisions (owner-approved in planning)
- **Scriptwriting → DeepSeek (R1 + V3)** via the existing OpenRouter free tier (better
  dramatic writing; a config change, not a new dependency).
- English voice engine → **Qwen3-TTS** (Apache-2.0, commercial-safe, no reference clips,
  voice-design), **locked as the sole English engine**. Arabic engine (VoiceTut)
  **unchanged**. Fish Audio S2 Pro was **evaluated and rejected** (non-commercial
  self-host license / fragile free API) — not used anywhere.
- Coach renamed **Mahmoud** (introduces himself by name; voice "Sayed" kept).
- **Voice consistency = Option B (VoiceClone from self-generated refs):** invent each
  voice via VoiceDesign in the audition, save a canonical ~10-15s WAV, then clone from it
  in production to lock pitch/timbre across all 10 episodes. Per-line `direction` drives
  emotion on top.
- **Macal** = Egyptian-**L2**-accented English, **3 evolving stages** across the season
  (explicit acoustic-marker prompts + script-level L2 reinforcement).
- **Nour** = native American-born (pure American accent — the taught target).
- **TaxiDriver** = Indian English (realism: Dubai drivers are typically South-Asian).
- Work at **season level**: write + approve all 10 scripts, then cast everyone once.

## Relationship to the base spec
This builds on `.kiro/specs/eec-podcast-automation/` (the short-episode format,
structure + duration gates, manifest-driven assembly). Those gates are reused unchanged.
