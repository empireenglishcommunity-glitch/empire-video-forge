# Step 1 Findings — Kaggle path PROVEN (live run, 2026-09-03)

> Build-order step 1 from `AUTO-EDIT-STAGE-DESIGN.md` — *prove the Kaggle
> path* — was executed end-to-end against real content on a free Kaggle T4.
> **Result: it works.** The owner reviewed the finished clips and approved the
> quality. This doc records what was proven, the exact fixes required, and the
> honest caveats, so the next run is reproducible and step 2 can begin.

## Verdict

A long video → finished, captioned, 9:16 clips, **$0**, on a free Kaggle GPU,
driven entirely over the reused `remote_exec_bridge.py`. Confirmed on:
- The bundled `demo-openshorts.mp4` (silent → Gemini vision path)
- A real Arabic teaching Short (speech → transcript path), the true test

From one 41s Arabic video the pipeline produced **2 clips**, each with an
AI-picked moment, a virality score, an Arabic title/hook, per-platform
captions + hashtags, a 9:16 frame, and **burned-in Arabic subtitles**.

## What was proven working

| Capability | Result |
|---|---|
| Runs on free Kaggle T4 (2× T4, 15GB each, 31GB RAM) | ✅ |
| **No Docker/compose needed** — `main.py` is a standalone CLI | ✅ (resolves the design's biggest step-1 unknown) |
| GPU transcription (faster-whisper, CUDA) | ✅ |
| AI clip selection (Gemini 3.1 Flash-Lite) | ✅ ~$0.0013/video, free-tier |
| Local-LLM moment-scoring supported (`LLM_BASE_URL`) | ✅ confirmed in `.env` — validates design §4 Option B |
| 9:16 face-tracked reframe (MediaPipe + YOLO) | ✅ 1920×1080 → 1080×1920; passes through already-vertical |
| Burned-in captions | ✅ (after the font fix below) |
| Auto per-platform titles/hooks/captions (Arabic) | ✅ |
| Speed | ~2.5 min/video warm; +~90s one-time on a fresh session for the `large-v3` model download |

## The fixes required (bake these into the setup notebook)

Two real problems surfaced. Both are now understood and fixed.

### 1. Dependency vise: protobuf / mediapipe / TensorFlow

OpenShorts pins `mediapipe==0.10.14`, which drags in an old protobuf.
Kaggle's pre-installed TensorFlow 2.20 needs protobuf ≥5.28, and mediapipe
imports TF lazily — so:
- protobuf 4.x → TF import breaks mediapipe's import
- protobuf 5.x → mediapipe 0.10.14's graph parser fails at runtime
  (`Error parsing text-format mediapipe.CalculatorGraphConfig`)

**Fix that works:** upgrade mediapipe to `0.10.21` (still has the legacy
`mp.solutions` API that `main.py` uses; `1.0.x` removed it — too new) and
**uninstall TensorFlow** (OpenShorts does not use it; only mediapipe's
optional doc-import pulled it in). After that, `mp.solutions.face_detection`
initialises cleanly and `torch.cuda.is_available()` is True.

```bash
pip install -r requirements.txt
pip install 'mediapipe==0.10.21'
pip uninstall -y tensorflow tensorflow-cpu tf-keras keras
```

### 2. Arabic captions rendered as tofu boxes (☐☐☐)

OpenShorts' auto-caption style hardcodes the font to **Anton**, and its
bundled fonts (`Anton-Regular.ttf`, `NotoSerif-Bold.ttf`) have **no Arabic
glyphs** — so every Arabic subtitle character burned in as an empty box. (The
source video's own baked-in caption was fine; only the AI-added subtitles
broke.)

**Fix that works:**
```bash
apt-get install -y fonts-noto-core fonts-noto-cjk   # provides Noto Sans/Naskh/Kufi Arabic
# in subtitles.py, AUTO_CAPTION_STYLE:  "font_name": "Anton"  ->  "Noto Sans Arabic"
# (also add an Anton->Noto Sans Arabic alias in fonts/openshorts-fontmap.conf as a safety net)
```

### 3. Whisper model: use `large-v3`, not `small`, for Arabic

`WHISPER_MODEL=small` garbled Egyptian/colloquial Arabic
(e.g. produced `عاست سعلم انجليش` — nonsense). `large-v3` produced coherent,
accurate transcription. The T4's ~15GB VRAM handles `large-v3` fine, so the
8GB-laptop concern from the design doc's open decisions is moot on Kaggle.

```bash
export WHISPER_MODEL=large-v3 WHISPER_DEVICE=cuda WHISPER_COMPUTE=float16
```

## The exact command that worked

```bash
cd openshorts
export WHISPER_MODEL=large-v3 WHISPER_DEVICE=cuda WHISPER_COMPUTE=float16
# GEMINI_API_KEY loaded from Kaggle Secrets into .env (never printed, never committed)
python main.py -i /kaggle/input/<dataset>/myvideo.mp4 -o /kaggle/working/final_clips --format vertical
# outputs: subtitled_*_clip_N.mp4  +  *_metadata.json (titles/hooks/per-platform captions)
```

CLI flags that matter: `-i` file **or** `-u` YouTube URL; `-o` output dir;
`--format vertical`; `--skip-analysis` converts the whole video with no LLM
(reframe+caption only, no clip-picking) — useful for a no-key smoke test.

## Honest caveats (real, not dealbreakers)

- **YouTube `-u` download is unreliable from Kaggle IPs** — hit "Sign in to
  confirm you're not a bot". **Upload the source file to Kaggle instead** (as
  a Dataset) and use `-i`. This is the recommended input path.
- **English loanwords get phonetically transliterated** into Arabic
  (e.g. "assessment" → "اسيسمنت"). Minor; the downstream human-review step
  catches it. This is the honest ceiling — "one glance before posting", not
  "zero-touch".
- **Kaggle sessions are ephemeral** — idle-out (~40 min) and manual restart
  both wipe `/kaggle/working/`. Re-run setup each fresh session. The `.env`
  holding the Gemini key dies with the session (good), but **stop the session
  when done** as hygiene.
- **`large-v3` adds a one-time ~90s model download** per fresh session.

## Security notes (as practised during the run)

- The Gemini key was stored in **Kaggle Secrets** and loaded into the
  session's `.env` via `UserSecretsClient` — its value was never printed to
  output nor pasted into chat. (An earlier key that was accidentally exposed
  was revoked and replaced first.)
- The `remote_exec_bridge.py` tunnel is an unauthenticated temporary shell;
  URL shared only in-session, session stopped afterward.

## Next: build-order step 2

Step 1 is closed. Step 2 (from the design doc): **wire the inbox → Drive
routing folders** so a dropped video is auto-processed and the finished clips
land in `01-EEC-only/` / `02-EEC-and-MACAL/` / `03-MACAL-only/` for the
existing social-publishing pipeline to pick up. The `generate_notebook.py`
should also be updated to bake in the three fixes above so future runs are a
single clean pass.
