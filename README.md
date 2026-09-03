# Empire Video Forge

The **video content-production pipeline** for the Empire ecosystem: turn
long-form footage into finished, captioned 9:16 short clips, automatically
and at $0, then hand them to the social-publishing pipeline for
multi-platform posting.

**Parent brand:** Empire English Community — for full cross-project context,
see `empireenglishcommunity-glitch/empire-nexus`.

## Why this repo exists (scope boundary)

This is a **distinct concern** from the repos it touches, and is kept
separate on purpose — the same reasoning `empire-server-forge`'s README uses
to justify its own split:

- It is **not** server/infra ops. That is `empire-server-forge` (n8n, MCP
  server, hardening, admin bot). The video pipeline is *driven by* n8n but is
  not part of running the box.
- It is **not** a single brand's product. It is **cross-brand** — it produces
  clips for both **Empire English Community (EEC)** and **MACAL**, with a
  safety-critical routing rule (MACAL content must never reach EEC). So it
  does not live inside either brand's repo.
- It is the **video** sibling of `macal-empire-image-forge` (the image
  content-generation pipeline). Same family — "$0 content production reusing
  free GPU" — different medium.

## History note

Started 2026-09. The design docs here were first drafted inside
`empire-server-forge` (PRs #4/#5 there) while the downstream social-publishing
design lived beside them, then moved out to this dedicated repo so
infrastructure ops and content production are not mixed. See the
`empire-server-forge` cleanup PR that removed them there.

## What's in this repo

| Path | Purpose |
|------|---------|
| `docs/AUTO-EDIT-STAGE-DESIGN.md` | Design for the auto-editing stage — long video in, finished 9:16 clips out. |
| `kaggle/` | **Build-order step 1** — the free-GPU setup notebook (`generate_notebook.py` → `AutoEdit_Kaggle_Setup.ipynb`) + the reused `remote_exec_bridge.py`, to prove one video end-to-end. Start with `kaggle/RUN_GUIDE.md`. |

## The pipeline in one line

```
long video → [ this repo: AI cut · reframe 9:16 · caption · hook ] → Drive routing folder
           → [ empire-server-forge n8n: stage · approve · fan out to 6 destinations ]
```

The hand-off between the two halves is deliberately narrow: **"a finished
clip appears in a Drive routing folder."** This repo owns everything upstream
of that line; `empire-server-forge`'s social-publishing pipeline owns
everything downstream.

## Compute — reused, not rebuilt

Heavy processing runs on **Kaggle's free GPU tier**, driven by the same
remote-exec bridge pattern already proven in `macal-empire-image-forge`.
Moment-scoring can use the **local Ollama** already installed by
`macal-overseer`. Nothing here duplicates infrastructure the org already
runs — see the design doc for the full rationale.

## Status

**Step 1 (prove the Kaggle path) is scaffolded, not yet run.** The design is in
`docs/AUTO-EDIT-STAGE-DESIGN.md` (build order in §7); the step-1 setup lives in
`kaggle/`. Nothing is deployed — the next action is to run the Kaggle notebook
against one real video and record the speed/quality result.
