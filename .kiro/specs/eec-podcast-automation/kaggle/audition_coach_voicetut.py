# ==========================================================================
# EEC "Yalla Fluent" — COACH (Mahmoud) re-audition (Phase B, task B.6g)
# --------------------------------------------------------------------------
# Owner doesn't like "Sayed" (the old placeholder Coach). Mahmoud is the show's
# ANCHOR and the biggest role (~136 lines/episode), so re-audition ALL 17 VoiceTut
# voices reading REAL Mahmoud coach lines, and pick the SINGLE best (Option A:
# one Coach for the whole season).
#
# Each voice reads two real Mahmoud snippets (Egyptian Arabic):
#   (1) a warm welcome/intro  — judge warmth + hosting presence
#   (2) a teaching-break snippet with English target phrases — judge clarity +
#       how it handles the embedded English (the Accent Lab / coach breaks)
#
# NOTE: Macal is now VoiceTut "Abdullah" and this Coach must sound DIFFERENT from
# Macal — Abdullah is flagged in the sheet so you don't pick a clashing voice.
# (Sayed is included too so you can A/B against the old one, but it's the reject.)
#
# ⚠️ Kaggle GPU=T4, Internet ON, fresh notebook.
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — copy EXACTLY, run, wait for the restart.
# VoiceTut needs 'omnivoice' (git) + transformers>=5.3.0; do NOT reinstall torch.
#
#   !pip install -q -U "transformers>=5.3.0"
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts catt-tashkeel soundfile
#   import os; os._exit(0)
#
# CELL 2 (this file) — after the restart. Just run it.
# ==========================================================================
import os, json, zipfile, html, urllib.request

OUT = "/kaggle/working/coach_audition"; os.makedirs(OUT, exist_ok=True)
BRANCH = "main"
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       f"empire-video-forge/{BRANCH}/.kiro/specs/eec-podcast-automation/")

# ALL 17 VoiceTut voices (11 male + 6 female). Owner hears every option.
MALE   = ["Sayed", "Omar", "Essam", "Ahmed", "Abdullah", "Abdelrahman",
          "Kamal", "Hossam", "Mohamed", "Zaki", "Aly"]
FEMALE = ["Yasmin", "Sarah", "Asmaa", "Esraa", "Hanan", "Omnia"]
VOICES = MALE + FEMALE
TAKEN  = {"Sayed": "old Coach (the reject — for A/B only)", "Abdullah": "= MACAL — do NOT pick for Coach (clash)"}

# Real Mahmoud lines (Egyptian Arabic). Shortened so the audition is quick but fair.
LINES = {
    "intro": ("أَهْلًا بِيكُمْ يَا جَمَاعَة فِي يَلَّا فْلُوَنْت! أَنَا مَحْمُود، "
              "وَمَعَاكُمْ كُلْ يَوْم، عَشَان نِتْعَلَّم إِنْجِلِيزِي وِإِحْنَا مُبْسُوطِين."),
    "break": ("يَلّا وِقْفَة سَرِيعَة! أَوَّل جُمْلَة: Nice to speak with you. "
              "وَتَانِي جُمْلَة مُهِمَّة لَمَّا مِتْفَهْمِش: Can you repeat that, please?"),
}

PARAMS = {"num_step": 64, "guidance_scale": 2.5, "speed": 1.0}   # same as production Arabic

# optional: apply the shared Egyptian lexicon so pronunciation matches production
LEX = {}
try:
    urllib.request.urlretrieve(RAW + "pipeline/egyptian_lexicon.json", "/kaggle/working/lex.json")
    LEX = json.load(open("/kaggle/working/lex.json")).get("lexicon", {})
except Exception:
    pass
def prep(text):
    import re
    for w in sorted(LEX, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", LEX[w], text)
    return text

# ==========================================================================
print("Loading VoiceTut (first load downloads ~GBs, 2-4 min — DO NOT interrupt)...", flush=True)
from voicetut_tts import VoiceTutTTS
vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
try:
    vt.add_lexicon(LEX)
except Exception:
    pass
print("VoiceTut ready.\n", flush=True)

rendered = []
def synth(voice, part, text):
    tag = f"Coach_{voice}_{part}"
    out = os.path.join(OUT, f"{tag}.wav")
    try:
        vt.synthesize(prep(text), speaker=voice, output=out, **PARAMS)
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            rendered.append({"voice": voice, "part": part, "file": os.path.basename(out)})
            print(f"  OK {tag}", flush=True)
        else:
            print(f"  !! {tag}: empty", flush=True)
    except Exception as e:
        print(f"  !! {tag}: {str(e)[:80]}", flush=True)

for v in VOICES:
    for part, text in LINES.items():
        synth(v, part, text)

# ==========================================================================
# CONTACT SHEET grouped by voice (intro + break side by side) + zip
# ==========================================================================
by_voice = {}
for r in rendered:
    by_voice.setdefault(r["voice"], {})[r["part"]] = r["file"]

def block(vlist, heading):
    out = [f"<h2>{heading}</h2>"]
    for v in vlist:
        if v not in by_voice:
            continue
        flag = f" &nbsp;<b style='color:#c0392b'>[{html.escape(TAKEN[v])}]</b>" if v in TAKEN else ""
        out.append(f"<div style='margin:10px 0;padding:10px;border:1px solid #ccc;border-radius:6px'>"
                    f"<b>{html.escape(v)}</b>{flag}<br>")
        for part in ("intro", "break"):
            f = by_voice[v].get(part)
            if f:
                out.append(f"<div style='margin:4px 0'><small>{part}</small><br>"
                           f"<audio controls src='{html.escape(f)}'></audio></div>")
        out.append("</div>")
    return "\n".join(out)

index = ("<html><head><meta charset='utf-8'><title>Yalla Fluent — Coach audition</title>"
         "<style>body{font-family:sans-serif;max-width:820px;margin:24px auto;padding:0 12px}"
         "h1{color:#b8860b}h2{margin-top:26px;border-bottom:2px solid #b8860b}</style></head><body>"
         "<h1>Yalla Fluent — pick MAHMOUD (the Coach)</h1>"
         "<p>All 17 VoiceTut voices reading two real Mahmoud lines (a warm intro + a "
         "teaching break with English phrases). Pick the SINGLE voice you love most as "
         "Mahmoud for the whole season. It must sound DIFFERENT from Macal (Abdullah). "
         "Tell Kiro the winner.</p>"
         + block(MALE, "Male voices") + block(FEMALE, "Female voices")
         + "</body></html>")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index)
json.dump({"rendered": rendered, "lines": LINES}, open(os.path.join(OUT, "coach_index.json"), "w"),
          ensure_ascii=False, indent=2)

zip_path = "/kaggle/working/yalla_fluent_coach_audition.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)):
        z.write(os.path.join(OUT, fn), fn)

print(f"\nDONE. {len(rendered)} clips ({len(by_voice)} voices). Download: {zip_path}")
print("Open coach_audition/index.html — pick the ONE Mahmoud voice (not Abdullah=Macal).")
