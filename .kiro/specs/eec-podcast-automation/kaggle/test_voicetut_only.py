# ==========================================================================
# EEC "Two Worlds" — VOICETUT-ONLY diagnostic (no error hiding)
# --------------------------------------------------------------------------
# The 3-way run only produced the Chatterbox file, which means VoiceTut failed
# silently (the two stacks likely conflict in one kernel). This notebook runs
# VoiceTut ALONE and prints the REAL error with a full traceback if anything
# breaks — so we see exactly what to fix instead of guessing.
#
# Requires: Kaggle GPU = T4, Internet = ON. FRESH notebook (not the Chatterbox one).
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — VoiceTut ONLY (do NOT install chatterbox here):
#   !pip install -q torch --index-url https://download.pytorch.org/whl/cu121
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts
#   import os; os._exit(0)
#
# CELL 2 (this file) — run AFTER the kernel restarts.
# ==========================================================================
import os, sys, traceback, urllib.request

print("=== STEP 1: import voicetut_tts ===")
try:
    from voicetut_tts import VoiceTutTTS
    print("OK import VoiceTutTTS")
except Exception:
    print("IMPORT FAILED — full traceback:")
    traceback.print_exc()
    sys.exit(0)

print("\n=== STEP 2: load the model ===")
try:
    tts = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
    print("OK model loaded")
except Exception:
    print("LOAD FAILED — full traceback:")
    traceback.print_exc()
    sys.exit(0)

print("\n=== STEP 3: list built-in speakers ===")
try:
    # some builds expose .list_speakers() or a .speakers attr
    for attr in ("list_speakers", "speakers", "available_speakers"):
        if hasattr(tts, attr):
            v = getattr(tts, attr)
            print(attr, "->", (v() if callable(v) else v))
except Exception:
    traceback.print_exc()

print("\n=== STEP 4: simplest possible Egyptian line, built-in voice ===")
try:
    tts.synthesize("ازيك عامل ايه النهاردة؟ اتفضل استريح.",
                   speaker="Mohamed", output="/kaggle/working/VT_smoke.wav")
    print("OK wrote VT_smoke.wav")
except Exception:
    print("SYNTHESIZE FAILED — full traceback:")
    traceback.print_exc()

print("\n=== STEP 5: the real Coach line (Arabic + English code-switch) ===")
AR_COACH = ("أهلاً بيك في أول حلقة من Two Worlds! ماكال لسه واصل دبي وبيتكلم مع "
            "سواق التاكسي. خد بالك من الجملة دي: 'How long does it take?' يعني "
            "'بياخد وقت قد إيه؟'. دي جملة هتفيدك جداً في أول يوم ليك في مدينة جديدة.")
for spk in ("Sayed", "Mohamed", "Omar", "Ahmed"):
    try:
        tts.synthesize(AR_COACH, speaker=spk, num_step=48, guidance_scale=2.5,
                       speed=1.0, output=f"/kaggle/working/VT_coach_{spk}.wav")
        print(f"OK wrote VT_coach_{spk}.wav")
    except Exception:
        print(f"coach ({spk}) failed:")
        traceback.print_exc()
        break  # if one speaker fails, they'll all fail the same way

print("\n=== STEP 6: English cast line, cloned from Nour ref ===")
try:
    RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
           "empire-video-forge/podcast-v2-arabic-test/.kiro/specs/eec-podcast-automation/voice-refs/")
    nour = "/kaggle/refs/nour_ref.wav"; os.makedirs("/kaggle/refs", exist_ok=True)
    urllib.request.urlretrieve(RAW + "nour_ref.wav", nour)
    EN_CAST = ("Macal! Over here! You made it! Welcome to Dubai — I'm so happy to "
               "see you. Come on, let's grab your bags and get some coffee.")
    tts.synthesize(EN_CAST, ref_audio=nour, ref_text="Hi there, welcome!",
                   output="/kaggle/working/VT_english_cast.wav")
    print("OK wrote VT_english_cast.wav")
except Exception:
    print("english clone failed:")
    traceback.print_exc()

print("\nDONE. If STEP 4/5 wrote files, VoiceTut works — download VT_*.wav.")
print("If something failed above, copy the FULL traceback back so we fix it exactly.")
