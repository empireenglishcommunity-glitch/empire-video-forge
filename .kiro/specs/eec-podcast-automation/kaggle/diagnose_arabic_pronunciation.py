# ==========================================================================
# EEC "Yalla Fluent" — ARABIC PRONUNCIATION ROOT-CAUSE DIAGNOSTIC
# --------------------------------------------------------------------------
# The QUESTION this settles: WHY does Mahmoud mispronounce (جماعة soft-j, يلا,
# متفهمش, وقفة q)? Two competing hypotheses:
#   H1: VoiceTut is MSA-biased and needs our tashkeel/phoneme rules to fix it.
#   H2: VoiceTut is ALREADY Egyptian (trained on 380h Egyptian podcasts, has its
#       OWN normalization) and OUR lexicon tashkeel is FIGHTING it and CAUSING errors.
#
# The model's own docs feed it BARE text ("ازيك عامل ايه النهاردة؟") and claim a
# "robust Egyptian normalization pipeline". So we TEST each problem word 3 ways and
# LISTEN to which is correct:
#   (1) BARE      — raw word, NO lexicon, let VoiceTut's own Egyptian brain decide
#   (2) OUR_LEX   — the current egyptian_lexicon.json tashkeel (what we ship now)
#   (3) IN_SENTENCE — the word in a natural carrier sentence, BARE (context helps TTS)
#
# Whichever column is CORRECT tells us the strategy:
#   if BARE wins  -> STOP over-tashkeeling; feed bare text, shrink the lexicon.
#   if OUR_LEX wins -> keep lexicon, fix the bad entries.
#   if neither -> THEN we need phoneme rules (g/ q-exceptions/SSML) — build next.
#
# ⚠️ Kaggle GPU=T4, Internet ON. VoiceTut install.
# --------------------------------------------------------------------------
# CELL 1:
#   !pip install -q -U "transformers>=5.3.0"
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts catt-tashkeel soundfile
#   import os; os._exit(0)
# CELL 2: run this file.
# ==========================================================================
import os, re, json, zipfile, html, urllib.request

OUT = "/kaggle/working/ar_diag"; os.makedirs(OUT, exist_ok=True)
VOICE = "Abdelrahman"
BRANCH = "main"
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       f"empire-video-forge/{BRANCH}/.kiro/specs/eec-podcast-automation/")

# current lexicon (what we ship) — to compare BARE vs OUR tashkeel
try:
    LEX = json.load(open(urllib.request.urlretrieve(RAW+"pipeline/egyptian_lexicon.json",
                    "/kaggle/working/lex.json")[0]))["lexicon"]
except Exception:
    LEX = {}

# the exact words the owner flagged + qaf-exception probes (from research/reviewer:
# قانون/قاهرة/ثقافة KEEP the qaf; قلب/وقفة become hamza)
PROBE = [
    # (bare word, natural carrier sentence)
    ("جماعة",   "أهلا بيكم يا جماعة"),
    ("يلا",     "يلا بينا نبدأ"),
    ("معاكم",   "أنا معاكم النهاردة"),
    ("إنجليزي", "عايزين نتعلم إنجليزي"),
    ("وقفة",    "يلا وقفة سريعة"),
    ("متفهمش",  "لو متفهمش حاجة قولي"),
    ("النهارده","النهارده هنتعلم حاجة حلوة"),
    # qaf EXCEPTIONS — must STAY qaf (not hamza). tests VoiceTut's own judgment:
    ("قانون",   "ده قانون مهم"),
    ("القاهرة", "أنا من القاهرة"),
    ("ثقافة",   "دي ثقافة جميلة"),
    # qaf that SHOULD become hamza in Egyptian:
    ("قلب",     "من قلبي"),
]

print("Loading VoiceTut (2-4 min)...", flush=True)
from voicetut_tts import VoiceTutTTS
import soundfile as sf
vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
print("VoiceTut ready.\n", flush=True)

def apply_lex(t):
    for w in sorted(LEX, key=len, reverse=True):
        t = re.sub(r"(?<!\w)"+re.escape(w)+r"(?!\w)", LEX[w], t)
    return t

rows = []
def synth(text, tag):
    out = os.path.join(OUT, f"{tag}.wav")
    try:
        vt.synthesize(text, speaker=VOICE, output=out, num_step=64, guidance_scale=2.5, speed=0.9)
        rows.append((tag, os.path.basename(out), text)); print(f"  OK {tag}", flush=True)
    except Exception as e:
        print(f"  !! {tag}: {str(e)[:60]}", flush=True)

for i,(word,sent) in enumerate(PROBE,1):
    synth(word,                 f"{i:02d}_{word}__1_BARE")
    lexd = apply_lex(word)
    if lexd != word:
        synth(lexd,             f"{i:02d}_{word}__2_OURLEX")
    synth(sent,                 f"{i:02d}_{word}__3_SENTENCE_bare")

# contact sheet grouped by word
by_word = {}
for tag,f,text in rows:
    key = tag.split("__")[0]
    by_word.setdefault(key, []).append((tag,f,text))
body=[]
for key,items in by_word.items():
    word = key.split("_",1)[1]
    body.append(f"<h2>{html.escape(word)}</h2>")
    for tag,f,text in items:
        variant = tag.split("__")[1]
        body.append(f"<div style='margin:6px 0;padding:6px;border:1px solid #ccc;border-radius:6px'>"
                    f"<b>{html.escape(variant)}</b> — synth text: {html.escape(text)}<br>"
                    f"<audio controls src='{html.escape(f)}'></audio></div>")
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(
    "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;max-width:760px;margin:24px auto}"
    "h1{color:#b8860b}h2{border-bottom:2px solid #b8860b;margin-top:22px}</style></head><body>"
    "<h1>Arabic pronunciation root-cause test</h1>"
    "<p>For each word compare: <b>1_BARE</b> (no lexicon, VoiceTut's own Egyptian brain) vs "
    "<b>2_OURLEX</b> (our current tashkeel) vs <b>3_SENTENCE</b> (bare, in context). "
    "Tell Kiro which column is CORRECT per word. Also: do قانون/القاهرة/ثقافة keep the QAF "
    "(correct) and قلب become hamza? That decides our whole strategy.</p>"
    + "\n".join(body) + "</body></html>")
with zipfile.ZipFile("/kaggle/working/ar_diag.zip","w",zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)): z.write(os.path.join(OUT,fn),fn)
print("\nDONE. Download ar_diag.zip, open ar_diag/index.html. Report which variant is correct per word.")
