#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — ARABIC COACH synthesizer (Gemini TTS, voice "Kore").

Runs on the SERVER (no GPU needed) via the existing Gemini API key. Reads an
episode script.json and synthesizes every Arabic Coach line into its own WAV,
plus a timeline.ar.json. The English lines are produced separately on Kaggle
(synth_english.py); the two timelines merge at the audio-assembly stage.

Why here (not Kaggle): the Coach is ~1/3 of the lines and Gemini TTS runs fine
on CPU via HTTP — so it stays fully unattended on the server while only the
GPU-bound English step needs Kaggle.

Gemini free TTS quota is tight (429s), so we pace requests and retry with
backoff. Fail-soft: a line that keeps failing is skipped (logged), never
aborting the whole run.

Usage:
  GEMINI_API_KEY=... python3 synth_coach.py --episode 1 \
      [--script /path/script.json] [--outdir /path/epNN] [--voice Kore]
"""
import os, sys, json, base64, struct, argparse, time
import urllib.request, urllib.error

TTS_MODEL = os.environ.get("EEC_TTS_MODEL", "gemini-2.5-flash-preview-tts")
VOICE = "Kore"
# Egyptian-coach delivery direction prepended to each line (style prompt).
STYLE = ("Say this warmly and clearly, like a friendly, encouraging Egyptian "
         "English coach speaking to a student: ")


def call_gemini_tts(text, api_key, voice):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{TTS_MODEL}:generateContent?key={api_key}")
    body = {
        "contents": [{"parts": [{"text": STYLE + text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
            },
        },
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))
    part = data["candidates"][0]["content"]["parts"][0]
    inline = part["inlineData"]
    pcm = base64.b64decode(inline["data"])
    # mimeType looks like "audio/L16;codec=pcm;rate=24000"
    mime = inline.get("mimeType", "")
    rate = 24000
    for tok in mime.split(";"):
        if tok.strip().startswith("rate="):
            rate = int(tok.strip().split("=")[1])
    return pcm, rate


def pcm_to_wav(pcm, rate, path):
    """Wrap raw signed-16 mono PCM in a WAV container (no deps)."""
    n = len(pcm)
    byte_rate = rate * 1 * 2
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + n))
        f.write(b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, rate, byte_rate, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", n))
        f.write(pcm)
    return round(n / byte_rate, 3)  # duration in seconds


def synth_line(text, api_key, voice, path, tries=4):
    """Fail-soft TTS with backoff on quota/5xx. Returns duration or None."""
    delay = 5
    for attempt in range(1, tries + 1):
        try:
            pcm, rate = call_gemini_tts(text, api_key, voice)
            return pcm_to_wav(pcm, rate, path)
        except urllib.error.HTTPError as e:
            code = e.code
            retryable = code in (429, 500, 503)
            print(f"    attempt {attempt}: HTTP {code}"
                  + (" (retrying)" if retryable and attempt < tries else ""),
                  file=sys.stderr)
            if not retryable or attempt == tries:
                return None
            time.sleep(delay)
            delay = min(delay * 2, 60)
        except Exception as e:
            print(f"    attempt {attempt}: {str(e)[:100]}", file=sys.stderr)
            if attempt == tries:
                return None
            time.sleep(delay)
            delay = min(delay * 2, 60)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--script", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--voice", default=VOICE)
    ap.add_argument("--pace", type=float, default=6.0,
                    help="seconds to wait between lines (quota pacing)")
    ap.add_argument("--force", action="store_true",
                    help="re-synthesize even lines that already have a WAV")
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY", file=sys.stderr); sys.exit(2)

    home = os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast")
    ep = args.episode
    script_path = args.script or os.path.join(
        home, "episodes", f"ep{ep:02d}", "script.json")
    outdir = args.outdir or os.path.join(home, "episodes", f"ep{ep:02d}")

    try:
        with open(script_path, encoding="utf-8") as f:
            script = json.load(f)
    except Exception as e:
        print(f"ERROR: cannot read script {script_path}: {e}", file=sys.stderr)
        sys.exit(2)

    os.makedirs(outdir, exist_ok=True)
    timeline = {"episode": ep, "title": script.get("title"),
                "lang": "ar", "voice": args.voice, "lines": []}

    idx = 0
    ok = 0
    for ln in script["lines"]:
        if ln.get("lang") != "ar":
            continue  # English lines handled by synth_english.py (Kaggle)
        idx += 1
        speaker = ln.get("speaker", "Coach")
        text = ln["text"].strip()
        fname = f"coach{idx:03d}_{speaker}.wav"
        path = os.path.join(outdir, fname)

        # RESUMABLE: keep an already-synthesized, valid WAV so a re-run only
        # fills the gaps that quota/errors left behind (never clobber good audio).
        if not args.force and os.path.exists(path) and os.path.getsize(path) > 1000:
            dur = round((os.path.getsize(path) - 44) / (24000 * 2), 3)
            ok += 1
            timeline["lines"].append({
                "idx": idx, "section": ln.get("section"), "speaker": speaker,
                "lang": "ar", "voice": args.voice, "file": fname,
                "sr": 24000, "duration": dur, "text": text,
                "teaches": ln.get("teaches", []),
            })
            print(f"  coach line {idx} ({speaker}) — already done, keeping ({dur}s)")
            continue

        print(f"  coach line {idx} ({speaker})...", flush=True)
        dur = synth_line(text, api_key, args.voice, path)
        if dur is None:
            print(f"  coach line {idx} SKIPPED after retries", file=sys.stderr)
            continue
        ok += 1
        timeline["lines"].append({
            "idx": idx, "section": ln.get("section"), "speaker": speaker,
            "lang": "ar", "voice": args.voice, "file": fname,
            "sr": 24000, "duration": dur, "text": text,
            "teaches": ln.get("teaches", []),
        })
        print(f"    -> {fname} {dur}s")
        if args.pace:
            time.sleep(args.pace)  # stay under the free-tier rate limit

    tl_path = os.path.join(outdir, "timeline.ar.json")
    with open(tl_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)

    total = round(sum(l["duration"] for l in timeline["lines"]), 1)
    print(f"DONE: {ok}/{idx} Arabic lines, ~{total}s -> {tl_path}")
    if ok < idx:
        sys.exit(1)  # signal partial success so the caller can re-run


if __name__ == "__main__":
    main()
