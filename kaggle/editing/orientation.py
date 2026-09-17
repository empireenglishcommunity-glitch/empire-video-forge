#!/usr/bin/env python3
"""
Hybrid Editing Pipeline — format-agnostic orientation detection.

Auto-detects a source video's orientation so the pipeline can adapt with NO
manual flag (owner sends any video; we do the right thing). See requirements
R1.0 / R1.1.

Returns one of: "landscape", "vertical", "square", plus the raw dims + a
recommendation of which output tracks to build.
"""
import subprocess, json


def _probe(path):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=width,height,r_frame_rate',
         '-show_entries', 'format=duration', '-of', 'json', path],
        capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        s = d['streams'][0]
        w, h = int(s['width']), int(s['height'])
        dur = float(d.get('format', {}).get('duration') or 0)
        fps = s.get('r_frame_rate', '30/1')
        return w, h, dur, fps
    except Exception:
        return 0, 0, 0.0, '30/1'


def analyze(path):
    """Return a dict describing the source and which tracks to build."""
    w, h, dur, fps = _probe(path)
    if w == 0 or h == 0:
        return {"ok": False, "reason": "probe failed", "path": path}

    ratio = w / h
    if ratio > 1.15:
        orientation = "landscape"
    elif ratio < 0.87:
        orientation = "vertical"
    else:
        orientation = "square"

    # Track plan:
    #   shorts: always (native crop for vertical/square, face-track crop for landscape)
    #   long_form: native for landscape; blurred-fill (optional) for vertical/square
    plan = {
        "landscape": {"shorts": "crop_9x16", "long_form": "native_16x9"},
        "vertical":  {"shorts": "native_9x16", "long_form": "blurfill_16x9_optional"},
        "square":    {"shorts": "crop_9x16", "long_form": "blurfill_16x9_optional"},
    }[orientation]

    return {
        "ok": True,
        "path": path,
        "width": w, "height": h, "ratio": round(ratio, 3),
        "duration": round(dur, 2), "fps": fps,
        "orientation": orientation,
        "tracks": plan,
    }


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else \
        "/kaggle/input/datasets/macalempire/eec-raw-video/english-pronunciation-tip.mp4.mp4"
    print(json.dumps(analyze(p), ensure_ascii=False, indent=2))
