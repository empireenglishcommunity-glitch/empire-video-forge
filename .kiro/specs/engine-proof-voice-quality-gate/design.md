# Engine Proof / Voice-Quality Gate — Design

> Implements `requirements.md`. Every claim below about engine capabilities was VERIFIED
> against the actually-installed library code (introspection kernels, real signatures/
> docstrings/source) — never assumed from README prose or third-party blog posts. Where a
> plausible-sounding capability turned out NOT to exist in our installed version, that is
> recorded explicitly so it is never re-attempted from a stale assumption.

## 1. Verified engine capabilities (the ground truth this design is built on)

### 1.1 VoiceTut (`voicetut-tts`, Arabic — LOCKED production)
Introspected `VoiceTutTTS.synthesize()` signature and `speakers.py` source directly:
```
synthesize(text, *, speaker=None, ref_audio=None, ref_text=None, instruct=None,
           language=None, normalize=True, output=None, params=None, **param_overrides)
```
- **`instruct` is an ALTERNATIVE voice-selection mode, not a modifier.** The engine enforces
  exactly ONE of `speaker=` / `ref_audio=` / `instruct=` (`_resolve_voice()` raises if more
  than one is set). You cannot do `speaker="Essam", instruct="energetic"` — there is no
  "keep this speaker but perform it differently" hook.
- **Style tags (`STYLE_TAGS` dict in `speakers.py`, e.g. Essam→["جاد","واضح"]) are, per the
  module's own comment, "used by the web UI chips. Purely cosmetic."** They attach to a
  `Speaker` dataclass for display only and are NEVER read by `synthesize()` or the
  generation path. **Do not use style tags as a performance lever — they do nothing.**
- **The real, load-bearing knobs are `GenerationParams`:** `num_step`, `guidance_scale`,
  `speed`, `duration`, `t_shift`, `denoise`, `postprocess_output`, `layer_penalty_factor`,
  `position_temperature`, `class_temperature`. FIX-008 already proved `guidance_scale` is the
  single highest-leverage knob (2.5→1.5 calmed pitch jitter, +0.5 UTMOS across most voices).
- **Pacing is NOT a text or engine-time concern** — FIX-007 proved text-injected pauses
  (commas/ellipses) make VoiceTut read each fragment as its own sentence, causing exactly
  the choppiness we spent a full session fixing. Pacing is applied AFTER synthesis via
  ffmpeg `atempo` (`post_processing.atempo` in `cast.json`). This stress test must not
  reintroduce text-injected pauses.
- **Practical implication for the Arabic stress-test script:** performance direction comes
  from (a) the WORDS themselves (Egyptian colloquial phrasing already carries energy/
  hesitation — "يلا!" reads differently from "يلا..."), (b) per-line `guidance_scale`
  variation if we want to deliberately test calm-vs-energetic transitions at the ENGINE
  level (not a text cue), and (c) natural code-switching in the text (proven to work — Macal
  already code-switches to Arabic in production).

### 1.2 Qwen3-TTS (`qwen-tts`, English — LOCKED production via VoiceClone)
Introspected `Qwen3TTSModel` directly — it exposes FOUR generation methods, and our
production pipeline uses only one of them:
| Method | Instruct support? | Used in production? |
|---|---|---|
| `generate_voice_clone()` | **No `instruct` param** | ✅ yes — every English character |
| `create_voice_clone_prompt()` | n/a (prompt builder) | ✅ yes |
| `generate_voice_design()` | **Yes** — `instruct` is a first-class natural-language param | used only to ORIGINATE a voice identity (frozen once, per Option B) |
| `generate_custom_voice()` | **Yes** — `speaker` + optional `instruct` together | not used at all today |

- **The natural-language "semantic style control" the research notes described is real —
  but it lives on `generate_voice_design` / `generate_custom_voice`, NOT on
  `generate_voice_clone`**, which is what every locked character actually uses. This means:
  our LOCKED cast identities cannot currently take an `instruct=` performance direction
  without either (a) switching them off VoiceClone (re-opening the voice-drift problem
  Option B exists to prevent), or (b) testing `generate_custom_voice` as a THIRD engine
  variant in a future gate (out of scope here).
- **What DOES work on `generate_voice_clone` today:** `**kwargs` forwards straight to
  HuggingFace `generate()` — `temperature`, `top_k`, `top_p`, `repetition_penalty`,
  `do_sample` are real, usable knobs for expressiveness/variation.
