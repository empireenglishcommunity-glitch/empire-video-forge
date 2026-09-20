# Episode Fixes Log — Yalla Fluent

> **Purpose:** turn each audio fix into a **permanent system guardrail**, not a one-off patch,
> so Phase D (Eps 2–10) inherits a hardened pipeline and we never repeat a mistake.
> Lightweight by design — one row per issue; the **Scope** column does the real work.
>
> **Owner reports issues** in this format:
> ```
> Location:      [timestamp or line #]
> Speaker:       [Macal / Nour / Coach / Interviewer / ...]
> Symptom:       [what was heard]
> Desired State: [what it should sound like]
> ```
> **Agent triages** each into 🔴 Systemic (becomes a rule, prevents recurrence in all eps)
> or 🟡 One-off (local re-roll of that clip only, via the manifest — no full re-synth).

## Triage key
- **Scope 🔴 Systemic** — fix lives in a config/rule so it auto-applies to every future episode.
- **Scope 🟡 One-off** — just this clip; re-synthesize the single line (manifest supports it).
- **Scope ⚫ Engine-limit** — the engine can't do it; fix = reword the line (a generator rule), not fight the tool.

## Where a fix belongs (subsystem → what it prevents)
| Symptom type | Fix location | Applies to |
|---|---|---|
| Arabic word mispronounced (Mahmoud) | `pipeline/egyptian_lexicon.json` | all future eps ✅ |
| **Macal English word mispronounced (VoiceTut)** | **`pipeline/english_phonetic_map.json`** (synth-boundary override; script.json stays clean) | all future eps ✅ |
| Awkward wording / wrong phrase | fix `script.json` + add a `gen_episode.py` prompt rule | all future eps ✅ |
| Flat/wrong emotion or delivery | `direction`→params mapper (#53) or a `cast.json` param | all future eps ✅ |
| Pacing / gaps / story→coach transition | `pipeline/assemble_audio.py` settings (`--gap`, `--coach-gap`) | all future eps ✅ |
| Structure (teaching in a story scene) | `pipeline/structure_check.py` gate | all future eps ✅ |
| One bad take, no pattern | manifest re-roll of that line | just that clip 🟡 |

---

## Fixes

<!-- Template row (copy for each issue):
### FIX-000 — <short title>
- **Location:** <line # / timestamp>
- **Speaker:** <name>
- **Symptom:** <what was heard>
- **Desired state:** <what it should sound like>
- **Root cause:** <why it happened>
- **Scope:** 🔴 Systemic | 🟡 One-off | ⚫ Engine-limit
- **Fix:** <what was changed>
- **Rule now lives in:** <file / config>
- **Status:** open | fixed | verified
-->

### FIX-001 — Macal speaks too fast (not natural/human)
- **Location:** all Macal lines (e.g. Ep1 lines 16/18/20)
- **Speaker:** Macal (VoiceTut "Abdullah", English)
- **Symptom:** speaking too fast — line16 **4.82 wps**, line20 4.1 wps, line18 3.64 wps.
- **Desired state:** natural, deliberate human pace; as a hesitant Egyptian **learner** he
  should be the SLOWEST voice — target ~1.8–2.2 words/sec (~110–135 wpm).
- **Root cause:** VoiceTut base `speed`=1.0 is too fast for Macal; not the direction mapper
  (his fast lines' directions were neutral).
- **Scope:** 🔴 **Systemic** — fix in `cast.json` Macal `speed` → applies to every Macal line, every episode.
- **Fix (round 1 — INSUFFICIENT):** lowering `speed` barely helped — calibration showed even
  `speed=0.75` left Macal at **3.1–3.9 wps** (still "too fast"). VoiceTut `speed` is a WEAK lever
  and floors out above target. So speed alone can't fix this.
- **Fix (round 2 — the real lever):** **prosodic PAUSES in the synth text** — commas as breath
  groups + `...` at clause boundaries (the same technique the Arabic coach uses, design §Layer-1).
  A hesitant learner pauses; that drops the pace to ~2 wps and sounds human. Applied at the
  **synth boundary** (script.json stays clean, like `english_phonetic_map`). Testing variants
  RAW/COMMA/ELLIPSIS/BOTH_SLOW via `kaggle/calibrate_macal_prosody.py`.
- **Rule now lives in:** `macal_prosody()` in `kaggle/synth_episode_v2.py` (synth-boundary:
  commas ~every 3 words + `...` at clause boundaries) + `cast.Macal.speed=0.85`. Applied only
  to Macal's English at synth time — `script.json` stays clean. Applies to ALL Macal lines,
  every episode.
- **Scope:** ⚫ Engine-limit on VoiceTut `speed` → resolved 🔴 **Systemic** via the prosody transform.
- **Resolution:** owner **listened to BOTH_SLOW and approved by ear** (wps metric said "still
  fast" but pauses make it read as a natural, hesitant learner — ear is the judge).
- **Status:** ✅ **VERIFIED** (owner-approved). Baked into the synth; will apply on the next Macal synth.


### FIX-002 — Language realism: Macal speaks English to his Arabic-speaking mom
- **Location:** Ep1 cold_open + act1 (lines 1, 5, 11, 12, 13 — the mom voice-note/call)
- **Speaker:** Macal
- **Symptom:** Macal talks to his mother (in Alexandria, Egypt) in English. An Egyptian son
  would speak ARABIC to his mom — the English breaks the reality of the world.
- **Desired state:** the world must make sense — characters speak English only where it's
  realistic; intimate all-Egyptian scenes aren't staged as English dialogue.
- **Root cause:** the generator had no language-realism rule; it wrote every scene in English.
- **Scope:** 🔴 **Systemic** — a LANGUAGE REALISM RULE now in the bible (§4) + `gen_episode.py`
  story-act prompt, so ALL future scripts obey it (Option B, owner-approved).
- **Fix (rule):** English only where realistic (Dubai work/social life, or Macal deliberately
  practicing/recording English). Never stage a private call home as English; reframe as Macal
  rehearsing/recording an English voice note (fits "family thinks he made it" thread + the
  ep title "The Voice Note"), or leave it to Mahmoud's Arabic narration.
- **Fix (Ep1) — DECIDED (owner-approved):** reframe the mom scene as **Macal recording a
  voice note to his family, deliberately in English, performing the polished "successful
  expat" image they believe** (fits the season thread + the ep title "The Voice Note"); his
  English then cracks on the real Dune & Co. call. Scope = **FULL Ep1 regeneration** with the
  new rule active (cleanest continuity — coach breaks/target phrases re-derive). Timing =
  **batch with all other Ep1 script fixes → ONE regeneration, ONE re-synth** (see the
  Pending Ep1 Regeneration Batch below).
- **Rule now lives in:** `series-bible.md` §4 + `pipeline/gen_episode.py` story-act craft.
- **Status:** rule LOCKED ✅; Ep1 reframe QUEUED in the regeneration batch (framing + scope + timing all owner-approved).

---

## ⏳ PENDING Ep1 REGENERATION BATCH
> Script-level fixes that require regenerating Ep1's script. We collect ALL of them from the
> owner's listen-through, then do **ONE** full Ep1 regeneration + **ONE** re-synth (efficient).
> Synth-time/param fixes (like FIX-001 pacing) apply automatically on that same re-synth.
- [ ] **FIX-002** — reframe mom scene as an English voice-note Macal performs for family
      ("successful expat" image); English cracks on the real call. (full-episode regen)
- _(add further Ep1 script/story issues here as the owner reports them)_

**Also auto-applied on the Ep1 re-synth (no regen needed):**
- FIX-001 — Macal prosody pauses + speed 0.85 (already baked into `synth_episode_v2.py`).


### FIX-003 — Coach (Mahmoud) voice change: Omar → Abdelrahman
- **Location:** all Coach/Mahmoud Arabic lines, every episode
- **Speaker:** Coach (Mahmoud)
- **Symptom / request:** owner prefers a different Coach voice.
- **Desired state:** Mahmoud = VoiceTut **"Abdelrahman"** (was Omar; earlier Sayed).
- **Scope:** 🔴 **Systemic** — `cast.json` `cast.Coach.voice` → applies to every Coach line, every episode.
- **Fix:** set `cast.Coach.voice="Abdelrahman"` (verified: valid VoiceTut voice, free, distinct
  from Macal=Abdullah). Updated all spec references (bible §7, requirements R2.1, OPERATIONS,
  voice-refs/README, cast-decisions-b6, tasks.md SPEC AMENDMENTS + Phase C).
- **Rule now lives in:** `pipeline/cast.json` → `cast.Coach.voice`.
- **Status:** ✅ config done; **audible on the next Ep1 re-synth** (Coach lines re-render in
  Abdelrahman — part of the pending Ep1 re-synth batch, no script regen needed for this one).

### FIX-004 — Mahmoud (Coach) Arabic mispronunciations (Wave 1 seed)
- **Location:** Coach lines, all episodes
- **Speaker:** Coach (Mahmoud, VoiceTut Abdelrahman, Arabic)
- **Symptom:** many Egyptian words mispronounced (owner reported: يلا, هنتمرن, البيت, اسمعوا, في دبي→run-together, fluent).
- **Root cause:** words missing from `egyptian_lexicon.json` (VoiceTut guesses MSA voweling); AND one existing entry was WRONG (يلا→يَاللَّا).
- **Scope:** 🔴 Systemic — lexicon (G2P dict) applies to every episode.
- **Fix (Wave 1):** DeepSeek drafted Egyptian tashkeel for the top ~69 high-frequency Coach
  words (extracted from real Ep1 Coach lines) + reported failures → merged into
  egyptian_lexicon.json (34→103 words; **65 added, 1 CORRECTED: يلا يَاللَّا→يَلَّا**). Added
  phrase/brand entries (في دبي→فِي دُبَيّ to stop run-together, فلونت, يلا فلونت). DeepSeek =
  Egyptian-colloquial source (NOT MSA CATT alone; not ElevenLabs — licensing).
- **Rule now lives in:** `pipeline/egyptian_lexicon.json` (+ `prepare_ar()` applies longest-first).
- **Known edge case (Wave 2):** hamza variants (انا vs أنا) — normalize in the factory.
- **Status:** Wave 1 seeded ✅; audible on next Ep1 re-synth; Wave 2 factory will cover the full season + verify via ASR.

### FIX-005 — Mahmoud (Coach) speaks too fast
- **Location:** Coach lines, all episodes
- **Speaker:** Coach (Mahmoud, Abdelrahman)
- **Symptom:** talks too fast; needs human pacing for his character (a warm, deliberate TEACHER).
- **Desired state:** unhurried, clear, breathes at teaching beats — teacher pace (calmer than a normal speaker; different from Macal's learner-hesitation).
- **Scope:** 🔴 Systemic — teacher-prosody transform + `cast.Coach.speed` → every Coach line.
- **Fix:** `kaggle/calibrate_mahmoud_pacing.py` tests RAW vs teacher-PROSODY (light '...'
  breaths at boundaries) × speeds 0.80/0.85/0.90/1.00, loading the Wave-1 lexicon so owner
  hears pacing + pronunciation together. Owner picks → bake teacher_prosody() + speed into synth.
- **Status:** calibration built; owner to run + pick (W1d). Then baked into synth_episode_v2.py like Macal.

### FIX-004 UPDATE — ROOT CAUSE CONFIRMED: we were over-tashkeeling (H2)
- **Diagnostic result (owner):** BARE text = "all amazing" — VoiceTut natively says جماعة (hard-g),
  يلا (right vowel), and correctly KEEPS qaf on قانون/القاهرة/ثقافة while making قلب->hamza.
  So VoiceTut's own Egyptian brain is correct; **OUR lexicon tashkeel was FIGHTING it and
  causing the errors** (confirmed: وقفة->our وَقْفَة made a hard-ت ending; متفهمش->our مِتِفْهَمِش
  made it robotic; the يلا->يَاللَّا bug earlier).
- **Root fix (systemic):** LIGHT-TOUCH lexicon — kept only 12 entries (brand/loan words +
  3 proven stumbles متنساش-class); DISABLED the other 91 (preserved in `_disabled_lexicon`,
  re-enable individually only if a word regresses bare). Stop fighting the model.
- **Impact:** the 818-word Wave-2 tashkeel factory is now MOSTLY UNNECESSARY — its role
  shrinks to "find the FEW words VoiceTut truly can't say (like متفهمش) via ASR-verify and fix
  only those," not tashkeel-everything. Big simplification (owner's "stop the word-by-word grind").
- **Still-open stragglers:** وقفة (ة-ending) + متفهمش (cluster) — now go BARE; re-synth will
  show if bare fixes them; if متفهمش still fails, ONE targeted respelling (verified by ASR).
- **Status:** light-touch lexicon done ✅; audible on next Ep1 re-synth; two stragglers to confirm.

### FIX-005 VERIFIED — Mahmoud pacing baked in
- Owner picked **PROSODY @ speed 0.80**. Baked `teacher_prosody()` into synth_episode_v2.py
  (light '...' breaths after sentence enders + before taught phrases; lighter than Macal's) +
  `cast.Coach.speed=0.80`. Applied to Coach Arabic lines only, synth-time (script.json clean).
- **Status:** ✅ VERIFIED; audible on next Ep1 re-synth.
