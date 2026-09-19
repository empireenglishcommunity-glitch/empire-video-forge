# Two Worlds — Season Production & Actor-Cast — IMPLEMENTATION PLAN

> Implements `design.md` / `requirements.md`. Phased plan + the live task list that
> execution follows. **Nothing runs without the owner's explicit command.** Gates are
> hard stops. Legend: 🤖 = agent does · 🧑 = owner does (GPU / reviews / decisions).

> ### 📌 SPEC AMENDMENTS (decisions made during execution — the current truth)
> These override the original plan text where they differ; kept here so the spec never
> drifts from reality.
> 1. **Season name = "Yalla Fluent"** (subtitle "The 90-Day English Drama"). ("Two Worlds"
>    survives only as the Ep10 title + legacy spec-folder name.)
> 2. **Duration gate REMOVED** (owner decision "C"). Episodes target ~5-6 min but length is
>    **informational only** — never a hard stop. Only the **structure gate** blocks.
> 3. **Scriptwriting = DeepSeek via the DIRECT API** (`api.deepseek.com`; `deepseek-chat`/V3
>    primary, `deepseek-reasoner`/R1 fallback), **single-pass** (not two-pass, not
>    OpenRouter-free). See design §2b "AS BUILT".
> 4. **English TTS = Qwen3-TTS** (Apache-2.0); **Chatterbox is retired** (archived, removed
>    in Phase E). `cast.json` still lists Chatterbox — rewritten to Qwen3-TTS in **B.7**
>    (tracked as issue **#52**). Not drift — scheduled.
> 5. **`direction` acting-note tag** = forward-looking metadata; generated + preserved but
>    NOT yet consumed by synth/assembly. Its consumer (direction→prosody mapper) is
>    **Phase C** work, tracked as issue **#53**.
> 6. **Status:** GATE 0.5 ✅, GATE 0 ✅, GATE A ✅ all passed. **Currently in Phase B, at B.3**
>    (owner reviews voice-design specs). Verification docs live in
>    `.kiro/specs/eec-podcast-automation/` (`qwen3-tts-verification.md`, `voice-design-specs.md`).

## Execution rules
1. Work strictly in phase order; do not start a phase until the previous phase's gate
   is signed off by the owner.
2. Every Kaggle GPU step is owner-run (🧑); the agent prepares paste-safe cells and
   verifies outputs afterward.
3. Never touch the Arabic engine (VoiceTut). Never disrupt the 12 live containers.
4. Push ALL commits to a branch BEFORE opening a PR (avoid the merged-early split).
5. Keep the retired Chatterbox path archived (not deleted) until the new cast is proven.
6. **All execution runs through a LIVE TASK LIST (mandatory — see the Execution
   Protocol below).** No task is done from memory; nothing is dropped.

## Execution protocol — the live task list is MANDATORY
> This is a hard process rule, not a suggestion. It exists so that across a long,
> multi-phase, multi-session effort we **never drop, skip, or lose track of a task** —
> no matter what interruptions, context switches, or session breaks happen.

**Rules of the live task list:**
- **P1 — One source of truth.** When execution begins, the agent creates a live task
  list mirroring this plan (Phases 0-E, every task). This tasks.md is the durable
  reference; the live list is the working tracker. They must not diverge.
- **P2 — Update on the go (real time).** The agent marks a task **in-progress** when it
  starts and **complete IMMEDIATELY** when its artifact is produced AND verified — never
  in a batch at the end, never from memory. Task status must always reflect reality.
- **P3 — Definition of done per task.** A task is complete ONLY when its concrete
  artifact exists and is verified (file written, output produced, check passed). A
  command exiting without error is NOT proof of done. Owner-run (🧑) tasks are marked
  complete only after the owner confirms.
- **P4 — Gates are hard stops in the list.** A GATE task cannot be marked complete until
  the owner explicitly signs off. Work does not cross a gate on assumption.
- **P5 — Add, don't silently drop.** If new work is discovered mid-phase, ADD it to the
  live list (and reflect it here) rather than doing it untracked. If a task becomes
  unnecessary, mark it removed with a one-line reason — never delete silently.
- **P6 — Survive session breaks.** At any stop/handoff, the live list + the handoff doc
  must together state exactly which tasks are done, in-progress, and next — so a fresh
  session resumes with zero loss. On resume, re-sync the live list from this tasks.md
  before doing anything.
- **P7 — Nothing outside the list.** No execution step happens that isn't represented as
  a task. If it's worth doing, it's worth tracking.
- **P8 — Step by step, together (owner-in-the-loop).** Any step that needs the owner —
  a credential, a decision, a Kaggle GPU run, a review, providing/creating anything — is
  done **one step at a time, together**. The agent presents exactly ONE actionable step,
  waits for the owner to complete it and confirm, then proceeds to the next. No bundling
  multiple owner asks at once; no racing ahead of the owner. The agent's job is to make
  each step small, clear, and easy to act on.

---

## Creative authorship model — models draft, owner approves, spine gets LOCKED
> The owner acts as **showrunner/approver**, not hand-writer. The models (DeepSeek R1/V3)
> do the heavy creative lifting *within the owner's brand guardrails*; the owner approves;
> then structural "spine" decisions are LOCKED so all 10 episodes stay consistent.
- **Models decide (craft):** prose, dialogue, dramatic beats, character depth/motives,
  phrasing, episode situations, pacing, the proposed arc + Macal stage split.
- **Owner owns (brand + spine):** approval of the regenerated series bible; the
  non-negotiable brand guardrails fed IN as constraints; the final lock of the arc +
  stage split so downstream episodes can't drift.
- **Brand guardrails fed to the models as hard constraints (non-negotiable):** EEC brand
  voice + honesty rules (no "hack/secret/guaranteed"/shaming); "learn with fun" mission;
  Macal-as-learner pedagogy (American = the taught target; Macal's L2→American arc);
  Dubai setting; cast realism principles; the short 5-10 min format + structure rule.

## PHASE 0.5 — Regenerate & approve the SERIES BIBLE (creative foundation)
Goal: a stronger, model-authored series bible — premise, character histories/motives,
season arc — that stays on-brand. Everything downstream inherits from it, so it's the
one creative artifact most worth the owner's eyes.
- [x] 0.5.1 🤖 Prompt **DeepSeek R1 (showrunner)** to regenerate the series bible —
      richer premise, deeper character histories + hidden motives, a compelling Season-1
      arc — **constrained by the brand guardrails above** (fed in explicitly). Preserve
      cast realism + pedagogy + the honesty rules.
- [x] 0.5.2 🤖 Produce a proposed **`series-bible.md` v2** (draft) + a one-page summary
      of what changed vs. the current bible, for fast review.
- [x] 0.5.3 🧑 **Owner reviews** the regenerated bible; iterate 🤖↔🧑 until on-brand + loved.
- [x] 0.5.4 🧑 **GATE 0.5:** owner approves the series bible. Bible LOCKED. ✅ (bible =
      "YALLA FLUENT", promoted to canonical via PR #46; scripting-craft §3.4/§3.5 folded in.)

## PHASE 0 — Lock the season plan (arc + stage split)
Goal: from the approved bible, lock the season spine so scripts stay consistent.
- [x] 0.1 🤖 From the locked bible, have the model **propose** the Season-1 episode list
      (10 titles/situations/levels) + the **Macal stage→episode split** (default
      S1=Eps1-3, S2=Eps4-7, S3=Eps8-10). Owner nudges rather than authors.
- [x] 0.2 🧑 Owner reviews/adjusts the proposed episode list + stage split.
- [x] 0.3 🤖 Write the approved plan into `season.json` (`episodes[]`, `macal_stage_map`).
- [x] 0.4 🧑 **GATE 0:** owner approves the season plan. Arc + stage split LOCKED. ✅
      (season.json: 10 eps, macal_stage_map 1-3/4-7/8-10; locked via PR #48.)

## PHASE A — Season scripts (must precede casting)
Goal: all 10 short scripts exist + approved, so the full cast is known.
- [x] A.0 🤖 **Adopt DeepSeek for scriptwriting**: set `EEC_LLM_MODEL` /
      `EEC_LLM_FALLBACKS` in the server `.env`; confirm the model strings resolve; have
      V3 emit a per-line **`direction`** acting note (schema §3.3). Verify one test
      generation + that the gates ignore `direction`. ✅ **DONE, with one DECISION:**
      live config is **direct DeepSeek API** (`EEC_LLM_BASE_URL=https://api.deepseek.com`,
      `EEC_LLM_MODEL=deepseek-chat` = V3, `EEC_LLM_FALLBACKS=deepseek-reasoner` = R1) —
      NOT the OpenRouter free tier the plan first imagined, because R1-via-free returned
      unparseable JSON + was slow; the direct API is the documented "paid escape hatch"
      (~$0.01/season, negligible). **Two-pass mode (R1 beats→V3 dialogue) was NOT built —
      single-pass V3 is used**, which the plan explicitly permits ("MAY gain… if not, a
      single strong model is used"). `direction` is emitted on every line; gates ignore it.
- [x] A.1 🤖 Generate **Eps 2-10** short scripts (`gen_episode.py`, ~7 min, `--no-advance`
      per episode), each passing the **structure gate** AND applying the
      **scripting-craft rules (design §3.4)**: in-media-res; Macal voice-stage markers;
      the REQUIRED mistake→correction→triumph loop; target phrases in act1 reused in act2;
      guest-accent clarity. ✅ (NOTE: the **duration gate was REMOVED** per owner decision
      "C" — length is now informational only, not a hard gate.)
- [x] A.2 🤖 Reconcile Ep1 into the season (regenerated short with the others); continuity
      (`story_so_far`) flows across all 10. ✅
- [x] A.3 🧑 **Review all 10 short scripts** against the **QA checklist (design §3.5)**.
      Iterate 🤖↔🧑 until good. ✅ (owner reviewed; applied fixes: ep01 brand bridge,
      ep08 pacing beat; plus enrichment pass — phrase_of_episode, Accent Lab drills,
      trackable Telegram CTA — merged via PR #50.)
- [x] A.4 🤖 **Derive the full cast list** from the 10 approved scripts (every speaker). ✅
      (11 speakers; `season1-cast-derived.md` refreshed from final scripts via PR #54.)
- [x] A.5 🧑 **GATE A:** owner approves the 10 scripts + the derived cast list. Scripts
      LOCKED. ✅ (owner approved this session.)

## PHASE B — Cast & voice design (Qwen3-TTS)
Goal: a locked `cast.json` with an owner-approved voice per character.
- [x] B.1 🤖 **Verify Qwen3-TTS engine facts** (design §2, V1-V6): model id, license,
      **VoiceDesign + VoiceClone** APIs, VoiceClone reproducibility (Option B),
      Kaggle install (1.7B, bf16, ~8GB VRAM on T4), output format. Document findings;
      adjust design if reality differs. ✅ (`qwen3-tts-verification.md`, PR #55. Confirmed
      Apache-2.0; Option B = official "Voice Design then Clone"; 1.7B is a FAMILY —
      `-VoiceDesign` + `-Base`; **Kaggle T4 caveat: use `attn_implementation="sdpa"`, NOT
      FlashAttention2 (T4 is Turing)**; load the two models sequentially.)
- [x] B.2 🤖 Draft **voice-design specs** for the whole roster: Macal's 3 stages (with
      **explicit L2 acoustic markers**), Nour (native American), TaxiDriver (Indian), +
      every derived guest by realism. ✅ (`voice-design-specs.md`, PR #56 — 11 voices,
      3-4 candidates each, grounded in the bible.)
- [ ] B.3 🧑 **← CURRENT STEP.** Review/tweak the voice-design descriptions (owner is the
      casting director).
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
- [ ] C.1a 🤖 **Lexicon additions (design §2c Tier 2):** add hand-verified entries for
      **Mahmoud (مَحْمُود)**, **"Yalla Fluent"**, **EEC**, and standing loan-words
      (interview→إِنْتَرْفْيُو, session→سِشْن, feedback→فِيدْبَاك) to `egyptian_lexicon.json`.
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
- [ ] C.5 🤖 Re-assemble Ep1 through the **structure gate**, verify 100% rendered + clean
      (duration informational, ~5-6 min expected); deliver plain audio to Drive `raw-audio`.
- [ ] C.6 🧑 **GATE C:** owner listens to the new Ep1 and approves the cast on a real
      episode (or requests fixes → iterate).

## PHASE C.5 — Mastering & Packaging (post-production; design §4b)
Goal: a `dist/` folder with broadcast-ready audio + a ready-to-publish text asset.
- [ ] C5.0 🤖 **Arabic FX for Mahmoud (design §2c Layer 3):** apply the per-clip Arabic
      FFmpeg chain (low-mid warmth + de-ess + 80 Hz high-pass) to Mahmoud's Arabic clips
      only, sequenced BEFORE the master. 🧑 Ear-tune the values on Ep1.
- [ ] C5.1 🤖 Upgrade `assemble_audio.py`'s final master to a chain: **two-pass loudnorm**
      (−16 LUFS, robust JSON parse), gentle EQ, and a **conservative `silenceremove`**.
      Do NOT add a duplicate loudnorm.
- [ ] C5.2 🧑 **Ear-validate on Ep1:** confirm the silence-trim does NOT collapse the
      intentional line/coach gaps or the story→coach beat. If it harms pacing, drop the
      trim, keep loudnorm+EQ.
- [ ] C5.3 🤖 Build `metadata.py`: from the script + `timeline.master.json` timings,
      call DeepSeek (strict JSON) → `seo_title`, `show_notes`, `timestamps` (from the
      timeline), `social_quotes`, `vocabulary_key` (EN+AR). Obey EEC honesty guardrails.
      Write to `dist/epNN/`.
- [ ] C5.4 🧑 Owner reviews the first packaged asset; iterate the prompt if needed.

## PHASE D — Batch the season (after Ep1 proven)
Goal: synthesize the rest of the season against the locked cast.
- [ ] D.1 🧑 Run the two Kaggle notebooks (EN Qwen3-TTS + AR VoiceTut) for **Eps 2-10**
      (Macal stage auto-selected per episode); drop WAVs per episode.
- [ ] D.2 🤖 Assemble each episode through the gates; verify; deliver plain audio.
- [ ] D.3 🧑 Review each episode's audio; iterate on any bad line (re-roll clip / fix
      text / add lexicon word). **Self-learning loop (design §2c Layer 4, OWNER-GATED):**
      ASR-QA flags a mispronounced Arabic word → 🧑 owner verifies/fixes the tashkeel →
      🤖 saves it to `egyptian_lexicon.json` so all future episodes auto-apply the fix.
      The human fix is REQUIRED before a word enters the permanent lexicon.
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
- [x] GATE 0.5: series bible (regenerated) approved (bible locked). ✅
- [x] GATE 0: season plan / arc + Macal stage split approved (spine locked). ✅
- [x] GATE A: 10 scripts + cast list approved (scripts locked). ✅
- [ ] GATE B: cast.json voices approved (cast locked). ← next gate (Phase B in progress: B.3)
- [ ] GATE C: new Ep1 audio approved (cast proven on a real episode).
- [ ] GATE D: season audio approved.

## Notes / open decisions carried from planning
- **Series bible is regenerated by the models (Phase 0.5)** within brand guardrails,
  owner-approved + locked, BEFORE the season plan + scripts. The current bible is the
  starting reference, not the final word.
- Season episode list + situations + Macal stage split are **model-proposed** from the
  locked bible (Phase 0), owner-approved. Default stage split 1-3 / 4-7 / 8-10.
- Owner is showrunner/approver, not hand-writer (see "Creative authorship model").
- Guest roster is unknown until scripts exist (A.4) — cast in Phase B.
- If Qwen3-TTS accent fidelity or reproducibility fails verification (B.1) or audition
  (B.6), fallback = Kokoro (Apache-2.0, built-in voices) — a documented alternative,
  not the default.
