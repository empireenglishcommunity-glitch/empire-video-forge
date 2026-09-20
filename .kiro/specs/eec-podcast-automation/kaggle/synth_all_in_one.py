# ==========================================================================
# EEC "Yalla Fluent" — ONE-RUN EPISODE PIPELINE  (generate-all + assemble)
# --------------------------------------------------------------------------
# ONE Kaggle notebook, ONE "Run All": renders EVERY voice (VoiceTut + Qwen),
# then assembles them into a SINGLE final ``epNN_audio_plain.m4a`` — no manual
# two-zip hand-off, no server round-trip.  Built for BOTH the Ep1 fix loop
# (fast, selective re-gen) AND the Phase-D season batch (hands-off).
#
# WHY THIS IS SAFE (the dep-clash that forced two passes):
#   VoiceTut (transformers>=5.3 + OmniVoice) and Qwen3-TTS want DIFFERENT
#   library stacks and stomp on each other in one Python process.  So we DON'T
#   run them in one process — the orchestrator runs each engine in its OWN
#   SUBPROCESS after (re)installing that engine's deps.  Models load one at a
#   time (T4 VRAM is plenty); the manifest + WAVs are shared on disk exactly
#   like the two-kernel flow, so every contract (manifest_lib, cast.json,
#   lineNNN_<Speaker>.wav @ 24 kHz, assemble_audio.py) is preserved untouched.
#
# CHOPPINESS FIX (FIX-007): we STOPPED injecting commas / '...' into the text
#   (macal_prosody / teacher_prosody made the TTS read each 3-word chunk as its
#   own sentence -> the "every word alone" robotic feel).  Instead the text goes
#   in NATURAL, and we slow a voice down AFTER generation with ffmpeg ``atempo``
#   (pitch-preserving time-stretch) using the cast ``speed`` as the tempo factor.
#   Smooth AND slower.  Same FIX-004 lesson: stop fighting the engine.
#
# ==========================================================================
#  HOW TO RUN  (Kaggle -> GPU T4 x1 -> Internet ON)
# --------------------------------------------------------------------------
#  CELL 1 (setup — run once):
#     !pip -q install requests soundfile
#     import urllib.request
#     urllib.request.urlretrieve(
#       "https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
#       "empire-video-forge/main/.kiro/specs/eec-podcast-automation/kaggle/"
#       "synth_all_in_one.py", "synth_all_in_one.py")
#
#  CELL 2 (run the whole pipeline):
#     !python synth_all_in_one.py --episode 1
#       # options:
#       #   --regen ALL            (default) render every line
#       #   --regen 8,35,36        render ONLY these global line indices (fast fix loop)
#       #   --regen macal-abc      build the A/B/C choppiness comparison for Macal & STOP
#       #   --engines voicetut     run only one engine (skip the other)
#       #   --no-assemble          synth only, skip the final .m4a
#       #   --branch main          which repo branch to pull scripts/cast from
#       #   --upload               auto-push the final .m4a to Drive (needs Kaggle
#       #                          Secrets EEC_GDRIVE_REFRESH_TOKEN / _CLIENT_ID /
#       #                          _CLIENT_SECRET; otherwise just download it)
#
#  OUTPUT (all under /kaggle/working/epNN/):
#     epNN_audio_plain.m4a   <- THE single final file (download this)
#     lineNNN_<Speaker>.wav  <- every rendered line
#     manifest.json          <- authoritative order/state
#     (macal-abc mode: macal_abc_A|B|C_*.wav for the listen test)
# ==========================================================================
import os, re, sys, json, argparse, subprocess, urllib.request, shutil, glob

REPO = "empireenglishcommunity-glitch/empire-video-forge"
SPEC = ".kiro/specs/eec-podcast-automation"
WORKROOT = "/kaggle/working"


# --------------------------------------------------------------------------
#  small helpers shared by orchestrator + workers
# --------------------------------------------------------------------------
def raw_url(branch, rel):
    return f"https://raw.githubusercontent.com/{REPO}/{branch}/{SPEC}/{rel}"


def fetch(branch, rel, dst):
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    urllib.request.urlretrieve(raw_url(branch, rel), dst)
    return dst


def sh(cmd, **kw):
    """Run a shell command, streaming output; raise on failure."""
    print("  $ " + (cmd if isinstance(cmd, str) else " ".join(cmd)), flush=True)
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=True, **kw)


