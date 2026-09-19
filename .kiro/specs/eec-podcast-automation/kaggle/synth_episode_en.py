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
# CELL 1 (install + restart) — ENGLISH ONLY (Chatterbox). Do NOT add voicetut here.
# Use the PyPI package (the git URL install is fragile and can leave the module
# missing -> "No module named 'chatterbox'"). If the deps conflict, the --no-deps
# fallback + explicit libs recipe works on Kaggle. Then RESTART (os._exit).
#   !pip install -q chatterbox-tts "numpy==1.26.4"
#   # If the line above errors on a dependency conflict, use this fallback instead:
#   # !pip install -q --no-deps chatterbox-tts
#   # !pip install -q librosa transformers accelerate safetensors "numpy==1.26.4"
#   import os; os._exit(0)
#
# After restart, run CELL 2 (this file). It VERIFIES chatterbox imports and prints
# a clear message + the exact fix if the install didn't take — no silent failure.
#
# CELL 2 (this file) — after restart. Set EPISODE below.
# ==========================================================================
import os, re, json, difflib, unicodedata, urllib.request, traceback
import soundfile as sf

EPISODE = 1
PASS = "en"   # ENGLISH-ONLY notebook (Chatterbox) — avoids VoiceTut dep clash
BRANCH = "main"
RAW = f"https://raw.githubusercontent.com/empireenglishcommunity-glitch/empire-video-forge/{BRANCH}/.kiro/specs/eec-podcast-automation/"

WORK = f"/kaggle/working/ep{EPISODE:02d}"
os.makedirs(WORK, exist_ok=True)

def fetch(rel, dst):
    urllib.request.urlretrieve(RAW + rel, dst); return dst

# ---- shared manifest library (single source of truth for order + regen) ---
import importlib.util as _ilu
_ml = fetch("kaggle/manifest_lib.py", "/kaggle/working/manifest_lib.py")
_spec = _ilu.spec_from_file_location("manifest_lib", _ml)
manifest_lib = _ilu.module_from_spec(_spec); _spec.loader.exec_module(manifest_lib)

# ---- load script, cast, shared lexicon (from the repo) --------------------
script = json.load(open(fetch(f"episodes/ep{EPISODE:02d}/script.json", "/kaggle/working/script.json")))
cast = json.load(open(fetch("pipeline/cast.json", "/kaggle/working/cast.json")))
LEX = json.load(open(fetch("pipeline/egyptian_lexicon.json", "/kaggle/working/lex.json")))
print(f"Episode {EPISODE}: {script.get('title')} — {len(script['lines'])} lines")

# Build/reconcile the FULL manifest (all lines, both languages). This pass will
# fill only its own language's slots; the other stays 'pending'. Downloading
# both zips + merging the two manifests yields one complete, authoritative order.
MANIFEST_PATH = f"{WORK}/manifest.json"
manifest = manifest_lib.load_or_init(MANIFEST_PATH, script)
manifest_lib.save(manifest, MANIFEST_PATH)

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
    AR_PARAMS = {"num_step": 64, "guidance_scale": 2.5, "speed": 1.0}
    print("Arabic pass...")
    for i, ln in enumerate(script["lines"]):
        idx = i + 1
        if ln.get("lang") != "ar": continue
        spk = ln["speaker"]; voice = role_voice.get(spk, DEFAULT_AR_VOICE)
        out = f"{WORK}/{manifest_lib.line_filename(idx, spk)}"
        try:
            vt.synthesize(prepare_ar(ln["text"]), speaker=voice, output=out, **AR_PARAMS)
            dur = round(len(sf.read(out)[0])/sf.read(out)[1], 3) if os.path.exists(out) else 0
            if asr:
                segs,_ = asr.transcribe(out, language="ar", beam_size=5)
                _, bad = asr_bad(ln["text"], " ".join(s.text for s in segs))
                for w in bad: flagged[w]=flagged.get(w,0)+1
            manifest_lib.mark(manifest, idx, status="rendered", engine="voicetut",
                              voice=voice, params=AR_PARAMS, duration=dur, synth_pass="ar")
            timeline["lines"].append({"idx":idx,"section":ln.get("section"),"speaker":spk,
                                      "lang":"ar","voice":voice,"file":os.path.basename(out),"duration":dur})
            print(f"  {idx} [{spk}/{voice}] {dur}s")
        except Exception:
            manifest_lib.mark(manifest, idx, status="failed", engine="voicetut",
                              voice=voice, params=AR_PARAMS, synth_pass="ar")
            print(f"  {idx} [{spk}] AR FAIL:"); traceback.print_exc()
        manifest_lib.save(manifest, MANIFEST_PATH)   # persist after each line (crash-safe)

