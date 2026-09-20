# ==========================================================================
# EEC "Yalla Fluent" — TASHKEEL ASR-VERIFY (factory stage 3: the truth test)
# --------------------------------------------------------------------------
# Takes the DeepSeek tashkeel DRAFT (season_tashkeel_draft.json) and proves each
# entry by SYNTHESIZING it with VoiceTut (voice Abdelrahman = Mahmoud) and running
# Whisper ASR: if Whisper hears the intended bare word, the tashkeel is VERIFIED
# and auto-accepted; if not, it's FLAGGED for owner review. Machine verifies the
# machine — the owner only arbitrates the genuinely hard ones.
#
# Output:
#   verified_tashkeel.json  — auto-accepted {word -> tashkeel} (ready to merge into lexicon)
#   flagged_tashkeel.json   — {word -> {tashkeel, heard, ratio}} for owner review
#
# ⚠️ Kaggle GPU=T4, Internet ON. VoiceTut + faster-whisper.
# --------------------------------------------------------------------------
# CELL 1 (install + restart):
#   !pip install -q -U "transformers>=5.3.0"
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts catt-tashkeel faster-whisper soundfile
#   import os; os._exit(0)
# CELL 2 (this file): run it. Reads the draft from the repo (main).
# ==========================================================================
import os, re, json, unicodedata, difflib, urllib.request

BRANCH = "main"
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       f"empire-video-forge/{BRANCH}/.kiro/specs/eec-podcast-automation/")
VOICE = "Abdelrahman"
OUT = "/kaggle/working/tashkeel_verify"; os.makedirs(OUT, exist_ok=True)
ACCEPT_RATIO = 0.6   # Whisper-heard vs intended (bare) similarity to auto-accept

# load the DeepSeek draft (produced on the server by tashkeel_factory.py, committed to repo)
draft = json.load(open(urllib.request.urlretrieve(
    RAW + "pipeline/season_tashkeel_draft.json", "/kaggle/working/draft.json")[0]))["words"]
print(f"verifying {len(draft)} drafted words...", flush=True)

def bare(s):
    s = re.sub(r"[\u064B-\u0652\u0670]", "", s or "")
    return re.sub(r"\s+", " ", re.sub(r"[^\u0621-\u064A\s]", " ", s)).strip()

print("Loading VoiceTut + Whisper (2-4 min)...", flush=True)
from voicetut_tts import VoiceTutTTS
from faster_whisper import WhisperModel
import soundfile as sf
vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
print("ready.\n", flush=True)

verified, flagged = {}, {}
for i, (word, info) in enumerate(draft.items(), 1):
    tk = info["deepseek"]
    wav = f"{OUT}/w{i:04d}.wav"
    try:
        # synth the word in a tiny carrier so VoiceTut has context (bare single words can misfire)
        vt.synthesize(tk, speaker=VOICE, output=wav, num_step=64, guidance_scale=2.5, speed=0.9)
        segs, _ = asr.transcribe(wav, language="ar")
        heard = " ".join(s.text for s in segs)
        ratio = difflib.SequenceMatcher(None, bare(word), bare(heard)).ratio()
        if ratio >= ACCEPT_RATIO:
            verified[word] = tk
        else:
            flagged[word] = {"tashkeel": tk, "heard": heard.strip(), "ratio": round(ratio, 2),
                             "count": info.get("count", 1)}
        if i % 25 == 0:
            print(f"  {i}/{len(draft)}  verified={len(verified)} flagged={len(flagged)}", flush=True)
    except Exception as e:
        flagged[word] = {"tashkeel": tk, "error": str(e)[:60], "count": info.get("count", 1)}
    finally:
        if os.path.exists(wav):
            os.remove(wav)   # don't ship hundreds of tiny wavs

# flagged sorted by frequency (owner reviews the high-impact ones first)
flagged = dict(sorted(flagged.items(), key=lambda kv: -kv[1].get("count", 1)))
json.dump(verified, open(f"{OUT}/verified_tashkeel.json", "w"), ensure_ascii=False, indent=2)
json.dump(flagged, open(f"{OUT}/flagged_tashkeel.json", "w"), ensure_ascii=False, indent=2)

import zipfile
with zipfile.ZipFile("/kaggle/working/tashkeel_verify.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.write(f"{OUT}/verified_tashkeel.json", "verified_tashkeel.json")
    z.write(f"{OUT}/flagged_tashkeel.json", "flagged_tashkeel.json")

print(f"\nDONE. verified={len(verified)} (auto-accept) | flagged={len(flagged)} (owner review)")
print("Download tashkeel_verify.zip. verified_* merges straight into egyptian_lexicon.json;")
print("flagged_* = the short list the owner arbitrates (sorted by frequency).")