- **Practical implication for the English stress-test script:** exactly as the research
  notes correctly said — **write the emotion into the text itself** ("Wait, hold on — the
  interview is TODAY?" carries the panic in its own punctuation/word choice), and vary
  `temperature`/`repetition_penalty` per line if we want to deliberately test flat-vs-
  expressive delivery. Do not invent an `instruct=` call on the clone path — it will error.

### 1.3 MOSS-TTSD (`OpenMOSS-Team/MOSS-TTSD-v1.0`, English — AUDITIONED CANDIDATE)
Verified via real Kaggle T4×2 runs (not docs):
- **API is fundamentally different in shape:** a `[S1]`/`[S2]`.../`[S5]` tagged CONTINUATION
  call — you supply each speaker's reference audio + its transcript as a prefix, then the
  FULL multi-speaker dialogue text, and the model generates the entire exchange (turn-taking,
  timing, overlaps) in ONE pass. This is NOT per-line clone-and-stitch like Qwen3-TTS in our
  pipeline — it's the actual reason to audition it (native conversational rhythm vs. our
  assembled rhythm).
- **`device_map="auto"` is broken for this model** on multi-GPU: it scatters `emb_ext` (the
  extra multi-codebook audio embedding table) onto a different GPU than
  `language_model.embed_tokens`; the model's `get_input_embeddings()` sums these two tensors
  directly with no device move → `RuntimeError: cuda:0 and cuda:1`. **Fix (verified working):**
  build the device map manually via `accelerate.infer_auto_device_map` with an ASYMMETRIC
  `max_memory` budget (`{0: "8GiB", 1: "13GiB"}`, since GPU0 also hosts the embedding/head
  tables and needs a smaller transformer-layer allotment), then force `emb_ext` onto the
  same device as `embed_tokens`. See `kaggle/moss_ttsd/gen_ttsd.py` (`load_model()`) for the
  exact, working implementation — reuse it verbatim, do not re-derive.
- **Single-GPU loading (fp16 or naive 8-bit) OOMs** on one T4 (~14.5GB usable) — this model
  REQUIRES Kaggle's T4×2 (confirmed `enable_gpu: true` gives 2×15.6GB on this account).
- **Generation params** (from the model card): `audio_temperature` (default 1.1, higher =
  more variation), `audio_top_p` (0.9), `audio_top_k` (50), `audio_repetition_penalty` (1.1).
- **License:** Apache 2.0 (verified — fetched the actual `LICENSE` file from the GitHub repo,
  not just a badge). **Languages:** the model's own README lists Arabic among 20 supported
  languages — logged as an OPEN QUESTION (see requirements.md Non-goals), not evaluated here.

### 1.4 Scripting engines (DeepSeek + Qwen-text via OpenRouter)
- `llm_backend.chat(prompt, temperature, engine="deepseek"|"qwen")` — both verified live
  with real round-trip calls through the actual production module (not a side script).
  `engine="qwen"` routes to OpenRouter (`qwen/qwen3-max`, already-live `OPENROUTER_KEY`,
  zero new credentials).
- `dialogue_polish.py` already implements the adversarial critic pattern this gate's scripts
  must use: `polish_story_lines()` (STORY English only, length-bounded, speaker-preserving,
  defensive `[Speaker]`-label stripping) and `polish_coach_direction()` (Arabic-safe: never
  rewrites text, only adds a delivery note). **Reuse these functions directly** — do not
  build a parallel critic for the stress-test scripts.

## 2. Stress-test script design (per G4)

### 2.1 Why NOT a normal episode script
A polished lesson script (cold_open → coach_break → phrase_of_episode) is optimized to sound
GOOD, which is the opposite of a stress test. The proof-clip scripts are deliberately
adversarial toward the engines: rapid register shifts, code-switching, interruptions,
questions — the specific patterns that produced FIX-008's worst UTMOS scores and that
generic "safe" dialogue would never exercise.

### 2.2 Arabic stress-test script (VoiceTut, ~5 min, 3+ characters mixed gender)
- **Cast:** Mahmoud/Essam (locked, male) + at least one FEMALE VoiceTut voice (audition per
  G6.2 — no female voice has been diagnostically scored yet) + one more male or female voice
  from the pool (`Omar` and `Sarah`/`Yasmin` are reasonable starting candidates per the
  existing `arabic_voice_pool`, subject to the G6.1 audition).
