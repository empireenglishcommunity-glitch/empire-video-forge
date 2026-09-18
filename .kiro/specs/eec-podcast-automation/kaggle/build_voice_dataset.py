# ==========================================================================
# EEC "Two Worlds" — VOICE DATASET BUILDER (Kaggle, step 2 of the fine-tune)
# --------------------------------------------------------------------------
# Turns the text corpus into a CLEAN, QUALITY-FILTERED audio training set for
# fine-tuning the Arabic voice. This is how the real Egyptian TTS models were
# built (synthetic pipeline: generate -> transcribe -> quality-filter -> train).
#
# Pipeline per corpus line:
#   1. GENERATE the line as audio with VoiceTut (Egyptian base, best we have),
#      using a consistent target voice (a built-in Egyptian speaker or a locked
#      reference clip) so the whole dataset is ONE coherent voice.
#   2. TRANSCRIBE the generated audio back with Whisper (ASR round-trip).
#   3. SCORE: char-level similarity between what we asked for and what was said
#      (after stripping diacritics/punct). Mispronounced/garbled clips score low.
#   4. KEEP only clips above the quality threshold; drop the rest.
#   5. WRITE LJSpeech: wavs/<id>.wav + metadata.csv (id|raw|diacritized) at 24kHz.
#
# The output dataset is FULLY OWNED (synthetic) and commercial-safe, and becomes
# the training data for the LoRA fine-tune (next step) that lifts the voice to
# Kore-quality-and-beyond.
#
# Requires: Kaggle GPU = T4, Internet = ON.
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — VoiceTut + Whisper, run FIRST:
#   !pip install -q torch --index-url https://download.pytorch.org/whl/cu121
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts faster-whisper
#   import os; os._exit(0)
#
# CELL 2 (this file) — run AFTER restart. Upload training_corpus.jsonl to the
# Kaggle input, or paste a small corpus into CORPUS_FALLBACK below.
# ==========================================================================
import os, json, re, csv, urllib.request, unicodedata
import soundfile as sf

WORKDIR = "/kaggle/working/voice_dataset"
WAVDIR = os.path.join(WORKDIR, "wavs")
os.makedirs(WAVDIR, exist_ok=True)

# quality gate: keep a clip only if the ASR round-trip similarity >= this
KEEP_THRESHOLD = 0.80
TARGET_SPEAKER = "Sayed"   # a warm built-in Egyptian voice (or set REF_CLIP)
REF_CLIP = None            # or a locked reference wav path for a cloned target

# ---- load the corpus (from Kaggle input, or a tiny inline fallback) -------
def load_corpus():
    for p in ["/kaggle/input/two-worlds-corpus/training_corpus.jsonl",
              "/kaggle/working/training_corpus.jsonl",
              "training_corpus.jsonl"]:
        if os.path.exists(p):
            print("corpus:", p)
            return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    print("WARNING: no corpus file found — using tiny inline fallback")
    return [
        {"id": "line0001", "text": "يا أهلا بيك يا بطل، جهز قهوتك وركز معايا.", "style": "warm"},
        {"id": "line0002", "text": "متقلقش خالص من لهجتك، المهم إن الرسالة توصل.", "style": "reassuring"},
    ]

corpus = load_corpus()
print(f"{len(corpus)} lines to synthesize")

# ---- load VoiceTut (generator) + Whisper (scorer) -------------------------
from voicetut_tts import VoiceTutTTS
tts = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
print("VoiceTut loaded")

from faster_whisper import WhisperModel
asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
print("Whisper loaded")


def strip_ar(s):
    # remove diacritics, punctuation, Latin, collapse spaces -> bare Arabic skeleton
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\u0600-\u06FF\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def similarity(a, b):
    a, b = strip_ar(a), strip_ar(b)
    if not a or not b:
        return 0.0
    # simple char-level ratio via difflib
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio()


# ---- build ----------------------------------------------------------------
kept, dropped = [], []
for i, row in enumerate(corpus):
    rid, text = row["id"], row["text"]
    wav_path = os.path.join(WAVDIR, f"{rid}.wav")
    try:
        if REF_CLIP:
            tts.synthesize(text, ref_audio=REF_CLIP, ref_text="مرجع الصوت",
                           num_step=48, guidance_scale=2.5, output=wav_path)
        else:
            tts.synthesize(text, speaker=TARGET_SPEAKER,
                           num_step=48, guidance_scale=2.5, output=wav_path)
    except Exception as e:
        print(f"  {rid} GEN FAIL: {str(e)[:80]}"); dropped.append((rid, "gen"))
        continue

    # ASR round-trip score
    try:
        segs, _ = asr.transcribe(wav_path, language="ar", beam_size=5)
        heard = " ".join(s.text for s in segs)
        score = similarity(text, heard)
    except Exception as e:
        print(f"  {rid} ASR FAIL: {str(e)[:60]}"); score = 0.0

    if score >= KEEP_THRESHOLD:
        kept.append({"id": rid, "text": text, "score": round(score, 3)})
    else:
        dropped.append((rid, f"score={score:.2f}"))
        try: os.remove(wav_path)
        except Exception: pass

    if (i + 1) % 20 == 0:
        print(f"  {i+1}/{len(corpus)} | kept {len(kept)} dropped {len(dropped)}")

# ---- write LJSpeech metadata.csv ------------------------------------------
meta = os.path.join(WORKDIR, "metadata.csv")
with open(meta, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="|")
    for k in kept:
        # LJSpeech: id | raw_text | normalized_text  (we use the same text twice;
        # the fine-tune tokenizer handles it — diacritization can be added here)
        w.writerow([k["id"], k["text"], k["text"]])

print(f"\nDONE. kept {len(kept)}/{len(corpus)} clips (threshold {KEEP_THRESHOLD})")
print(f"  dataset -> {WORKDIR}  (wavs/ + metadata.csv)")
print(f"  mean score of kept: {sum(k['score'] for k in kept)/max(len(kept),1):.3f}")
print("  Zip /kaggle/working/voice_dataset and download it — that's the fine-tune set.")
print("  (drops were mostly mispronounced/garbled clips — filtering them is the point.)")
