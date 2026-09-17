#!/usr/bin/env python3
"""
EEC Sound Design — add cinematic music bed (ducked under speech) + intro impact.
Input: a video WITH speech audio. Output: same video with music mixed under it.
- Music ducks under narration via sidechaincompress (voice stays clear).
- An impact SFX hits at t=0 for a cinematic "start".
Throttled (nice). Fail-soft to input.
"""
import subprocess, sys, os

MUSIC = "/opt/eec-editor/assets/music/cinematic_pad.mp3"
IMPACT = "/opt/eec-editor/assets/sfx/impact.mp3"

def run(c): return subprocess.run("nice -n 19 "+c, shell=True, capture_output=True, text=True)
def dur(p):
    r=subprocess.run(f'ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 "{p}"',shell=True,capture_output=True,text=True)
    try:return float((r.stdout or "0").strip())
    except:return 0.0

def sound_design(inp, out):
    d = dur(inp) or 20.0
    # Mix graph:
    #  [0:a] = original speech (video's audio)
    #  [1:a] = music, looped/trimmed to length, lowered
    #  [2:a] = impact at start
    # sidechaincompress: key music by the voice so music ducks when speaking.
    filt = (
        # music: trim to duration, set volume base
        f"[1:a]atrim=0:{d:.2f},asetpts=PTS-STARTPTS,volume=0.35[music];"
        # impact: short, at start, quieter
        f"[2:a]atrim=0:2,asetpts=PTS-STARTPTS,volume=0.5,adelay=0|0[imp];"
        # duck music under the voice
        f"[music][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=5:release=300[ducked];"
        # combine voice + ducked music + impact
        f"[0:a][ducked][imp]amix=inputs=3:duration=first:dropout_transition=0:normalize=0[aout]"
    )
    cmd = (f'ffmpeg -y -loglevel error -i "{inp}" -i "{MUSIC}" -i "{IMPACT}" '
           f'-filter_complex "{filt}" -map 0:v -map "[aout]" '
           f'-c:v copy -c:a aac -b:a 192k -threads 2 -movflags +faststart "{out}"')
    r = run(cmd)
    if r.returncode==0 and os.path.exists(out) and os.path.getsize(out)>0:
        return out
    print("sound err:", r.stderr[-400:])
    return inp

if __name__=="__main__":
    i=sys.argv[1] if len(sys.argv)>1 else "/opt/eec-editor/work/test_cinematic.mp4"
    o=sys.argv[2] if len(sys.argv)>2 else "/opt/eec-editor/work/test_final.mp4"
    print("output:", sound_design(i,o))
