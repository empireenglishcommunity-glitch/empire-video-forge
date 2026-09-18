# ==========================================================================
# EEC "Two Worlds" — UNIFIED EPISODE SYNTH (the production synthesizer)
# --------------------------------------------------------------------------
# Turns one episode script.json into per-line audio + a timeline, routing each
# line to the right CAST voice:
#   - Arabic lines -> VoiceTut (built-in Egyptian voice from cast.json) through
#     the SHARED PRONUNCIATION BRAIN (egyptian_lexicon.json) + ASR-QA auto-catch
#   - English lines -> Chatterbox (character reference + expressive settings)
# Emits lineNNN_<speaker>.wav + timeline.json + a QA report (words to add to the
# shared lexicon). Loads engines sequentially (all AR lines, free VRAM, then EN)
# so both fit on a T4.
#
# Requires: Kaggle GPU = T4, Internet ON. Fresh notebook.
# --------------------------------------------------------------------------
# CELL 1 (install + restart):
#   !pip install -q torch --index-url https://download.pytorch.org/whl/cu121
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts catt-tashkeel faster-whisper
#   !pip install -q git+https://github.com/resemble-ai/chatterbox.git
#   !pip install -q "numpy==1.26.4"
#   import os; os._exit(0)
#
#   # If VoiceTut + Chatterbox clash in one kernel, run in TWO passes:
#   #   PASS=ar (VoiceTut only) then PASS=en (Chatterbox only) — see PASS below.
#
# CELL 2 (this file) — after restart. Set EPISODE below.
# ==========================================================================
import os, re, json, difflib, unicodedata, urllib.request, traceback
import soundfile as sf

EPISODE = 1
PASS = os.environ.get("PASS", "both")   # "ar", "en", or "both"
BRANCH = "podcast-v2-arabic-test"
RAW = f"https://raw.githubusercontent.com/empireenglishcommunity-glitch/empire-video-forge/{BRANCH}/.kiro/specs/eec-podcast-automation/"

WORK = f"/kaggle/working/ep{EPISODE:02d}"
os.makedirs(WORK, exist_ok=True)

def fetch(rel, dst):
    urllib.request.urlretrieve(RAW + rel, dst); return dst

# ---- load script, cast, shared lexicon (from the repo) --------------------
script = json.load(open(fetch(f"episodes/ep{EPISODE:02d}/script.json", "/kaggle/working/script.json")))
cast = json.load(open(fetch("pipeline/cast.json", "/kaggle/working/cast.json")))
LEX = json.load(open(fetch("pipeline/egyptian_lexicon.json", "/kaggle/working/lex.json")))
print(f"Episode {EPISODE}: {script.get('title')} — {len(script['lines'])} lines")

# recurring role -> voice map (+ main cast)
role_voice = {}
for name, spec in cast.get("cast", {}).items():
    if spec.get("engine") == "voicetut":
        role_voice[name] = spec.get("voice", "Sayed")
for name, spec in cast.get("arabic_recurring_cast", {}).items():
    if isinstance(spec, dict) and spec.get("voice"):
        role_voice[name] = spec["voice"]
DEFAULT_AR_VOICE = "Sayed"

# English cast refs (from cast.json)
en_cast = {n: s for n, s in cast.get("cast", {}).items() if s.get("engine") == "chatterbox"}

# ---- shared-brain helpers -------------------------------------------------
_AR = re.compile(r"[\u0600-\u06FF]")
def prepare_ar(text):
    lex = LEX["lexicon"]
    for w in sorted(lex, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", lex[w], text)
    return text
def skeleton(s):
    s = unicodedata.normalize("NFKD", s); s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\u0600-\u06FF\s]", " ", s)).strip()
def asr_bad(intended, heard):
    a, b = skeleton(intended).split(), skeleton(heard).split()
    sm = difflib.SequenceMatcher(None, a, b); bad=[]
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag in ("replace","delete"): bad += a[i1:i2]
    return round(sm.ratio(),3), bad

