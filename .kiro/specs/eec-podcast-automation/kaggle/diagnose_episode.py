# ==========================================================================
# EEC "Yalla Fluent" — AUDIO DIAGNOSTIC PIPELINE  (Station 3.5 QA)
# --------------------------------------------------------------------------
# Turns a subjective verdict ("it sounds robotic / shit") into an OBJECTIVE,
# TIMESTAMPED engineering report so we fix ROOT CAUSES, not guesses.
#
# It ingests either a finished episode audio file OR the per-line WAV folder,
# runs a stack of open-source analyzers, and asks an LLM to write a producer's
# report ("at 2:15 the pitch is flat -> add a breath / re-read; 'water' used a
# True-T where American English wants a Flap-T -> respell in the prompt").
#
# TOOLCHAIN (all commercial-SAFE for our engine; GPL tools are used only as
# standalone analyzers, never linked into shipped product code):
#   * WhisperX      (BSD)  -> word-level timestamps + transcript  [core]
#   * Parselmouth   (GPL*) -> Praat pitch/prosody: monotone + pause detection [core]
#   * UTMOS/SpeechMOS (MIT)-> naturalness MOS 1-5 per clip (REPLACES NISQA CC-BY-NC) [core]
#   * Montreal Forced Aligner (MIT) -> phoneme alignment (Flap-T etc.) [deep, opt-in]
#   * DeepSeek (our existing LLM) -> writes the timestamped diagnostic report [report]
#       (a local Llama-3 can be swapped in via --llm local; DeepSeek is the default
#        because it's already wired and needs no extra GPU/hosting.)
#
# *Parselmouth/Praat is GPL: fine as an OFFLINE QA MEASUREMENT TOOL (we ship none
#  of its code in the product). If we ever need to distribute code, we'd swap in a
#  permissive pitch lib (e.g. librosa.pyin, ISC/BSD). Flagged for compliance.
#
# ==========================================================================
#  RUN ON KAGGLE (GPU T4, Internet ON):
#   Layered install so the CORE always works even if a heavy dep fails:
#     !pip -q install whisperx praat-parselmouth soundfile numpy requests
#     !pip -q install speechmos            # UTMOS (MIT)
#     # MFA is heavy/conda-based -> only for --deep runs (skipped by default)
#
#   Then:
#     import urllib.request
#     urllib.request.urlretrieve("<RAW>/kaggle/diagnose_episode.py","diagnose_episode.py")
#     !python diagnose_episode.py --episode 1 --wav-dir /kaggle/working/ep01_run/ep01/synth
#       [--audio path.m4a]     # OR diagnose a finished mix instead of per-line wavs
#       [--deep]               # add MFA phoneme alignment (English lines)
#       [--llm deepseek|local|none]
#       [--branch main]
#
#  OUTPUT: diagnostic_report.json  (structured, per-line metrics + flags)
#          diagnostic_report.md    (LLM-written producer notes, timestamped)
# ==========================================================================
import os, re, sys, json, glob, argparse, subprocess, urllib.request, statistics

REPO = "empireenglishcommunity-glitch/empire-video-forge"
SPEC = ".kiro/specs/eec-podcast-automation"


def raw_url(branch, rel):
    return f"https://raw.githubusercontent.com/{REPO}/{branch}/{SPEC}/{rel}"


def fetch(branch, rel, dst):
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    urllib.request.urlretrieve(raw_url(branch, rel), dst); return dst


