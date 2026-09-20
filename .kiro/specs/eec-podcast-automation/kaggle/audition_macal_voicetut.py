# ==========================================================================
# EEC "Yalla Fluent" — MACAL via VoiceTut PROOF TEST (Phase B, task B.6f)
# --------------------------------------------------------------------------
# Owner insight: VoiceTut (the Egyptian-Arabic engine we already run for Mahmoud)
# pronounced ENGLISH with a natural Egyptian accent in earlier tests. Qwen could
# not fake an Egyptian accent (B.5/B.6c) and Common Voice had no Arab-English refs
# (B.6e). So: test VoiceTut AS Macal's English voice.
#
# DECISIONS (owner):
#   - Use ANY male voice for this proof; a proper voice audition comes later IF it works.
#   - ARC = option (a): Macal stays Egyptian-accented across ALL 3 stages; his growth
#     shows through LANGUAGE (fluency/contractions/confidence in the script), NOT an
#     accent shift. So all 3 stage lines use the SAME VoiceTut voice — we just want to
#     hear that the English is intelligible + authentically Egyptian.
#
# THE ACTUAL EXPERIMENT — can VoiceTut (an Arabic engine) read English text? We try
# THREE text strategies per line so we can see which reads best:
#   (1) RAW English  — "Hello, Mama. I am in Dubai."  (does it read Latin at all?)
#   (2) AR-TRANSLIT  — the English written in Arabic script ("هِيلُو مَامَا...")
#                      → plays to its strength; expected strongest Egyptian accent.
#   (3) MIXED        — Arabic-translit for flow + keep a couple of KEY English words.
# Rendered across a few male voices (NOT Sayed — that's Mahmoud/Coach).
#
# ⚠️ Kaggle GPU=T4, Internet ON, fresh notebook.
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — copy EXACTLY, run, wait for the restart:
#
#   !pip install -q voicetut-tts soundfile
#   import os; os._exit(0)
#
# CELL 2 (this file) — after the restart. Just run it.
# ==========================================================================
import os, json, zipfile, html, traceback

OUT = "/kaggle/working/macal_voicetut"; os.makedirs(OUT, exist_ok=True)

# A few male VoiceTut voices to try (NOT Sayed = Mahmoud). Owner said "any for now".
VOICES = ["Omar", "Essam", "Ahmed", "Abdullah"]

# Macal's 3 stage lines. ARC = (a): same accent, growth via LANGUAGE.
#   raw  = the real English line (as written in the script)
#   ar   = the SAME line hand-transliterated into Arabic script (Egyptian voweling)
#          so VoiceTut reads it in its comfort zone -> strong Egyptian accent
#   mix  = Arabic-translit flow but keep the KEY English brand/content words in Latin
LINES = {
    "S1": {
        "raw": "Hello, Mama. I am in Dubai. Everything is good. Everything is very good.",
        "ar":  "هِيلُّو مَامَا. آي آم إِن دُوبَاي. إِيفْرِي ثِنْج إِز جُوود. إِيفْرِي ثِنْج إِز فِيرِي جُوود.",
        "mix": "هِيلُّو Mama. آي آم إِن Dubai. إِيفْرِيثِنْج إِز good. فِيرِي good.",
    },
    "S2": {
        "raw": "Okay. Okay, I'm coming. I mean, I'm on my way down right now.",
        "ar":  "أُوكِيه. أُوكِيه، آيم كَامِنج. آي مِين، آيم أُون مَاي وَيْ دَاوِن رَايْت نَاو.",
        "mix": "أُوكِيه، آيم coming. آي مِين، آيم أُون ماي way down رايت ناو.",
    },
    "S3": {
        "raw": "Okay, so at Dune and Co., we were going to miss a big deadline, right?",
        "ar":  "أُوكِيه، سُو آت دُيُون آند كُو، وِي وِير جُوِينج تُو مِيس آ بِيج دِيدْلَايْن، رَايْت؟",
        "mix": "أُوكِيه، سُو آت Dune and Co.، وِي وِير going to miss آ big deadline، رايت؟",
    },
}