def load_shared(branch, work):
    """Fetch the shared contracts every stage needs (manifest_lib, cast, script,
    lexicon, phonetic map). Returns a dict of local paths."""
    import importlib.util as ilu
    ml = fetch(branch, "kaggle/manifest_lib.py", f"{work}/manifest_lib.py")
    spec = ilu.spec_from_file_location("manifest_lib", ml)
    manifest_lib = ilu.module_from_spec(spec); spec.loader.exec_module(manifest_lib)
    return manifest_lib


# ==========================================================================
#  ENGINE WORKERS  — each runs in its OWN subprocess (isolated deps).
#  The worker is invoked as:  python synth_all_in_one.py __worker <engine> <json-args>
# ==========================================================================

def _prepare_ar(text, lex):
    for w in sorted(lex, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", lex[w], text)
    return text


def _skeleton(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s); s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\u0640", "")
    for src, dst in (("أإآٱ", "ا"), ("ة", "ه"), ("ى", "ي"), ("ؤ", "و"), ("ئ", "ي"), ("ء", "")):
        for ch in src:
            s = s.replace(ch, dst)
    return re.sub(r"\s+", " ", re.sub(r"[^\u0600-\u06FF\s]", " ", s)).strip()


def _apply_en_phonetic(text, enphon):
    if not enphon:
        return text
    def repl(m):
        return enphon[m.group(0).lower()]
    for w in sorted(enphon, key=len, reverse=True):
        text = re.sub(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", repl, text, flags=re.IGNORECASE)
    return text


def _atempo_chain(factor):
    """ffmpeg atempo supports 0.5..2.0 per stage; chain stages for extremes.
    factor < 1.0 slows down (pitch preserved). Returns an -af string or None."""
    if abs(factor - 1.0) < 1e-3:
        return None
    f = max(0.5, min(2.0, factor))
    # for our range (0.8..0.9) a single stage is enough
    return f"atempo={round(f,4)}"


def _slow_wav_inplace(path, factor):
    """FIX-007: slow a rendered WAV by `factor` with pitch-preserving atempo,
    replacing it in place. This is how we pace a voice now — NOT by mangling text."""
    af = _atempo_chain(factor)
    if af is None:
        return
    tmp = path + ".slow.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path,
                    "-af", af, "-ar", "24000", "-ac", "1", tmp], check=True)
    os.replace(tmp, path)


