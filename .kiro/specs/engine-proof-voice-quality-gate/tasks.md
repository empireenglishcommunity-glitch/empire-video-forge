
> Implements `design.md`. This is the execution checklist for the gate defined in
> `requirements.md`. Nothing here proceeds to Phase D until every checked item's
> corresponding G-criterion is verified true, AND the owner has given an explicit G5 verdict.

## Phase A — Cast audition (G6) ✅ DONE
- [x] A.1 Confirmed the Arabic 3+ mixed-gender cast: Essam (locked, FIX-008) + Esraa (this
      audition's winner, mean UTMOS 3.598 @ gs1.5) + Asmaa (2nd place, 3.391, cast as
      "Nadia"). Same FIX-008 methodology, full ranking in
      `../eec-podcast-automation/diagnostics/female_audition.json`. Samples delivered to
      Drive for reference during the audition.
- [x] A.2 Selected Nour (F, General American) + Tarek (M, polished Egyptian) + Qureshi (M,
      Pakistani/Urdu) — widest accent spread in the locked roster, mixed gender.

## Phase B — Stress-test scripts (G2, G4) ✅ DONE
- [x] B.1 Arabic stress-test script written (`scripts/arabic_stress_test.json`): 96 lines,
      663 words, ~5.1 min. All G4.1 patterns present (calm/energetic alternation via word
      choice not text-pauses, 6+ code-switches, 3 drill/correction exchanges, phone-ring
      interruption).
- [x] B.2 `dialogue_polish.polish_coach_direction()` run: 36/96 lines got delivery notes,
      Arabic text VERIFIED UNCHANGED (0 diffs against the pre-polish draft).
- [x] B.3 English stress-test script written (`scripts/english_stress_test.json`): 66 lines,
      765 words, ~5.1 min. All G4.2 patterns present (text-embedded emotion, register
      shifts, em-dash interruptions, a real Q&A-reaction chain, energetic close).
- [x] B.4 `dialogue_polish.polish_story_lines()` run (`engine="qwen"`): 6/66 lines fixed
      (caught real clichés/dead lines/overly theatrical phrasing); verified zero
      `[Speaker]`-label leakage.

## Phase C — Generation (G1, G3, G4) ✅ DONE
- [x] C.1 Arabic clip rendered: 96/96 lines, natural text + atempo post-processing
      (FIX-007 discipline, no text-injected pauses), 333.99s (~5.6 min).
- [x] C.2 English clip rendered via Qwen3-TTS `generate_voice_clone` (production path):
      66/66 lines, 282.8s (~4.7 min).
- [x] C.3 English clip rendered AGAIN via MOSS-TTSD (`kaggle/moss_ttsd/gen_ttsd.py`,
      chunked continuation, SAME script + SAME 3 voice-refs as C.2): 7/7 chunks
      (66 lines), 270.8s (~4.5 min).
- [x] C.4 All three generations ran autonomously via the Kaggle API (push/poll/pull) — no
      manual notebook steps. See `clips/MANIFEST.md` for the full kernel-by-kernel record.

## Phase D — Objective diagnostic (G3) ✅ DONE
- [x] D.1 Diagnostic run (WhisperX-class transcription + Parselmouth + UTMOS, via a Kaggle
      Dataset mount of all per-line/chunk audio) on the Arabic clip: **mean UTMOS 3.702
      (n=96) — CLEARS the ≥3.7 bar.** 2/96 lines flagged (both Mahmoud saying "call") — a
      specific, root-cause-able signal, 2% flag rate, not gate-blocking.
- [x] D.2 Same diagnostic on both English renders: Qwen3-TTS mean UTMOS **4.333 (n=66, zero
      flagged)** — strongest result. MOSS-TTSD mean UTMOS **3.526 (n=7 chunks)** — below bar,
      but measured at chunk (not line) granularity, a coarser unit; see `clips/MANIFEST.md`
      for why this isn't a strict like-for-like comparison.
- [x] D.3 ASR-QA/CER sanity pass run on the Arabic clip (`clips/ar_cer_report.json`): 17/96
      lines flagged by the raw ratio, but on inspection ALL 17 are measurement artifacts
      (12 = code-switch skeleton-stripping quirk, 2 = deliberately-wrong drill
      pronunciations working as intended, 3 = ASR transcription noise) — **zero actual
      هنعيش/دبي-class script-spelling regressions found.** G3.2 effectively passes; the
      code-switch skeleton limitation is logged as a follow-up tool improvement, not a
      synthesis defect.

## Phase E — Delivery + owner ear-test (G5 — the actual gate)
- [x] E.1 All 3 clips delivered to the owner's Drive `output` folder with clear comparative
      filenames encoding the diagnostic numbers ("ENGINE PROOF - 1 ARABIC ... UTMOS 3.70
      PASS", "- 2 ENGLISH Qwen3-TTS ... UTMOS 4.33 PASS", "- 3 ENGLISH MOSS-TTSD candidate
      ... UTMOS 3.53"), alongside this spec's diagnostic summary (`clips/MANIFEST.md`).
- [ ] E.2 ⏳ **OWNER:** listen to all 3 clips; record an explicit verdict per clip (pass /
      fail / conditional) with specific, timestamped notes on anything that breaks
      immersion. THIS IS THE ACTUAL GATE — everything above is evidence for this step, not
      a substitute for it.
- [ ] E.3 ⏳ **OWNER:** for the English head-to-head specifically, record preference and
      whether MOSS-TTSD should (a) become a routed production engine (needs a follow-on
      integration spec), (b) stay a documented candidate, or (c) be dropped.
- [ ] E.4 Any failure noted in E.2 gets root-caused and logged as a new FIX-0XX entry in
      `episode-fixes-log.md` (never a blind patch) — then Phases C-E re-run for the affected
      clip only.

## Phase F — Close the gate
- [ ] F.1 Once both G1 clips have an explicit owner PASS (G5), update this spec's status to
      DONE and record the final locked configuration (voices, engine params, and — if
      applicable — the MOSS-TTSD production decision) back into `cast.json` and
      `episode-fixes-log.md`.
- [ ] F.2 Explicitly unblock Phase D (batch Episodes 2-10) in `eec-podcast-automation/tasks.md`
      — this gate existing and passing is the unblock condition; state that plainly so it
      isn't missed by a future session.
