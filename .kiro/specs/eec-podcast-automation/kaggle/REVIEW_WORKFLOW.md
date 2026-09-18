# Two Worlds — Review & Fix Workflow (Human-in-the-Loop)

The review dashboard lets you fix mispronounced/wrong clips **one at a time**
without re-generating the whole episode. It runs inside Colab/Kaggle next to the
GPU, so "Regenerate" takes seconds.

## The pieces
| File | Role |
|------|------|
| `manifest_lib.py` | The single source of truth: line order, per-line status, text fingerprint. |
| `regen_engine.py` | GPU worker — re-synthesizes ONE line with the same engine/voice/params. |
| `streamlit_review.py` | The review UI (remote control). Holds no synth logic. |
| `review_app_launcher.py` | Colab/Kaggle notebook cells that install, fetch, and launch. |

## How to run (Colab — recommended)
1. New Colab notebook → Runtime → **GPU**, Internet ON.
2. Paste **CELL 1** from `review_app_launcher.py` → run (installs Streamlit + engines).
3. Upload the two episode zips (`ep01_ar.zip`, `ep01_en.zip`) into `/content`
   (Files panel), or mount Drive and set `EEC_ZIP_DIR` to the raw-audio folder.
4. Paste **CELL 2** → run (fetches code/data, unpacks, merges the manifests).
5. Paste **CELL 3** → run → open the printed public URL.

## The loop
1. **Listen** to a clip in the list (grouped by section: cold_open, act1, …).
2. If a word is wrong, **edit the text** in that line's box → it turns
   *"needs regen"* (the text fingerprint changed).
3. Hit **🎤 Regenerate this clip** → the GPU re-synthesizes just that line and
   updates the manifest. Everything else is untouched.
4. When happy, hit **🎬 Re-assemble episode** → ffmpeg stitches the full episode
   (lossless concat + one loudnorm pass) → download `ep01_audio_plain.m4a`.

## Fixing pronunciation for ALL cast (permanent)
Editing a line's text fixes only that clip. To make a word pronounce correctly
for **every** voice **forever**, add it to `pipeline/egyptian_lexicon.json`
(the shared brain) — then every future synth + regen applies the fix. The QA
step already flags candidate words into `qa_flagged.json` during synthesis.

## Notes / gotchas
- VoiceTut (Arabic) and Chatterbox (English) can clash on `transformers`/`torch`
  in one kernel. For review you usually fix one language at a time — the engine
  for that language loads lazily on first use. If you must fix both in one
  session and hit a clash, run two review sessions (one per language).
- The manifest is authoritative: an edit+regen you make in the app survives a
  reload. Re-generating the whole SCRIPT upstream is a separate, explicit reset
  (`manifest_lib.reset_from_script`) — a routine reload never wipes your fixes.
- Tunnels: localtunnel (default, no signup), ngrok (needs a free token, most
  stable), cloudflared (no signup) — all shown in CELL 3.
