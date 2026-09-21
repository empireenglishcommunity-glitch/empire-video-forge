# Engine Proof — Phase C generation manifest

Generated 2026-09-21, all three clips rendered autonomously via Kaggle (push/poll/pull).
Audio itself lives on the server (`/tmp/*.m4a`) and will be delivered to Drive in Phase E —
not committed to git (binary audio, large files). This manifest is the record of what ran.

## 1. Arabic proof clip (VoiceTut) — `ar_proof_clip.m4a`
- Kernel: `empireenglish/yalla-fluent-proof-arabic`
- Script: `scripts/arabic_stress_test.json` (96 lines, 663 words)
- Cast: Mahmoud→Essam (locked, gs1.5, atempo 0.80) | Esraa→Esraa (Phase A winner, gs1.5,
  atempo 0.85) | Nadia→Asmaa (Phase A 2nd place, gs1.5, atempo 0.85)
- Result: **96/96 lines rendered, 333.99s (~5.6 min)**
- Pipeline: natural text (no injected pauses, FIX-007 discipline) → VoiceTut synth →
  ffmpeg atempo post-processing → concat with 0.35s gaps

## 2. English proof clip — Qwen3-TTS (production engine) — `en_qwen_proof_clip.m4a`
- Kernel: `empireenglish/yalla-fluent-proof-english-qwen`
- Script: `scripts/english_stress_test.json` (66 lines, 765 words) — IDENTICAL to #3 below
- Cast: Nour, Tarek, Qureshi — existing locked `voice-refs/*.wav` via
  `create_voice_clone_prompt` + `generate_voice_clone` (per-line clone-and-stitch, our
  current production path)
- Result: **66/66 lines rendered, 282.8s (~4.7 min)**

## 3. English proof clip — MOSS-TTSD (candidate engine) — `en_ttsd_proof_clip.m4a`
- Kernel: `empireenglish/yalla-fluent-proof-english-ttsd`
- Script: `scripts/english_stress_test.json` — SAME script and SAME 3 voice-refs as #2,
  for a fair head-to-head
- Cast: Nour→S1, Tarek→S2, Qureshi→S3 (native multi-speaker tags), reference audio =
  the SAME `voice-refs/*.wav` files (no new voice assets needed)
- Method: chunked continuation (MOSS-TTSD generates a whole multi-speaker exchange per
  call, not per-line) — 7 chunks of ~10 lines each, using the custom device_map fix from
  `kaggle/moss_ttsd/gen_ttsd.py` (T4x2, asymmetric max_memory, emb_ext pinned to
  embed_tokens's device)
- Result: **7/7 chunks rendered, 270.8s (~4.5 min)**

## Phase D — objective diagnostic results (WhisperX/Parselmouth/UTMOS via Kaggle,
`proof_diagnostic_report.json` in this dir)

Delivery mechanism: per-line/per-chunk audio + the 3 whole clips were packaged as a
private Kaggle Dataset (`empireenglish/yalla-fluent-engine-proof-clips`, 81MB) since these
are throwaway stress-test files, not committed episode content — the diagnostic kernel
mounts the dataset (`dataset_sources` in `kernel-metadata.json`) rather than fetching from
GitHub raw (our usual pattern for repo-committed files).

### Per-line / per-chunk scores (the meaningful numbers — G3.1 bar is UTMOS ≥ 3.7)
| Clip | n | mean UTMOS | min UTMOS | flagged |
|---|---|---|---|---|
| Arabic (VoiceTut) | 96 lines | **3.702** ✅ clears bar | 2.505 | 2/96 |
| English (Qwen3-TTS) | 66 lines | **4.333** ✅ | 3.416 | 0/66 |
| English (MOSS-TTSD) | 7 chunks (66 lines) | 3.526 ⚠️ below bar | 3.287 | 0/7 |

- **Arabic clears G3.1** (mean 3.702 ≥ 3.7), consistent with FIX-008's Essam/Esraa scores.
  Both flagged lines are **Mahmoud saying "call"** (line014 mid-sentence code-switch,
  line052 the drill line teaching the word) — a specific, root-cause-able finding: VoiceTut
  may destabilize on this particular embedded English word. Worth a targeted follow-up
  (not blocking this gate — 2/96 = 2% flag rate, well within noise) if it recurs elsewhere.
- **Qwen3-TTS clears G3.1 comfortably** (4.333, zero flags) — strongest result of the three.
- **MOSS-TTSD is measured PER-CHUNK (10 lines/chunk), not per-line** — a coarser unit, so one
  weak stretch in a chunk pulls its whole average down even if most lines were fine. This
  is an inherent measurement-granularity difference (its native multi-speaker generation
  doesn't produce discrete per-line files), NOT necessarily a real quality gap of the same
  size the number suggests. Treat 3.526 as a directional signal, not a like-for-like score
  against the other two — the owner's ear-test (G5) is what actually resolves this.

### Whole-clip scores — NOT comparable, included for completeness only
`{"arabic_whole": 1.795, "english_qwen_whole": 2.977, "english_ttsd_whole": 2.714}`
UTMOS was trained on short single-utterance audio, not 5-minute multi-speaker
concatenations with silence gaps and speaker/voice changes — it scores long-form structural
artifacts (gaps, transitions) rather than voice quality per se at this duration. These
numbers are **not a real quality signal** and must not be used to judge the clips; the
per-line/per-chunk table above is the valid comparison, and the owner's ear-test is final.

### D.3 — ASR-QA/CER sanity pass on the Arabic clip (`ar_cer_report.json`)
Ran WhisperX-style transcription (faster-whisper large-v3) + the FIX-006 skeleton
normalization (hamza-seat/taa-marbuta/alef-maqsura collapse + brand-name ignore) on all 96
Arabic lines, comparing intended vs. heard text.

**17/96 lines flagged (ratio < 0.5) — but on inspection, ZERO represent an actual TTS
mispronunciation.** Breakdown:
- **12/17 are code-switch measurement artifacts**: these lines are 40-60% English words
  (email, call, design, content, deadline, notes, group, feedback, file, client, review,
  update). The skeleton comparator strips non-Arabic characters from both sides before
  scoring — so once the English portion is removed, only a short Arabic fragment remains,
  which naturally scores a low ratio even when BOTH the Arabic and the English were spoken
  correctly. This is the same class of issue FIX-006 already solved for brand names
  (يلا/فلونت) but not yet extended to generic embedded English words — logged as a
  **follow-up improvement to the ASR-QA tool itself** (not a synthesis bug, not gate-blocking).
- **2/17 are DELIBERATE mispronunciation lines** (line022 "ri-view", line092 "أَبْ-ديت") —
  the script intentionally has Esraa attempt the WRONG pronunciation right before Mahmoud
  corrects her (the drill/teaching pattern from G4.1). Whisper transcribing these as garbled
  is the CORRECT/expected outcome for an intentionally-wrong line, not a defect.
- **3/17 are ASR transcription noise on legitimately correct Arabic** (Whisper's own
  phonetic-spelling variance, e.g. مظبوط/مصبوط, or misreading "عَشَرَة" as the digit "10") —
  not a synthesis issue.

**Conclusion: G3.2 (CER/pronunciation sanity) effectively PASSES** — no هنعيش/دبي-class
script-spelling regression was found. The 17 flags are a measurement-tool limitation
(documented, follow-up noted), not a synthesis defect.

## Next: Phase E — deliver all clips + this diagnostic summary to the owner for the ear-test
