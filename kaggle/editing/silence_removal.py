#!/usr/bin/env python3
"""
Hybrid Editing Pipeline — Phase 1 / Task 1.1: silence / dead-air removal.

Pure-ffmpeg implementation (NO external binaries). We deliberately do NOT use
`auto-editor`: its bundled binary requires GLIBC 2.38 which the Kaggle image
lacks (confirmed 2026-09), so it fails there. ffmpeg's `silencedetect` +
trim/concat does the same job with tools already installed on the box.

Approach:
  1. `silencedetect` to find silence intervals below NOISE_DB lasting >= MIN_SIL.
  2. Invert to SPEECH segments, keeping a small MARGIN of air around speech so
     the result isn't choppy.
  3. Trim + concat the speech segments (video+audio) via a single
     filter_complex, re-encode once.

Notes:
  - Best value is on RAW, unedited footage (natural pauses). Already-tight edits
    (e.g. a polished creator video) will show little change — that's expected.
  - Fails soft: callers should fall back to the original clip if this returns
    no output.

Usage:
  clean = remove_silence("/path/in.mp4", "/path/out.mp4")
"""
import subprocess, os, re

# Tunables (safe defaults for talking-head lessons)
NOISE_DB = "-30dB"   # below this loudness counts as silence
MIN_SIL  = 0.6       # only cut silences longer than this (seconds)
MARGIN   = 0.15      # keep this much air around kept speech (seconds)


def _run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def _duration(path):
    r = _run(f'ffprobe -v error -show_entries format=duration '
             f'-of default=nokey=1:noprint_wrappers=1 "{path}"')
    try:
        return float((r.stdout or "0").strip())
    except Exception:
        return 0.0


def remove_silence(in_path, out_path,
                   noise_db=NOISE_DB, min_sil=MIN_SIL, margin=MARGIN):
    """Remove silences; return out_path on success, or in_path on fail-soft."""
    total = _duration(in_path)
    if total <= 0:
        return in_path

    det = _run(f'ffmpeg -i "{in_path}" '
               f'-af silencedetect=noise={noise_db}:d={min_sil} -f null - 2>&1')
    log = det.stdout + det.stderr
    starts = [float(x) for x in re.findall(r'silence_start:\s*([0-9.]+)', log)]
    ends = [float(x) for x in re.findall(r'silence_end:\s*([0-9.]+)', log)]
    if not starts:
        # nothing to cut — copy through unchanged (fail-soft = original is fine)
        return in_path

    if len(ends) < len(starts):
        ends = ends + [total]
    sil = list(zip(starts, ends))

    # invert to speech segments with margin
    speech, cur = [], 0.0
    for s, e in sil:
        seg_end = max(cur, s + margin)
        if seg_end - cur > 0.05:
            speech.append((cur, seg_end))
        cur = max(cur, e - margin)
    if cur < total:
        speech.append((cur, total))
    speech = [(max(0, a), min(total, b)) for a, b in speech if b - a > 0.10]
    if not speech:
        return in_path

    # build trim+concat filter
    parts = []
    for i, (a, b) in enumerate(speech):
        parts.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}];")
        parts.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}];")
    concat_in = "".join(f"[v{i}][a{i}]" for i in range(len(speech)))
    filt = "".join(parts) + f"{concat_in}concat=n={len(speech)}:v=1:a=1[vout][aout]"

    fpath = out_path + ".filter.txt"
    open(fpath, "w").write(filt)
    r = _run(f'ffmpeg -y -loglevel error -i "{in_path}" '
             f'-filter_complex_script "{fpath}" -map "[vout]" -map "[aout]" '
             f'-c:v libx264 -preset veryfast -crf 20 -c:a aac '
             f'-movflags +faststart "{out_path}"')
    try:
        os.remove(fpath)
    except Exception:
        pass

    if r.returncode == 0 and os.path.exists(out_path) and _duration(out_path) > 0:
        return out_path
    return in_path  # fail-soft


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "/kaggle/working/fatm/vid.webm"
    dst = sys.argv[2] if len(sys.argv) > 2 else "/kaggle/working/silence_test/clean.mp4"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    before = _duration(src)
    out = remove_silence(src, dst)
    after = _duration(out)
    print(f"before={before:.1f}s after={after:.1f}s removed={before-after:.1f}s "
          f"({(before-after)/before*100:.1f}%)" if before else "no input")
    print("output:", out)
