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
            # objective pacing verdict vs the natural-learner target band (license-clean,
            # pure math — the Station-3.5 pacing metric used as a down-payment here).
            TARGET_LO, TARGET_HI = 1.8, 2.2
            verdict = ("in-band ✓" if TARGET_LO <= wps <= TARGET_HI
                       else ("too fast" if wps > TARGET_HI else "too slow"))
            rows.append((lid, sp, os.path.basename(out), wps, round(dur, 1), verdict))
            print(f"  OK {tag}  speed={sp}  {wps} wps  ({dur:.1f}s)  -> {verdict}", flush=True)
        except Exception as e:
            print(f"  !! {tag}: {str(e)[:70]}", flush=True)

# contact sheet grouped by line + an OBJECTIVE per-speed average (pacing metric),
# so the owner's ear is backed by a number. Recommend the speed whose AVERAGE wps
# across all test lines is closest to the middle of the target band (~2.0).
by_line, by_speed = {}, {}
for lid, sp, f, wps, dur, verdict in rows:
    by_line.setdefault(lid, []).append((sp, f, wps, dur, verdict))
    by_speed.setdefault(sp, []).append(wps)
avg = {sp: round(sum(v) / len(v), 2) for sp, v in by_speed.items()}
rec = min(avg, key=lambda s: abs(avg[s] - 2.0)) if avg else None

summary = ["<h2>Objective pacing summary (avg words/sec across the test lines)</h2>",
           "<table border=1 cellpadding=6 style='border-collapse:collapse'>"
           "<tr><th>speed</th><th>avg wps</th><th>verdict</th></tr>"]
for sp in sorted(avg):
    a = avg[sp]
    v = "in-band ✓" if 1.8 <= a <= 2.2 else ("too fast" if a > 2.2 else "too slow")
    star = " ⬅ recommended" if sp == rec else ""
    summary.append(f"<tr><td>{sp}</td><td>{a}</td><td>{v}{star}</td></tr>")
summary.append("</table>")

body = []
for lid, items in by_line.items():
    body.append(f"<h2>{lid}: “{html.escape(LINES[lid])}”</h2>")
    for sp, f, wps, dur, verdict in sorted(items):
        tag = " &nbsp;<i>(current, too fast)</i>" if sp == 1.0 else ""
        tag += " &nbsp;<b>⬅ recommended</b>" if sp == rec else ""
        body.append(f"<div style='margin:6px 0;padding:6px;border:1px solid #ccc;border-radius:6px'>"
                    f"<b>speed={sp}</b> — {wps} wps ({dur}s) — <i>{verdict}</i>{tag}<br>"
                    f"<audio controls src='{html.escape(f)}'></audio></div>")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(
    "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;max-width:760px;"
    "margin:24px auto}h1{color:#b8860b}h2{border-bottom:2px solid #b8860b;margin-top:24px}"
    "table{margin:10px 0}th{background:#f4e8c1}</style></head>"
    "<body><h1>Macal speed calibration (FIX-001)</h1>"
    "<p>Pick the speed that sounds like a natural, deliberate Egyptian learner. Your EAR "
    "decides — the objective target band is ~1.8–2.2 words/sec (an L2 learner is slower "
    f"than native). Objective recommendation below = <b>speed {rec}</b>. "
    "Tell Kiro your pick (e.g. 'speed 0.85').</p>"
    + "\n".join(summary) + "\n" + "\n".join(body) + "</body></html>")
print(f"\nObjective recommendation (closest avg to 2.0 wps): speed {rec}  | per-speed avg: {avg}")
zp = "/kaggle/working/macal_speed_calibration.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)):
        z.write(os.path.join(OUT, fn), fn)
print(f"\nDONE. Download: {zp} — open macal_speed/index.html, pick the natural speed.")