def worker_voicetut(args):
    """Render every voicetut-engine line NATURALLY, then time-stretch to the
    cast pace with atempo. No text-injected pauses (FIX-007)."""
    import soundfile as sf
    branch, work, ep = args["branch"], args["work"], args["episode"]
    regen = set(args["regen"]) if args["regen"] != "ALL" else None
    manifest_lib = load_shared(branch, work)
    script = json.load(open(f"{work}/script.json", encoding="utf-8"))
    cast = json.load(open(f"{work}/cast.json", encoding="utf-8"))["cast"]
    LEX = json.load(open(f"{work}/lex.json", encoding="utf-8"))
    try:
        enphon = json.load(open(f"{work}/enphon.json", encoding="utf-8")).get("map", {})
    except Exception:
        enphon = {}

    mpath = f"{work}/manifest.json"
    manifest = manifest_lib.load_or_init(mpath, script)

    def is_vt(spk):
        return cast.get(spk, {}).get("engine") == "voicetut"

    mine = [(i, ln) for i, ln in enumerate(script["lines"], 1)
            if ln.get("lang") in ("ar", "en") and is_vt(ln["speaker"])
            and (regen is None or i in regen)]
    print(f"[voicetut] rendering {len(mine)} line(s)", flush=True)
    if not mine:
        manifest_lib.save(manifest, mpath); return

    from voicetut_tts import VoiceTutTTS
    vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
    try:
        vt.add_lexicon(LEX["lexicon"])
        if LEX.get("names_en_ar") and hasattr(vt, "add_names"):
            vt.add_names(LEX["names_en_ar"])
    except Exception:
        import traceback; traceback.print_exc()

    asr = None
    try:
        from faster_whisper import WhisperModel
        asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
    except Exception:
        print("  (faster-whisper unavailable — skipping ASR-QA)", flush=True)

    flagged = {}
    for idx, ln in mine:
        spk = ln["speaker"]; spec = cast.get(spk, {})
        voice = spec.get("voice", "Abdelrahman")
        is_ar = (ln.get("lang") == "ar")
        # FIX-007: NATURAL text only. Arabic -> light-touch lexicon; English -> phonetic map.
        # NO macal_prosody / teacher_prosody injection. Pace comes from atempo below.
        text = _prepare_ar(ln["text"], LEX["lexicon"]) if is_ar else _apply_en_phonetic(ln["text"], enphon)
        # engine runs at NATURAL speed; we pace afterwards with atempo (pitch-safe)
        params = {"num_step": spec.get("num_step", 64),
                  "guidance_scale": spec.get("guidance_scale", 2.5),
                  "speed": 1.0}
        out = f"{work}/{manifest_lib.line_filename(idx, spk)}"
        try:
            vt.synthesize(text, speaker=voice, output=out, **params)
            # pace: cast 'speed' becomes the atempo factor (0.85 => 15% slower, smooth)
            pace = float(spec.get("speed", 1.0))
            _slow_wav_inplace(out, pace)
            dur = sf.info(out).duration if os.path.exists(out) else 0.0
            manifest_lib.mark(manifest, idx, status="rendered", engine="voicetut",
                              voice=voice, params={**params, "atempo": pace},
                              duration=round(dur, 3), synth_pass="voicetut")
            if asr is not None and is_ar and dur > 0:
                try:
                    segs, _ = asr.transcribe(out, language="ar")
                    heard = " ".join(s.text for s in segs)
                    import difflib
                    a, b = _skeleton(ln["text"]).split(), _skeleton(heard).split()
                    ratio = difflib.SequenceMatcher(None, a, b).ratio()
                    if ratio < 0.5:
                        flagged[idx] = {"intended": ln["text"], "heard": heard, "ratio": round(ratio, 3)}
                except Exception:
                    pass
            print(f"  OK line{idx:03d} {spk} [{'ar' if is_ar else 'en'}] {voice} @atempo{pace}", flush=True)
        except Exception as e:
            manifest_lib.mark(manifest, idx, status="failed", engine="voicetut",
                              voice=voice, params=params, synth_pass="voicetut")
            print(f"  !! line{idx:03d} {spk}: {str(e)[:90]}", flush=True)

    manifest_lib.save(manifest, mpath)
    if flagged:
        json.dump(flagged, open(f"{work}/qa_flagged.json", "w"), ensure_ascii=False, indent=2)
        print(f"  ASR-QA flagged {len(flagged)} line(s) -> qa_flagged.json", flush=True)


def worker_qwen(args):
    """Render every qwen-clone line from its frozen voice_ref (unchanged logic)."""
    import soundfile as sf, torch
    branch, work, ep = args["branch"], args["work"], args["episode"]
    regen = set(args["regen"]) if args["regen"] != "ALL" else None
    manifest_lib = load_shared(branch, work)
    script = json.load(open(f"{work}/script.json", encoding="utf-8"))
    cast = json.load(open(f"{work}/cast.json", encoding="utf-8"))["cast"]

    mpath = f"{work}/manifest.json"
    manifest = manifest_lib.load_or_init(mpath, script)

    def is_qwen(spk):
        return cast.get(spk, {}).get("engine") in ("qwen3-tts-clone", "qwen3-tts-design")

    mine = [(i, ln) for i, ln in enumerate(script["lines"], 1)
            if ln.get("lang") in ("ar", "en") and is_qwen(ln["speaker"])
            and (regen is None or i in regen)]
    print(f"[qwen] rendering {len(mine)} line(s)", flush=True)
    if not mine:
        manifest_lib.save(manifest, mpath); return

    from qwen_tts import Qwen3TTSModel
    def load():
        for dt in (torch.bfloat16, torch.float16):
            try:
                return Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                        device_map="cuda:0", dtype=dt, attn_implementation="sdpa")
            except Exception:
                print(f"  {dt} load failed, retrying...", flush=True)
        raise RuntimeError("Qwen load failed")
    clone = load()

    cache = {}
    def get_prompt(ref_rel, ref_text):
        key = (ref_rel, bool(ref_text))
        if key not in cache:
            local = f"{work}/{os.path.basename(ref_rel)}"
            if not os.path.exists(local):
                fetch(branch, ref_rel, local)
            arr, sr = sf.read(local)
            cache[key] = (clone.create_voice_clone_prompt(ref_audio=(arr, sr), ref_text=ref_text)
                          if ref_text else
                          clone.create_voice_clone_prompt(ref_audio=(arr, sr), x_vector_only_mode=True))
        return cache[key]

    for idx, ln in mine:
        spk = ln["speaker"]; spec = cast.get(spk, {})
        ref = spec.get("voice_ref")
        out = f"{work}/{manifest_lib.line_filename(idx, spk)}"
        if not ref:
            manifest_lib.mark(manifest, idx, status="failed", engine="qwen3-tts-clone",
                              voice=None, synth_pass="qwen")
            print(f"  !! line{idx:03d} {spk}: no voice_ref", flush=True); continue
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
                              voice=os.path.basename(ref) if ref else None, synth_pass="qwen")
            print(f"  !! line{idx:03d} {spk}: {str(e)[:90]}", flush=True)

    manifest_lib.save(manifest, mpath)