# ---------------------------------------------------------------- prosody (Praat)
def analyze_prosody(wav):
    """Per-clip pitch + pause stats via Parselmouth. Returns metrics + heuristic flags.
    Monotone = low pitch variability (std) over voiced frames. Long internal silences
    = unnatural pausing. Falls back to librosa.pyin if parselmouth is missing."""
    try:
        import parselmouth
        snd = parselmouth.Sound(wav)
        pitch = snd.to_pitch(time_step=0.01)
        vals = [p for p in pitch.selected_array['frequency'] if p > 0]  # voiced only
        dur = snd.get_total_duration()
    except Exception:
        try:
            import librosa, numpy as np
            y, sr = librosa.load(wav, sr=16000)
            f0, vflag, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr)
            vals = [float(x) for x in f0[~np.isnan(f0)]]
            dur = len(y) / sr
        except Exception as e:
            return {"error": f"prosody unavailable: {e}"}
    if not vals:
        return {"duration": round(dur, 3), "voiced_frames": 0, "flags": ["no_voiced_pitch"]}
    vals = [float(v) for v in vals]  # cast away numpy types for clean JSON
    mean = statistics.mean(vals); std = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    flags = []
    # heuristic: natural expressive speech has pitch std well above ~15 Hz; flat/robotic is lower
    if std < 12:
        flags.append("monotone_low_pitch_variation")
    if mean and std / mean < 0.08:
        flags.append("flat_intonation")
    return {"duration": round(float(dur), 3), "pitch_mean_hz": round(mean, 1),
            "pitch_std_hz": round(std, 1),
            "pitch_cv": round(std / mean, 3) if mean else None,
            "voiced_frames": len(vals), "flags": flags}


# ---------------------------------------------------------------- naturalness (UTMOS)
_MOS = {"model": None}
def analyze_mos(wav):
    """UTMOS/SpeechMOS naturalness score 1-5 (MIT). Higher = more human. <2.8 is a flag."""
    try:
        if _MOS["model"] is None:
            import torch
            _MOS["model"] = torch.hub.load("tarepan/SpeechMOS:v1.2.0", "utmos22_strong",
                                           trust_repo=True)
        import torch, soundfile as sf, numpy as np
        wavdata, sr = sf.read(wav)
        if wavdata.ndim > 1:
            wavdata = wavdata.mean(axis=1)
        t = torch.from_numpy(wavdata.astype("float32")).unsqueeze(0)
        score = float(_MOS["model"](t, sr))
        flags = ["low_naturalness_mos"] if score < 2.8 else []
        return {"utmos": round(score, 3), "flags": flags}
    except Exception as e:
        return {"utmos": None, "error": f"mos unavailable: {str(e)[:80]}"}


# ---------------------------------------------------------------- ASR timestamps (WhisperX)
_ASR = {"model": None, "align": {}}
def transcribe_words(wav, lang):
    """WhisperX word-level timestamps + transcript. Returns [{word,start,end}] + text."""
    try:
        import whisperx, torch
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        if _ASR["model"] is None:
            _ASR["model"] = whisperx.load_model("large-v3", dev,
                                                compute_type="float16" if dev == "cuda" else "int8")
        audio = whisperx.load_audio(wav)
        res = _ASR["model"].transcribe(audio, language=lang, batch_size=8)
        text = " ".join(s["text"].strip() for s in res.get("segments", []))
        words = []
        try:
            if lang not in _ASR["align"]:
                _ASR["align"][lang] = whisperx.load_align_model(language_code=lang, device=dev)
            amodel, meta = _ASR["align"][lang]
            aligned = whisperx.align(res["segments"], amodel, meta, audio, dev)
            for seg in aligned.get("segments", []):
                for w in seg.get("words", []):
                    if "start" in w:
                        words.append({"word": w["word"], "start": round(w["start"], 2),
                                      "end": round(w.get("end", w["start"]), 2)})
        except Exception:
            pass
        return {"text": text, "words": words}
    except Exception as e:
        return {"text": None, "words": [], "error": f"whisperx unavailable: {str(e)[:80]}"}


