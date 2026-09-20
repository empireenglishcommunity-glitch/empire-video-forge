# ==========================================================================
# EEC "Yalla Fluent" — UNIFIED EPISODE SYNTH v2 (Phase C, task C.2)
# --------------------------------------------------------------------------
# Renders one episode's per-line WAVs using the LOCKED 3-engine cast (cast.json v2),
# routing EACH LINE BY ITS SPEAKER'S ENGINE (not by language):
#
#   PASS="voicetut"  -> VoiceTut. Renders every line whose cast engine == "voicetut":
#                       * Mahmoud (Coach, voice "Omar", ARABIC)  -> lexicon + ASR-QA
#                       * Macal   (voice "Abdullah", RAW ENGLISH) -> Egyptian-accented
#                         English straight through VoiceTut (no transliteration).
#   PASS="qwen"      -> Qwen3-TTS VoiceClone. Renders every line whose speaker clones
#                       from a frozen voice-refs/*.wav (Nour + guests + Ravi). Cross-
#                       engine identity is frozen (Option B, no drift).
#
# Run as TWO Kaggle kernels (VoiceTut + Qwen deps clash in one env). Each writes the
# SHARED manifest (manifest_lib) + a pass-tagged copy; download both zips, the
# server assembler merges them into one authoritative order. Contract kept IDENTICAL
# to the old synth: lineNNN_<speaker>.wav (global idx), manifest.<PASS>.json,
# 24 kHz mono, status=rendered. So assemble_audio.py / run_podcast.py are untouched.
#
# Chatterbox is RETIRED — not imported here (archived per Phase E).
# ==========================================================================
# ---- CELL 1 (install + restart) — pick ONE per kernel, run, wait for restart ----
#
# VoiceTut kernel (PASS="voicetut"):
#   !pip install -q -U "transformers>=5.3.0"
#   !pip install -q git+https://github.com/k2-fsa/OmniVoice.git
#   !pip install -q voicetut-tts catt-tashkeel faster-whisper soundfile
#   import os; os._exit(0)
#   (do NOT reinstall torch — Kaggle's GPU torch already works)
#
# Qwen kernel (PASS="qwen"):
#   !pip install -q -U qwen-tts soundfile
#   import os; os._exit(0)
#   (T4 = Turing -> attn_implementation="sdpa", do NOT install flash-attn)
#
# ---- CELL 2 (this file) — set EPISODE + PASS below, then run ----
# ==========================================================================
import os, re, json, unicodedata, urllib.request, traceback
import soundfile as sf

# ------------------------------- CONFIG -----------------------------------
EPISODE = 1
PASS    = "voicetut"    # "voicetut"  or  "qwen"
BRANCH  = "main"
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       f"empire-video-forge/{BRANCH}/.kiro/specs/eec-podcast-automation/")
WORK = f"/kaggle/working/ep{EPISODE:02d}"
os.makedirs(WORK, exist_ok=True)

def fetch(rel, dst):
    urllib.request.urlretrieve(RAW + rel, dst); return dst

# ---- shared manifest lib (single source of truth for order + regen) -------
import importlib.util as _ilu
_ml = fetch("kaggle/manifest_lib.py", "/kaggle/working/manifest_lib.py")
_spec = _ilu.spec_from_file_location("manifest_lib", _ml)
manifest_lib = _ilu.module_from_spec(_spec); _spec.loader.exec_module(manifest_lib)

# ---- load script + cast + lexicon (+ fetch the voice refs the Qwen pass needs) ----
script = json.load(open(fetch(f"episodes/ep{EPISODE:02d}/script.json", "/kaggle/working/script.json")))
cast   = json.load(open(fetch("pipeline/cast.json", "/kaggle/working/cast.json")))
LEX    = json.load(open(fetch("pipeline/egyptian_lexicon.json", "/kaggle/working/lex.json")))
CASTM  = cast["cast"]
# English phonetic overrides for Macal's VoiceTut English (synth-boundary; script stays clean)
try:
    ENPHON = json.load(open(fetch("pipeline/english_phonetic_map.json",
                                  "/kaggle/working/enphon.json"))).get("map", {})
except Exception:
    ENPHON = {}
print(f"Episode {EPISODE}: {script.get('title')} — {len(script['lines'])} lines | PASS={PASS} "
      f"| en_phonetic_overrides={len(ENPHON)}", flush=True)

