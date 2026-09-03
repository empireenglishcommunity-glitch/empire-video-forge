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
md("""## 2. Clone OpenShorts + install deps (with the proven fixes)

> **Confirmed by the 2026-09-03 live run (see `docs/STEP1-FINDINGS.md`):**
> OpenShorts runs as a **standalone CLI** (`main.py`) — **no Docker/compose,
> no API server needed.** This cell also applies the three fixes the live run
> required, so this is a single clean pass rather than the trial-and-error the
> first run went through.

The baked-in fixes:
1. **Dependency vise** — pin `mediapipe==0.10.21` (keeps the legacy
   `mp.solutions` API `main.py` uses; `1.0.x` removed it) and **remove
   TensorFlow** (unused by OpenShorts; only mediapipe's optional doc-import
   dragged it in, and its protobuf pin fought mediapipe's).
2. **Viral Arabic font rotation** — install 7 free/OFL Arabic display fonts
   (Tajawal Black, Cairo, Lalezar, Lemonada, Changa, Reem Kufi, Marhey) and
   patch `subtitles.py` so **each video picks a different one automatically**
   (feed looks varied, not templated). Force one with `EMPIRE_FONT=<name>`.
   All verified rendering Arabic through libass. See `docs/VIRAL-FONTS.md`.
   (This also fixes the original tofu-box bug — the bundled `Anton` font had
   no Arabic glyphs.)
3. **Whisper `large-v3`** — set at run time (Cell 4); `small` garbled
   colloquial Arabic.

Takes a few minutes (torch + the fonts).
""")

code("""%cd /kaggle/working
!apt-get -qq update >/dev/null 2>&1
!apt-get -qq install -y ffmpeg fonts-noto-core fonts-noto-cjk >/dev/null 2>&1
!git clone --depth 1 https://github.com/mutonby/openshorts.git
%cd openshorts
!pip install -q -r requirements.txt
# Fix 1: dependency vise
!pip install -q "mediapipe==0.10.21"
!pip uninstall -y tensorflow tensorflow-cpu tf-keras keras >/dev/null 2>&1

# Fix 2: install the viral Arabic font pool (all OFL / commercial-safe).
# See docs/VIRAL-FONTS.md. All verified rendering Arabic through libass.
import os as _os
_os.makedirs("/usr/share/fonts/truetype/viral", exist_ok=True)
%cd /usr/share/fonts/truetype/viral
B = "https://github.com/google/fonts/raw/main/ofl"
!wget -q "{B}/cairo/Cairo%5Bslnt,wght%5D.ttf" -O Cairo.ttf
!wget -q "{B}/tajawal/Tajawal-Black.ttf" -O Tajawal-Black.ttf
!wget -q "{B}/lalezar/Lalezar-Regular.ttf" -O Lalezar.ttf
!wget -q "{B}/lemonada/Lemonada%5Bwght%5D.ttf" -O Lemonada.ttf
!wget -q "{B}/changa/Changa%5Bwght%5D.ttf" -O Changa.ttf
!wget -q "{B}/reemkufi/ReemKufi%5Bwght%5D.ttf" -O ReemKufi.ttf
!wget -q "{B}/marhey/Marhey%5Bwght%5D.ttf" -O Marhey.ttf
!fc-cache -f >/dev/null 2>&1
%cd /kaggle/working/openshorts

# Fix 3: patch subtitles.py — rotate through the viral font pool per run.
import pathlib
sp = pathlib.Path("subtitles.py"); s = sp.read_text()
if "import random" not in s:
    s = s.replace("import os\\n", "import os\\nimport random\\n", 1)
pool = '''
VIRAL_FONT_POOL = [
    ("Tajawal Black", 52), ("Cairo", 52), ("Lalezar", 54),
    ("Lemonada", 50), ("Changa", 54), ("Reem Kufi", 54), ("Marhey", 52),
]
def _pick_viral_font():
    forced = os.environ.get("EMPIRE_FONT", "").strip()
    if forced:
        for _n, _sz in VIRAL_FONT_POOL:
            if _n.lower() == forced.lower():
                return _n, _sz
        return forced, 52
    return random.choice(VIRAL_FONT_POOL)
_EMPIRE_FONT_NAME, _EMPIRE_FONT_SIZE = _pick_viral_font()
print("\\U0001F3A8 Caption font this run:", _EMPIRE_FONT_NAME, f"({_EMPIRE_FONT_SIZE}pt)")

'''
if "VIRAL_FONT_POOL" not in s:
    s = s.replace("AUTO_CAPTION_STYLE = {", pool + "AUTO_CAPTION_STYLE = {", 1)
s = s.replace('"font_name": "Anton",', '"font_name": _EMPIRE_FONT_NAME,')
s = s.replace('"font_size": 44,', '"font_size": _EMPIRE_FONT_SIZE,')
# bolder outline for the viral look
s = s.replace('"border_width": 4,', '"border_width": 6,')
sp.write_text(s)
print("OpenShorts installed + deps fixed + 7 viral fonts + rotation applied.")
""")


