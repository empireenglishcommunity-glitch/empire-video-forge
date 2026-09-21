
> Implements `design.md`. This is the execution checklist for the gate defined in
> `requirements.md`. Nothing here proceeds to Phase D until every checked item's
> corresponding G-criterion is verified true, AND the owner has given an explicit G5 verdict.

## Phase A — Cast audition (G6)
- [ ] A.1 Confirm the Arabic 3+ mixed-gender cast: re-confirm Essam (locked, FIX-008) +
      UTMOS-audition at least one FEMALE VoiceTut voice (none scored yet) + one more voice,
      using the SAME methodology as FIX-008 (score on hard/representative lines, rank, owner
      ear-confirm the winner) — not picked by assumption.
- [ ] A.2 Confirm the English 3+ mixed-gender cast from the existing locked Qwen3-TTS roster
      (no new audition needed — these are already locked; just SELECT three that span male +
      female + at least two distinct accents for a meaningful stress test).

## Phase B — Stress-test scripts (G2, G4)
- [ ] B.1 Write the Arabic stress-test script via `gen_episode`-style prompting to
      `llm_backend.chat(engine="deepseek")`: ~5 min spoken (~750 words at Arabic speaking
      pace), 3+ speakers from A.1, includes the required patterns from design.md §2.2
      (calm/energetic alternation, 3+ code-switch moments, one drill/imperative exchange).
- [ ] B.2 Run `dialogue_polish.polish_coach_direction()`-style review on the Arabic draft —
      delivery notes only, Arabic text untouched. Capture the report (reviewed/applied
      counts) as evidence for G2.1.
- [ ] B.3 Write the English stress-test script via `llm_backend.chat(engine="deepseek")`:
      ~5 min spoken (~750-800 words at English pace), 3+ speakers from A.2, includes the
      required patterns from design.md §2.3 (text-semantic emotion, rapid register shift,
      overlapping reactions, a real Q&A chain).
- [ ] B.4 Run `dialogue_polish.polish_story_lines()` on the English draft (the real adversarial
      critic, `engine="qwen"`). Capture the report as evidence for G2.1; verify no
      `[Speaker]`-label leakage (already defended in code, confirm it holds here too).

## Phase C — Generation (G1, G3, G4)
- [ ] C.1 Render the Arabic clip with VoiceTut via the `synth_all_in_one.py` pattern (natural
      text, `atempo` post-processing per cast.json, NOT text-injected pauses — FIX-007
      discipline). One continuous ~5 min output.
- [ ] C.2 Render the English clip with Qwen3-TTS (`generate_voice_clone`, existing production
      path) from the SAME B.3 script.
- [ ] C.3 Render the English clip AGAIN with MOSS-TTSD (`kaggle/moss_ttsd/gen_ttsd.py`,
      `load_model()` + `generate_dialogue()`, reusing the three characters' existing
      `voice-refs/*.wav` as reference audio) from the IDENTICAL B.3 script — this is the
      head-to-head, so the script must not differ between C.2 and C.3.
- [ ] C.4 All generation runs execute autonomously via the Kaggle API (push/poll/pull), per
      the established pattern — no manual notebook steps.

## Phase D — Objective diagnostic (G3)
- [ ] D.1 Run `diagnose_episode.py` (WhisperX + Parselmouth + UTMOS → DeepSeek report) on the
      Arabic clip. Record mean UTMOS, any flagged lines, and the DeepSeek producer report.
      Must clear G3.1's ≥3.7 / zero-flagged bar to proceed to the owner ear-test; if not,
      root-cause and fix before wasting the owner's listening time (same discipline as
      FIX-008 — diagnose before asking for an ear-test).
- [ ] D.2 Run the same diagnostic on BOTH English renders (Qwen3-TTS and MOSS-TTSD) from the
      identical script, producing a directly comparable UTMOS + flagged-line table.
- [ ] D.3 Run the ASR-QA/CER sanity pass (G3.2) on the Arabic clip specifically — confirm no
      script-spelling regressions of the هنعيش/دبي class before the owner listens.

## Phase E — Delivery + owner ear-test (G5 — the actual gate)
- [ ] E.1 Deliver all clips to the owner's Drive `output` folder with clear comparative
      filenames (Arabic proof clip; English proof clip — Qwen3-TTS; English proof clip —
      MOSS-TTSD candidate), plus a short summary of the D-phase diagnostic numbers.
- [ ] E.2 Owner listens; record an explicit verdict per clip (pass / fail / conditional) with
      specific, timestamped notes on anything that breaks immersion.
- [ ] E.3 For the English head-to-head specifically: record the owner's preference and
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