def worker_macal_abc(args):
    """FIX-007 A/B/C listen test on ONE Macal line: prove the fix by ear.
       A = OLD (prosody hacks + speed) — the choppy version you heard.
       B = NEW natural text, natural speed (baseline smoothness).
       C = NEW natural text + atempo pace (smooth AND slowed) — the proposed fix.
    """
    import soundfile as sf
    branch, work = args["branch"], args["work"]
    cast = json.load(open(f"{work}/cast.json", encoding="utf-8"))["cast"]
    spec = cast["Macal"]; voice = spec.get("voice", "Abdullah")
    pace = float(spec.get("speed", 0.85))
    try:
        enphon = json.load(open(f"{work}/enphon.json", encoding="utf-8")).get("map", {})
    except Exception:
        enphon = {}
    # a representative Macal line (a couple of sentences)
    line = args.get("line_text") or ("Hi guys, nice to meet you. I am learning English "
                                     "every day, and I want to get better and better.")

    # OLD prosody (reproduced here so A truly matches what the owner heard)
    def old_macal_prosody(text):
        out, buf = [], []
        for w in text.split():
            buf.append(w)
            if len(buf) >= 3 and buf[-1][-1:] not in ".,!?…":
                out.append(" ".join(buf) + ","); buf = []
        if buf:
            out.append(" ".join(buf))
        t = " ".join(out)
        t = re.sub(r"([.!?])\s+", r"\1.. ", t)
        t = re.sub(r",\s+", r"... ", t)
        return t

    from voicetut_tts import VoiceTutTTS
    vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")

    base = {"num_step": spec.get("num_step", 64), "guidance_scale": spec.get("guidance_scale", 2.5)}
    natural = _apply_en_phonetic(line, enphon)

    outs = {}
    # A: OLD — injected pauses + engine speed 0.85
    a = f"{work}/macal_abc_A_old_prosody.wav"
    vt.synthesize(old_macal_prosody(natural), speaker=voice, output=a, speed=0.85, **base); outs["A"] = a
    # B: NEW natural text, natural speed 1.0
    b = f"{work}/macal_abc_B_natural_1.0.wav"
    vt.synthesize(natural, speaker=voice, output=b, speed=1.0, **base); outs["B"] = b
    # C: NEW natural text + atempo pace (the proposed fix)
    c = f"{work}/macal_abc_C_natural_atempo{pace}.wav"
    vt.synthesize(natural, speaker=voice, output=c, speed=1.0, **base)
    _slow_wav_inplace(c, pace); outs["C"] = c

    for k, p in outs.items():
        print(f"  {k}: {p}  ({round(sf.info(p).duration,2)}s)", flush=True)
    print("\nLISTEN to A (old/choppy) vs B (natural) vs C (natural+paced). "
          "Tell me which sounds human & smooth; C is the proposed fix.", flush=True)


# ==========================================================================
#  ORCHESTRATOR  — installs each engine's deps, runs its worker in a subprocess,
#  then assembles.  This is what CELL 2 calls.
# ==========================================================================
VT_INSTALL = [
    # NOTE: each entry is an ARGUMENT LIST (no shell, no quotes). When passing a
    # list to subprocess there is NO shell to strip quotes, so a token must be the
    # bare requirement, e.g. "transformers>=5.3.0" (a literal '"' inside the token
    # makes pip fail with 'Invalid requirement').
    ["install", "-U", "transformers>=5.3.0"],
    ["install", "git+https://github.com/k2-fsa/OmniVoice.git"],
    ["install", "voicetut-tts", "catt-tashkeel", "faster-whisper", "soundfile"],
]
QWEN_INSTALL = [
    ["install", "-U", "qwen-tts", "soundfile"],
]


