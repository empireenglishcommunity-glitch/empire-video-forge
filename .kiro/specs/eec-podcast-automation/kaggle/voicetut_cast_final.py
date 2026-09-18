# ==========================================================================
# EEC "Two Worlds" — FINAL Arabic cast audition (all 17 voices + lexicon)
# --------------------------------------------------------------------------
# Arabic is SOLVED: VoiceTut built-in voices + the Egyptian pronunciation
# lexicon (add_lexicon) fixes the hard colloquial words that made voices stumble.
# This run auditions ALL 17 voices on hard, real-coach lines WITH the lexicon
# applied — so the owner locks the FINAL cast now that pronunciation is fixed.
# The "mistake" voices from round 1 should now be usable -> bigger cast.
#
# Each voice reads 2 lines: (A) hard colloquial words + (B) a code-switch coach
# line — the two things that used to break them. If a voice is clean on both,
# it's cast-worthy.
#
# Requires: Kaggle GPU = T4, Internet ON. Fresh notebook.
# --------------------------------------------------------------------------
# CELL 1 (install + restart):
#   !pip install -q torch --index-url https://download.pytorch.org/whl/cu121
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts
#   import os; os._exit(0)
#
# CELL 2 (this file) — after restart.
# ==========================================================================
import traceback
from voicetut_tts import VoiceTutTTS

tts = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
print("VoiceTut loaded")

# ---- the Egyptian pronunciation lexicon (from egyptian_lexicon.json) ------
# Solve each hard word once; every voice uses it. Grows over time.
LEXICON = {
    "الجداد": "الجُدَاد", "جداد": "جُدَاد",
    "دلوقتي": "دِلْوَأْتِي", "إزيك": "إِزَّيَّك",
    "عايز": "عَايِز", "عاوز": "عَاوِز", "خد": "خُد",
    "بتاعي": "بِتَاعِي", "كده": "كِدَه", "أهو": "أَهُوَّ",
    "معلش": "مَعْلِش", "يلا": "يَاللَّا", "بص": "بُصّ",
    "عشان": "عَشَان", "علشان": "عَلَشَان",
}
NAMES = {"Macal": "مَاكَال", "Nour": "نُور", "Dubai": "دُبَيّ"}
try:
    tts.add_lexicon(LEXICON)
    if hasattr(tts, "add_names"):
        tts.add_names(NAMES)
    print("lexicon applied:", len(LEXICON), "words +", len(NAMES), "names")
except Exception:
    print("add_lexicon issue:"); traceback.print_exc()

# ---- the two hard test lines ---------------------------------------------
LINE_A = "خد بالك من الثلاث كلمات الجداد دول، عايز دلوقتي تركز معايا كده وبص هنا."
LINE_B = ("أهلاً بيك يا بطل في عالمين! ركز في الجملة دي: Could I get a coffee, "
          "please? يعني ممكن آخد قهوة لو سمحت؟ متنساش كلمة please.")

ALL_VOICES = {
    "male": ["Abdelrahman", "Abdullah", "Kamal", "Hossam", "Mohamed", "Omar",
             "Sayed", "Zaki", "Aly", "Essam", "Ahmed"],
    "female": ["Asmaa", "Esraa", "Hanan", "Sarah", "Yasmin", "Omnia"],
}

def gen(tag, text, spk):
    try:
        out = "/kaggle/working/" + tag + ".wav"
        tts.synthesize(text, speaker=spk, num_step=64, guidance_scale=2.5,
                       speed=1.0, output=out)
        print("wrote", out)
    except Exception:
        print(tag, "FAILED:"); traceback.print_exc()

for gender, voices in ALL_VOICES.items():
    print("\n=== " + gender.upper() + " voices (with lexicon) ===")
    for spk in voices:
        gen("FINAL_" + spk + "_A", LINE_A, spk)   # hard colloquial words
        gen("FINAL_" + spk + "_B", LINE_B, spk)   # code-switch coach line

print("\nDONE - listen to FINAL_<voice>_A (hard words) and FINAL_<voice>_B (coach).")
print("A voice clean on BOTH = cast-worthy. Pick the final Arabic cast:")
print("  - COACH (warm, teacherly)  - male leads  - female leads  - guests")
print("The lexicon should have fixed the round-1 'mistake' voices -> bigger cast.")
