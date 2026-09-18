#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — branded audio assets, generated with ffmpeg (100% original).

Produces, into <home>/assets/:
  sfx/intro.wav   a short warm "gold ident" sting (rising chord + soft swell)
  sfx/outro.wav   a shorter resolving version for the episode close
  music/bed.wav   a long, very subtle ambient pad to sit UNDER speech (ducked)

Why synthesized (not a downloaded track): zero licensing risk, zero copyright
claims on YouTube, $0, reproducible, and tuned to the brand (warm, calm,
disciplined — never hype). Everything is built from ffmpeg's sine/anoise
sources + fades; no external audio is fetched.

Tuning notes:
- Chord = C major-ish (C4/E4/G4) with a gentle octave shimmer for warmth.
- The bed is intentionally quiet + low-passed so speech always wins; the
  assembler ducks it further with sidechaincompress.

Usage:  python3 make_audio_brand.py [--home /opt/eec-podcast]
"""
import os, subprocess, argparse

SR = 48000


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def sine(freq, dur, vol):
    # a single sine "voice" as a filter string producing [out]
    return (f"sine=frequency={freq}:sample_rate={SR}:duration={dur},"
            f"volume={vol}")


def make_intro(path):
    """~3.2s: three chord tones swell in together, a soft shimmer, fade out."""
    dur = 3.2
    tones = {"c": (261.63, 0.30), "e": (329.63, 0.24), "g": (392.00, 0.24),
             "c2": (523.25, 0.14)}
    inputs, labels = [], []
    for i, (name, (f, v)) in enumerate(tones.items()):
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:sample_rate={SR}:duration={dur}"]
        labels.append(f"[{i}:a]volume={v},afade=t=in:st=0:d=1.1[{name}]")
    mix_in = "".join(f"[{n}]" for n in tones)
    fc = (";".join(labels) + ";" +
          f"{mix_in}amix=inputs={len(tones)}:normalize=0[chord];"
          f"[chord]afade=t=out:st={dur-1.4}:d=1.4,"
          f"aformat=sample_rates={SR}:channel_layouts=mono,"
          f"loudnorm=I=-18:TP=-2:LRA=7[out]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[out]", path])


def make_outro(path):
    """~2.6s: same chord resolving down + quicker fade, a touch softer."""
    dur = 2.6
    tones = {"g": (392.00, 0.22), "e": (329.63, 0.22), "c": (261.63, 0.30)}
    inputs, labels = [], []
    for i, (name, (f, v)) in enumerate(tones.items()):
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:sample_rate={SR}:duration={dur}"]
        labels.append(f"[{i}:a]volume={v},afade=t=in:st=0:d=0.6[{name}]")
    mix_in = "".join(f"[{n}]" for n in tones)
    fc = (";".join(labels) + ";" +
          f"{mix_in}amix=inputs={len(tones)}:normalize=0[chord];"
          f"[chord]afade=t=out:st={dur-1.6}:d=1.6,"
          f"aformat=sample_rates={SR}:channel_layouts=mono,"
          f"loudnorm=I=-19:TP=-2:LRA=7[out]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[out]", path])


def make_bed(path, dur=180):
    """A long, calm ambient pad: two detuned low sines + a soft airy layer,
    heavily low-passed and quiet so it never competes with speech."""
    inputs = [
        "-f", "lavfi", "-i", f"sine=frequency=110:sample_rate={SR}:duration={dur}",
        "-f", "lavfi", "-i", f"sine=frequency=164.81:sample_rate={SR}:duration={dur}",
        "-f", "lavfi", "-i", f"sine=frequency=220:sample_rate={SR}:duration={dur}",
    ]
    fc = (
        f"[0:a]volume=0.5[a0];"
        f"[1:a]volume=0.35,tremolo=f=0.12:d=0.4[a1];"   # slow gentle movement
        f"[2:a]volume=0.22[a2];"
        f"[a0][a1][a2]amix=inputs=3:normalize=0[m];"
        f"[m]lowpass=f=700,highpass=f=60,"                # warm, no harsh highs/lows
        f"afade=t=in:st=0:d=3,afade=t=out:st={dur-4}:d=4,"
        f"aformat=sample_rates={SR}:channel_layouts=mono,"
        f"loudnorm=I=-30:TP=-6:LRA=5[out]"                # very quiet — it's a bed
    )
    run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[out]", path])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"))
    ap.add_argument("--bed-seconds", type=int, default=180)
    args = ap.parse_args()

    sfx = os.path.join(args.home, "assets", "sfx")
    music = os.path.join(args.home, "assets", "music")
    os.makedirs(sfx, exist_ok=True)
    os.makedirs(music, exist_ok=True)

    intro = os.path.join(sfx, "intro.wav")
    outro = os.path.join(sfx, "outro.wav")
    bed = os.path.join(music, "bed.wav")

    print("generating intro sting...");  make_intro(intro);  print("  ->", intro)
    print("generating outro sting...");  make_outro(outro);  print("  ->", outro)
    print("generating music bed...");    make_bed(bed, args.bed_seconds); print("  ->", bed)
    print("DONE")


if __name__ == "__main__":
    main()
