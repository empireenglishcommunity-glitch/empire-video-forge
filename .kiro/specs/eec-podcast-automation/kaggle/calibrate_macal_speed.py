# ==========================================================================
# EEC "Yalla Fluent" — MACAL SPEED CALIBRATION (FIX-001)
# --------------------------------------------------------------------------
# Macal (VoiceTut "Abdullah", English) spoke too fast (~4 wps). He's a hesitant
# Egyptian LEARNER — should be the slowest voice (~1.8-2.2 wps). This renders a
# few real Macal lines at several `speed` values so the owner PICKS the most
# natural one; we then lock it in cast.json (applies to every episode).
#
# VoiceTut `speed`: we believe lower = slower — THIS TEST CONFIRMS the direction
# by ear before we commit a full re-synth.
#
# ⚠️ Kaggle GPU=T4, Internet ON. Same VoiceTut install as the synth.
# --------------------------------------------------------------------------
# CELL 1 (install + restart):
#   !pip install -q -U "transformers>=5.3.0"
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts catt-tashkeel soundfile
#   import os; os._exit(0)
# CELL 2 (this file): run it.
# ==========================================================================
import os, zipfile, html

OUT = "/kaggle/working/macal_speed"; os.makedirs(OUT, exist_ok=True)
VOICE = "Abdullah"
SPEEDS = [0.75, 0.80, 0.85, 0.90, 0.95, 1.00]   # 1.00 = current (too fast) baseline
# real Macal Ep1 lines (a short one, a medium one, a longer one)
LINES = {
    "L1": "Hello, Mama. I am in Dubai. Everything is good. Everything is very good.",
    "L2": "Yes. Yes, I am here. Sorry, one moment. I am listening.",
    "L3": "No, Mama, I am not tired. Dubai is very nice. The weather is hot, but I am okay.",
}
PARAMS = {"num_step": 64, "guidance_scale": 2.5}

print("Loading VoiceTut (2-4 min first load)...", flush=True)
from voicetut_tts import VoiceTutTTS
import soundfile as sf
vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
print("VoiceTut ready.\n", flush=True)

rows = []
for lid, text in LINES.items():
    words = len(text.split())
    for sp in SPEEDS:
        tag = f"Macal_{lid}_speed{str(sp).replace('.','')}"
        out = os.path.join(OUT, f"{tag}.wav")
        try:
            vt.synthesize(text, speaker=VOICE, output=out, speed=sp, **PARAMS)
            dur = sf.info(out).duration if os.path.exists(out) else 0
            wps = round(words / dur, 2) if dur else 0
            rows.append((lid, sp, os.path.basename(out), wps, round(dur, 1)))
            print(f"  OK {tag}  speed={sp}  {wps} wps  ({dur:.1f}s)", flush=True)
        except Exception as e:
            print(f"  !! {tag}: {str(e)[:70]}", flush=True)

# contact sheet grouped by line, speeds in order — owner picks the natural one
by_line = {}
for lid, sp, f, wps, dur in rows:
    by_line.setdefault(lid, []).append((sp, f, wps, dur))
body = []
for lid, items in by_line.items():
    body.append(f"<h2>{lid}: “{html.escape(LINES[lid])}”</h2>")
    for sp, f, wps, dur in sorted(items):
        body.append(f"<div style='margin:6px 0;padding:6px;border:1px solid #ccc;border-radius:6px'>"
                    f"<b>speed={sp}</b> — {wps} wps ({dur}s){' &nbsp;<i>(current, too fast)</i>' if sp==1.0 else ''}<br>"
                    f"<audio controls src='{html.escape(f)}'></audio></div>")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(
    "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;max-width:760px;"
    "margin:24px auto}h1{color:#b8860b}h2{border-bottom:2px solid #b8860b;margin-top:24px}</style></head>"
    "<body><h1>Macal speed calibration (FIX-001)</h1>"
    "<p>Pick the speed that sounds like a natural, deliberate Egyptian learner "
    "(target ~1.8–2.2 wps). Tell Kiro the number (e.g. 'speed 0.85').</p>"
    + "\n".join(body) + "</body></html>")
zp = "/kaggle/working/macal_speed_calibration.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)):
        z.write(os.path.join(OUT, fn), fn)
print(f"\nDONE. Download: {zp} — open macal_speed/index.html, pick the natural speed.")
