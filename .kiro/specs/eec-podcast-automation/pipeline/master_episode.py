#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Yalla Fluent" — SERVER-SIDE MASTERING ENGINE (Stage 2).

TWO-STAGE ARCHITECTURE (owner-locked):
  * Kaggle  = SYNTHESIS engine  -> raw per-line WAVs (kaggle/synth_all_in_one.py).
              Kaggle's ffmpeg has NO loudnorm, so it only concats un-mastered voices.
  * SERVER  = MASTERING engine  -> THIS script. Full ffmpeg 8.x (loudnorm/EQ/comp/
              sidechain) turns the raw voices into a broadcast-ready episode.

This is deliberately SEPARATE from assemble_audio.py:
  - assemble_audio.py  = ORDER + CONCAT the manifest's clips into one dry speech track
                         (+ optional simple music/stings). Runs anywhere.
  - master_episode.py  = the BROADCAST CHAIN on top of that speech track: cleanup EQ ->
                         dynamics compression -> ducked music bed -> intro/outro stings ->
                         two-pass EBU R128 loudnorm -> AAC export. Runs on the SERVER.

MASTERING CHAIN (each step fail-soft; a missing asset is skipped, never fatal):
  1. speech track     : reuse assemble_audio.py --plain (manifest-ordered dry concat)
  2. cleanup EQ       : highpass 80 Hz (kill rumble) + gentle de-ess/presence
  3. dynamics         : acompressor to even out line-to-line loudness
  4. music bed        : loop assets/music/bed.wav, duck under speech (sidechaincompress)
  5. stings           : prepend assets/sfx/intro.wav, append assets/sfx/outro.wav
  6. loudnorm (2-pass): EBU R128 measured pass -> corrective pass to -16 LUFS / -1.5 dBTP
                        (Apple/Spotify podcast target); dialnorm-accurate, not single-pass.
  7. export           : AAC 160k, 48 kHz -> epNN_audio_master.m4a  (+ timeline.master.json)

Usage (on the server):
  python3 master_episode.py --episode 1
    [--home /opt/eec-podcast] [--dir <epdir>] [--wav-dir <synth>]
    [--target-lufs -16] [--tp -1.5] [--lra 11]
    [--no-music] [--no-stings] [--bed path] [--intro path] [--outro path]
    [--music-gain 0.16] [--voice-only]   # voice-only = EQ+comp+loudnorm, no bed/stings