def run_worker(engine, args, installs):
    """Install engine deps, then run its worker in a FRESH python subprocess so
    the two engines' libraries never coexist in one interpreter."""
    print(f"\n===== ENGINE: {engine} — installing deps =====", flush=True)
    for pip_args in installs:
        # python -m pip -q install ... (quiet, no shell)
        sh([sys.executable, "-m", "pip", "-q", *pip_args])
    print(f"===== ENGINE: {engine} — synthesizing =====", flush=True)
    payload = json.dumps(args)
    sh([sys.executable, os.path.abspath(__file__), "__worker", engine, payload])


def prefetch(branch, work):
    """Grab the shared contracts once, up front (workers reuse them from disk)."""
    ep = os.environ.get("_EEC_EP", "1")
    fetch(branch, f"episodes/ep{int(ep):02d}/script.json", f"{work}/script.json")
    fetch(branch, "pipeline/cast.json", f"{work}/cast.json")
    fetch(branch, "pipeline/egyptian_lexicon.json", f"{work}/lex.json")
    try:
        fetch(branch, "pipeline/english_phonetic_map.json", f"{work}/enphon.json")
    except Exception:
        pass
    fetch(branch, "kaggle/manifest_lib.py", f"{work}/manifest_lib.py")
    fetch(branch, "pipeline/assemble_audio.py", f"{work}/assemble_audio.py")
    try:
        fetch(branch, "pipeline/structure_check.py", f"{work}/structure_check.py")
    except Exception:
        pass


def assemble(work, ep):
    """Run the SAME server assembler locally on Kaggle -> one epNN_audio_plain.m4a.
    We lay the flat lineNNN_*.wav + manifest.json into <epdir>/synth/ (the global
    -idx layout assemble_audio.py already understands) and call it in --plain mode."""
    epdir = f"{work}/ep{ep:02d}"
    synth = f"{epdir}/synth"
    os.makedirs(synth, exist_ok=True)
    shutil.copy(f"{work}/script.json", f"{epdir}/script.json")
    for f in glob.glob(f"{work}/line*_*.wav") + glob.glob(f"{work}/manifest*.json"):
        shutil.copy(f, synth)
    # structure_check import is optional inside assemble_audio; copy it beside it
    for f in ("assemble_audio.py", "manifest_lib.py", "structure_check.py"):
        if os.path.exists(f"{work}/{f}"):
            shutil.copy(f"{work}/{f}", f"{epdir}/{f}")
    print("\n===== ASSEMBLE (plain, dry voices) =====", flush=True)
    sh([sys.executable, f"{epdir}/assemble_audio.py", "--episode", str(ep),
        "--dir", epdir, "--wav-dir", synth, "--plain"])
    out = f"{epdir}/ep{ep:02d}_audio_plain.m4a"
    if os.path.exists(out):
        # surface it at the working root for a one-click download
        final = f"{work}/ep{ep:02d}_audio_plain.m4a"
        shutil.copy(out, final)
        print(f"\n✅ FINAL: {final}", flush=True)
    return out


