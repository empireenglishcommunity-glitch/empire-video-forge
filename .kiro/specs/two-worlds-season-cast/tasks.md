# Two Worlds — Season Production & Actor-Cast — IMPLEMENTATION PLAN

> Implements `design.md` / `requirements.md`. Phased plan + the live task list that
> execution follows. **Nothing runs without the owner's explicit command.** Gates are
> hard stops. Legend: 🤖 = agent does · 🧑 = owner does (GPU / reviews / decisions).

## Execution rules
1. Work strictly in phase order; do not start a phase until the previous phase's gate
   is signed off by the owner.
2. Every Kaggle GPU step is owner-run (🧑); the agent prepares paste-safe cells and
   verifies outputs afterward.
3. Never touch the Arabic engine (VoiceTut). Never disrupt the 12 live containers.
4. Push ALL commits to a branch BEFORE opening a PR (avoid the merged-early split).
5. Keep the retired Chatterbox path archived (not deleted) until the new cast is proven.

---

## PHASE 0 — Lock the season plan (design inputs)
Goal: agree WHAT the season is before writing it.
- [ ] 0.1 🧑 Confirm the **Season-1 episode list** (10 titles/situations/levels) — start
      from series-bible §4; owner edits as desired.
- [ ] 0.2 🧑 Confirm **Macal stage→episode map** (default S1=Eps1-3, S2=Eps4-7, S3=Eps8-10).
- [ ] 0.3 🤖 Write the confirmed plan into `season.json` (`episodes[]`, `macal_stage_map`).
- [ ] 0.4 🧑 **GATE 0:** owner approves the season plan.

## PHASE A — Season scripts (must precede casting)
Goal: all 10 short scripts exist + approved, so the full cast is known.
- [ ] A.0 🤖 **Adopt DeepSeek for scriptwriting**: set `EEC_LLM_MODEL` /
      `EEC_LLM_FALLBACKS` (DeepSeek R1 + V3, via OpenRouter free) in the server `.env`;
      confirm the exact free model strings resolve; add the optional two-pass
      (R1 beats → V3 dialogue) mode to `gen_episode.py`, and have V3 emit a per-line
      **`direction`** acting note (schema §3.3). Verify one test generation + that the
      gates ignore `direction`.
- [ ] A.1 🤖 Generate **Eps 2-10** short scripts (`gen_episode.py`, ~7 min, `--no-advance`
      handling per episode), each passing **structure + duration gates**. Ep1 already exists.
- [ ] A.2 🤖 Reconcile Ep1 into the season (it already exists short); ensure continuity
      (`story_so_far`) flows across all 10.
- [ ] A.3 🧑 **Review all 10 short scripts** (story + teaching). Iterate 🤖↔🧑 until good.
- [ ] A.4 🤖 **Derive the full cast list** from the 10 approved scripts (every speaker).
- [ ] A.5 🧑 **GATE A:** owner approves the 10 scripts + the derived cast list. Scripts LOCKED.

## PHASE B — Cast & voice design (Qwen3-TTS)
Goal: a locked `cast.json` with an owner-approved voice per character.
- [ ] B.1 🤖 **Verify Qwen3-TTS engine facts** (design §2, V1-V6): model id, license,
      **VoiceDesign + VoiceClone** APIs, VoiceClone reproducibility (Option B),
      Kaggle install (1.7B, bf16, ~8GB VRAM on T4), output format. Document findings;
      adjust design if reality differs.
- [ ] B.2 🤖 Draft **voice-design specs** for the whole roster: Macal's 3 stages (with
      **explicit L2 acoustic markers** for Stage 1 — rolled r's, crisp T's, deliberate
      pacing, earnest), Nour (native American), TaxiDriver (Indian), + every derived
      guest by realism.
- [ ] B.3 🧑 Review/tweak the voice-design descriptions (owner is the casting director).
- [ ] B.4 🤖 Build `kaggle/audition_qwen.py` (paste-safe): 3-4 candidates/character
      (Macal = 3 stages) reading real Season-1 lines → labeled clips + zip.
- [ ] B.5 🧑 **Run the audition on Kaggle**; download the clips.
- [ ] B.6 🧑 **Pick** one voice per character + approve **Macal's 3-stage arc**
      (iterate B.2-B.5 on any character until happy).