"""
import os, sys, json, subprocess, argparse, tempfile, shutil, glob

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SR = 48000  # master at 48k (broadcast/video-friendly); voices are 24k, upsampled cleanly


def run(cmd, **kw):
    try:
        return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)
    except subprocess.CalledProcessError as e:
        tail = (e.stderr or "").strip().splitlines()[-15:]
        print("  ffmpeg FAILED:\n    " + "\n    ".join(tail), file=sys.stderr)
        raise


def probe_dur(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nokey=1:noprint_wrappers=1", path]).stdout.strip()
    return float(out)


def have_filter(name):
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                             capture_output=True, text=True).stdout
        return (" " + name + " ") in out
    except Exception:
        return False


def build_speech_track(ep, ep_dir, wav_dir, workdir):
    """Reuse assemble_audio.py --plain to produce the manifest-ordered dry concat, then
    hand back that speech .wav (we re-render to wav so the mastering chain is lossless
    until the final AAC)."""
    import assemble_audio  # sibling module
    # assemble writes epNN_audio_plain.m4a; we want the intermediate speech, so we call
    # its internal builders directly for a clean wav.
    mres = assemble_audio.build_order_from_manifest(ep_dir, wav_dir)
    if mres is None:
        script, placed, skipped = assemble_audio.build_order(ep_dir, wav_dir)
    else:
        script, placed, skipped = mres
    if not placed:
        raise SystemExit("no rendered line WAVs found — run synthesis first")
    speech, timeline, total = assemble_audio.concat_speech(placed, 0.35, 0.7, workdir)
    print(f"  speech track: {round(total,1)}s, {len(placed)} lines"
          + (f", {len(skipped)} skipped" if skipped else ""))
    return script, speech, timeline, skipped


def cleanup_and_compress(speech, workdir):
    """Step 2+3: gentle cleanup EQ + dynamics compression on the dry speech."""
    out = os.path.join(workdir, "speech_eqcomp.wav")
    # highpass 80Hz (rumble), soft presence lift ~3kHz, then even out dynamics.
    af = ("highpass=f=80,"
          "equalizer=f=3000:width_type=q:w=1.2:g=1.5,"
          "acompressor=threshold=-18dB:ratio=3:attack=15:release=180:makeup=2")
    try:
        run(["ffmpeg", "-y", "-i", speech, "-af", af, "-ar", str(SR), "-ac", "1", out])
        return out
    except subprocess.CalledProcessError:
        print("  (cleanup/compress skipped — filter error; using raw speech)", file=sys.stderr)
        return speech


def mix_music(body, bed, gain, workdir):
    """Step 4: loop + duck a music bed under the body (sidechaincompress)."""
    dur = probe_dur(body)
    out = os.path.join(workdir, "with_music.wav")
    fc = (
        f"[1:a]aformat=sample_rates={SR}:channel_layouts=mono,volume={gain},"
        f"afade=t=in:st=0:d=1.5,afade=t=out:st={max(dur-2.0,0)}:d=2.0[bed];"
        "[bed][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck];"
        f"[0:a][duck]amix=inputs=2:duration=first:dropout_transition=0,aresample={SR}[out]"
    )
    run(["ffmpeg", "-y", "-i", body, "-stream_loop", "-1", "-i", bed,
         "-filter_complex", fc, "-map", "[out]", "-t", f"{dur}", out])
    return out


def add_stings(body, intro, outro, workdir):
    """Step 5: prepend intro sting, append outro sting."""
    inputs, labels, idx = [], [], 0
    for s in (intro, body, outro):
        if s and os.path.exists(s):
            inputs += ["-i", s]
            labels.append(f"[{idx}:a]aformat=sample_rates={SR}:channel_layouts=mono[a{idx}]")
            idx += 1
    if idx <= 1:
        return body
    chain = ";".join(labels)
    concat_in = "".join(f"[a{i}]" for i in range(idx))
    fc = f"{chain};{concat_in}concat=n={idx}:v=0:a=1[out]"
    out = os.path.join(workdir, "with_stings.wav")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[out]", out])
    return out


def measure_loudnorm(body, I, TP, LRA):
    """Loudnorm pass 1: MEASURE (print_format=json) so pass 2 can correct accurately."""
    p = subprocess.run(
        ["ffmpeg", "-y", "-i", body,
         "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True)
    err = p.stderr
    # the JSON block is the last {...} in stderr
    try:
        start = err.rindex("{"); end = err.rindex("}") + 1
        return json.loads(err[start:end])
    except Exception:
        return None


def apply_loudnorm(body, I, TP, LRA, measured, out):
    """Loudnorm pass 2: CORRECT using measured values (true two-pass EBU R128)."""
    ln = f"loudnorm=I={I}:TP={TP}:LRA={LRA}"
    if measured:
        ln += (f":measured_I={measured['input_i']}"
               f":measured_TP={measured['input_tp']}"
               f":measured_LRA={measured['input_lra']}"
               f":measured_thresh={measured['input_thresh']}"
               f":offset={measured.get('target_offset','0')}:linear=true")
    ln += f",aresample={SR}"
    run(["ffmpeg", "-y", "-i", body, "-af", ln, "-ar", str(SR),
         "-c:a", "aac", "-b:a", "160k", out])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--home", default=os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"))
    ap.add_argument("--dir", default=None)
    ap.add_argument("--wav-dir", default=None)
    ap.add_argument("--target-lufs", type=float, default=-16.0)
    ap.add_argument("--tp", type=float, default=-1.5)
    ap.add_argument("--lra", type=float, default=11.0)
    ap.add_argument("--bed", default=None)
    ap.add_argument("--intro", default=None)
    ap.add_argument("--outro", default=None)
    ap.add_argument("--music-gain", type=float, default=0.16)
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--no-stings", action="store_true")
    ap.add_argument("--voice-only", action="store_true",
                    help="EQ + compression + loudnorm ONLY (no music, no stings) — a clean "
                         "dry-but-mastered vocal for A/B against the raw Kaggle output")
    args = ap.parse_args()

    ep = args.episode
    ep_dir = args.dir or os.path.join(args.home, "episodes", f"ep{ep:02d}")
    wav_dir = args.wav_dir or os.path.join(ep_dir, "synth")
    assets = os.path.join(args.home, "assets")
    if not os.path.isdir(ep_dir):
        print(f"ERROR: no episode dir {ep_dir}", file=sys.stderr); sys.exit(2)
    if not have_filter("loudnorm"):
        print("ERROR: this ffmpeg has no loudnorm — mastering must run on the SERVER "
              "(full ffmpeg), not Kaggle.", file=sys.stderr); sys.exit(3)

    if args.voice_only:
        args.no_music = args.no_stings = True
    bed = args.bed or (None if args.no_music else _first(os.path.join(assets, "music"),
                                                          (".wav", ".mp3", ".m4a")))
    intro = args.intro or (None if args.no_stings else _exists(os.path.join(assets, "sfx", "intro.wav")))
    outro = args.outro or (None if args.no_stings else _exists(os.path.join(assets, "sfx", "outro.wav")))

    workdir = tempfile.mkdtemp(prefix=f"ep{ep:02d}_master_")
    try:
        script, speech, timeline, skipped = build_speech_track(ep, ep_dir, wav_dir, workdir)

        body = cleanup_and_compress(speech, workdir)
        if bed and os.path.exists(bed):
            print(f"  music bed: {os.path.basename(bed)} (ducked, gain {args.music_gain})")
            body = mix_music(body, bed, args.music_gain, workdir)
        else:
            print("  (no music bed)")
        if (intro or outro):
            print(f"  stings: intro={bool(intro)} outro={bool(outro)}")
            body = add_stings(body, intro, outro, workdir)

        print(f"  loudnorm 2-pass -> {args.target_lufs} LUFS / {args.tp} dBTP / LRA {args.lra}")
        measured = measure_loudnorm(body, args.target_lufs, args.tp, args.lra)
        if measured is None:
            print("  (measure pass failed — falling back to single-pass loudnorm)", file=sys.stderr)

        suffix = "_voice_master" if args.voice_only else "_master"
        out_audio = os.path.join(ep_dir, f"ep{ep:02d}_audio{suffix}.m4a")
        apply_loudnorm(body, args.target_lufs, args.tp, args.lra, measured, out_audio)

        dur = round(probe_dur(out_audio), 3)
        master = {"episode": ep, "title": script.get("title"),
                  "phrase_of_episode": script.get("phrase_of_episode"),
                  "audio": os.path.basename(out_audio), "duration": dur,
                  "mastering": {"target_lufs": args.target_lufs, "tp": args.tp,
                                "lra": args.lra, "music": bool(bed and not args.no_music),
                                "stings": bool((intro or outro) and not args.no_stings),
                                "voice_only": args.voice_only, "measured": measured},
                  "lines": timeline, "skipped": skipped}
        json.dump(master, open(os.path.join(ep_dir, "timeline.master.json"), "w"),
                  ensure_ascii=False, indent=2)
        print(f"OK -> {out_audio}  ({dur}s)")
        print(f"OK -> {os.path.join(ep_dir, 'timeline.master.json')}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _first(d, exts):
    if not os.path.isdir(d):
        return None
    for f in sorted(os.listdir(d)):
        if f.lower().endswith(exts):
            return os.path.join(d, f)
    return None


def _exists(p):
    return p if os.path.exists(p) else None


if __name__ == "__main__":
    main()
