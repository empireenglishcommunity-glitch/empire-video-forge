# ==========================================================================
# EEC "Two Worlds" — WORD-FIX test (solve hard words like "الجداد")
# --------------------------------------------------------------------------
# Owner's sharp finding: the voices are GOOD; they only stumble on specific
# colloquial words — e.g. "الجداد" (Egyptian for "the new ones"). That's a
# pronunciation-DICTIONARY problem, not a voice problem. VoiceTut has a built-in
# lexicon override (add_lexicon) designed exactly for this: force the correct
# Egyptian pronunciation of hard words via a diacritized spelling.
#
# This proves the fix: render the SAME line with the hard word, BEFORE and AFTER
# applying the lexicon, on a few voices. If "الجداد" now says "el-gudaad" cleanly,
# the whole approach is validated -> we build a growing Egyptian lexicon and every
# cast voice says hard words right forever. No fine-tune needed for this.
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

# the line that failed, plus a couple more hard colloquial words
LINE = "خد بالك من الثلاث كلمات الجداد دول، عايز دلوقتي تركز معايا كده."

# voices to test the fix on (a couple that stumbled + a clean one for control)
VOICES = ["Kamal", "Hossam", "Mohamed", "Sayed"]

def gen(tag, text, spk):
    try:
        out = "/kaggle/working/" + tag + ".wav"
        tts.synthesize(text, speaker=spk, num_step=64, guidance_scale=2.5,
                       speed=1.0, output=out)
        print("wrote", out)
    except Exception:
        print(tag, "FAILED:"); traceback.print_exc()

# BEFORE: no lexicon override (baseline of the mistake)
print("=== BEFORE (no override) ===")
for spk in VOICES:
    gen("BEFORE_" + spk, LINE, spk)

# APPLY the Egyptian lexicon: force correct pronunciation of hard words
# (diacritized target spellings the model reads the Egyptian way)
LEXICON = {
    "الجداد": "الجُدَاد",
    "جداد": "جُدَاد",
    "دلوقتي": "دِلْوَأْتِي",
    "عايز": "عَايِز",
    "كده": "كِدَه",
    "خد": "خُد",
}
try:
    tts.add_lexicon(LEXICON)
    print("lexicon applied:", list(LEXICON.keys()))
except Exception:
    print("add_lexicon FAILED (will show if API differs):"); traceback.print_exc()

# AFTER: same line, same voices, with the override
print("\n=== AFTER (lexicon override) ===")
for spk in VOICES:
    gen("AFTER_" + spk, LINE, spk)

# Also try: manually pre-diacritizing the hard word inline (fallback method)
LINE_INLINE = "خد بالك من الثلاث كلمات الجُدَاد دول، عَايِز دِلْوَأْتِي تركز معايا كِدَه."
print("\n=== INLINE diacritized (fallback method) ===")
for spk in VOICES:
    gen("INLINE_" + spk, LINE_INLINE, spk)

print("\nDONE - compare BEFORE_* vs AFTER_* vs INLINE_* on the word 'الجداد'.")
print("If AFTER/INLINE say it correctly, the lexicon approach is proven -> we build")
print("a growing Egyptian pronunciation dictionary and the whole cast uses it.")
