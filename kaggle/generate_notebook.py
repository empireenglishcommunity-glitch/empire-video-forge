"""
Generates AutoEdit_Kaggle_Setup.ipynb from plain Python cell definitions.

Same approach and conventions as
macal-empire-image-forge/kaggle/generate_notebook.py: notebooks are JSON with
a lot of boilerplate, so the reviewed source of truth is this Python script and
the .ipynb is a build artifact — regenerate it by re-running this script after
any edit.

What the generated notebook does: brings up the OpenShorts auto-edit engine on
a free Kaggle GPU (T4/P100), then hands control to Kiro via the reused
remote_exec_bridge.py so a real long video can be processed end-to-end. This is
build-order **step 1** from docs/AUTO-EDIT-STAGE-DESIGN.md — "prove the Kaggle
path" — not the finished pipeline.

Usage:
    python generate_notebook.py
    # writes AutoEdit_Kaggle_Setup.ipynb in the same directory
"""
import json
import os

CELLS = []


def md(text: str):
    CELLS.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": text.splitlines(keepends=True),
    })


def code(text: str):
    CELLS.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    })


# ---------------------------------------------------------------------------
# Cell 1 — Title / overview
# ---------------------------------------------------------------------------
md("""# Empire Video Forge — Auto-Edit Setup (Kaggle, free GPU)

Sets up **OpenShorts** (open-source AI clip generator, MIT) on Kaggle's free
GPU tier so a long video can be turned into finished 9:16 clips — captions,
face-tracked reframe, hooks — at **$0**.

This is **build-order step 1** from `docs/AUTO-EDIT-STAGE-DESIGN.md`: *prove the
Kaggle path*. The goal here is to process **one real video** end-to-end and
measure speed + output quality on a T4. It is not yet the automated pipeline.

**Compute reuse:** this mirrors the proven pattern in
`macal-empire-image-forge` (free Kaggle GPU + `remote_exec_bridge.py`). Nothing
here is new infrastructure.

**Session limits to plan around (same as the image-forge notebook):** Kaggle
sessions have a ~9-12h ceiling, a 60-min idle timeout, and **30 GPU-hrs/week**.
The environment does not survive between sessions — re-run these setup cells
each fresh start, and download your clips before the session ends. Work lives
under `/kaggle/working/` (persisted within a session).
""")


# ---------------------------------------------------------------------------
# Cell 2 — GPU check
# ---------------------------------------------------------------------------
md("""## 1. Verify GPU is available

Set the notebook's **Accelerator** (right sidebar) to **GPU T4 x2** or
**GPU P100** before running this. If this shows no GPU, stop and fix the
accelerator setting — the whole point of the Kaggle path is CUDA transcription
+ reframing (~50s/8-min video vs ~5-8 min on a CPU).
""")

code("""!nvidia-smi
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
else:
    raise SystemExit("No GPU — set Accelerator to GPU T4 x2 / P100 and re-run.")
""")


# ---------------------------------------------------------------------------
# Cell 3 — Clone OpenShorts + system deps
# ---------------------------------------------------------------------------
md("""## 2. Clone OpenShorts and install system dependencies

Clones the MIT-licensed engine and makes sure `ffmpeg` is present (it is the
cut/burn workhorse). This takes a few minutes.

> **Step-1 unknown to validate (flagged in the design doc):** OpenShorts ships
> as a Docker-Compose app (API + render-service + DB). Kaggle notebooks are not
> a clean Docker host, so this notebook runs the **backend/pipeline directly**
> rather than via `docker compose`. If a component insists on the full compose
> stack, that is exactly the finding step 1 exists to surface — record it and
> fall back to the parts-based CLI (`faster-whisper` + `PySceneDetect` +
> `ffmpeg`) described in design doc §2.
""")