- [ ] B.7 🤖 For each approved voice, **save the canonical ~10-15s reference WAV**
      (self-generated from the winning audition take) to `voice-refs/` (Macal = 3 refs,
      one per stage); write chosen voices + `voice_ref` paths into **`cast.json`
      (schema v2)**; set statuses to `locked`.
- [ ] B.8 🧑 **GATE B:** owner approves the locked cast (voices + Macal arc).

## PHASE C — Wire up + prove on Ep1
Goal: the new engine + cast produces a real, approved episode.
- [ ] C.1 🤖 **Rename Coach → Mahmoud**: `cast.json` (`display_name`), the Arabic
      self-intro line(s) in scripts, and the lexicon name entry. Keep speaker id `Coach`
      so gates/pipeline are untouched (design §6).
- [ ] C.2 🤖 Build `kaggle/synth_episode_en_qwen.py`: **VoiceClone** from each
      character's canonical `voice_ref` (Option B; Macal picks the stage's ref via
      `stage_map`), passing each line's **`direction`** to Qwen3-TTS for emotional
      delivery. Replaces the Chatterbox English notebook; update `run_podcast.py`/docs;
      archive the Chatterbox path (not deleted).
- [ ] C.2a 🤖 **Verify `direction` sanitization**: assert the text-cleaner, text_hash/
      manifest builder, timeline, and gates read only `text`/`speaker`/`section` and
      never see `direction` (add a test).
- [ ] C.3 🤖 Update `series-bible.md` casting section (realism + pedagogy + Macal arc)
      and `OPERATIONS.md` (new English engine + audition workflow).
- [ ] C.4 🧑 **Re-synth Ep1 English on Qwen3-TTS** (Macal Stage 1) via the new notebook;
      drop WAVs into `episodes/ep01/synth/`. (Coach/Arabic already done; if the Mahmoud
      self-intro line changed, re-synth just that Arabic line too.)
- [ ] C.5 🤖 Re-assemble Ep1 through the gates (structure + duration), verify 5-10 min +
      100% rendered + clean; deliver plain audio to Drive `raw-audio`.
- [ ] C.6 🧑 **GATE C:** owner listens to the new Ep1 and approves the cast on a real
      episode (or requests fixes → iterate).

## PHASE D — Batch the season (after Ep1 proven)
Goal: synthesize the rest of the season against the locked cast.
- [ ] D.1 🧑 Run the two Kaggle notebooks (EN Qwen3-TTS + AR VoiceTut) for **Eps 2-10**
      (Macal stage auto-selected per episode); drop WAVs per episode.
- [ ] D.2 🤖 Assemble each episode through the gates; verify; deliver plain audio.
- [ ] D.3 🧑 Review each episode's audio; iterate on any bad line (re-roll clip / fix
      text / add lexicon word).
- [ ] D.4 🤖 Update `season.json` continuity + status as episodes complete.
- [ ] D.5 🧑 **GATE D:** season audio complete + approved (owner then adds music/video/
      cover + publishes — downstream, owner-owned).

## PHASE E — Close out
- [ ] E.1 🤖 Remove the archived Chatterbox path once the season is proven (owner OK).
- [ ] E.2 🤖 Update the handoff doc + tasks; final commit; confirm 12 containers healthy.

---

## Ownership summary
- 🤖 **Agent:** scripts generation, engine verification, notebook + code builds, cast.json,
  assembly, docs, commits/PRs, output verification.
- 🧑 **Owner:** season plan approval, script reviews, all Kaggle GPU runs (audition +
  synth), voice picks, audio reviews, publishing.

## Gate checklist (hard stops — owner sign-off required)
- GATE 0: season plan approved.
- GATE A: 10 scripts + cast list approved (scripts locked).
- GATE B: cast.json voices approved (cast locked).
- GATE C: new Ep1 audio approved (cast proven on a real episode).
- GATE D: season audio approved.

## Notes / open decisions carried from planning
- Season episode list + situations: from series-bible §4, pending owner confirm (0.1).
- Macal stage split default 1-3 / 4-7 / 8-10 (0.2).
- Guest roster is unknown until scripts exist (A.4) — cast in Phase B.
- If Qwen3-TTS accent fidelity or reproducibility fails verification (B.1) or audition
  (B.6), fallback = Kokoro (Apache-2.0, built-in voices) — a documented alternative,
  not the default.
