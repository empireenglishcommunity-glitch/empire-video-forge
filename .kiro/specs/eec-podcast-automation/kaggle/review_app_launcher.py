# ==========================================================================
# EEC "Two Worlds" — REVIEW APP LAUNCHER (Colab / Kaggle)
# --------------------------------------------------------------------------
# Runs the Streamlit review dashboard NEXT TO THE GPU (option B) so fixing a
# clip is instant. Paste these cells into a fresh Colab (or Kaggle) notebook
# with GPU + Internet ON.
#
# WHAT IT DOES
#   * pulls the review app + engine + manifest lib from the repo
#   * pulls script / cast / lexicon / English voice-refs
#   * unpacks the episode audio (both pass zips) into one WORK dir
#   * launches Streamlit and opens a public URL (localtunnel by default,
#     ngrok/cloudflared optional) so you review from any browser
#
# THE LOOP (all inside this one environment):
#   listen -> edit a line's text -> "Regenerate this clip" (GPU, seconds)
#   -> "Re-assemble episode" (ffmpeg) -> download the fixed ep01_audio_plain.m4a
# ==========================================================================

# --------------------------------------------------------------------------
# CELL 1 — install deps (Streamlit + a tunnel + both TTS engines + ffmpeg)
# --------------------------------------------------------------------------
# COLAB (recommended for the review UI — Drive mounts natively, ffmpeg preinstalled):
#   !pip install -q streamlit soundfile
#   !pip install -q -U "transformers>=5.3.0"
#   !pip install -q voicetut-tts catt-tashkeel faster-whisper
#   !pip install -q git+https://github.com/resemble-ai/chatterbox.git "numpy==1.26.4"
#   !npm install -g localtunnel            # zero-signup tunnel (default)
#   # ffmpeg is preinstalled on Colab; on Kaggle: !apt-get -qq install -y ffmpeg
#
# NOTE: VoiceTut and Chatterbox can clash on transformers/torch in one kernel
# (the same reason synth is split into two notebooks). For REVIEW you usually
# only fix one language at a time — load just that engine. If you must fix both
# in one session and hit a clash, run two review sessions (one per language):
#   set EEC_ONLY_LANG=ar  (or =en) below to hard-limit which engine can load.

