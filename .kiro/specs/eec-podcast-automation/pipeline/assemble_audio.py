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
import os, sys, json, subprocess, argparse, tempfile, shutil, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import manifest_lib
except Exception:
    manifest_lib = None
try:
    import structure_check   # LOCKED story/teaching separation gate (series-bible §10)
except Exception:
    structure_check = None

SR = 24000  # both engines emit 24kHz mono; keep the whole chain at one rate


def run(cmd, **kw):
    """Run a command, but on failure SURFACE ffmpeg/ffprobe's stderr instead of
    swallowing it (the silent capture_output hid the real cause on Kaggle)."""
    try:
        return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)
    except subprocess.CalledProcessError as e:
        tail = (e.stderr or "").strip().splitlines()[-12:]
        print("  ffmpeg/ffprobe FAILED:\n    " + "\n    ".join(tail), file=sys.stderr)
        raise


def probe_dur(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nokey=1:noprint_wrappers=1", path]).stdout.strip()
    return float(out)


def build_order_from_manifest(episode_dir, wav_dir):
    """Build the placement order from the MERGED manifest(s) in wav_dir.

    The two synth passes each drop a pass-tagged manifest (manifest.ar.json,
    manifest.en.json) plus a plain manifest.json. We merge every manifest we
    find over a fresh skeleton (from script.json) so neither pass clobbers the
    other. Returns (script, placed, skipped) or None if no manifest is usable.
    """
    if manifest_lib is None:
        return None
    mans = sorted(glob.glob(os.path.join(wav_dir, "manifest*.json")))
    if not mans:
        return None
    try:
        with open(os.path.join(episode_dir, "script.json"), encoding="utf-8") as f:
            script = json.load(f)
    except Exception:
        return None
    merged = manifest_lib.build_skeleton(script)
    for mp in mans:
        try:
            merged = manifest_lib.merge_pass(merged, json.load(open(mp, encoding="utf-8")))
        except Exception:
            continue
    placed, skipped = [], []
    for e in merged["lines"]:
        cand = os.path.join(wav_dir, e["file"])
        if e.get("status") == "rendered" and os.path.exists(cand) and os.path.getsize(cand) > 1000:
            placed.append({"section": e.get("section"), "speaker": e["speaker"],
                           "lang": e["lang"], "text": e["text"], "file": cand})
        else:
            skipped.append((e["lang"], e["speaker"], (e.get("text") or "")[:40]))
    return script, placed, skipped


def build_order(episode_dir, wav_dir=None):
    """Return the ordered list of placed lines using script.json as master.

    Two supported WAV naming schemes, tried in order:

    1. GLOBAL-IDX (current unified synth): every line -- EN and AR alike -- is
       emitted as ``lineNNN_<Speaker>.wav`` where NNN is the line's GLOBAL index
       in script.json (1-based), all in one flat directory (``--wav-dir``,
       default ``<episode>/synth``). Source of truth when present.

    2. LEGACY per-language: English -> ``kaggle_en/lineNNN_*.wav`` (running EN
       index), Arabic -> ``coachNNN_Coach.wav`` (running AR index).
    """
    with open(os.path.join(episode_dir, "script.json"), encoding="utf-8") as f:
        script = json.load(f)

    wav_dir = wav_dir or os.path.join(episode_dir, "synth")
    use_global = os.path.isdir(wav_dir) and any(
        n.startswith("line") and n.endswith(".wav") for n in os.listdir(wav_dir))

    placed, skipped = [], []
    if use_global:
        for i, ln in enumerate(script["lines"], 1):
            lang = ln.get("lang")
            if lang not in ("en", "ar"):
                continue
            cand = _find(wav_dir, f"line{i:03d}_")
            if cand and os.path.getsize(cand) > 1000:
                placed.append({"section": ln.get("section"), "speaker": ln["speaker"],
                               "lang": lang, "text": ln["text"], "file": cand})
            else:
                skipped.append((lang, ln["speaker"], ln["text"][:40]))
        return script, placed, skipped

    en_dir = os.path.join(episode_dir, "kaggle_en")
    en_i = ar_i = 0
    for ln in script["lines"]:
        lang = ln.get("lang")
        if lang == "en":
            en_i += 1
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
    ap.add_argument("--wav-dir", default=None,
                    help="flat dir of lineNNN_<Speaker>.wav (global-idx synth); "
                         "default <episode>/synth")
    ap.add_argument("--home", default=os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"))
    ap.add_argument("--music", default=None, help="music bed path (optional)")
    ap.add_argument("--intro", default=None)
    ap.add_argument("--outro", default=None)
    ap.add_argument("--gap", type=float, default=0.35)
    ap.add_argument("--coach-gap", type=float, default=0.7)
    ap.add_argument("--no-normalize", action="store_true")
    ap.add_argument("--plain", action="store_true",
                    help="PLAIN mode: dry voices only — no music bed, no intro/outro "
                         "stings. The owner adds their own music/branding downstream.")
    ap.add_argument("--force", action="store_true",
                    help="bypass the structure gate (assemble even if the script "
                         "violates the story/teaching separation rule). Use only for "
                         "deliberate edge cases.")
    args = ap.parse_args()

    ep = args.episode
    ep_dir = args.dir or os.path.join(args.home, "episodes", f"ep{ep:02d}")
    if not os.path.isdir(ep_dir):
        print(f"ERROR: no episode dir {ep_dir}", file=sys.stderr); sys.exit(2)

    # STRUCTURE GATE (series-bible §10): refuse to assemble a script whose story/
    # teaching separation is broken (Coach lines inside story scenes) — that is the
    # root cause of "messy" audio. Fail-closed with the exact offending idx so it's a
    # clear error, never a silently-shipped bad episode. Bypass only with --force.
    script_path = os.path.join(ep_dir, "script.json")
    if structure_check is not None and os.path.exists(script_path):
        try:
            _script = json.load(open(script_path, encoding="utf-8"))
            _violations = structure_check.check_script(_script)
        except Exception as _e:
            _violations = []
            print(f"  (structure gate skipped: {str(_e)[:80]})")
        if _violations:
            print(structure_check.format_report(_violations), file=sys.stderr)
            if not args.force:
                print("ERROR: script violates the LOCKED structure rule "
                      "(series-bible §10). Fix the section tags / re-order (or pass "
                      "--force to override). Refusing to assemble a messy episode.",
                      file=sys.stderr)
                sys.exit(5)
            print("  --force: assembling despite structure violations", file=sys.stderr)

    # auto-discover branding assets if not passed — SKIPPED entirely in --plain mode
    assets = os.path.join(args.home, "assets")
    if args.plain:
        args.intro = args.outro = args.music = None
    else:
        if args.intro is None:
            p = os.path.join(assets, "sfx", "intro.wav"); args.intro = p if os.path.exists(p) else None
        if args.outro is None:
            p = os.path.join(assets, "sfx", "outro.wav"); args.outro = p if os.path.exists(p) else None
        if args.music is None:
            md = os.path.join(assets, "music")
            if os.path.isdir(md):
                beds = [f for f in sorted(os.listdir(md)) if f.lower().endswith((".mp3", ".wav", ".m4a"))]
                args.music = os.path.join(md, beds[0]) if beds else None

    wav_dir = args.wav_dir or os.path.join(ep_dir, "synth")
    mres = build_order_from_manifest(ep_dir, wav_dir)
    if mres is not None:
        script, placed, skipped = mres
        print(f"  (order source: merged manifest in {wav_dir})")
    else:
        script, placed, skipped = build_order(ep_dir, args.wav_dir)
        print("  (order source: script.json + filename match)")
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
        elif args.plain:
            print("  PLAIN mode: dry voices only (no music, no stings)")
        else:
            print("  no music bed (assets/music empty) — speech only for now")

        body = add_stings(body, args.intro, args.outro, workdir)
        if args.intro or args.outro:
            print(f"  stings: intro={bool(args.intro)} outro={bool(args.outro)}")

        suffix = "_plain" if args.plain else ""
        out_audio = os.path.join(ep_dir, f"ep{ep:02d}_audio{suffix}.m4a")
        # RESILIENT final encode. Some ffmpeg builds (e.g. Kaggle's) can choke on the
        # loudnorm filter or lack the native 'aac' encoder. Try the best option first,
        # then degrade gracefully so a full render is never lost at the last step:
        #   1) loudnorm + native aac  (broadcast level, .m4a)
        #   2) native aac, NO filter  (skips a bad loudnorm build)
        #   3) libmp3lame .mp3        (if the aac encoder is unavailable)
        af = "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000"
        attempts = []
        if not args.no_normalize:
            attempts.append((["-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "160k"], out_audio))
        attempts.append((["-ar", "48000", "-c:a", "aac", "-b:a", "160k"], out_audio))  # no filter
        mp3_out = os.path.splitext(out_audio)[0] + ".mp3"
        attempts.append((["-ar", "48000", "-c:a", "libmp3lame", "-b:a", "192k"], mp3_out))  # last resort
        last_err = None
        for enc, dst in attempts:
            try:
                run(["ffmpeg", "-y", "-i", body, *enc, dst])
                out_audio = dst
                if "libmp3lame" in enc:
                    print("  NOTE: aac encoder unavailable — wrote MP3 instead", file=sys.stderr)
                elif "-af" not in enc and not args.no_normalize:
                    print("  NOTE: loudnorm unavailable on this ffmpeg — wrote un-normalized audio",
                          file=sys.stderr)
                break
            except subprocess.CalledProcessError as e:
                last_err = e
                continue
        else:
            raise last_err

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
