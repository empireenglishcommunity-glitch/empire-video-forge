# ==========================================================================
# EEC "Two Worlds" — VoiceTut TUNED quality pass (fast win before fine-tuning)
# --------------------------------------------------------------------------
# Before committing to a multi-day fine-tune, squeeze the best out of VoiceTut
# with proper generation tuning + the Arabic front-end. If this reaches ~Kore,
# we may not need training at all. Generates the SAME Coach line across a sweep
# of quality settings + built-in voices so we pick the best by ear.
#
# Knobs that matter for VoiceTut/OmniVoice quality:
#   num_step        : diffusion steps — higher = cleaner (32 fast, 64 best)
#   guidance_scale  : adherence/expressiveness (2.0-3.5)
#   speed           : pacing (0.95-1.1)
# Plus: built-in Egyptian speakers vs cloning a reference.
#
# Requires: Kaggle GPU = T4, Internet ON.
# --------------------------------------------------------------------------
# CELL 1 (install + restart):
#   !pip install -q torch --index-url https://download.pytorch.org/whl/cu121
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts
#   import os; os._exit(0)
#
# CELL 2 (this file) — after restart.
# ==========================================================================
import os, urllib.request, traceback
from voicetut_tts import VoiceTutTTS

tts = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
print("VoiceTut loaded")

# The real Coach line (Egyptian + a code-switched English teaching phrase).
# Note: VoiceTut has its OWN Egyptian normalizer, so we feed natural text; it
# handles diacritics/numbers internally.
COACH = ("أهلاً بيك في أول حلقة من Two Worlds! النهاردة هنتعلم مع بعض إزاي تطلب "
         "حاجة بأدب في مطعم أو كافيه. خد بالك من الجملة دي، هتفيدك جداً. "
         "متنساش تشترك في القناة عشان يوصلك كل جديد!")

# built-in Egyptian voices to audition (male + female)
VOICES = ["Sayed", "Mohamed", "Omar", "Asmaa", "Sarah", "Hanan"]

# quality settings to sweep (label, num_step, guidance_scale, speed)
SETTINGS = [
    ("s32_g25", 32, 2.5, 1.0),
    ("s64_g25", 64, 2.5, 1.0),   # more steps = cleaner
    ("s64_g30", 64, 3.0, 1.0),   # higher guidance = more expressive
    ("s64_g20_slow", 64, 2.0, 0.97),  # calmer, coach-like
]

# 1) audition built-in voices at a good default (pick the warmest)
print("\n=== built-in voice audition (num_step=64, g=2.5) ===")
for spk in VOICES:
    try:
        out = f"/kaggle/working/AUD_{spk}.wav"
        tts.synthesize(COACH, speaker=spk, num_step=64, guidance_scale=2.5,
                       speed=1.0, output=out)
        print("wrote", out)
    except Exception:
        print(f"voice {spk} failed:"); traceback.print_exc()

# 2) settings sweep on the two best default voices (edit after audition)
print("\n=== settings sweep (Sayed = warm male) ===")
for label, ns, gs, sp in SETTINGS:
    try:
        out = f"/kaggle/working/SWEEP_Sayed_{label}.wav"
        tts.synthesize(COACH, speaker="Sayed", num_step=ns, guidance_scale=gs,
                       speed=sp, output=out)
        print("wrote", out)
    except Exception:
        print(f"sweep {label} failed:"); traceback.print_exc()

print("\nDONE. Download AUD_*.wav (pick the best voice) and SWEEP_*.wav (pick the")
print("best settings). Tell me which combo is closest to / beats Kore, and whether")
print("this is good enough to SHIP or we still go for the fine-tune.")
