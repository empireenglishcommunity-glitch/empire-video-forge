# ==========================================================================
# EEC "Two Worlds" — CHATTERBOX MULTILINGUAL V3: ARABIC QUALITY TEST
# --------------------------------------------------------------------------
# Goal: prove whether Chatterbox Multilingual V3 can voice the Egyptian-Arabic
# COACH well enough to REPLACE Gemini Kore. If yes, the WHOLE episode (English
# cast + Arabic Coach) generates in ONE Kaggle batch — unlimited, no Gemini
# 10/day TTS cap — which unlocks 30-minute episodes.
#
# This renders the SAME Ep1 Coach lines the owner already heard from Gemini Kore,
# so it's a direct A/B comparison. It clones an Egyptian-Arabic reference (a slice
# of the approved Kore Coach audio) so timbre + dialect are in-domain.
#
# Requires: Kaggle GPU = T4, Internet = ON.
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — run FIRST, wait for "Kernel Restarting" -> Ok.
# Install the LATEST from source so you get Multilingual V3 (better Arabic).
# If the git install is slow/flaky, the plain pip line also works (older, but the
# notebook auto-falls-back and still tests Arabic).
#   !pip install -q git+https://github.com/resemble-ai/chatterbox.git
#   !pip uninstall -q -y torchvision
#   !pip install -q "numpy==1.26.4"
#   import os; os._exit(0)
#
#   # (fallback if the git line fails: !pip install -q chatterbox-tts )
#
# CELL 2 (this file) — run AFTER the kernel restarts. The code tries V3 and
# gracefully falls back to whatever multilingual build is installed.
# ==========================================================================
import os, urllib.request
import torch, soundfile as sf, numpy as np
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device, "| numpy", np.__version__)
if device != "cuda":
    print("WARNING: enable the T4 GPU for usable speed/quality.")

# --- load the Multilingual model (23 langs incl. Arabic 'ar') -------------
# Newer chatterbox-tts accepts t3_model="v3"; older pip builds don't. Try the
# V3 arg, fall back to the plain loader so this works on whatever Kaggle installs.
try:
    model = ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model="v3")
    print("loaded Multilingual V3")
except TypeError:
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    print("loaded Multilingual (pip default — older than V3, still supports Arabic)")
print("model sr:", model.sr)

# --- pull the Egyptian-Arabic reference clip from the repo (raw GitHub) ----
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       "empire-video-forge/podcast-v2-arabic-test/.kiro/specs/eec-podcast-automation/voice-refs/")
os.makedirs("/kaggle/refs", exist_ok=True)
ref = "/kaggle/refs/coach_ar_ref.wav"
try:
    urllib.request.urlretrieve(RAW + "coach_ar_ref.wav", ref)
    print("got Arabic ref clip")
    have_ref = True
except Exception as e:
    print("REF MISSING (will use default voice):", str(e)[:80])
    have_ref = False

# --- the REAL Ep1 Coach lines (Egyptian Arabic) — same as the Gemini test --
coach_lines = [
    ("coach1_break",
     "أهلاً بيك في أول حلقة من Two Worlds! ماكال لسه واصل دبي وبيتكلم مع سواق "
     "التاكسي. خد بالك من الجملتين دول: الأولى 'How long does it take?' يعني "
     "'بياخد وقت قد إيه؟'. والجملة التانية 'I just landed' يعني 'أنا لسه واصل "
     "بالطيارة حالاً'. غلطة شائعة: ناس تقول 'How long it takes?' من غير 'does'."),
    ("coach2_short",
     "نور استقبلت ماكال بكلمة 'You made it!'، ومعناها 'حمد الله على السلامة، "
     "أخيراً وصلت!'. جملة يومية مهمة جداً في دبي."),
    ("coach3_outro",
     "دي كانت خطوة ماكال الأولى. في الحلقة الجاية هيحاول يطلب أول قهوة ليه في "
     "دبي. اشترك دلوقتي في قناة التليجرام عشان تتمرن معانا!"),
]

# --- generate: try a few delivery settings so we can pick the best ---------
# Tip from Resemble: match ref language to tag; for expressive coach use a
# slightly higher exaggeration + lower cfg_weight for deliberate pacing.
settings = [
    ("A_natural",  dict(exaggeration=0.5, cfg_weight=0.5)),
    ("B_warm",     dict(exaggeration=0.6, cfg_weight=0.4)),  # warmer, slower coach
]

for tag, text in coach_lines:
    for sname, opt in settings:
        try:
            if have_ref:
                wav = model.generate(text, language_id="ar",
                                     audio_prompt_path=ref, **opt)
            else:
                wav = model.generate(text, language_id="ar", **opt)
            out = f"/kaggle/working/AR_{tag}_{sname}.wav"
            sf.write(out, wav.squeeze().cpu().numpy(), model.sr)
            print("wrote", out)
        except Exception as e:
            print(f"FAILED {tag}/{sname}: {str(e)[:120]}")

# --- also test English + Arabic code-switching in ONE line (the real need) -
# The Coach mixes English terms into Arabic — this is the hardest case.
mix = ("طيب يا جماعة، الجملة النهاردة هي 'How long does it take?' — "
       "ركزوا على النطق: how long does it take.")
try:
    w = model.generate(mix, language_id="ar",
                       audio_prompt_path=ref if have_ref else None,
                       exaggeration=0.5, cfg_weight=0.4)
    sf.write("/kaggle/working/AR_codeswitch_test.wav", w.squeeze().cpu().numpy(), model.sr)
    print("wrote AR_codeswitch_test.wav")
except Exception as e:
    print("codeswitch failed:", str(e)[:120])

print("\nDONE — download the AR_*.wav files and compare to the Gemini Kore Coach.")
print("Judge: (1) is the Egyptian dialect natural? (2) are the English terms")
print("inside the Arabic clear? (3) is it as good/better than Kore? Send them back.")
