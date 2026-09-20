# ==========================================================================
# EEC "Yalla Fluent" — MACAL PROSODY/PACING TEST (FIX-001, round 2)
# --------------------------------------------------------------------------
# Round 1 proved VoiceTut `speed` is a WEAK lever — even 0.75 left Macal at
# 3+ wps ("too fast"). Real fix = PROSODIC PAUSES in the synth text (the same
# trick the Arabic coach uses: `...` = breath, commas = breath-groups). A
# hesitant learner PAUSES; that's what drops the pace to ~2 wps and sounds human.
#
# This test renders each Macal line in 4 variants so we SEE + HEAR what works:
#   RAW        — original text (baseline, too fast)
#   COMMA      — a comma inserted every ~3-4 words (breath groups)
#   ELLIPSIS   — a short "..." pause at each clause boundary (hesitation)
#   BOTH+SLOW  — commas + ellipses AND speed=0.85 (the full treatment)
# Measures words/sec for each so we pick the natural one. Pauses are a SYNTH-
# BOUNDARY transform — script.json stays clean (like english_phonetic_map).
#
# ⚠️ Kaggle GPU=T4, Internet ON. Same VoiceTut install as the synth.
# --------------------------------------------------------------------------
# CELL 1: !pip install -q -U "transformers>=5.3.0"
#         !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#         !pip install -q voicetut-tts catt-tashkeel soundfile
#         import os; os._exit(0)
# CELL 2: run this file.
# ==========================================================================
import os, re, zipfile, html

OUT = "/kaggle/working/macal_prosody"; os.makedirs(OUT, exist_ok=True)
VOICE = "Abdullah"
LINES = {
    "L1": "Hello, Mama. I am in Dubai. Everything is good. Everything is very good.",
    "L2": "Yes. Yes, I am here. Sorry, one moment. I am listening.",
    "L3": "No, Mama, I am not tired. Dubai is very nice. The weather is hot, but I am okay.",
}
PARAMS = {"num_step": 64, "guidance_scale": 2.5}

def add_commas(text, every=3):
    """Insert a comma roughly every `every` words as breath groups (skip if punctuation
    already ends the chunk)."""
    out, buf = [], []
    for w in text.split():
        buf.append(w)
        if len(buf) >= every and not buf[-1][-1:] in ".,!?…":
            out.append(" ".join(buf) + ","); buf = []
    if buf:
        out.append(" ".join(buf))
    return " ".join(out)

def add_ellipsis(text):
    """Turn sentence/clause boundaries into short hesitation pauses '...'."""
    t = re.sub(r"([.!?])\s+", r"\1.. ", text)      # after sentence enders
    t = re.sub(r",\s+", r"... ", t)                # commas -> longer breath
    return t

def both_slow(text):
    return add_ellipsis(add_commas(text, every=3))

VARIANTS = [
    ("RAW",       lambda t: t,                1.0),
    ("COMMA",     lambda t: add_commas(t, 3), 1.0),
    ("ELLIPSIS",  add_ellipsis,               1.0),
    ("BOTH_SLOW", both_slow,                  0.85),
]

print("Loading VoiceTut (2-4 min first load)...", flush=True)
from voicetut_tts import VoiceTutTTS
import soundfile as sf
vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
print("VoiceTut ready.\n", flush=True)

rows = []
for lid, text in LINES.items():
    words = len(text.split())   # count REAL words (pauses don't add words)
    for vname, fn, sp in VARIANTS:
        synth_text = fn(text)
        tag = f"Macal_{lid}_{vname}"
        out = os.path.join(OUT, f"{tag}.wav")
        try:
            vt.synthesize(synth_text, speaker=VOICE, output=out, speed=sp, **PARAMS)
            dur = sf.info(out).duration if os.path.exists(out) else 0
            wps = round(words / dur, 2) if dur else 0
            verdict = "in-band ✓" if 1.8 <= wps <= 2.2 else ("too fast" if wps > 2.2 else "too slow")
            rows.append((lid, vname, os.path.basename(out), wps, round(dur, 1), verdict, synth_text))
            print(f"  OK {tag:18} {wps} wps ({dur:.1f}s) -> {verdict}", flush=True)
        except Exception as e:
            print(f"  !! {tag}: {str(e)[:70]}", flush=True)

# contact sheet
by_line = {}
for r in rows:
    by_line.setdefault(r[0], []).append(r)
body = []
for lid, items in by_line.items():
    body.append(f"<h2>{lid}: “{html.escape(LINES[lid])}”</h2>")
    for lid_, vname, f, wps, dur, verdict, stext in items:
        body.append(f"<div style='margin:6px 0;padding:6px;border:1px solid #ccc;border-radius:6px'>"
                    f"<b>{vname}</b> — {wps} wps ({dur}s) — <i>{verdict}</i><br>"
                    f"<small>synth text: {html.escape(stext)}</small><br>"
                    f"<audio controls src='{html.escape(f)}'></audio></div>")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(
    "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;max-width:760px;"
    "margin:24px auto}h1{color:#b8860b}h2{border-bottom:2px solid #b8860b;margin-top:24px}</style></head>"
    "<body><h1>Macal pacing via PROSODIC PAUSES (FIX-001 round 2)</h1>"
    "<p>speed alone couldn't slow Macal. This tests PAUSES (commas + '...') in the synth "
    "text. Pick the variant that sounds like a natural, hesitant Egyptian learner "
    "(target ~1.8–2.2 wps). Tell Kiro which (RAW/COMMA/ELLIPSIS/BOTH_SLOW).</p>"
    + "\n".join(body) + "</body></html>")
zp = "/kaggle/working/macal_prosody.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)):
        z.write(os.path.join(OUT, fn), fn)
print(f"\nDONE. Download: {zp} — open macal_prosody/index.html, pick the natural variant.")
