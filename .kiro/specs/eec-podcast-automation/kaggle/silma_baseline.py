# ==========================================================================
# EEC "Two Worlds" — SILMA-TTS BASELINE (our locked Arabic base, pre-fine-tune)
# --------------------------------------------------------------------------
# SILMA = F5-TTS-based, Apache-2.0, bilingual AR+EN, with CATT diacritization +
# NeMo normalization BUILT IN. This is our chosen Arabic base to FINE-TUNE to
# Egyptian + a target Coach voice. First we BASELINE it (zero-shot) on the exact
# Coach line so we know the starting point before training.
#
# We generate 3 ways:
#   1) SILMA default reference voice (its built-in quality)
#   2) SILMA cloned onto our Egyptian Kore reference (coach_ar_ref.wav)
#   3) A code-switch line (Arabic + English term) — the real Coach case
#
# NOTE: SILMA base is Fusha/MSA-leaning; expect it to sound clean but not yet
# Egyptian. That gap is exactly what the fine-tune closes. This baseline is the
# "before" we measure the fine-tune "after" against.
#
# Requires: Kaggle GPU = T4, Internet ON.
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — run FIRST:
#   !apt-get -q update && apt-get -q install -y ffmpeg
#   !pip install -q silma-tts
#   import os; os._exit(0)
#
# CELL 2 (this file) — run AFTER the kernel restarts.
# ==========================================================================
import os, urllib.request, traceback

# ---- fetch our Egyptian reference clip (Kore slice) for cloning -----------
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       "empire-video-forge/podcast-v2-arabic-test/.kiro/specs/eec-podcast-automation/voice-refs/")
os.makedirs("/kaggle/refs", exist_ok=True)
coach_ref = "/kaggle/refs/coach_ar_ref.wav"
try:
    urllib.request.urlretrieve(RAW + "coach_ar_ref.wav", coach_ref)
    print("got Egyptian Kore reference clip")
    have_ref = True
except Exception as e:
    print("ref missing:", str(e)[:80]); have_ref = False

# ---- load SILMA -----------------------------------------------------------
from silma_tts.api import SilmaTTS
silma = SilmaTTS()
print("SILMA loaded")

# The real Coach content
PURE_AR = ("أهلاً بيك في أول حلقة من عالمين. النهاردة هنتعلم مع بعض إزاي تطلب "
           "حاجة بأدب في مطعم أو كافيه، ومتنساش تشترك في القناة.")
CODESWITCH = ("خد بالك من الجملة دي، هتفيدك جداً: How long does it take? "
              "يعني بياخد وقت قد إيه؟")

# reference the built-in sample ships with the package (for default voice)
DEFAULT_REF = "/usr/local/lib/python3.11/site-packages/silma_tts/infer/ref_audio_samples/ar.ref.24k.wav"
# fall back to searching for it if the path differs
if not os.path.exists(DEFAULT_REF):
    import glob
    hits = glob.glob("/usr/**/silma_tts/infer/ref_audio_samples/ar.ref*.wav", recursive=True)
    DEFAULT_REF = hits[0] if hits else None
    print("default ref ->", DEFAULT_REF)

DEFAULT_REF_TEXT = ("ويدقق النظر في القرآن الكريم وسائر الكتب السماوية ويتبع "
                    "مسالك الرسل العظام عليهم الصلاة والسلام.")


def gen(tag, gen_text, ref_file, ref_text):
    try:
        out = f"/kaggle/working/SILMA_{tag}.wav"
        silma.infer(ref_file=ref_file, ref_text=ref_text, gen_text=gen_text,
                    file_wave=out, seed=None, speed=1)
        print("wrote", out)
    except Exception:
        print(f"{tag} FAILED:"); traceback.print_exc()

# 1) default built-in voice, pure Egyptian text
if DEFAULT_REF:
    gen("default_pureAR", PURE_AR, DEFAULT_REF, DEFAULT_REF_TEXT)

# 2) cloned onto our Egyptian Kore reference
if have_ref:
    gen("cloned_pureAR", PURE_AR, coach_ref, None)   # ref_text=None -> auto-transcribe
    gen("cloned_codeswitch", CODESWITCH, coach_ref, None)

# 3) code-switch on default voice too (compare)
if DEFAULT_REF:
    gen("default_codeswitch", CODESWITCH, DEFAULT_REF, DEFAULT_REF_TEXT)

print("\nDONE. Download SILMA_*.wav. This is our BASELINE (before fine-tuning).")
print("Judge honestly: how far from Kore? Is the Egyptian there or is it MSA-ish?")
print("Then we fine-tune SILMA on Egyptian data to close the gap.")
