# Auto-Edit on Kaggle — Run Guide (build-order step 1)

> Follow this top to bottom on your first run. This is **step 1** of
> `docs/AUTO-EDIT-STAGE-DESIGN.md`: *prove the Kaggle path* by processing
> **one real video** end-to-end and measuring speed + quality on a free GPU.
> It is not the finished automated pipeline — it is the go/no-go test the whole
> design hinges on.
>
> **Cost: $0.** Runs on Kaggle's free GPU tier (T4/P100, ~30 hrs/week, no
> credit card). Same zero-cost pattern as `macal-empire-image-forge`.

## What's in this folder

```
kaggle/
├── RUN_GUIDE.md              ← you are here
├── generate_notebook.py      ← source of truth; regenerates the .ipynb
├── AutoEdit_Kaggle_Setup.ipynb  ← build artifact (do not hand-edit)
└── remote_exec_bridge.py     ← reused verbatim from macal-empire-image-forge
```

If you edit the notebook, edit `generate_notebook.py` and re-run
`python generate_notebook.py` — never hand-edit the `.ipynb`.

## Step 0 — Kaggle account (one-time)

1. Create a free account at kaggle.com (no credit card).
2. Verify your phone if prompted (Kaggle requires it to enable GPU).

## Step 1 — Upload the notebook + bridge

1. kaggle.com → Create → New Notebook.
2. File → Upload Notebook → `AutoEdit_Kaggle_Setup.ipynb`.
3. Add `remote_exec_bridge.py` so the notebook can find it. Easiest: in the
   notebook's first code cell, paste the file's contents to `/kaggle/working/`,
   **or** add it as a notebook input dataset (the notebook checks
   `/kaggle/input/empire-video-forge/remote_exec_bridge.py`).
4. Right sidebar → **Accelerator → GPU T4 x2** (or P100).

## Step 2 — Run the setup cells

Run cells 1–5 top to bottom:

- **Cell 1 (GPU check)** must show a GPU. If not, fix the Accelerator setting.
- **Cell 4 (`.env`)** — paste a **free Gemini key** from aistudio.google.com
  for the simplest first run, *or* leave it blank and configure a local
  `LLM_BASE_URL` (design §4 Option B). The key stays in this ephemeral
  session only — **never commit it.**
- **Cell 5 (start API)** tries a few entrypoints until `/health` responds.

> **If Cell 5 never goes healthy:** that is a legitimate step-1 finding, not a
> failure of the plan. OpenShorts is a Docker-Compose app and Kaggle is not a
> clean Docker host. Capture the log it prints and fall back to the parts-based
> CLI (`faster-whisper` + `PySceneDetect` + `ffmpeg`) from design doc §2 — same
> compute path, simpler to run headless.

## Step 3 — Hand control to Kiro

1. Run **Cell 6** (the bridge). Leave it running.
2. Copy the printed **`BRIDGE_URL`** and paste it into the Kiro chat.
3. From there Kiro will: upload your long video, run
   `openshorts process ... --wait`, poll it, and download the finished clips —
   all over the bridge. Cell 7 lists the exact commands if you'd rather run the
   test by hand.

> **Security (same as image-forge):** the `BRIDGE_URL` is an unauthenticated
> temporary root shell on a sandboxed, ephemeral session. Only share it
> in-session, and **stop the Kaggle session when the test is done.**

## Step 4 — Record the result

Step 1 exists to produce **one data point**:

- **Wall-clock time** to process one real video on the T4.
- **Quality check:** caption sync, reframe stays on the speaker, hook text
  makes sense.

Write those numbers down (a short note in `docs/`) before anyone builds step 2.
Good result → proceed to wiring the inbox → Drive folders (design §7 step 2).
Bad result → the parts-based fallback, still on this same Kaggle compute.