# ======================= ENGLISH PASS (Chatterbox) =========================
if PASS in ("en", "both"):
    import torch
    print("CUDA available:", torch.cuda.is_available(),
          "| GPU:", (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NONE — enable T4!"))
    try:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except ModuleNotFoundError:
        raise SystemExit(
            "\n*** Chatterbox is NOT installed in this kernel. ***\n"
            "Run CELL 1 first (install + restart), then re-run this cell:\n"
            "  !pip install -q chatterbox-tts \"numpy==1.26.4\"\n"
            "  import os; os._exit(0)\n"
            "If that errored on a dependency conflict, use the fallback:\n"
            "  !pip install -q --no-deps chatterbox-tts\n"
            "  !pip install -q librosa transformers accelerate safetensors \"numpy==1.26.4\"\n"
            "  import os; os._exit(0)\n")
    print("Loading Chatterbox (first load downloads ~GBs, 2-4 min — DO NOT interrupt; "
          "wait for 'Chatterbox ready')...", flush=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    try: cb = ChatterboxMultilingualTTS.from_pretrained(device=dev, t3_model="v3")
    except TypeError: cb = ChatterboxMultilingualTTS.from_pretrained(device=dev)
    print("Chatterbox ready ✅", flush=True)
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
        idx = i + 1
        if ln.get("lang") != "en": continue
        spk = ln["speaker"]; out = f"{WORK}/{manifest_lib.line_filename(idx, spk)}"
        spec = en_cast.get(spk, {})
        ref = refs.get(spk)
        en_params = {"exaggeration": spec.get("exaggeration", 0.5),
                     "cfg_weight": spec.get("cfg_weight", 0.5)}
        try:
            w = cb.generate(ln["text"], language_id="en", audio_prompt_path=ref,
                            exaggeration=en_params["exaggeration"],
                            cfg_weight=en_params["cfg_weight"])
            sf.write(out, w.squeeze().cpu().numpy(), cb.sr)
            dur = round(len(w.squeeze())/cb.sr, 3)
            manifest_lib.mark(manifest, idx, status="rendered", engine="chatterbox",
                              voice=spec.get("voice_ref"), params=en_params,
                              duration=dur, synth_pass="en")
            timeline["lines"].append({"idx":idx,"section":ln.get("section"),"speaker":spk,
                                      "lang":"en","voice":spec.get("voice_ref"),"file":os.path.basename(out),"duration":dur})
            print(f"  {idx} [{spk}] {dur}s")
        except Exception:
            manifest_lib.mark(manifest, idx, status="failed", engine="chatterbox",
                              voice=spec.get("voice_ref"), params=en_params, synth_pass="en")
            print(f"  {idx} [{spk}] EN FAIL:"); traceback.print_exc()
        manifest_lib.save(manifest, MANIFEST_PATH)   # persist after each line (crash-safe)

# ---- write manifest + timeline + QA report -------------------------------
manifest_lib.save(manifest, MANIFEST_PATH)
# ALSO write a pass-tagged copy so both survive when the two zips extract into
# one folder (a plain manifest.json would be clobbered by the second zip).
manifest_lib.save(manifest, f"{WORK}/manifest.{PASS}.json")
timeline["lines"].sort(key=lambda x: x["idx"])
json.dump(timeline, open(f"{WORK}/timeline.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
# structured QA -> feeds the shared lexicon loop (words to add so ALL cast get the fix)
json.dump({"episode": EPISODE, "pass": PASS,
           "flagged": dict(sorted(flagged.items(), key=lambda kv: -kv[1]))},
          open(f"{WORK}/qa_flagged.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
s = manifest_lib.summary(manifest)
print("DONE ep{:02d} [PASS={}]: {}/{} rendered, {} failed, {} pending (other pass), ~{}min".format(
    EPISODE, PASS, s["rendered"], s["total"], s["failed"], s["pending"], s["duration_min"]))
if s["failed_idx"]:
    print("  FAILED idx:", s["failed_idx"])
print("QA flagged words (add to egyptian_lexicon.json):", flagged or "NONE - clean!")
print("Zip {} (includes manifest.json), download it, drop in Drive raw-audio -> server merges + assembles.".format(WORK))



# ==========================================================================
# CELL 3 (zip + download) — run after the synth cell finishes.
# Packages the whole WORK dir (WAVs + manifest.json + timeline.json +
# qa_flagged.json) into ONE zip. Download it once; drop it in the Drive
# raw-audio folder. The server merges manifest.json from both passes.
# ==========================================================================
# import shutil, os
# zip_path = shutil.make_archive("/kaggle/working/ep{:02d}_{}".format(EPISODE, PASS), "zip", WORK)
# print("Zip ready:", zip_path, "(", round(os.path.getsize(zip_path)/1e6, 1), "MB )")
# # In Kaggle: the file appears under /kaggle/working — use the download button,
# # or the notebook's Output tab, to pull ep01_en.zip to your machine.