timeline = {"episode": EPISODE, "title": script.get("title"), "lines": []}
flagged = {}

# ======================= ARABIC PASS (VoiceTut) ============================
if PASS in ("ar", "both"):
    from voicetut_tts import VoiceTutTTS
    vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
    try:
        vt.add_lexicon(LEX["lexicon"])
        if LEX.get("names_en_ar") and hasattr(vt, "add_names"): vt.add_names(LEX["names_en_ar"])
    except Exception: traceback.print_exc()
    try:
        from faster_whisper import WhisperModel
        asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
    except Exception:
        asr = None
    print("Arabic pass...")
    for i, ln in enumerate(script["lines"]):
        if ln.get("lang") != "ar": continue
        spk = ln["speaker"]; voice = role_voice.get(spk, DEFAULT_AR_VOICE)
        out = f"{WORK}/line{i+1:03d}_{spk}.wav"
        try:
            vt.synthesize(prepare_ar(ln["text"]), speaker=voice, num_step=64,
                          guidance_scale=2.5, speed=1.0, output=out)
            dur = round(len(sf.read(out)[0])/sf.read(out)[1], 3) if os.path.exists(out) else 0
            if asr:
                segs,_ = asr.transcribe(out, language="ar", beam_size=5)
                _, bad = asr_bad(ln["text"], " ".join(s.text for s in segs))
                for w in bad: flagged[w]=flagged.get(w,0)+1
            timeline["lines"].append({"idx":i+1,"section":ln.get("section"),"speaker":spk,
                                      "lang":"ar","voice":voice,"file":os.path.basename(out),"duration":dur})
            print(f"  {i+1} [{spk}/{voice}] {dur}s")
        except Exception:
            print(f"  {i+1} [{spk}] AR FAIL:"); traceback.print_exc()

# ======================= ENGLISH PASS (Chatterbox) =========================
if PASS in ("en", "both"):
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    try: cb = ChatterboxMultilingualTTS.from_pretrained(device=dev, t3_model="v3")
    except TypeError: cb = ChatterboxMultilingualTTS.from_pretrained(device=dev)
    # fetch english refs
    os.makedirs("/kaggle/refs", exist_ok=True)
    refs = {}
    for name, spec in en_cast.items():
        r = spec.get("voice_ref")
        if r:
            try: refs[name] = fetch("voice-refs/"+r, "/kaggle/refs/"+r)
            except Exception: refs[name] = None
    print("English pass...")
    for i, ln in enumerate(script["lines"]):
        if ln.get("lang") != "en": continue
        spk = ln["speaker"]; out = f"{WORK}/line{i+1:03d}_{spk}.wav"
        spec = en_cast.get(spk, {})
        ref = refs.get(spk)
        try:
            w = cb.generate(ln["text"], language_id="en",
                            audio_prompt_path=ref,
                            exaggeration=spec.get("exaggeration",0.5),
                            cfg_weight=spec.get("cfg_weight",0.5))
            sf.write(out, w.squeeze().cpu().numpy(), cb.sr)
            dur = round(len(w.squeeze())/cb.sr, 3)
            timeline["lines"].append({"idx":i+1,"section":ln.get("section"),"speaker":spk,
                                      "lang":"en","voice":spec.get("voice_ref"),"file":os.path.basename(out),"duration":dur})
            print(f"  {i+1} [{spk}] {dur}s")
        except Exception:
            print(f"  {i+1} [{spk}] EN FAIL:"); traceback.print_exc()

# ---- write timeline + QA report ------------------------------------------
timeline["lines"].sort(key=lambda x: x["idx"])
json.dump(timeline, open(f"{WORK}/timeline.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
total = round(sum(l["duration"] for l in timeline["lines"]),1)
print(f"\nDONE ep{EPISODE:02d}: {len(timeline['lines'])} lines, ~{total}s (~{round(total/60,1)}min)")
print("QA flagged words (add to egyptian_lexicon.json):", flagged or "NONE - clean!")
print(f"Zip {WORK} and download -> server assembles plain audio -> raw-audio.")
