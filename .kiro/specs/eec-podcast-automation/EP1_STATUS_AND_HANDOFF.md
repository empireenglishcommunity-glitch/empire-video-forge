# Two Worlds — Ep1 Status & Session Handoff

> Checkpoint written to survive a session switch. **Focus: finish Episode 1
> (fix Arabic pronunciation → owner approves → post), THEN Ep2.** Nothing about
> Ep2 should proceed until Ep1 is posted.

## THE ONE OPEN PROBLEM
Owner listened to the assembled Ep1 plain audio (40.6 min) and heard **Arabic
pronunciation mistakes**. We designed + built a review/fix tool to solve this,
but **have NOT actually used it to fix Ep1 yet.** Ep1 audio still has the errors.

## WHAT IS PROVEN vs. NOT PROVEN (be honest with the owner)
| Component | Built | Proven with REAL model? |
|-----------|-------|-------------------------|
| `kaggle/manifest_lib.py` — clip list / source of truth | ✅ | ✅ real Ep1 (276/276) |
| `kaggle/regen_engine.py` — regenerate ONE clip on GPU | ✅ | ❌ only with a FAKE/stub TTS |
| `kaggle/streamlit_review.py` — review dashboard | ✅ | ❌ never launched once |
| `kaggle/review_app_launcher.py` — Colab runner | ✅ | ❌ never run |
| `pipeline/assemble_audio.py` — manifest-driven assembly | ✅ | ✅ Ep1 assembled 40.6min |

**=> The review tool's plumbing is proven (edit→stale→re-stitch), but
"regenerate with real VoiceTut/Chatterbox on a GPU" has NEVER been executed.
It needs ONE real test run before we trust it for the whole Ep1 review.**

## HOW THE REVIEW TOOL WORKS (option B — runs in Colab next to the GPU)
1. Owner opens a Colab notebook (free GPU), runs 3 cells from
   `kaggle/review_app_launcher.py` (install → fetch code+data+unpack zips+merge
   manifests → launch Streamlit + public URL).
2. Owner uploads the two Ep1 voice zips (or mounts Drive `raw-audio`).
3. In the browser dashboard: listen to each clip (grouped by section) → hear a
   wrong Arabic word → edit that line's text → clip turns 🟡 "needs regen" →
   click **Regenerate this clip** (GPU, seconds) → click **Re-assemble episode**
   (ffmpeg) → download the fixed `ep01_audio_plain.m4a`.

**Two fix strategies (BOTH matter):**
- One clip: edit the line's text in the app → regenerate just it.
- Permanent for ALL cast forever: add the word to
  `pipeline/egyptian_lexicon.json` (the shared pronunciation brain). This is what
  the owner asked for originally. Prefer this for any word that could recur.

## THE PLAN TO FINISH EP1 (agreed; nothing runs without owner's OK)
- **Step 1 — Prove the tool.** Launch the review app in Colab, load Ep1, and
  regenerate ONE clip for real. If it comes back clean → tool is trusted.
- **Step 2 — Owner reviews Ep1**, marks every mispronounced Arabic word.
- **Step 3 — Fix them.** Per word: "one clip" vs "add to lexicon" (prefer lexicon
  for recurring words). Regenerate affected clips.
- **Step 4 — Re-assemble → owner approves the final audio.**
- **Step 5 — Post Ep1** (owner adds music/video/cover, then publish via the
  YouTube forwarder + RSS feed). THEN move to Ep2.

Open questions for Step 1: owner has a Google account for Colab? Owner remembers
some wrong words already, or catch them fresh in the app?

## WHERE EVERYTHING LIVES
- **Repo**: `/projects/sandbox/empire-video-forge`
- **Branch**: `podcast-v2-review-and-publish` → **PR #32** (open, NOT merged).
- **Spec dir**: `.kiro/specs/eec-podcast-automation/`
  - `kaggle/` — synth notebooks + review tool (manifest_lib, regen_engine,
    streamlit_review, review_app_launcher, REVIEW_WORKFLOW.md)
  - `pipeline/` — server scripts (assemble_audio, run_podcast, publish_*,
    egyptian_lexicon.json, cast.json, PODCAST_DISTRIBUTION.md, SECURITY_ROTATION.md)
  - `EP1_STATUS_AND_HANDOFF.md` — THIS FILE
- **Server**: `ssh eec-editor` (⚠️ fail2ban bans rapid reconnects — use SINGLE
  sessions, wait ~45s after a refusal). Podcast home `/opt/eec-podcast`.
  - `episodes/ep01/synth/` — the 276 line WAVs + manifest.json + manifest.ar/en.json
  - `episodes/ep01/script.json` — the 276-line master (title "The Arrival")
  - `episodes/ep01/ep01_audio_plain.m4a` — assembled 40.6min (HAS the pronunciation errors)
  - `.env` (chmod 600) — EEC_LLM_* (OpenRouter, Gemini-free)
- **Drive raw-audio** (`1GLKvNq3LAKZ6BaACIMvYeUSJomFErav0`): ep01_arabic.zip,
  ep01_english.zip, EEC_TwoWorlds_Ep01_The-Arrival_plain.m4a
- **Voice engine**: Arabic=VoiceTut (Coach=Sayed), English=Chatterbox. Both on
  Kaggle GPU (clash in one kernel → two notebooks). Server has NO GPU — never
  synth on server.

## ⚠️ PREMATURE / TO DECIDE
- **Ep2 script was generated prematurely** (`episodes/ep02/script.json` exists;
  `season.json` advanced to `current_episode: 3`). This jumped ahead — Ep1 isn't
  done. DECISION NEEDED: set aside, or roll `season.json` back to 2 and remove
  ep02 until Ep1 is posted. (Do NOT act on Ep2 until Ep1 is posted.)

## SANDBOX GOTCHAS
- No ffmpeg / no soundfile locally in the sandbox — heavy audio ops run on the
  server (ffmpeg 8.0.1) or in Colab.
- `str_replace`/file tools operate on the LOCAL repo, NOT the server — push edits
  to the server with `cat file | ssh eec-editor 'cat > /path'`.
- 12 live containers on the server — never disrupt them.
