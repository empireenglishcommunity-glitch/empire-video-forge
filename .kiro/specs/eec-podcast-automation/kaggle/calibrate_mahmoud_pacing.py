# ==========================================================================
# EEC "Yalla Fluent" — MAHMOUD (Coach) PACING CALIBRATION (FIX-005)
# --------------------------------------------------------------------------
# Owner: Abdelrahman (Mahmoud) talks too fast; needs human pacing suited to HIS
# character — a warm, DELIBERATE TEACHER (unhurried, clear, breathes at teaching
# beats). Different from Macal (hesitant learner). Same levers, teacher tuning:
#   - Arabic prosodic punctuation (design Layer-1: '...' = breath before a key
#     point; commas = breath groups) — but lighter/statelier than Macal's.
#   - `speed` (VoiceTut). Round-1 for Macal showed speed is weak alone, so we
#     test speed x prosody together and MEASURE + LISTEN.
# Uses the CURRENT lexicon so pronunciation is the fixed Wave-1 version too.
#
# ⚠️ Kaggle GPU=T4, Internet ON. Same VoiceTut install.
# --------------------------------------------------------------------------
# CELL 1 (install + restart):
#   !pip install -q -U "transformers>=5.3.0"
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts catt-tashkeel soundfile
#   import os; os._exit(0)
# CELL 2 (this file): run it.
# ==========================================================================
import os, re, zipfile, html, json, urllib.request

OUT = "/kaggle/working/mahmoud_pacing"; os.makedirs(OUT, exist_ok=True)
VOICE = "Abdelrahman"
BRANCH = "main"
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       f"empire-video-forge/{BRANCH}/.kiro/specs/eec-podcast-automation/")

# load the CURRENT lexicon (Wave-1 fixed pronunciations) so we hear BOTH fixes together
try:
    LEX = json.load(open(urllib.request.urlretrieve(RAW + "pipeline/egyptian_lexicon.json",
                    "/kaggle/working/lex.json")[0]))["lexicon"]
except Exception:
    LEX = {}
def prepare_ar(t):
    for w in sorted(LEX, key=len, reverse=True):
        t = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", LEX[w], t)
    return t

# real Mahmoud Ep1 lines (bare — prepare_ar applies the lexicon)
LINES = {
    "intro": "أهلا بيكم يا جماعة في يلا فلونت! أنا محمود، ومعاكم كل يوم، عشان نتعلم إنجليزي وإحنا مبسوطين.",
    "break": "يلا وقفة سريعة! أول جملة: Nice to speak with you. وتاني جملة مهمة لما متفهمش: Can you repeat that, please?",
}

# teacher prosody: commas as gentle breath-groups (~every 4-5 words) + '...' at
# strong boundaries. LIGHTER than Macal's hesitation — a teacher is calm, not broken.
def teacher_prosody(text):
    # add a breath '...' after sentence enders and before an English target phrase
    t = re.sub(r"([.!])\s+", r"\1.. ", text)
    t = re.sub(r"([:؛])\s+", r"\1... ", t)   # after a colon (before a taught phrase)
    return t

SPEEDS = [0.80, 0.85, 0.90, 1.00]   # 1.00 = current (too fast) baseline
VARIANTS = [
    ("RAW",           lambda t: t,               None),
    ("PROSODY",       teacher_prosody,           None),   # prosody only, speeds swept below
]

print("Loading VoiceTut (2-4 min first load)...", flush=True)
from voicetut_tts import VoiceTutTTS
import soundfile as sf
vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
try: vt.add_lexicon(LEX)
except Exception: pass
print("VoiceTut ready.\n", flush=True)

rows = []
def do(lid, text_variant, vname, sp):
    words = len(re.findall(r"[\u0621-\u064A]+", text_variant))
    synth_text = prepare_ar(text_variant)
    tag = f"Mahmoud_{lid}_{vname}_s{str(sp).replace('.','')}"
    out = os.path.join(OUT, f"{tag}.wav")
    try:
        vt.synthesize(synth_text, speaker=VOICE, output=out, num_step=64, guidance_scale=2.5, speed=sp)
        dur = sf.info(out).duration if os.path.exists(out) else 0
        wps = round(words / dur, 2) if dur else 0
        rows.append((lid, vname, sp, os.path.basename(out), wps, round(dur, 1)))
        print(f"  OK {tag}  {wps} wps ({dur:.1f}s)", flush=True)
    except Exception as e:
        print(f"  !! {tag}: {str(e)[:70]}", flush=True)

for lid, text in LINES.items():
    # baseline raw at current speed
    do(lid, text, "RAW", 1.0)
    # prosody + a sweep of speeds
    for sp in SPEEDS:
        do(lid, teacher_prosody(text), "PROSODY", sp)

# contact sheet
by_line = {}
for r in rows: by_line.setdefault(r[0], []).append(r)
body = []
for lid, items in by_line.items():
    body.append(f"<h2>{lid}</h2>")
    for lid_, vname, sp, f, wps, dur in items:
        note = " (current, too fast)" if (vname=="RAW" and sp==1.0) else ""
        body.append(f"<div style='margin:6px 0;padding:6px;border:1px solid #ccc;border-radius:6px'>"
                    f"<b>{vname} @ speed {sp}</b> — {wps} wps ({dur}s){note}<br>"
                    f"<audio controls src='{html.escape(f)}'></audio></div>")
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(
    "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;max-width:760px;margin:24px auto}"
    "h1{color:#b8860b}h2{border-bottom:2px solid #b8860b;margin-top:24px}</style></head><body>"
    "<h1>Mahmoud (Coach) pacing — FIX-005</h1>"
    "<p>Abdelrahman as a WARM, DELIBERATE TEACHER. Pick the variant+speed that sounds "
    "unhurried and natural (a teacher, not rushed, not robotic). Also confirm the Wave-1 "
    "pronunciation fixes sound right (يلا, etc.). Tell Kiro your pick (e.g. 'PROSODY speed 0.85').</p>"
    + "\n".join(body) + "</body></html>")
zp="/kaggle/working/mahmoud_pacing.zip"
with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)): z.write(os.path.join(OUT,fn),fn)
print(f"\nDONE. Download: {zp} — open mahmoud_pacing/index.html. Pick variant+speed; also confirm pronunciation.")
