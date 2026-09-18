# ==========================================================================
# EEC "Two Worlds" — 3-WAY VOICE ENGINE TEST (decides the architecture)
# --------------------------------------------------------------------------
# One test, three outputs, so your EARS decide (no more theory):
#   1) VoiceTut  -> Egyptian ARABIC Coach line (built-in Egyptian voice)
#        => is the Egyptian dialect + Arabic<->English code-switch RIGHT?
#   2) VoiceTut  -> ENGLISH cast line (cloned from the Nour reference)
#        => is VoiceTut's English expressive enough for a drama?
#   3) Chatterbox -> the SAME English line (same Nour reference)
#        => A/B the English quality head-to-head
#
# Decision after listening:
#   - VoiceTut wins BOTH  -> UNIFY everything on VoiceTut (one engine).
#   - VoiceTut wins Arabic, Chatterbox wins English -> SPLIT (Chatterbox EN +
#     VoiceTut AR).
#
# VoiceTut is Egyptian-first (380h), has native code-switching + a built-in
# Egyptian text normalizer (diacritics, numbers, Egyptian clock, EN->AR names),
# Apache-2.0, runs on a T4. No CATT/numpy conflict — it's self-contained.
#
# Requires: Kaggle GPU = T4, Internet = ON.
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — run FIRST, wait for "Kernel Restarting" -> Ok:
#   !pip install -q torch --index-url https://download.pytorch.org/whl/cu121
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts
#   !pip install -q git+https://github.com/resemble-ai/chatterbox.git
#   !pip install -q "numpy==1.26.4"
#   import os; os._exit(0)
#
#   # If the two models fight over deps, run them in SEPARATE notebook runs:
#   #   Run 1: VoiceTut only (comment out the Chatterbox block)
#   #   Run 2: Chatterbox only (comment out the VoiceTut block)
#
# CELL 2 (this file) — run AFTER the kernel restarts.
# ==========================================================================
import os, urllib.request
import soundfile as sf, numpy as np

# ---- reference clip (same voice for both English engines = fair A/B) ------
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       "empire-video-forge/podcast-v2-arabic-test/.kiro/specs/eec-podcast-automation/voice-refs/")
os.makedirs("/kaggle/refs", exist_ok=True)
def fetch(name):
    p = f"/kaggle/refs/{name}"
    try:
        urllib.request.urlretrieve(RAW + name, p); print("got", name); return p
    except Exception as e:
        print("ref missing", name, str(e)[:60]); return None
NOUR = fetch("nour_ref.wav")          # English cast reference (Nour = Emma clone)
COACH_AR = fetch("coach_ar_ref.wav")  # Egyptian Arabic reference (Kore slice)

# ---- test lines ----------------------------------------------------------
AR_COACH = ("أهلاً بيك في أول حلقة من Two Worlds! ماكال لسه واصل دبي وبيتكلم مع "
            "سواق التاكسي. خد بالك من الجملة دي: 'How long does it take?' يعني "
            "'بياخد وقت قد إيه؟'. دي جملة هتفيدك جداً في أول يوم ليك في مدينة جديدة.")
EN_CAST  = ("Macal! Over here! You made it! Oh my goodness, welcome to Dubai — "
            "I am so happy to see you. Come on, let's grab your bags and get some coffee.")

# ==========================================================================
# 1 + 2) VOICETUT — Egyptian Arabic Coach  AND  English cast (cloned)
# ==========================================================================
try:
    from voicetut_tts import VoiceTutTTS
    vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
    print("VoiceTut loaded")

    # (1) Arabic Coach — try a warm built-in Egyptian voice
    try:
        vt.synthesize(AR_COACH, speaker="Sayed", num_step=48, guidance_scale=2.5,
                      speed=1.0, output="/kaggle/working/VT_arabic_coach.wav")
        print("wrote VT_arabic_coach.wav (built-in Egyptian voice)")
    except Exception as e:
        print("VT arabic (builtin) failed:", str(e)[:120])

    # (1b) Arabic Coach — cloned onto our Kore Egyptian reference (voice match)
    if COACH_AR:
        try:
            vt.synthesize(AR_COACH, ref_audio=COACH_AR,
                          ref_text="أهلا بيكم في بودكاست الحلقة الأولى",
                          num_step=48, guidance_scale=2.5, speed=1.0,
                          output="/kaggle/working/VT_arabic_coach_cloned.wav")
            print("wrote VT_arabic_coach_cloned.wav (cloned Egyptian ref)")
        except Exception as e:
            print("VT arabic (cloned) failed:", str(e)[:120])

    # (2) English cast line — cloned onto the Nour reference
    if NOUR:
        try:
            vt.synthesize(EN_CAST, ref_audio=NOUR, ref_text="Hi there, welcome!",
                          num_step=48, guidance_scale=2.5, speed=1.0,
                          output="/kaggle/working/VT_english_cast.wav")
            print("wrote VT_english_cast.wav (cloned Nour)")
        except Exception as e:
            print("VT english failed:", str(e)[:120])
except Exception as e:
    print("VoiceTut unavailable this run:", str(e)[:150])

# ==========================================================================
# 3) CHATTERBOX — the SAME English cast line (same Nour reference) for A/B
# ==========================================================================
try:
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        cb = ChatterboxMultilingualTTS.from_pretrained(device=dev, t3_model="v3")
    except TypeError:
        cb = ChatterboxMultilingualTTS.from_pretrained(device=dev)
    print("Chatterbox loaded")
    if NOUR:
        w = cb.generate(EN_CAST, language_id="en", audio_prompt_path=NOUR,
                        exaggeration=0.6, cfg_weight=0.3)
        sf.write("/kaggle/working/CB_english_cast.wav",
                 w.squeeze().cpu().numpy(), cb.sr)
        print("wrote CB_english_cast.wav (cloned Nour)")
except Exception as e:
    print("Chatterbox unavailable this run:", str(e)[:150])

print("\nDONE. Download and compare:")
print("  ARABIC : VT_arabic_coach.wav / VT_arabic_coach_cloned.wav  <- is Egyptian RIGHT?")
print("  ENGLISH: VT_english_cast.wav  vs  CB_english_cast.wav      <- which is better?")
print("Verdict -> VoiceTut wins both = UNIFY on VoiceTut; else SPLIT (CB English + VT Arabic).")