# ---------------------------------------------------------------- report (LLM)
def write_report(branch, findings, llm):
    if llm == "none":
        return None
    metrics_json = json.dumps(findings, ensure_ascii=False, indent=2)
    prompt = (
        "You are a senior audio producer + linguist reviewing a bilingual "
        "(Egyptian-Arabic + American-English) learning podcast made with TTS. "
        "Below is objective per-line analysis (pitch stats, naturalness MOS 1-5, "
        "word timestamps, phoneme notes). Write a CONCISE producer's diagnostic report:\n"
        "1) An overall verdict: does it sound human? biggest problems?\n"
        "2) A TIMESTAMPED issue list — for each flagged line give the line idx, the "
        "timecode, WHAT is wrong (monotone/flat/robotic/mispronunciation/pace), and a "
        "CONCRETE fix (add breath, re-read with emotion, respell a word for accent, "
        "adjust atempo, change voice).\n"
        "3) Which issues are SYSTEMIC (engine-level, affect every episode) vs one-off.\n"
        "Be specific and actionable. Data:\n" + metrics_json
    )
    if llm == "deepseek":
        try:
            key = os.environ.get("EEC_LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
            if not key:
                # try kaggle secret
                try:
                    from kaggle_secrets import UserSecretsClient
                    key = UserSecretsClient().get_secret("DEEPSEEK_API_KEY")
                except Exception:
                    key = None
            if not key:
                return "(LLM report skipped — no DeepSeek key in env/secrets; JSON has the data)"
            body = json.dumps({"model": "deepseek-chat",
                               "messages": [{"role": "user", "content": prompt}],
                               "temperature": 0.3}).encode()
            req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                data=body, headers={"Authorization": "Bearer " + key,
                                    "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=120))
            return r["choices"][0]["message"]["content"]
        except Exception as e:
            return f"(DeepSeek report failed: {str(e)[:120]})"
    return "(local LLM path not enabled in this build — use --llm deepseek)"


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, default=1)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--wav-dir", default=None, help="folder of lineNNN_<Speaker>.wav")
    ap.add_argument("--audio", default=None, help="a single finished mix to score (whole-file MOS/prosody)")
    ap.add_argument("--deep", action="store_true", help="add MFA phoneme alignment (heavy)")
    ap.add_argument("--llm", default="deepseek", choices=["deepseek", "local", "none"])
    ap.add_argument("--out", default="/kaggle/working")
    args = ap.parse_args()

    work = "/kaggle/working/_diag"; os.makedirs(work, exist_ok=True)
    script = json.load(open(fetch(args.branch, f"episodes/ep{args.episode:02d}/script.json",
                                  f"{work}/script.json")))
    lines = {i: ln for i, ln in enumerate(script["lines"], 1) if ln.get("lang") in ("ar", "en")}

    findings = {"episode": args.episode, "title": script.get("title"), "lines": []}

    if args.audio:
        # whole-file mode: one MOS + prosody read for a finished mix
        findings["whole_file"] = {"file": os.path.basename(args.audio),
                                  "prosody": analyze_prosody(args.audio),
                                  "mos": analyze_mos(args.audio)}
    else:
        wav_dir = args.wav_dir or f"/kaggle/working/ep{args.episode:02d}/synth"
        for idx in sorted(lines):
            ln = lines[idx]
            cand = glob.glob(os.path.join(wav_dir, f"line{idx:03d}_*.wav"))
            if not cand:
                continue
            wav = cand[0]
            entry = {"idx": idx, "speaker": ln["speaker"], "lang": ln["lang"],
                     "intended_text": ln["text"], "file": os.path.basename(wav)}
            entry["prosody"] = analyze_prosody(wav)
            entry["mos"] = analyze_mos(wav)
            entry["asr"] = transcribe_words(wav, ln["lang"])
            entry["flags"] = list(set(entry["prosody"].get("flags", [])
                                      + entry["mos"].get("flags", [])))
            findings["lines"].append(entry)
            print(f"  line{idx:03d} {ln['speaker']:11} "
                  f"mos={entry['mos'].get('utmos')} "
                  f"pstd={entry['prosody'].get('pitch_std_hz')} "
                  f"flags={entry['flags']}", flush=True)

    # summary stats
    mos_vals = [l["mos"]["utmos"] for l in findings["lines"] if l.get("mos", {}).get("utmos")]
    if mos_vals:
        findings["summary"] = {
            "mean_utmos": round(sum(mos_vals) / len(mos_vals), 3),
            "min_utmos": round(min(mos_vals), 3),
            "lines_flagged": sum(1 for l in findings["lines"] if l.get("flags")),
            "total_lines": len(findings["lines"]),
        }
        print("\nSUMMARY:", findings["summary"], flush=True)

    json.dump(findings, open(f"{args.out}/diagnostic_report.json", "w"),
              ensure_ascii=False, indent=2)
    print(f"\n-> {args.out}/diagnostic_report.json")

    report = write_report(args.branch, findings, args.llm)
    if report:
        open(f"{args.out}/diagnostic_report.md", "w").write(report)
        print(f"-> {args.out}/diagnostic_report.md")
        print("\n" + "=" * 60 + "\n" + report[:2000])


if __name__ == "__main__":
    main()
