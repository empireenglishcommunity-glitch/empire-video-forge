#!/usr/bin/env python3
"""
Hybrid Editing Pipeline — Phase 1 / Task 1.2: light warm color grade.

A single, gentle ffmpeg grade applied to all outputs so footage feels
"produced" without looking oversaturated. Matches the reference creator's soft,
warm look (analyzed 2026-09): modest saturation + warmth + a touch of contrast,
NOT a heavy cinematic LUT.

Filter rationale (kept intentionally subtle):
  eq=saturation=1.12:contrast=1.05:brightness=0.015:gamma=1.02
  + a warm white-balance nudge via colorbalance (lift reds, drop blues slightly)

Fail-soft: returns the input path if the grade fails.
"""
import subprocess, os

# One tuned, reusable filter string. Keep subtle.
GRADE = ("eq=saturation=1.12:contrast=1.05:brightness=0.015:gamma=1.02,"
         "colorbalance=rs=0.03:gs=0.01:bs=-0.03:rm=0.02:bm=-0.02")


def _run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def _ok(path):
    return os.path.exists(path) and os.path.getsize(path) > 0


def color_grade(in_path, out_path, grade=GRADE):
    """Apply the warm grade. Returns out_path on success, else in_path."""
    r = _run(f'ffmpeg -y -loglevel error -i "{in_path}" -vf "{grade}" '
             f'-c:v libx264 -preset veryfast -crf 20 -c:a copy '
             f'-movflags +faststart "{out_path}"')
    if r.returncode == 0 and _ok(out_path):
        return out_path
    return in_path  # fail-soft


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "/kaggle/working/eec_clean.mp4"
    dst = sys.argv[2] if len(sys.argv) > 2 else "/kaggle/working/eec_graded.mp4"
    out = color_grade(src, dst)
    print("graded:", out, "ok" if _ok(out) and out == dst else "(fell back to source)")
    # extract a before/after frame at t=2s for visual comparison
    _run(f'ffmpeg -y -loglevel error -ss 2 -i "{src}" -frames:v 1 /kaggle/working/grade_before.jpg')
    _run(f'ffmpeg -y -loglevel error -ss 2 -i "{out}" -frames:v 1 /kaggle/working/grade_after.jpg')
    print("frames: grade_before.jpg / grade_after.jpg")
