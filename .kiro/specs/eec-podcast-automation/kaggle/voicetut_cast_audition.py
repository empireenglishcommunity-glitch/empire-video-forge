# ==========================================================================
# EEC "Two Worlds" — VoiceTut CAST AUDITION (Sayed was near the bar!)
# --------------------------------------------------------------------------
# Owner loved AUD_Sayed (VoiceTut's built-in voice). Built-in voices are the
# model at its BEST (they're the tuned reference speakers) — better than cloning
# a random ref. So the smart move: use VoiceTut's best built-in voices AS THE
# CAST, no fine-tune needed.
#
# This does two things:
#   1. FULL Coach passage on Sayed at top quality — is it shippable as the Coach?
#   2. Audition ALL built-in voices on a real coach line — pick our voice-identity
#      library (Coach + Egyptian leads) from the ones that sound great.
#
# Requires: Kaggle GPU = T4, Internet ON.  (Fresh notebook recommended.)
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

# A FULL, real Coach passage (not a fragment) — Egyptian + code-switch, the way
# the Coach actually talks. This is the true "is it shippable" test.
COACH_FULL = ("أهلاً بيك في حلقة جديدة من عالمين! النهاردة معانا موقف حلو أوي، "
              "ماكال لسه واصل دبي وداخل يطلب أول قهوة ليه. ركز معايا في الجملة دي "
              "لأنها هتفيدك كل يوم: Could I get a coffee, please? يعني ممكن آخد "
              "قهوة، لو سمحت؟ خد بالك من كلمة please، هي اللي بتخلي الطلب مؤدب. "
              "وبعد ما تخلص، متنساش تقول thank you. جرب تقولها بصوت عالي دلوقتي معايا. "
              "تمام كده! فخور بيك، ويلا نكمل القصة.")

# 1) FULL Coach on Sayed at top quality (the shippability test)
for label, ns, gs, sp in [("best", 64, 2.5, 1.0), ("warm_slow", 64, 2.2, 0.97)]:
    try:
        out = "/kaggle/working/COACH_Sayed_" + label + ".wav"
        tts.synthesize(COACH_FULL, speaker="Sayed", num_step=ns,
                       guidance_scale=gs, speed=sp, output=out)
        print("wrote", out)
    except Exception:
        print("Sayed", label, "FAILED:"); traceback.print_exc()

# 2) audition ALL built-in voices on a shorter coach line -> pick the cast
LINE = ("أهلاً بيك يا بطل! النهاردة هنتعلم إزاي تطلب حاجة بأدب. "
        "ركز معايا وقول ورايا: Excuse me, please.")
VOICES = ["Abdelrahman", "Abdullah", "Kamal", "Hossam", "Mohamed", "Omar",
          "Sayed", "Zaki", "Aly", "Essam", "Ahmed",
          "Asmaa", "Esraa", "Hanan", "Sarah", "Yasmin", "Omnia"]
for spk in VOICES:
    try:
        out = "/kaggle/working/CAST_" + spk + ".wav"
        tts.synthesize(LINE, speaker=spk, num_step=64, guidance_scale=2.5,
                       speed=1.0, output=out)
        print("wrote", out)
    except Exception:
        print("voice", spk, "FAILED:"); traceback.print_exc()

print("DONE - download COACH_Sayed_*.wav (is Sayed shippable as the Coach?)")
print("and CAST_*.wav (pick the best voices for the Arabic cast library)")
