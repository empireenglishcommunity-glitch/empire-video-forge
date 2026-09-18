# Two Worlds — Ep1 Status & Session Handoff

> Checkpoint written to survive a session switch. **Focus: finish Episode 1
> (owner reviews the assembled audio → fixes as needed → post), THEN Ep2.**
> Nothing about Ep2 proceeds until Ep1 is posted.

## LOCKED-DOWN PROGRESS (the real, proven state)
- **Ep1 was generated with the REAL voice models** — Arabic = VoiceTut
  (Coach = "Sayed") through the shared Egyptian lexicon; English = Chatterbox
  (cloned character refs). This is done, not stubbed.
- **The episode is assembled**: `ep01_audio_plain.m4a` (40.6 min, 276 lines) is
  built and lives on the server.
- **Models are locked.** Auditions are complete and the cast is chosen; the
  audition/experiment notebooks have been removed from the repo (they served
  their purpose). The production synth path is the only thing that remains.
- **The Human-in-the-Loop review tool has been RETIRED.** The owner reviews the
  assembled audio directly (not through the Streamlit/Colab regenerate loop),
  so `streamlit_review.py`, `review_app_launcher.py`, `regen_engine.py`, and
  `REVIEW_WORKFLOW.md` were deleted. If a specific clip needs a fix, re-run the
  production synth notebook for that line, or add the word to the shared lexicon
  and re-synth.

## THE ONE OPEN ITEM
Owner is **reviewing the assembled Ep1 audio** for Arabic pronunciation. Any word
that's wrong gets fixed the permanent way — add it to
`pipeline/egyptian_lexicon.json` (the shared pronunciation brain, one fix → every
cast voice says it right forever) — then re-synth the affected lines with the
production notebook and re-assemble. Prefer the lexicon fix over a one-off.

## PRODUCTION PIPELINE (what actually makes an episode)
| File | Role | Proven with REAL model? |
|------|------|-------------------------|
| `kaggle/synth_episode_ar.py` | Arabic synth pass (VoiceTut + lexicon), manifest-driven | ✅ Ep1 |
| `kaggle/synth_episode_en.py` | English synth pass (Chatterbox + refs), manifest-driven | ✅ Ep1 |
| `kaggle/synth_arabic_qa.py` | Arabic synth + ASR-QA that flags words for the lexicon | ✅ |
| `kaggle/manifest_lib.py` | Shared source of truth (line order, status, text hash) | ✅ Ep1 (276/276) |
| `pipeline/assemble_audio.py` | Manifest-driven ffmpeg assembly | ✅ Ep1 (40.6 min) |
| `pipeline/manifest_lib.py` | Server-side copy of the manifest lib (byte-identical) | ✅ |

> Note: `manifest_lib.py` intentionally exists in BOTH `kaggle/` and `pipeline/`.
> The Kaggle synth notebooks fetch the `kaggle/` copy over raw GitHub at runtime;
> the server assembler imports the `pipeline/` copy locally. They are identical —
> keep them in sync if either is edited.

## THE PLAN TO FINISH EP1
- **Step 1 — Owner reviews Ep1** (`ep01_audio_plain.m4a`), notes any mispronounced
  Arabic words.
- **Step 2 — Fix them permanently.** Add each word to `pipeline/egyptian_lexicon.json`,
  re-run the Arabic synth notebook for the affected lines, re-assemble.
- **Step 3 — Owner approves the final audio.**
- **Step 4 — Post Ep1** (owner adds music/video/cover, then publish via the
  YouTube forwarder + RSS feed). THEN move to Ep2.

## WHERE EVERYTHING LIVES
- **Repo**: `/projects/sandbox/empire-video-forge`
- **Branch**: `podcast-v2-review-and-publish` → **PR #32** (open, NOT merged).
- **Spec dir**: `.kiro/specs/eec-podcast-automation/`
  - `kaggle/` — production synth notebooks (`synth_episode_ar`, `synth_episode_en`,
    `synth_arabic_qa`), `manifest_lib.py`, `README.md`
  - `pipeline/` — server scripts (assemble_audio, run_podcast, publish_*,
    egyptian_lexicon.json, cast.json, manifest_lib.py, PODCAST_DISTRIBUTION.md,
    SECURITY_ROTATION.md)
  - `EP1_STATUS_AND_HANDOFF.md` — THIS FILE
- **Server**: `ssh eec-editor` (⚠️ fail2ban bans rapid reconnects — use SINGLE
  sessions, wait ~45s after a refusal). Podcast home `/opt/eec-podcast`.
  - `episodes/ep01/synth/` — the 276 line WAVs + manifest.json + manifest.ar/en.json
  - `episodes/ep01/script.json` — the 276-line master (title "The Arrival")
  - `episodes/ep01/ep01_audio_plain.m4a` — assembled 40.6 min
  - `.env` (chmod 600) — EEC_LLM_* (OpenRouter, Gemini-free)
- **Drive raw-audio** (`1GLKvNq3LAKZ6BaACIMvYeUSJomFErav0`): ep01_arabic.zip,
  ep01_english.zip, EEC_TwoWorlds_Ep01_The-Arrival_plain.m4a
- **Voice engine**: Arabic = VoiceTut (Coach = Sayed), English = Chatterbox. Both
  on Kaggle GPU (they clash in one kernel → two notebooks). Server has NO GPU —
  never synth on the server.

## ⚠️ PREMATURE / TO DECIDE (do NOT act until Ep1 is posted)
- **Ep2 script was generated prematurely** (`episodes/ep02/script.json` exists;
  `season.json` advanced to `current_episode: 3`). This jumped ahead. DECISION
  NEEDED once Ep1 is posted: leave it, or roll `season.json` back to 2 and remove
  ep02 until Ep1 ships.

## SANDBOX GOTCHAS
- No ffmpeg / no soundfile locally in the sandbox — heavy audio ops run on the
  server (ffmpeg 8.0.1) or in Colab/Kaggle.
- `str_replace`/file tools operate on the LOCAL repo, NOT the server — push edits
  to the server with `cat file | ssh eec-editor 'cat > /path'`.
- 12 live containers on the server — never disrupt them.
