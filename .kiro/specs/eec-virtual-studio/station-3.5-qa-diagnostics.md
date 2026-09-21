# Station 3.5 — Automated QA / Diagnostics

> Part of the [EEC Virtual Studio](architecture.md). Turns subjective "it sounds off"
> into **measured, timestamped, explained** diagnostics — so QA scales to Phase D's 9
> episodes (and future seasons) instead of relying on the owner's ear alone, and so every
> defect feeds the `episode-fixes-log.md` + phonetic maps automatically.
>
> **Status:** ✅ BUILT AND RUN FOR REAL (superseding the "scheduled after GATE C" plan below
> — the GATE-C crisis made this urgent immediately). `kaggle/diagnose_episode.py` implements
> WhisperX + Parselmouth + UTMOS (chosen over NISQA specifically for its non-commercial
> licensing risk, exactly per the caveat below) → DeepSeek report. First real run diagnosed
> Ep1 and objectively found the root cause of the owner's "it's shit" verdict (Mahmoud/
> VoiceTut UTMOS 3.03 vs. 4+ for every other voice) — see `episode-fixes-log.md` FIX-008.
> Now reused as the objective half of the Engine Proof / Voice-Quality Gate
> (`.kiro/specs/engine-proof-voice-quality-gate/`). The architecture below (as originally
> designed) matches what was actually built.

## Why (owner + developer vision)
Ep1 QA today = the owner listens and reports issues. That works for one episode but doesn't
scale and is subjective. A diagnostic pipeline takes the assembled audio, analyzes it
tool-by-tool, and emits a plain-language report ("line 16: flat pitch 3s → add a breath;
'water' rendered true-T, should be flap-T → phonetic-map it"). It makes the system *learn*.

## Architecture — orchestrate several tools (no single magic model)
```
episode audio + timeline.master.json
        │
   ┌────┴─────────────────────────────────────────────┐
   │ per-line analysis (each line WAV + its text)      │
   │  • WhisperX      → word-level timestamps (WHERE)  │
   │  • Parselmouth/Praat → pitch/prosody (monotone?,  │
   │                     unnatural pauses) (HOW)        │
   │  • pacing metric → words/sec vs target band       │
   │  • [later] MFA   → phoneme align (flap-T vs true-T,│
   │                     connected speech) (WHAT sound) │
   │  • [eval] MOS naturalness (see licensing note)     │
   └────┬─────────────────────────────────────────────┘
        │  features per line
        ▼
   DeepSeek (our existing LLM) → DIAGNOSTIC REPORT (JSON + prose):
     per line: {score, issues[], suggested_fix, fix_subsystem}
        │
        ▼
   feeds → episode-fixes-log.md rows (auto-drafted) + a MOS/pacing GATE
```

## Tool shortlist — license-VERIFIED (this session)
| Tool | Job | Code license | **Weights/usage caveat** | Verdict |
|---|---|---|---|---|
| **WhisperX** | word-level timestamps (pinpoint the second) | BSD-2 | model weights permissive | ✅ adopt |
| **Parselmouth (Praat)** | pitch/prosody — flat/monotone + pause analysis | GPL-3.0 | run server-side only (don't bundle) | ✅ adopt (analysis-only) |
| **Montreal Forced Aligner (MFA)** | phoneme alignment (flap-T vs true-T, connected speech) | MIT | Kaldi-based, heavy | ✅ adopt LATER (deepest, heaviest) |
| **pacing metric** | words/sec vs target band (already used in FIX-001) | ours | — | ✅ use now (cheap) |
| **NISQA / NISQA-TTS** | MOS naturalness score + why | MIT code | ⚠️ **model WEIGHTS = CC BY-NC-SA 4.0 (NON-COMMERCIAL)** | ⚠️ **INTERNAL QA ONLY** — never bundle/ship the weights or its output; evaluating our own audio internally is acceptable, but flag it |
| **Turing ARC-Speech-Quality-LLM** | MOS + natural-language explanation (matches the "report" idea) | check at adoption | newer/less proven | 🔬 evaluate as the report engine |
| **DeepSeek (ours)** | fuse features → written diagnostic report | MIT (open) | live on server | ✅ the report brain |

### ⚠️ Licensing decisions (honest)
- **NISQA weights are non-commercial (CC BY-NC-SA).** Same class as MusicGen (which we
  rejected). Difference: NISQA would be an **internal measurement tool**, not part of the
  shipped product — we score our own clips, we don't distribute NISQA or embed its output.
  That's defensible, but to stay clean: **(a) never bundle NISQA weights into any shipped
  artifact, (b) prefer a commercial-safe MOS model if one is good enough.** Evaluate at
  build time: **UTMOS / DNSMOS / SpeechMOS** (torch-based, often permissive) as commercial-
  safe MOS alternatives before defaulting to NISQA.
- **Parselmouth/MFA (GPL/MIT):** fine to run server-side for analysis (output = numbers, not
  a derivative work). Don't statically bundle GPL code into distributed software.

## Gate & feedback loop (the payoff)
- **MOS/pacing GATE:** an episode can require e.g. every line ≥ target pace band + naturalness
  threshold before it ships — "CI for audio."
- **Auto-feeds the fix system:** the DeepSeek report drafts `episode-fixes-log.md` rows and
  proposes the fix subsystem (lexicon / english_phonetic_map / assemble gap / cast param /
  reword), so recurring issues become permanent guardrails with less manual triage.

## Build plan (after GATE C)
1. `pipeline/diagnose_episode.py` — takes an assembled episode, runs WhisperX + Parselmouth
   + pacing per line, dumps `diagnostics.json`.
2. Add MOS: evaluate a **commercial-safe** MOS model first; fall back to NISQA (internal-only)
   if needed.
3. DeepSeek pass → human-readable `diagnostic_report.md` + auto-drafted fix-log rows.
4. Wire a soft GATE into `run_podcast.py` (report-only first; hard threshold once trusted).
5. MFA phoneme layer last (heaviest) — for accent-precision (flap-T etc.).

## Relationship to current work
- The FIX-001 Macal calibration uses the **pacing metric** piece of this station **now**
  (objective words/sec alongside the owner's ear) — a proven down-payment.
- Full station is built after Ep1 is approved, so Phase D's 9 episodes get automated QA.