PARAMS = {"num_step": 64, "guidance_scale": 2.5, "speed": 1.0}   # same as Mahmoud

# ==========================================================================
print("Loading VoiceTut (first load downloads ~GBs, 2-4 min — DO NOT interrupt)...", flush=True)
from voicetut_tts import VoiceTutTTS
vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
print("VoiceTut ready.\n", flush=True)

rendered = []
def synth(text, voice, tag, note):
    out = os.path.join(OUT, f"{tag}.wav")
    try:
        vt.synthesize(text, speaker=voice, output=out, **PARAMS)
        ok = os.path.exists(out) and os.path.getsize(out) > 1000
        if ok:
            rendered.append({"voice": voice, "tag": tag, "file": os.path.basename(out), "note": note})
            print(f"  OK {tag}", flush=True)
        else:
            print(f"  !! {tag}: no/empty output", flush=True)
    except Exception as e:
        print(f"  !! {tag}: {str(e)[:90]}", flush=True)

# Render: for each voice, each stage, all 3 text strategies.
for voice in VOICES:
    for stage, variants in LINES.items():
        for strat in ("raw", "ar", "mix"):
            synth(variants[strat], voice,
                  f"Macal_{stage}_{strat}_{voice}",
                  f"{voice} | {stage} | {strat}-text")

# ==========================================================================
# CONTACT SHEET grouped by strategy first (so owner compares raw vs ar vs mix) +
# a zip. The KEY question the owner answers: which text strategy reads English
# intelligibly AND sounds authentically Egyptian?
# ==========================================================================
STRAT_LABEL = {"raw": "(1) RAW English text — can VoiceTut read Latin at all?",
               "ar":  "(2) Arabic-translit — English written in Arabic script (expected best)",
               "mix": "(3) MIXED — Arabic-translit + key English words kept"}
by_strat = {}
for r in rendered:
    strat = r["tag"].split("_")[2]
    by_strat.setdefault(strat, []).append(r)

rows = []
for strat in ("raw", "ar", "mix"):
    items = by_strat.get(strat, [])
    if not items:
        continue
    rows.append(f"<h2>{html.escape(STRAT_LABEL[strat])}</h2>")
    for r in sorted(items, key=lambda x: x["tag"]):
        rows.append(f"<div style='margin:6px 0;padding:8px;border:1px solid #ccc;border-radius:6px'>"
                    f"<b>{html.escape(r['voice'])} — {html.escape(r['tag'].split('_')[1])}</b><br>"
                    f"<audio controls src='{html.escape(r['file'])}'></audio><br>"
                    f"<small>{html.escape(r['note'])}</small></div>")
index = ("<html><head><meta charset='utf-8'><title>Macal via VoiceTut</title>"
         "<style>body{font-family:sans-serif;max-width:820px;margin:24px auto;padding:0 12px}"
         "h1{color:#b8860b}h2{margin-top:26px;border-bottom:2px solid #b8860b}</style></head><body>"
         "<h1>Macal via VoiceTut — English with an Egyptian accent?</h1>"
         "<p>THE QUESTION: which text strategy makes VoiceTut read the English "
         "intelligibly AND sound authentically Egyptian? Compare (1) raw vs (2) Arabic-"
         "translit vs (3) mixed, across the voices. Also confirm the S1/S2/S3 lines are "
         "understandable. Tell Kiro: best strategy + best voice (or 'doesn't work').</p>"
         + "\n".join(rows) + "</body></html>")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index)
json.dump({"rendered": rendered, "lines": LINES, "voices": VOICES},
          open(os.path.join(OUT, "macal_voicetut_index.json"), "w"), ensure_ascii=False, indent=2)

zip_path = "/kaggle/working/yalla_fluent_macal_voicetut.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)):
        z.write(os.path.join(OUT, fn), fn)

print(f"\nDONE. {len(rendered)} clips. Download: {zip_path}")
print("Open macal_voicetut/index.html — compare RAW vs AR-TRANSLIT vs MIXED.")
print("Tell Kiro: which text strategy + which voice sound best (or if it doesn't work).")