- **Content pattern (per G4.1):** alternating calm/energetic lines across speakers (test
  `guidance_scale` variation, NOT text-injected pauses); at least 3 Arabic↔English
  code-switch moments (Egyptian colloquial style, e.g. "عندي meeting بكرة" — the exact
  pattern the research notes flagged, and the exact pattern that historically scored worst
  in FIX-008's diagnostic); one short drill/imperative exchange (mirrors the Coach teaching
  pattern that produced the worst-scoring lines before FIX-008).
- **Written via the real pipeline:** DeepSeek drafts the Arabic stress dialogue with full
  Egyptian tashkeel (per the FIX-004/FIX-009 lesson — light-touch, do not over-diacritize);
  `polish_coach_direction()`-style pass may suggest DELIVERY notes only, never rewrite the
  Arabic text itself.

### 2.3 English stress-test script (Qwen3-TTS vs MOSS-TTSD, ~5 min, 3+ characters mixed
gender, SAME script for both engines)
- **Cast:** 3 existing Qwen3-TTS characters spanning at least one male + one female voice
  (e.g. `Nour` [F, General American] + `Tarek` [M, polished Egyptian] + `Farida` [F, Gulf] or
  `Qureshi` [M, Pakistani] — mix per G6.1's audition-based pick, not by assumption).
- **Content pattern (per G4.2):** written-in emotion via text semantics ("Wait, hold on...",
  "No way — seriously?"), NOT bracket tags; rapid pace/register shift (calm → excited/loud)
  across consecutive lines/speakers; genuine overlapping reactions (one speaker cuts in);
  at least one real question-answer-reaction chain (not monologue).
- **Written via the real pipeline:** DeepSeek drafts, `polish_story_lines()` runs the
  adversarial critic pass (catches on-the-nose emotion lines, dead greetings, clichés — the
  exact failure modes it already caught live during Task #2's verification).
- **Same text, two renders:** once through Qwen3-TTS `generate_voice_clone()` (per-line,
  stitched — our current production path), once through MOSS-TTSD's continuation API
  (whole-exchange, native turn-taking) using the SAME three characters' existing
  `voice-refs/*.wav` as MOSS-TTSD's reference clips (it accepts arbitrary reference audio,
  so our existing frozen refs work directly — no new voice assets needed).

## 3. Generation pipeline (reuses existing, proven infrastructure)

```
DeepSeek draft (llm_backend.chat(engine="deepseek"))
        │
Qwen-text adversarial polish (dialogue_polish.polish_story_lines / polish_coach_direction)
        │
   ┌────┴─────────────────────────────┬──────────────────────────────┐
   │  ARABIC clip                     │  ENGLISH clip                │
   │  VoiceTut, synth_all_in_one.py   │  Qwen3-TTS (existing path)    │
   │  pattern (natural text + atempo, │  AND MOSS-TTSD                │
   │  FIX-007 discipline)             │  (kaggle/moss_ttsd/gen_ttsd.py)│
   └────┬─────────────────────────────┴──────────────────────────────┘
        │
   diagnose_episode.py (WhisperX + Parselmouth + UTMOS) → DeepSeek report
        │
   owner ear-test (the actual gate — G5)
```

- **Autonomous execution:** every generation step runs the same way the rest of this
  project's Kaggle work has run — pushed via the Kaggle API, polled to completion, output
  pulled back. No manual cell-by-cell notebook babysitting.
- **Delivery:** both proof clips (and, for the English side, both engine variants) land in
  the owner's Drive `output` folder with clear, comparable filenames (mirroring the
  `Mahmoud AUDITION -` naming convention already established in FIX-008), so the owner can
  A/B by ear without needing this document open.

## 4. What happens after the gate (not built here, just the fork points)
- **Pass on both G1 clips + G5 owner verdict:** Phase D resumes — batch Episodes 2-10 through
  the now-proven pipeline.
- **English candidate decision:** if MOSS-TTSD wins the head-to-head, a FOLLOW-ON spec is
  needed to route it into `cast.json`/`synth_all_in_one.py` production (a new "third engine"
  wiring, analogous to how Qwen3-TTS was integrated) — not automatic just because it audits
  well; the owner decides per G5.3.
- **Fail on any G criterion:** the specific failure is logged as a new FIX-0XX entry in
  `episode-fixes-log.md`, root-caused (never patched blind), and this gate is re-run — same
  discipline as every fix in this project to date.
