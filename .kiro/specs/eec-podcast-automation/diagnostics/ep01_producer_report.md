# Ep1 Diagnostic — Producer Report (objective, tool-driven)

**Run:** autonomous Kaggle kernel `yalla-fluent-ep01-diagnose` (fresh FIX-007 regen) →
WhisperX (timestamps) + Parselmouth (pitch) + UTMOS (naturalness MOS) → DeepSeek report.

## Headline metrics
- **Mean UTMOS: 3.64 / 5** (min 2.42). 6 of 46 lines flagged — **all of them Coach/Mahmoud.**

| Speaker | Mean UTMOS | Verdict |
|---|---|---|
| Nour / Official / Tarek | 4.47–4.57 | ✅ excellent (Qwen) |
| **Macal** | **4.06** | ✅ FIX-007 worked — English hero sounds good |
| TaxiDriver (Ravi) | 3.73 | ✅ good |
| **Coach (Mahmoud)** | **3.03** | 🔴 the problem (worst line 2.42) |

## Root cause (DeepSeek verdict)
Systemic to the **Mahmoud / VoiceTut** voice, NOT the script. Signature = low UTMOS
paired with HIGH pitch_std (idx29 108Hz@2.46, idx27 73Hz@2.42) = **unstable/jittery
synthesis** ("thrashing pitch to fake intonation → uncanny valley"), worst on short
punchy drill/imperative lines. Mahmoud currently sounds like the least-human voice in the
room — fatal for a coach.

Arabic+English **code-switch drill lines** (idx 24, 27–29, 42–43) are the WORST offenders
(engine switches phoneme inventories mid-utterance, pitch controller destabilizes) — but
pure-Arabic Coach lines also sit 2.7–3.3, so code-switch *aggravates* a pre-existing
voice-quality problem, it doesn't create it.

## Top 3 fixes (ranked)
1. **Re-cast or re-tune the Coach voice** (root cause): try a different VoiceTut Arabic
   voice, or a different engine for Mahmoud; if locked, reduce pitch-range/expressiveness
   and slow delivery 5–10%.
2. **Fix the drill block first** (idx 23–31, 42–46) — the lines learners replay most.
3. **Consistent compression/EQ + shared pacing** across speakers to mask residual artifacts
   and stop tonal whiplash (Coach 50–108Hz vs Macal ~42Hz).

**Target: Coach ≥ 3.7 UTMOS to match the cast.**

## What this PROVES about the pipeline
- FIX-007 succeeded: Macal (the original "too fast/choppy" complaint) is now 4.06.
- The "it's shit" verdict was driven by ONE voice (Mahmoud/VoiceTut), not the whole episode.
- The diagnostic pipeline works: objective, timestamped, per-speaker, root-cause. This is now
  our permanent QA gate before any episode ships.
