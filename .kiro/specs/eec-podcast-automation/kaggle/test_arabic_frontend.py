# ==========================================================================
# EEC "Two Worlds" — ARABIC FRONT-END + CHATTERBOX (the professional fix)
# --------------------------------------------------------------------------
# The first Arabic test sounded human but MISPRONOUNCED — because we fed
# Chatterbox raw, undiacritized Arabic with Latin-script English inside it.
# This notebook adds the missing text FRONT-END that Gemini/ElevenLabs run
# internally, then lets Chatterbox perform:
#   1. SEGMENT by language (Arabic vs English) — each spoken natively
#   2. DIACRITIZE the Arabic (CATT, SOTA, Apache-2.0) — fixes the vowels
#   3. NORMALIZE numbers/symbols to spoken Arabic
#   4. generate each segment (language_id + cfg_weight=0) and STITCH
#
# Output: TWO files per line so you can A/B directly:
#   FIXED_*.wav   — new front-end pipeline
# Compare against the earlier broken AR_*.wav and the Gemini Kore Coach.
#
# Requires: Kaggle GPU = T4, Internet = ON.
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — run FIRST, wait for "Kernel Restarting" -> Ok:
#   !pip install -q git+https://github.com/resemble-ai/chatterbox.git
#   !pip install -q catt-tashkeel
#   !pip uninstall -q -y torchvision
#   !pip install -q "numpy==1.26.4"
#   import os; os._exit(0)
#
# CELL 2 (this file) — run AFTER the kernel restarts.
# ==========================================================================
import os, re, urllib.request
import torch, soundfile as sf, numpy as np
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device, "| numpy", np.__version__)

# ---- load Chatterbox multilingual (V3 if available) ----------------------
try:
    model = ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model="v3")
    print("loaded Multilingual V3")
except TypeError:
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    print("loaded Multilingual (pip default)")
SR = model.sr

# ---- load CATT diacritizer (THE key fix) ---------------------------------
try:
    from catt_tashkeel import CATTEncoderDecoder
    catt = CATTEncoderDecoder()
    print("CATT diacritizer ready")
except Exception as e:
    catt = None
    print("WARNING: CATT unavailable:", str(e)[:100])

# ---- reference clips (Arabic coach ref for AR, an English ref for EN) -----
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       "empire-video-forge/podcast-v2-arabic-test/.kiro/specs/eec-podcast-automation/voice-refs/")
os.makedirs("/kaggle/refs", exist_ok=True)
refs = {}
for name, dst in [("coach_ar_ref.wav", "coach_ar"), ("nour_ref.wav", "en_voice")]:
    try:
        p = f"/kaggle/refs/{name}"
        urllib.request.urlretrieve(RAW + name, p)
        refs[dst] = p
        print("got ref:", name)
    except Exception as e:
        print("ref missing:", name, str(e)[:60])

# ==========================================================================
# ARABIC FRONT-END (mirrors pipeline/arabic_prep.py)
# ==========================================================================
_LATIN = re.compile(r"[A-Za-z]")
_RUN = re.compile(r"[A-Za-z][A-Za-z0-9\s'’\-\.\,!\?:]*|[^A-Za-z]+")
_EDGE = " '\"’‘`.,:;!?()[]{}«»…-\n\t"

def segment_by_language(text):
    raw = []
    for m in _RUN.finditer(text):
        seg = m.group(0)
        if not seg.strip():
            continue
        lang = "en" if _LATIN.search(seg) else "ar"
        raw.append([lang, seg])
    merged = []
    for lang, seg in raw:
        if merged and merged[-1][0] == lang:
            merged[-1][1] += seg
        else:
            merged.append([lang, seg])
    out = []
    for lang, seg in merged:
        s = seg.strip().strip(_EDGE).strip()
        if s:
            out.append((lang, s))
    return out

def normalize_ar(text):
    text = re.sub(r"['\"’‘`]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def diacritize(text):
    if not catt:
        return text
    try:
        r = catt.do_tashkeel_batch([text], verbose=False)
        return r[0] if isinstance(r, list) and r else text
    except Exception as e:
        print("  diacritize failed:", str(e)[:60]); return text

def prepare(text):
    segs = []
    for lang, seg in segment_by_language(text):
        if lang == "ar":
            segs.append(("ar", diacritize(normalize_ar(seg))))
        else:
            segs.append(("en", seg))
    return segs

# ==========================================================================
# GENERATE — real Ep1 Coach lines, front-ended + stitched
# ==========================================================================
coach_lines = [
    ("coach1", "أهلاً بيك في أول حلقة من Two Worlds! ماكال لسه واصل دبي وبيتكلم "
               "مع سواق التاكسي. خد بالك من الجملتين دول: الأولى 'How long does it "
               "take?' يعني 'بياخد وقت قد إيه؟'. والجملة التانية 'I just landed' "
               "يعني 'أنا لسه واصل بالطيارة حالاً'."),
    ("coach2", "نور استقبلت ماكال بكلمة 'You made it!'، ومعناها 'حمد الله على "
               "السلامة، أخيراً وصلت!'. جملة يومية شايعة جداً في دبي."),
]

def gen(seg_lang, seg_text):
    # AR uses the Arabic coach ref; EN uses a clean English ref. cfg_weight=0 is
    # Resemble's recommendation for clean cross-lingual pronunciation.
    if seg_lang == "ar":
        ref = refs.get("coach_ar")
        return model.generate(seg_text, language_id="ar",
                              audio_prompt_path=ref, exaggeration=0.5, cfg_weight=0.0)
    else:
        ref = refs.get("en_voice") or refs.get("coach_ar")
        return model.generate(seg_text, language_id="en",
                              audio_prompt_path=ref, exaggeration=0.5, cfg_weight=0.3)

def silence(sec):
    return torch.zeros(1, int(SR * sec))

for tag, line in coach_lines:
    print(f"\n=== {tag} ===")
    segs = prepare(line)
    for lang, t in segs:
        print(f"  [{lang}] {t}")
    chunks = []
    for i, (lang, t) in enumerate(segs):
        try:
            w = gen(lang, t)
            if w.dim() == 1:
                w = w.unsqueeze(0)
            chunks.append(w)
            chunks.append(silence(0.12))  # tiny gap between segments
        except Exception as e:
            print(f"  seg {i} ({lang}) FAILED: {str(e)[:100]}")
    if chunks:
        full = torch.cat(chunks, dim=1)
        out = f"/kaggle/working/FIXED_{tag}.wav"
        sf.write(out, full.squeeze().cpu().numpy(), SR)
        print("  wrote", out)

print("\nDONE — download FIXED_*.wav and compare to the broken AR_*.wav + Gemini Kore.")
print("Judge: is the Arabic pronunciation NOW correct? are the taught English")
print("phrases clean native English? is the whole thing broadcast-grade?")