# --------------------------------------------------------------------------
# CELL 2 — fetch code + assets from the repo, unpack the episode
# --------------------------------------------------------------------------
FETCH = r'''
import os, json, urllib.request, zipfile, glob, shutil

EPISODE = 1
BRANCH  = "podcast-v2-arabic-test"
RAW = f"https://raw.githubusercontent.com/empireenglishcommunity-glitch/empire-video-forge/{BRANCH}/.kiro/specs/eec-podcast-automation/"

WORK = f"/content/ep{EPISODE:02d}" if os.path.isdir("/content") else f"/kaggle/working/ep{EPISODE:02d}"
REFS = "/content/refs" if os.path.isdir("/content") else "/kaggle/refs"
os.makedirs(WORK, exist_ok=True); os.makedirs(REFS, exist_ok=True)

def fetch(rel, dst):
    urllib.request.urlretrieve(RAW + rel, dst); return dst

# ---- code (must sit on sys.path for streamlit to import) ----
CODE = "/content" if os.path.isdir("/content") else "/kaggle/working"
for f in ["kaggle/manifest_lib.py", "kaggle/regen_engine.py", "kaggle/streamlit_review.py"]:
    fetch(f, os.path.join(CODE, os.path.basename(f)))

# ---- data ----
fetch(f"episodes/ep{EPISODE:02d}/script.json", os.path.join(CODE, "script.json"))
fetch("pipeline/cast.json", os.path.join(CODE, "cast.json"))
fetch("pipeline/egyptian_lexicon.json", os.path.join(CODE, "lex.json"))

# ---- English voice references (needed to regenerate EN lines) ----
cast = json.load(open(os.path.join(CODE, "cast.json")))
for name, spec in cast.get("cast", {}).items():
    r = spec.get("voice_ref")
    if r:
        try: fetch("voice-refs/" + r, os.path.join(REFS, r))
        except Exception as e: print("  (no ref for", name, "->", r, ")")

# ---- episode audio: UPLOAD the two zips (ep01_ar.zip, ep01_en.zip) OR mount Drive ----
# Option A (Colab, Drive): from google.colab import drive; drive.mount('/content/drive')
#   then set ZIP_DIR to the raw-audio folder path under /content/drive/...
# Option B: use the Files panel to upload the two zips into ZIP_DIR below.
ZIP_DIR = os.environ.get("EEC_ZIP_DIR", CODE)
for z in sorted(glob.glob(os.path.join(ZIP_DIR, f"ep{EPISODE:02d}_*.zip"))):
    with zipfile.ZipFile(z) as zf: zf.extractall(WORK)
    print("unpacked", os.path.basename(z))

print("WORK :", WORK, "->", len(glob.glob(WORK + "/line*.wav")), "clips")
print("MANIFESTS:", [os.path.basename(m) for m in glob.glob(WORK + "/manifest*.json")])

# ---- merge any pass manifests into one authoritative manifest.json ----
import sys; sys.path.insert(0, CODE)
import manifest_lib
script = json.load(open(os.path.join(CODE, "script.json")))
merged = manifest_lib.build_skeleton(script)
for m in sorted(glob.glob(WORK + "/manifest*.json")):
    try: merged = manifest_lib.merge_pass(merged, json.load(open(m, encoding="utf-8")))
    except Exception as e: print("  skip", m, e)
manifest_lib.save(merged, os.path.join(WORK, "manifest.json"))
print("merged manifest:", manifest_lib.summary(merged))

# ---- export config for the streamlit process ----
with open(os.path.join(CODE, "eec_env.sh"), "w") as f:
    f.write(f"export EEC_WORK='{WORK}'\n")
    f.write(f"export EEC_SCRIPT='{os.path.join(CODE,'script.json')}'\n")
    f.write(f"export EEC_CAST='{os.path.join(CODE,'cast.json')}'\n")
    f.write(f"export EEC_LEX='{os.path.join(CODE,'lex.json')}'\n")
    f.write(f"export EEC_REFS='{REFS}'\n")
    f.write(f"cd '{CODE}'\n")
print("wrote eec_env.sh — CELL 3 sources it before launching Streamlit")
'''
exec(FETCH)

# --------------------------------------------------------------------------
# CELL 3 — launch Streamlit + public URL
# --------------------------------------------------------------------------
# DEFAULT (localtunnel, zero signup). Run this as a shell cell (leading !):
#
#   !source /content/eec_env.sh 2>/dev/null || source /kaggle/working/eec_env.sh; \
#     streamlit run streamlit_review.py --server.port 8501 --server.headless true &>/content/st.log &
#   !sleep 6 && npx localtunnel --port 8501
#   # localtunnel prints a URL + asks for a "tunnel password" = the public IP:
#   !curl -s https://loca.lt/mytunnelpassword ; echo   # <- paste this as the password
#
# MORE STABLE (ngrok, needs a free token from https://dashboard.ngrok.com):
#   !pip install -q pyngrok
#   import os; os.environ["EEC_WORK"] and None
#   from pyngrok import ngrok
#   ngrok.set_auth_token("PASTE_YOUR_NGROK_TOKEN")
#   # start streamlit (same background command as above) then:
#   print("Public URL:", ngrok.connect(8501).public_url)
#
# FALLBACK (cloudflared, zero signup):
#   !wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/bin/cloudflared && chmod +x /usr/bin/cloudflared
#   !cloudflared tunnel --url http://localhost:8501
#
# Open the printed URL -> review, edit, regenerate, re-assemble. When happy,
# download WORK/ep01_audio_plain.m4a (or re-upload to Drive raw-audio).