code("""%cd /kaggle/working
!apt-get -qq update && apt-get -qq install -y ffmpeg >/dev/null 2>&1
!ffmpeg -version | head -1
!git clone --depth 1 https://github.com/mutonby/openshorts.git
%cd openshorts
!ls -la
print("\\nOpenShorts cloned. Inspect the repo layout above before installing.")
""")


# ---------------------------------------------------------------------------
# Cell 4 — Python deps + Whisper on GPU
# ---------------------------------------------------------------------------
md("""## 3. Install Python dependencies (GPU transcription)

Installs the backend requirements and the CLI. We pin Whisper to run on CUDA
with a turbo model — the T4 is what makes this fast. `small` is a safe start
(better than `base` on non-English audio, per OpenShorts' own `.env`
guidance); step up to `large-v3-turbo` once the pipeline is proven.
""")

code("""%cd /kaggle/working/openshorts

# Backend requirements (path may differ per repo layout — adjust if needed after
# inspecting Cell 3 output). Try common locations.
import os, subprocess
for req in ["requirements.txt", "render-service/requirements.txt", "backend/requirements.txt"]:
    if os.path.exists(req):
        print(f"Installing {req} ...")
        subprocess.run(["pip", "install", "-q", "-r", req], check=False)

# The zero-dependency CLI that drives a running instance
!pip install -q openshorts

print("Dependencies installed (review any pip errors above).")
""")


# ---------------------------------------------------------------------------
# Cell 5 — Configure .env (GPU Whisper + moment-scoring)
# ---------------------------------------------------------------------------
md("""## 4. Configure the engine (`.env`)

Two decisions here, both covered in design doc §4:

- **Whisper on GPU:** `WHISPER_DEVICE=cuda`, turbo model.
- **Moment-scoring:** paste a **free Google Gemini key** below for the simplest
  first run. The private, zero-dependency alternative (local Ollama, design §4
  Option B) is shown commented-out — OpenShorts supports any OpenAI-compatible
  `LLM_BASE_URL`, at which point the Gemini key becomes optional.

> **SECURITY:** the key you paste lives only in this ephemeral Kaggle session's
> `.env`. Never commit it, never paste it into the repo or a chat that gets
> committed — same rule as every other Empire credential.
""")

code("""import os

# --- moment-scoring: EITHER a Gemini free-tier key ... ---
GEMINI_API_KEY = ""  # <-- paste your free key from aistudio.google.com (session-only)

# --- ... OR local Ollama (design doc §4 Option B; leave Gemini blank to use) ---
# LLM_BASE_URL = "http://host.docker.internal:11434/v1"
# LLM_MODEL    = "qwen2.5:14b"

env_lines = [
    "WHISPER_MODEL=small",          # step up to large-v3-turbo once proven
    "WHISPER_DEVICE=cuda",
    "WHISPER_COMPUTE=float16",
    "TRANSCRIBE_BACKEND=whisper",
]
if GEMINI_API_KEY:
    env_lines.append(f"GEMINI_API_KEY={GEMINI_API_KEY}")
# else: configure LLM_BASE_URL / LLM_MODEL above for local scoring

with open("/kaggle/working/openshorts/.env", "w") as f:
    f.write("\\n".join(env_lines) + "\\n")

# Print WITHOUT the secret value, so this cell's output is safe to screenshot
print("Wrote .env with keys:", [l.split("=")[0] for l in env_lines])
if not GEMINI_API_KEY:
    print("No Gemini key set — configure a local LLM_BASE_URL for moment-scoring.")
""")


# ---------------------------------------------------------------------------
# Cell 6 — Start the OpenShorts API in the background
# ---------------------------------------------------------------------------
md("""## 5. Start the OpenShorts backend (API on :8000)

The CLI talks to a running instance at `OPENSHORTS_API_URL`. This starts the
backend in the background and waits for its health endpoint.

The exact start command depends on the repo layout you saw in Cell 3 — the
candidates below cover the common ones. If none come up healthy, that is a
step-1 finding: capture the error and switch to the parts-based fallback
(design §2).
""")

