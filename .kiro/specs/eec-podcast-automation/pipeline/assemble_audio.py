#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — AUDIO ASSEMBLY (ffmpeg).

Takes the per-line WAVs produced by the two synth stages and builds one mixed
episode audio track, plus the merged master timeline the video stage needs.

Inputs (in an episode dir, default /opt/eec-podcast/episodes/epNN):
  script.json                 master line ORDER (the source of truth)
  kaggle_en/lineNNN_*.wav     English lines (Chatterbox, from Kaggle batch)
  kaggle_en/timeline.en.json  English durations
  coachNNN_Coach.wav          Arabic Coach lines (Gemini Kore, server)
  timeline.ar.json            Coach durations
Optional branding (fail-soft — skipped if absent):
  assets/music/<bed>.mp3      music bed, ducked under speech
  assets/sfx/intro.wav        branded intro sting (prepended)
  assets/sfx/outro.wav        branded outro sting (appended)

Output (in the episode dir):
  epNN_audio.m4a              final mixed, loudnorm'd AAC
  timeline.master.json        every placed line with absolute start/end (for captions)

Design:
- The MASTER order is script.json. For each line we locate its rendered WAV by
  (idx within its language stream) -> file. A line whose WAV is MISSING is skipped
  (fail-soft) and logged, so a partially-synthesized episode still assembles.
- Natural pacing: a small gap between lines, a longer breath around Coach breaks.
- Speech is concatenated first (building the timeline), THEN an optional music bed
  is mixed under it with sidechain ducking, THEN optional intro/outro stings, THEN
  a final loudnorm pass to a consistent broadcast level.

Usage:
  python3 assemble_audio.py --episode 1 [--music assets/music/bed.mp3]
                            [--gap 0.35] [--coach-gap 0.7] [--no-normalize]