def drive_upload(local_path, drive_name, folder_id):
    """OPTIONAL auto-upload of the final .m4a straight from Kaggle to the Drive
    'output' folder — so the owner doesn't even do the download+upload step.

    Kaggle CANNOT reach the server's n8n container, so we can't reuse
    pipeline/drive_upload.py's `docker exec` token path. Instead we use a Google
    OAuth **refresh token** provided via Kaggle Secrets (Add-ons -> Secrets):
        EEC_GDRIVE_REFRESH_TOKEN , EEC_GDRIVE_CLIENT_ID , EEC_GDRIVE_CLIENT_SECRET
    If any secret is missing we SKIP silently and fall back to the one-click
    download of the final file (never blocks the run).
    """
    try:
        from kaggle_secrets import UserSecretsClient
        sec = UserSecretsClient()
        rt = sec.get_secret("EEC_GDRIVE_REFRESH_TOKEN")
        cid = sec.get_secret("EEC_GDRIVE_CLIENT_ID")
        csec = sec.get_secret("EEC_GDRIVE_CLIENT_SECRET")
    except Exception:
        print("  (Drive auto-upload skipped — Kaggle secrets not set; "
              "download the final .m4a instead)", flush=True)
        return None
    if not (rt and cid and csec):
        print("  (Drive auto-upload skipped — secrets incomplete)", flush=True)
        return None
    import urllib.parse
    try:
        body = urllib.parse.urlencode({"client_id": cid, "client_secret": csec,
            "refresh_token": rt, "grant_type": "refresh_token"}).encode()
        at = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://oauth2.googleapis.com/token", data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=30))["access_token"]
        b = "===EECB==="
        payload = b""
        payload += ("--"+b+"\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n").encode()
        payload += (json.dumps({"name": drive_name, "parents": [folder_id]})+"\r\n").encode()
        payload += ("--"+b+"\r\nContent-Type: audio/mp4\r\n\r\n").encode()
        payload += open(local_path, "rb").read()+b"\r\n"
        payload += ("--"+b+"--").encode()
        r = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true",
            data=payload, headers={"Authorization": "Bearer "+at,
                                   "Content-Type": "multipart/related; boundary="+b}), timeout=600))
        print(f"  ✅ UPLOADED to Drive: {r.get('name')}  (id {r.get('id')})", flush=True)
        return r.get("id")
    except Exception as e:
        print(f"  (Drive auto-upload failed: {str(e)[:120]} — download the .m4a instead)", flush=True)
        return None


# Drive 'output' folder id (same target the owner uses); overridable via --drive-folder
DRIVE_OUTPUT_FOLDER = "1bKV8ALl6luA31CKayW2O3loofEWWHmHh"


def main():
    # dispatch worker subprocess mode first
    if len(sys.argv) >= 4 and sys.argv[1] == "__worker":
        engine, payload = sys.argv[2], json.loads(sys.argv[3])
        {"voicetut": worker_voicetut, "qwen": worker_qwen,
         "macal-abc": worker_macal_abc}[engine](payload)
        return

    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, default=1)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--regen", default="ALL",
                    help="'ALL', a comma list of global line idxs (e.g. 8,35,36), "
                         "or 'macal-abc' for the choppiness listen-test")
    ap.add_argument("--engines", default="voicetut,qwen",
                    help="comma list of engines to run (voicetut,qwen)")
    ap.add_argument("--no-assemble", action="store_true")
    ap.add_argument("--upload", action="store_true",
                    help="after assembly, auto-upload the final .m4a to the Drive "
                         "'output' folder using Kaggle Secrets (EEC_GDRIVE_*). "
                         "Skipped silently if secrets are absent.")
    ap.add_argument("--drive-folder", default=DRIVE_OUTPUT_FOLDER,
                    help="Drive folder id to upload into (default: EEC output folder)")
    args = ap.parse_args()

    ep = args.episode
    os.environ["_EEC_EP"] = str(ep)
    work = f"{WORKROOT}/ep{ep:02d}_run"
    os.makedirs(work, exist_ok=True)
    prefetch(args.branch, work)

    # ---- A/B/C choppiness test: run only the voicetut env + the abc worker, STOP ----
    if args.regen.strip().lower() == "macal-abc":
        run_worker("macal-abc", {"branch": args.branch, "work": work}, VT_INSTALL)
        print("\nmacal-abc done — no assembly (this is a listen test).")
        return

    regen = "ALL" if args.regen.strip().upper() == "ALL" else \
        [int(x) for x in re.split(r"[,\s]+", args.regen.strip()) if x]
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]

    if "voicetut" in engines:
        run_worker("voicetut", {"branch": args.branch, "work": work,
                                "episode": ep, "regen": regen}, VT_INSTALL)
    if "qwen" in engines:
        run_worker("qwen", {"branch": args.branch, "work": work,
                            "episode": ep, "regen": regen}, QWEN_INSTALL)

    if not args.no_assemble:
        out = assemble(work, ep)
        final = f"{work}/ep{ep:02d}_audio_plain.m4a"
        if args.upload and os.path.exists(final):
            drive_upload(final, f"Yalla Fluent - Ep{ep:02d} - {os.path.basename(final)}",
                         args.drive_folder)
        print(f"\n👉 Download the single final file from the Kaggle output panel: {final}")
    else:
        print("\n--no-assemble: skipped final mix. WAVs + manifest are in", work)


if __name__ == "__main__":
    main()
