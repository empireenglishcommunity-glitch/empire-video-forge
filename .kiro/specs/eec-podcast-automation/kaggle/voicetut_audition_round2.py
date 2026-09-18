# ==========================================================================
# EEC "Two Worlds" — VoiceTut AUDITION ROUND 2: fix mistakes + more voices
# --------------------------------------------------------------------------
# Round 1: owner kept Sayed(Coach), Yasmin, Sarah, Omar, Essam, Ahmed, Abdullah
# as CLEAN; filtered out 9 voices that MISPRONOUNCED (the MSA-vs-Egyptian vowel
# problem). This round answers the owner's two questions:
#
#   Q2 (fix mistakes cheaply): re-run the "mistake" voices with CATT-DIACRITIZED
#      text. Tashkeel tells the model the exact vowels -> most MSA mistakes vanish
#      with NO fine-tune. Proves what's fixable free vs what truly needs training.
#
#   Q1 (more to audition): also render the CLEAN voices on a DIFFERENT harder line
#      (difficult letters ض ظ ذ ث ق + code-switch) to confirm they hold up, and
#      give more female options (fewer were kept in round 1).
#
# For each "mistake" voice we output BOTH raw and diacritized so you hear the fix.
#
# Requires: Kaggle GPU = T4, Internet ON. Fresh notebook.
# --------------------------------------------------------------------------
# CELL 1 (install + restart):
#   !pip install -q torch --index-url https://download.pytorch.org/whl/cu121
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts catt-tashkeel
#   import os; os._exit(0)
#
# CELL 2 (this file) — after restart.
# ==========================================================================
import traceback
from voicetut_tts import VoiceTutTTS

tts = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
print("VoiceTut loaded")

# CATT diacritizer (the cheap fix for MSA-vowel mistakes)
catt = None
try:
    from catt_tashkeel import CATTEncoderDecoder
    catt = CATTEncoderDecoder()
    print("CATT diacritizer ready")
except Exception as e:
    print("CATT unavailable (raw only):", str(e)[:80])

def tashkeel(t):
    if not catt:
        return t
    try:
        r = catt.do_tashkeel_batch([t], verbose=False)
        return r[0] if isinstance(r, list) and r else t
    except Exception:
        return t

def gen(tag, text, spk):
    try:
        out = "/kaggle/working/" + tag + ".wav"
        tts.synthesize(text, speaker=spk, num_step=64, guidance_scale=2.5,
                       speed=1.0, output=out)
        print("wrote", out)
    except Exception:
        print(tag, "FAILED:"); traceback.print_exc()

# A line with the exact hard Egyptian sounds + a code-switch term
LINE = ("خد بالك من الثلاث كلمات الجداد دول، ظروف الحياة بتتغير بسرعة. "
        "وقول ورايا: Excuse me, could you help me please?")
LINE_DIAC = tashkeel(LINE)
print("RAW :", LINE)
print("DIAC:", LINE_DIAC)

# Q2: the voices that made mistakes -> raw vs diacritized (hear the fix)
MISTAKE_VOICES = ["Abdelrahman", "Kamal", "Hossam", "Mohamed", "Zaki", "Aly",
                  "Esraa", "Hanan", "Omnia"]
print("\n=== FIX TEST: mistake voices, raw vs diacritized ===")
for spk in MISTAKE_VOICES:
    gen("FIX_" + spk + "_raw", LINE, spk)
    gen("FIX_" + spk + "_diac", LINE_DIAC, spk)

# Q1: confirm the CLEAN voices hold on this harder line (diacritized)
CLEAN_VOICES = ["Sayed", "Yasmin", "Sarah", "Omar", "Essam", "Ahmed", "Abdullah"]
print("\n=== CONFIRM clean voices on the hard line (diacritized) ===")
for spk in CLEAN_VOICES:
    gen("CONFIRM_" + spk, LINE_DIAC, spk)

print("DONE - compare FIX_*_raw vs FIX_*_diac (did diacritics fix the mistakes?)")
print("and check CONFIRM_* (do the clean voices still hold on the hard line?)")
