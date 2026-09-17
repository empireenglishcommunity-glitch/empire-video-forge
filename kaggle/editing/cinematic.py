#!/usr/bin/env python3
"""
EEC Cinematic FX — the "movie feel" layer (CPU, throttled).
Applies, in ONE ffmpeg pass:
  - cinematic color grade (teal-shadow / warm-highlight, film contrast)
  - subtle vignette (draws eye to center)
  - light film grain (texture)
  - gentle slow zoom-in (ken-burns "push") for energy
  - thin cinematic top/bottom gradient bars (film signal without eating frame)
Runs with low priority (nice) so it never starves the server's live services.
Fail-soft: on error, returns the input path unchanged.
"""
import subprocess, sys, os

def run(cmd):
    # low priority: nice + ionice; single-ish thread to protect the box
    return subprocess.run("nice -n 19 " + cmd, shell=True, capture_output=True, text=True)

def dur(p):
    r = subprocess.run(f'ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 "{p}"',
                       shell=True, capture_output=True, text=True)
    try: return float((r.stdout or "0").strip())
    except: return 0.0

def cinematic(inp, out):
    d = dur(inp) or 20.0
    fps = 30
    total_frames = int(d * fps)
    # slow push: zoom from 1.0 to 1.08 across the whole clip, centered
    zoom = (f"zoompan=z='min(zoom+0.00015,1.08)':d=1:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}")
    # cinematic grade: lift/gamma/gain via curves + eq; teal shadows, warm highlights
    grade = ("curves=r='0/0.03 0.5/0.48 1/0.97':"
             "g='0/0.02 0.5/0.5 1/0.98':"
             "b='0/0.06 0.5/0.52 1/0.95',"
             "eq=contrast=1.12:saturation=1.10:gamma=0.98")
    # film grain (subtle) + vignette
    grain = "noise=alls=6:allf=t"
    vig = "vignette=PI/5"
    # thin cinematic bars: dark gradient at very top & bottom (10% each) via drawbox semi-transparent
    bars = ("drawbox=x=0:y=0:w=iw:h=ih*0.06:color=black@0.55:t=fill,"
            "drawbox=x=0:y=ih*0.94:w=iw:h=ih*0.06:color=black@0.55:t=fill")
    vf = f"{zoom},{grade},{grain},{vig},{bars}"
    cmd = (f'ffmpeg -y -loglevel error -i "{inp}" -vf "{vf}" '
           f'-c:v libx264 -profile:v high -pix_fmt yuv420p -preset veryfast -crf 20 -threads 2 -c:a copy '
           f'-movflags +faststart "{out}"')
    r = run(cmd)
    if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    print("cinematic err:", r.stderr[-400:])
    return inp

if __name__ == "__main__":
    i = sys.argv[1] if len(sys.argv)>1 else "/opt/eec-editor/work/test_input.mp4"
    o = sys.argv[2] if len(sys.argv)>2 else "/opt/eec-editor/work/test_cinematic.mp4"
    res = cinematic(i, o)
    print("output:", res, "size:", os.path.getsize(res) if os.path.exists(res) else 0)