"""
import os, sys, json, subprocess, argparse, tempfile, shutil

SR = 24000  # both engines emit 24kHz mono; keep the whole chain at one rate


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def probe_dur(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nokey=1:noprint_wrappers=1", path]).stdout.strip()
    return float(out)


def build_order(episode_dir):
    """Return the ordered list of placed lines using script.json as master.

    Each English line maps to kaggle_en/lineNNN_*.wav (NNN = running EN index),
    each Arabic line to coachNNN_Coach.wav (NNN = running AR index) — matching
    exactly how the two synth stages number their outputs.
    """
    with open(os.path.join(episode_dir, "script.json"), encoding="utf-8") as f:
        script = json.load(f)

    en_dir = os.path.join(episode_dir, "kaggle_en")
    placed, skipped = [], []
    en_i = ar_i = 0
    for ln in script["lines"]:
        lang = ln.get("lang")
        if lang == "en":
            en_i += 1
            # file name embeds the speaker; glob by the numeric prefix
            cand = _find(en_dir, f"line{en_i:03d}_")
        elif lang == "ar":
            ar_i += 1
            cand = _find(episode_dir, f"coach{ar_i:03d}_")
        else:
            continue
        if cand and os.path.getsize(cand) > 1000:
            placed.append({"section": ln.get("section"), "speaker": ln["speaker"],
                           "lang": lang, "text": ln["text"], "file": cand})
        else:
            skipped.append((lang, ln["speaker"], ln["text"][:40]))
    return script, placed, skipped


def _find(d, prefix):
    if not os.path.isdir(d):
        return None
    for name in sorted(os.listdir(d)):
        if name.startswith(prefix) and name.endswith(".wav"):
            return os.path.join(d, name)
    return None


def concat_speech(placed, gap, coach_gap, workdir):
    """Concatenate placed WAVs with silence gaps; return (path, timeline)."""
    parts = []
    timeline = []
    t = 0.0
    silences = {}

    def silence(dur):
        if dur not in silences:
            p = os.path.join(workdir, f"sil_{int(dur*1000)}.wav")
            run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                 f"anullsrc=r={SR}:cl=mono", "-t", f"{dur}", p])
            silences[dur] = p
        return silences[dur]

    for i, ln in enumerate(placed):
        # normalize each clip to the common rate/mono/codec for a clean concat
        norm = os.path.join(workdir, f"clip_{i:03d}.wav")
        run(["ffmpeg", "-y", "-i", ln["file"], "-ar", str(SR), "-ac", "1", norm])
        dur = probe_dur(norm)
        timeline.append({"idx": i + 1, "section": ln["section"],
                         "speaker": ln["speaker"], "lang": ln["lang"],
                         "text": ln["text"], "start": round(t, 3),
                         "end": round(t + dur, 3), "duration": round(dur, 3)})
        parts.append(norm)
        t += dur
        # gap after this line (bigger breath around Coach teaching breaks)
        if i < len(placed) - 1:
            nxt = placed[i + 1]
            g = coach_gap if (ln["lang"] == "ar" or nxt["lang"] == "ar") else gap
            parts.append(silence(g))
            t += g

    listfile = os.path.join(workdir, "concat.txt")
    with open(listfile, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    speech = os.path.join(workdir, "speech.wav")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
         "-ar", str(SR), "-ac", "1", speech])
    return speech, timeline, t


def mix_music(speech, music, workdir):
    """Duck a looped music bed under the speech via sidechaincompress."""
    dur = probe_dur(speech)
    out = os.path.join(workdir, "mixed.wav")
    # bed: loop, trim to speech length, quieten, fade in/out; sidechain-duck by speech
    fc = (
        "[1:a]aformat=sample_rates={sr}:channel_layouts=mono,volume=0.18,"
        "afade=t=in:st=0:d=1.5,afade=t=out:st={fo}:d=2.0[bed];"
        "[bed][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:"
        "release=400[ducked];"
        "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=0,"
        "aresample={sr}[out]"
    ).format(sr=SR, fo=max(dur - 2.0, 0))
    run(["ffmpeg", "-y", "-i", speech,
         "-stream_loop", "-1", "-i", music,
         "-filter_complex", fc, "-map", "[out]", "-t", f"{dur}", out])
    return out


def add_stings(body, intro, outro, workdir):
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
    out = os.path.join(workdir, "withstings.wav")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[out]", out])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--dir", default=None)
    ap.add_argument("--home", default=os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"))
    ap.add_argument("--music", default=None, help="music bed path (optional)")
    ap.add_argument("--intro", default=None)
    ap.add_argument("--outro", default=None)
    ap.add_argument("--gap", type=float, default=0.35)
    ap.add_argument("--coach-gap", type=float, default=0.7)
    ap.add_argument("--no-normalize", action="store_true")
    args = ap.parse_args()

    ep = args.episode
    ep_dir = args.dir or os.path.join(args.home, "episodes", f"ep{ep:02d}")
    if not os.path.isdir(ep_dir):
        print(f"ERROR: no episode dir {ep_dir}", file=sys.stderr); sys.exit(2)

    # auto-discover branding assets if not passed
    assets = os.path.join(args.home, "assets")
    if args.intro is None:
        p = os.path.join(assets, "sfx", "intro.wav"); args.intro = p if os.path.exists(p) else None
    if args.outro is None:
        p = os.path.join(assets, "sfx", "outro.wav"); args.outro = p if os.path.exists(p) else None
    if args.music is None:
        md = os.path.join(assets, "music")
        if os.path.isdir(md):
            beds = [f for f in sorted(os.listdir(md)) if f.lower().endswith((".mp3", ".wav", ".m4a"))]
            args.music = os.path.join(md, beds[0]) if beds else None

    script, placed, skipped = build_order(ep_dir)
    if not placed:
        print("ERROR: no line WAVs found — run the synth stages first", file=sys.stderr)
        sys.exit(1)
    print(f"Assembling ep{ep:02d} '{script.get('title')}': {len(placed)} lines placed"
          + (f", {len(skipped)} skipped (missing WAV)" if skipped else ""))
    for lang, sp, txt in skipped:
        print(f"  MISSING [{lang}] {sp}: {txt}...")

    workdir = tempfile.mkdtemp(prefix=f"ep{ep:02d}_asm_")
    try:
        speech, timeline, total = concat_speech(placed, args.gap, args.coach_gap, workdir)
        print(f"  speech track: {round(total,1)}s")

        body = speech
        if args.music and os.path.exists(args.music):
            print(f"  mixing music bed: {os.path.basename(args.music)} (ducked)")
            body = mix_music(speech, args.music, workdir)
        else:
            print("  no music bed (assets/music empty) — speech only for now")

        body = add_stings(body, args.intro, args.outro, workdir)
        if args.intro or args.outro:
            print(f"  stings: intro={bool(args.intro)} outro={bool(args.outro)}")

        out_audio = os.path.join(ep_dir, f"ep{ep:02d}_audio.m4a")
        aac = ["ffmpeg", "-y", "-i", body]
        if not args.no_normalize:
            # loudnorm resamples internally; pin the final rate to a clean 48k
            aac += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000"]
        aac += ["-ar", "48000", "-c:a", "aac", "-b:a", "160k", out_audio]
        run(aac)

        master = {"episode": ep, "title": script.get("title"),
                  "phrase_of_episode": script.get("phrase_of_episode"),
                  "shorts_highlight_hint": script.get("shorts_highlight_hint"),
                  "audio": os.path.basename(out_audio),
                  "duration": round(probe_dur(out_audio), 3),
                  "lines": timeline, "skipped": skipped}
        with open(os.path.join(ep_dir, "timeline.master.json"), "w", encoding="utf-8") as f:
            json.dump(master, f, ensure_ascii=False, indent=2)

        print(f"OK -> {out_audio}  ({master['duration']}s)")
        print(f"OK -> {os.path.join(ep_dir, 'timeline.master.json')}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