code("""import subprocess, time, os, urllib.request

os.environ["OPENSHORTS_API_URL"] = "http://localhost:8000"

# Try the likely backend entrypoints in order; keep the first that boots.
CANDIDATES = [
    "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000",
    "python -m uvicorn main:app --host 0.0.0.0 --port 8000",
    "python render-service/main.py",
]

log = open("/kaggle/working/openshorts_api.log", "w")
proc = None
for cmd in CANDIDATES:
    print(f"Trying: {cmd}")
    proc = subprocess.Popen(cmd, shell=True, cwd="/kaggle/working/openshorts",
                            stdout=log, stderr=subprocess.STDOUT)
    time.sleep(20)
    try:
        urllib.request.urlopen("http://localhost:8000/health", timeout=5)
        print("API is healthy on :8000")
        break
    except Exception:
        print("  ...not healthy, trying next candidate")
        proc.terminate()
        proc = None

if proc is None:
    print("\\nNo entrypoint came up. Tail the log to see why:")
    !tail -40 /kaggle/working/openshorts_api.log
    print("\\nThis is a valid step-1 result — record it and use the parts-based fallback.")
""")


# ---------------------------------------------------------------------------
# Cell 7 — Hand control to Kiro via the remote-exec bridge
# ---------------------------------------------------------------------------
md("""## 6. Hand control to Kiro (remote-exec bridge)

This is the **reused** `remote_exec_bridge.py` from `macal-empire-image-forge`
(verbatim server logic). It exposes this session over a Cloudflare quick tunnel
so Kiro can upload your video, run the clip job, poll it, and download the
finished clips — no manual file shuffling.

Run this cell, then **paste the printed `BRIDGE_URL` back into the Kiro chat.**
Leave the cell running; the tunnel auto-restarts if it drops.

> Same security note as image-forge: the tunnel is an unauthenticated temporary
> root shell on an ephemeral sandbox. Only share the URL in-session, and stop
> the session when done.
""")

code("""# The bridge file lives next to this notebook in the repo. On Kaggle, either
# upload remote_exec_bridge.py as a notebook input, or paste its contents into
# this cell. If added as a dataset input at /kaggle/input/, copy it first:
import os, shutil
for p in ["/kaggle/input/empire-video-forge/remote_exec_bridge.py",
          "/kaggle/working/remote_exec_bridge.py"]:
    if os.path.exists(p):
        if p != "/kaggle/working/remote_exec_bridge.py":
            shutil.copy(p, "/kaggle/working/remote_exec_bridge.py")
        break

%cd /kaggle/working
!python remote_exec_bridge.py
""")


# ---------------------------------------------------------------------------
# Cell 8 — What Kiro does over the bridge (reference / manual fallback)
# ---------------------------------------------------------------------------
md("""## 7. What happens next (reference)

Once you paste the `BRIDGE_URL`, Kiro drives these over the bridge — but they
also work as plain terminal commands if you ever want to run the test by hand:

```bash
export OPENSHORTS_API_URL=http://localhost:8000

# process the uploaded long video into clips, wait for completion
openshorts process /kaggle/working/inbox/my_video.mp4 --wait

# list the produced clips + their job id
openshorts clips <job_id>

# (clips are then downloaded via the bridge's /download endpoint)
```

**Step-1 success criteria (from the design doc):** measure wall-clock time for
one real video and eyeball clip quality (caption sync, reframe stays on the
speaker, hook makes sense). That single data point confirms the Kaggle path or
triggers Plan B. Record the numbers in `docs/` before building step 2.
""")


# ---------------------------------------------------------------------------
# Notebook assembly
# ---------------------------------------------------------------------------
NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.10"},
        "accelerator": "GPU",
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


def main():
    out_path = os.path.join(os.path.dirname(__file__), "AutoEdit_Kaggle_Setup.ipynb")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1)
    print(f"Wrote {out_path} ({len(CELLS)} cells)")


if __name__ == "__main__":
    main()
