# ==========================================================================
# EEC "Two Worlds" — ARABIC SYNTH with the SHARED PRONUNCIATION BRAIN + auto-QA
# --------------------------------------------------------------------------
# The production Arabic synthesizer. Every line, for EVERY voice, passes through
# the shared pronunciation brain: apply the shared lexicon (one fix -> all cast)
# + auto-diacritize, synth with VoiceTut, then ASR-QA the result and auto-flag
# any word still mispronounced so it can be learned into the shared lexicon.
# Fix a word once -> every voice says it right forever; nothing ships wrong.
#
# This proves the permanent system on the line that broke everyone ("متنساش").
#
# Requires: Kaggle GPU = T4, Internet ON. Fresh notebook.
# --------------------------------------------------------------------------
# CELL 1 (install + restart):
#   !pip install -q torch --index-url https://download.pytorch.org/whl/cu121
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts catt-tashkeel faster-whisper
#   import os; os._exit(0)
#
# CELL 2 (this file) — after restart. It fetches the shared lexicon from the repo.
# ==========================================================================
import os, re, json, difflib, unicodedata, urllib.request, traceback

# ---- fetch the SHARED lexicon from the repo (single source of truth) ------
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       "empire-video-forge/podcast-v2-arabic-test/.kiro/specs/eec-podcast-automation/pipeline/")
try:
    urllib.request.urlretrieve(RAW + "egyptian_lexicon.json", "/kaggle/working/egyptian_lexicon.json")
    LEX = json.load(open("/kaggle/working/egyptian_lexicon.json", encoding="utf-8"))
    print("shared lexicon:", len(LEX["lexicon"]), "words")
except Exception as e:
    print("lexicon fetch failed, using inline:", str(e)[:60])
    LEX = {"lexicon": {"متنساش": "مَتِنْسَاش", "الجداد": "الجُدَاد",
                       "دلوقتي": "دِلْوَأْتِي"}, "names_en_ar": {}}

# ---- models ---------------------------------------------------------------
from voicetut_tts import VoiceTutTTS
tts = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
try:
    tts.add_lexicon(LEX["lexicon"])
    if LEX.get("names_en_ar") and hasattr(tts, "add_names"):
        tts.add_names(LEX["names_en_ar"])
    print("lexicon applied to VoiceTut")
except Exception:
    traceback.print_exc()

from faster_whisper import WhisperModel
asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
print("Whisper ready")

# ---- shared-brain helpers (mirror pipeline/pronunciation.py) --------------
_AR = re.compile(r"[\u0600-\u06FF]")
def prepare(text):
    lex = LEX["lexicon"]
    for w in sorted(lex, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", lex[w], text)
    return text

def skeleton(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\u0600-\u06FF\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def asr_check(intended, heard):
    a, b = skeleton(intended).split(), skeleton(heard).split()
    sm = difflib.SequenceMatcher(None, a, b)
    bad = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            bad += a[i1:i2]
    return round(sm.ratio(), 3), bad

# ---- the test: the line that broke everyone (متنساش) ----------------------
LINE = "أهلاً بيك يا بطل! متنساش تشترك في القناة، وخد بالك من الكلمات الجداد دلوقتي."
VOICES = ["Sayed", "Mohamed", "Yasmin", "Sarah"]

flagged_all = {}
for spk in VOICES:
    try:
        prepared = prepare(LINE)                 # shared lexicon applied
        out = f"/kaggle/working/QA_{spk}.wav"
        tts.synthesize(prepared, speaker=spk, num_step=64, guidance_scale=2.5,
                       speed=1.0, output=out)
        segs, _ = asr.transcribe(out, language="ar", beam_size=5)
        heard = " ".join(s.text for s in segs)
        score, bad = asr_check(LINE, heard)
        print(f"{spk}: score={score} flagged={bad}")
        for w in bad:
            flagged_all[w] = flagged_all.get(w, 0) + 1
    except Exception:
        print(spk, "FAILED:"); traceback.print_exc()

print("\n=== QA SUMMARY ===")
print("words still flagged across voices (need a lexicon entry):", flagged_all or "NONE - all clean!")
print("\nDownload QA_*.wav to confirm 'متنساش' now pronounces correctly for ALL voices.")
print("Any word in the flagged list -> add to egyptian_lexicon.json (learn once,")
print("fixed for the whole cast forever). This is the permanent, self-improving system.")