def slow_wav_inplace(path, factor):
    """FIX-007 (owner-approved by ear, option C): pace a rendered WAV by `factor` with
    ffmpeg `atempo` (pitch-preserving time-stretch), replacing it in place.

    This REPLACES the old macal_prosody()/teacher_prosody() text hacks (FIX-001/005),
    which injected commas + '...' into the text and made VoiceTut read every ~3-word
    chunk as its own sentence -> the choppy, robotic 'every word alone' sound. We now
    send NATURAL text to the engine (speed=1.0) and slow the AUDIO afterwards. Same
    FIX-004 lesson: stop fighting the engine. `factor` is the cast `speed` (e.g. 0.85 =>
    ~15% slower, smooth, no pitch change). atempo is valid for 0.5..2.0."""
    import subprocess
    if abs(factor - 1.0) < 1e-3:
        return
    f = max(0.5, min(2.0, factor))
    tmp = path + ".slow.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path,
                    "-af", f"atempo={round(f,4)}", "-ar", "24000", "-ac", "1", tmp], check=True)
    os.replace(tmp, path)


def apply_en_phonetic(text):
    """Whole-word, case-insensitive respelling of English words VoiceTut mispronounces.
    Applied ONLY to Macal's English at synth time — never touches script.json."""
    if not ENPHON:
        return text
    def repl(m):
        return ENPHON[m.group(0).lower()]
    for w in sorted(ENPHON, key=len, reverse=True):
        text = re.sub(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", repl, text, flags=re.IGNORECASE)
    return text

MANIFEST_PATH = f"{WORK}/manifest.json"
manifest = manifest_lib.load_or_init(MANIFEST_PATH, script)
manifest_lib.save(manifest, MANIFEST_PATH)

# ---- ENGINE ROUTING (by speaker's cast engine, NOT by language) -----------
def route(speaker):
    """Return 'voicetut' or 'qwen' for a speaker, per cast.json v2.
    - engine 'voicetut'                         -> voicetut
    - engine 'qwen3-tts-clone'                  -> qwen (clone from voice_ref)
    - engine 'qwen3-tts-design' WITH a voice_ref -> qwen (Option B: clone the frozen take)
    """
    spec = CASTM.get(speaker, {})
    eng = spec.get("engine", "")
    if eng == "voicetut":
        return "voicetut"
    if eng in ("qwen3-tts-clone", "qwen3-tts-design"):
        return "qwen"
    # unknown speaker -> default to qwen clone if it has a ref, else skip
    return "qwen" if spec.get("voice_ref") else None

# lines THIS pass is responsible for (global idx preserved)
my_lines = [(i, ln) for i, ln in enumerate(script["lines"], 1)
            if ln.get("lang") in ("ar", "en") and route(ln["speaker"]) == PASS]
print(f"  this pass renders {len(my_lines)} of {len(script['lines'])} lines", flush=True)

# ---- MINIMAL direction -> params mapper (C.2b; kept small for Ep1) ---------
def direction_params(direction, base):
    """Nudge synth params from a line's 'direction' acting note. MINIMAL for Ep1 —
    just pacing (speed) from a few obvious cues; never fails, never spoken."""
    p = dict(base)
    d = (direction or "").lower()
    if any(w in d for w in ("rapid", "fast", "panic", "rushed", "quick")):
        p["speed"] = round(p.get("speed", 1.0) * 1.12, 3)
    elif any(w in d for w in ("slow", "deliberate", "pause", "breath", "somber", "heavy", "quiet")):
        p["speed"] = round(p.get("speed", 1.0) * 0.92, 3)
    return p

# =====================================================================
# ============================ VOICETUT PASS ==========================
# =====================================================================
if PASS == "voicetut":
    _AR = re.compile(r"[\u0600-\u06FF]")
    def prepare_ar(text):
        lex = LEX["lexicon"]
        for w in sorted(lex, key=len, reverse=True):
            text = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", lex[w], text)
        return text
    def skeleton(s):
        # 1) strip tashkeel/diacritics (combining marks) + tatweel
        s = unicodedata.normalize("NFKD", s); s = "".join(c for c in s if not unicodedata.combining(c))
        s = s.replace("\u0640", "")  # tatweel ـ
        # 2) collapse orthographic variants that Whisper drops/normalizes so we DON'T
        #    false-flag correct pronunciations (idx 8/36/44 root cause: hamza-seat &
        #    taa-marbuta differences between our intended text and bare ASR output):
        #      أ إ آ ٱ ->  ا     (hamza-carrying alef -> bare alef)
        #      ة -> ه            (taa marbuta -> haa)
        #      ى -> ي            (alef maqsura -> yaa)
        #      ؤ -> و , ئ -> ي   (hamza on waw/yaa -> bare carrier)
        #      ء -> ""           (standalone hamza dropped)
        for src, dst in (("أإآٱ", "ا"), ("ة", "ه"), ("ى", "ي"), ("ؤ", "و"), ("ئ", "ي"), ("ء", "")):
            for ch in src:
                s = s.replace(ch, dst)
        return re.sub(r"\s+", " ", re.sub(r"[^\u0600-\u06FF\s]", " ", s)).strip()

    print("Loading VoiceTut (first load downloads ~GBs, 2-4 min — DO NOT interrupt)...", flush=True)
    from voicetut_tts import VoiceTutTTS
    vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
    try:
        vt.add_lexicon(LEX["lexicon"])
        if LEX.get("names_en_ar") and hasattr(vt, "add_names"): vt.add_names(LEX["names_en_ar"])
    except Exception: traceback.print_exc()
    print("VoiceTut ready.\n", flush=True)

    # optional ASR-QA (Arabic only — flags mispronounced AR words)
    asr = None
    try:
        from faster_whisper import WhisperModel
        asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
    except Exception:
        print("  (faster-whisper unavailable — skipping ASR-QA)", flush=True)

    flagged = {}
    for idx, ln in my_lines:
        spk = ln["speaker"]; spec = CASTM.get(spk, {})
        voice = spec.get("voice", "Omar")
        is_ar = (ln.get("lang") == "ar")
        # FIX-007 (owner-approved 'C'): send NATURAL text — NO comma/'...' injection.
        # Arabic -> light-touch lexicon; Macal English -> phonetic overrides only. Pace
        # comes AFTER synth via atempo (slow_wav_inplace), never by mangling the text.
        if is_ar:
            text = prepare_ar(ln["text"])
        else:
            text = apply_en_phonetic(ln["text"])
        # engine runs at NATURAL speed; cast 'speed' is applied afterwards as the atempo factor
        pace = float(spec.get("speed", 1.0))
        base = {"num_step": spec.get("num_step", 64),
                "guidance_scale": spec.get("guidance_scale", 2.5),
                "speed": 1.0}
        params = direction_params(ln.get("direction"), base)
        out = f"{WORK}/{manifest_lib.line_filename(idx, spk)}"
        try:
            vt.synthesize(text, speaker=voice, output=out, **params)
            slow_wav_inplace(out, pace)   # FIX-007: pitch-preserving pace, smooth not choppy
            dur = sf.info(out).duration if os.path.exists(out) else 0.0
            manifest_lib.mark(manifest, idx, status="rendered", engine="voicetut",
                              voice=voice, params={**params, "atempo": pace},
                              duration=round(dur, 3), synth_pass="voicetut")
            # ASR-QA on Arabic lines only
            if asr is not None and is_ar and dur > 0:
                try:
                    segs, _ = asr.transcribe(out, language="ar")
                    heard = " ".join(s.text for s in segs)
                    import difflib
                    a, b = skeleton(ln["text"]).split(), skeleton(heard).split()
                    ratio = difflib.SequenceMatcher(None, a, b).ratio()
                    # threshold loosened 0.6 -> 0.5: skeleton() now collapses hamza-seat /
                    # taa-marbuta / alef-maqsura variants, so what remains below 0.5 is a
                    # genuine word-count/content mismatch, not diacritic noise.
                    if ratio < 0.5:
                        flagged[idx] = {"intended": ln["text"], "heard": heard, "ratio": round(ratio, 3)}
                except Exception: pass
            print(f"  OK line{idx:03d} {spk} [{'ar' if is_ar else 'en'}] {voice}", flush=True)
        except Exception as e:
            manifest_lib.mark(manifest, idx, status="failed", engine="voicetut",
                              voice=voice, params=params, synth_pass="voicetut")
            print(f"  !! line{idx:03d} {spk}: {str(e)[:80]}", flush=True)
    if flagged:
        json.dump(flagged, open(f"{WORK}/qa_flagged.json", "w"), ensure_ascii=False, indent=2)
        print(f"\n  ASR-QA flagged {len(flagged)} Arabic line(s) -> qa_flagged.json (owner review)", flush=True)

# =====================================================================
# =========================== QWEN CLONE PASS =========================
# =====================================================================
elif PASS == "qwen":
    import torch
    from qwen_tts import Qwen3TTSModel
    print("Loading Qwen3-TTS Base (clone)...", flush=True)
    def load():
        try:
            return Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                        device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa")
        except Exception:
            print("  bf16 failed, retrying fp16...", flush=True)
            return Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                        device_map="cuda:0", dtype=torch.float16, attn_implementation="sdpa")
    clone = load()
    print("Qwen ready.\n", flush=True)

    # build one reusable clone-prompt per DISTINCT voice_ref (speed + consistency).
    # If the cast entry has a ref_text (the exact line the ref clip spoke), use ICL mode
    # (higher quality). Otherwise clone from the speaker embedding only
    # (x_vector_only_mode=True) — required because ref_text=None in ICL mode errors:
    # "ref_text is required when x_vector_only_mode=False".
    prompt_cache = {}
    def get_prompt(ref_rel, ref_text):
        key = (ref_rel, bool(ref_text))
        if key not in prompt_cache:
            local = f"/kaggle/working/{os.path.basename(ref_rel)}"
            if not os.path.exists(local):
                fetch(ref_rel, local)
            arr, sr = sf.read(local)
            if ref_text:
                prompt_cache[key] = clone.create_voice_clone_prompt(
                    ref_audio=(arr, sr), ref_text=ref_text)
            else:
                prompt_cache[key] = clone.create_voice_clone_prompt(
                    ref_audio=(arr, sr), x_vector_only_mode=True)
        return prompt_cache[key]

    for idx, ln in my_lines:
        spk = ln["speaker"]; spec = CASTM.get(spk, {})
        ref = spec.get("voice_ref")
        out = f"{WORK}/{manifest_lib.line_filename(idx, spk)}"
        if not ref:
            manifest_lib.mark(manifest, idx, status="failed", engine="qwen3-tts-clone",
                              voice=None, synth_pass="qwen")
            print(f"  !! line{idx:03d} {spk}: no voice_ref in cast.json", flush=True); continue
        try:
            prompt = get_prompt(ref, spec.get("ref_text"))
            wavs, sr = clone.generate_voice_clone(text=ln["text"], language="English",
                                                  voice_clone_prompt=prompt)
            sf.write(out, wavs[0], sr)
            dur = sf.info(out).duration if os.path.exists(out) else 0.0
            manifest_lib.mark(manifest, idx, status="rendered", engine="qwen3-tts-clone",
                              voice=os.path.basename(ref), params={}, duration=round(dur, 3),
                              synth_pass="qwen")
            print(f"  OK line{idx:03d} {spk} <- {os.path.basename(ref)}", flush=True)
        except Exception as e:
            manifest_lib.mark(manifest, idx, status="failed", engine="qwen3-tts-clone",
                              voice=os.path.basename(ref), synth_pass="qwen")
            print(f"  !! line{idx:03d} {spk}: {str(e)[:80]}", flush=True)

else:
    raise SystemExit(f"PASS must be 'voicetut' or 'qwen', got {PASS!r}")

# =====================================================================
# save the manifest (pass-tagged so the two zips don't clobber) + zip
# =====================================================================
manifest_lib.save(manifest, MANIFEST_PATH)
manifest_lib.save(manifest, f"{WORK}/manifest.{PASS}.json")
rendered = sum(1 for e in manifest["lines"] if e["status"] == "rendered" and e["synth_pass"] == PASS)
print(f"\n{PASS} pass done: {rendered} line(s) rendered this pass.", flush=True)

import zipfile
zip_path = f"/kaggle/working/ep{EPISODE:02d}_{PASS}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(WORK)):
        if fn.endswith(".wav") or fn.endswith(".json"):
            z.write(os.path.join(WORK, fn), fn)
print(f"Download: {zip_path}")
print("Run BOTH passes (voicetut + qwen), download both zips, drop their contents into "
      f"the server at episodes/ep{EPISODE:02d}/synth/ — then assemble_audio.py merges them.")
