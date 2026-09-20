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
- **Fix:** lower Macal `speed` (1.0 → **calibrating**: 0.75 / 0.85 / 0.95 audition first, since
  VoiceTut speed direction must be confirmed by ear before locking).
- **Rule now lives in:** `pipeline/cast.json` → `cast.Macal.speed`.
- **Status:** in progress — calibration audition built (`kaggle/calibrate_macal_speed.py`).