# ---------------------------------------------------------------------------
# Cell 4 — Verify deps + set GPU/Whisper env
# ---------------------------------------------------------------------------
md("""## 3. Verify the environment

Confirms CUDA is live and mediapipe's face detector initialises (this is what
the dependency vise used to break). If this prints `ENV_OK`, the heavy stuff
works.
""")

code("""import torch, mediapipe, faster_whisper
mediapipe.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
assert torch.cuda.is_available(), "No CUDA — set Accelerator to GPU"
print(f"ENV_OK  cuda={torch.cuda.is_available()}  mediapipe={mediapipe.__version__}")
""")


# ---------------------------------------------------------------------------
# Cell 5 — Moment-scoring key (Kaggle Secrets — the safe way)
# ---------------------------------------------------------------------------
md("""## 4. Load the Gemini key from Kaggle Secrets

**Do NOT paste the key into a cell or the chat.** Store it in **Add-ons →
Secrets** as `GEMINI_API_KEY`, then this cell loads it into the session's
`.env` without ever printing the value. (The private, zero-dependency
alternative is local Ollama via `LLM_BASE_URL` — design §4 Option B — in which
case the Gemini key is optional.)
""")

code("""from kaggle_secrets import UserSecretsClient
k = UserSecretsClient().get_secret("GEMINI_API_KEY")
with open("/kaggle/working/openshorts/.env", "a") as f:
    f.write("\\nGEMINI_API_KEY=%s\\n" % k)
print("Key loaded from Secrets into .env — loaded=%s length=%d (value never printed)"
      % (bool(k), len(k)))
""")


# ---------------------------------------------------------------------------
# Cell 6 — Run the pipeline directly (no API server)
# ---------------------------------------------------------------------------
md("""## 5. Run the pipeline on your video

`main.py` is a standalone CLI. **Upload your source video to Kaggle as a
Dataset** and use `-i` with its `/kaggle/input/...` path — this is the
reliable input path. (YouTube `-u` download tends to hit an anti-bot block
from Kaggle IPs.)

`large-v3` Whisper is set here (first use downloads ~3GB, one-time per
session). Output: `subtitled_*_clip_N.mp4` + a `*_metadata.json` with
AI titles, hooks and per-platform captions.
""")

code("""import os, glob
# EDIT this to your uploaded file's path (Input panel shows /kaggle/input/<dataset>/<file>)
INPUT = glob.glob("/kaggle/input/**/*.mp4", recursive=True)
INPUT = INPUT[0] if INPUT else "/kaggle/input/<your-dataset>/<your-video>.mp4"
print("Processing:", INPUT)

os.environ["WHISPER_MODEL"] = "large-v3"
os.environ["WHISPER_DEVICE"] = "cuda"
os.environ["WHISPER_COMPUTE"] = "float16"

%cd /kaggle/working/openshorts
!python main.py -i "{INPUT}" -o /kaggle/working/clips_out --format vertical
print("\\nDone. Finished clips + metadata are in /kaggle/working/clips_out/")
!ls -lh /kaggle/working/clips_out/
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
