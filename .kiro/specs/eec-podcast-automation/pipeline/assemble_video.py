#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — VIDEO ASSEMBLY (ffmpeg), typographic scene-card style (v1).

Turns timeline.master.json + the mixed audio into a branded 1920x1080 episode
video with karaoke-style captions. No character art yet (that's the optional
v2 upgrade); this is the fast, consistent, on-brand text treatment.

Look:
- Near-black brand background (#0d0c0d) with a soft radial vignette.
- A per-SPEAKER accent color + a name/role badge (top-left) that switches as the
  speaker changes, driven by the timeline. This is the "scene card per speaker".
- Captions (burned via libass, which shapes Arabic + does bidi correctly):
    * English story lines: centered, white, Cairo/Tajawal bold.
    * Coach (Arabic) lines: larger, RTL, brand-gold accent — the teaching moments.
  The current line is on screen for exactly its [start,end] window.
- The episode title card holds during the intro sting; a "phrase of the episode"
  lower-third appears under the Coach breaks.

Output (in the episode dir):
  epNN_video.mp4   1920x1080, H.264 High, yuv420p, +faststart (YouTube-ready)

Requires ffmpeg built with libass + libharfbuzz + libfribidi (verified on box).

Usage:
  python3 assemble_video.py --episode 1 [--home /opt/eec-podcast]
"""
import os, sys, json, subprocess, argparse, tempfile, shutil

W, H = 1920, 1080
BG = "0x0d0c0d"          # brand near-black
GOLD = "&H0056C4E9"      # ASS BGR for #e9c456 (alpha 00)
WHITE = "&H00FFFFFF"
GREYED = "&H00CFCFCF"
BLACK_OUT = "&H00000000"

# Per-speaker accent (ASS BGR) + display label. Guests fall back by prefix.
SPEAKERS = {
    "Macal": ("&H004AB0E9", "MACAL", "the learner"),      # warm blue-gold
    "Nour":  ("&H008A6CF0", "NOUR", "the guide"),         # violet
    "Coach": ("&H0056C4E9", "COACH", "your teacher"),     # gold (teaching)
}
GUEST_LABEL = {"m": ("&H0080C080", "GUEST"), "f": ("&H00B0A0E0", "GUEST")}
FEMALE_HINTS = ("_f", "female", "woman", "lady", "girl", "barista",
                "receptionist", "hostess", "waitress")


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def speaker_style(sp):
    if sp in SPEAKERS:
        return SPEAKERS[sp]
    g = "f" if any(h in sp.lower() for h in FEMALE_HINTS) else "m"
    color, label = GUEST_LABEL[g]
    # humanize a guest id like "guest_driver" -> "GUEST · DRIVER"
    role = sp.replace("guest_", "").replace("_", " ").strip().upper() or "GUEST"
    return (color, "GUEST", role.title())


def chunk_text(text, maxlen):
    """Split a long caption into readable chunks (<= maxlen chars), preferring
    sentence/clause boundaries, then word boundaries. Works for AR + EN."""
    text = " ".join(text.split())
    if len(text) <= maxlen:
        return [text]
    # split on sentence-ish punctuation (Arabic + Latin) keeping the delimiter
    import re
    sentences, buf = [], ""
    for tok in re.split(r"([.!?،؛]+\s+)", text):
        buf += tok
        if re.search(r"[.!?،؛]+\s+$", tok):
            sentences.append(buf.strip()); buf = ""
    if buf.strip():
        sentences.append(buf.strip())
    # pack sentences/words into <=maxlen chunks
    chunks, cur = [], ""
    for s in sentences:
        if len(s) > maxlen:  # a very long sentence -> pack by words
            for w in s.split():
                if len(cur) + len(w) + 1 > maxlen:
                    if cur: chunks.append(cur.strip()); cur = ""
                cur += w + " "
            if cur: chunks.append(cur.strip()); cur = ""
        elif len(cur) + len(s) + 1 > maxlen:
            if cur: chunks.append(cur.strip())
            cur = s + " "
        else:
            cur += s + " "
    if cur.strip():
        chunks.append(cur.strip())
    return chunks or [text]


def ass_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def esc(s):
    return s.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", " ")


def build_ass(master, font_dir, path):
    """Write an ASS file: speaker badge + line captions, timed to the master timeline."""
    dur = master["duration"]
    # styles: EN centered mid, AR (coach) larger gold, BADGE top-left, PHRASE lower
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: EN,Cairo,60,{WHITE},{WHITE},{BLACK_OUT},&H64000000,-1,0,0,0,100,100,0,0,1,3,2,5,240,240,150,1
Style: AR,Amiri,78,{GOLD},{GOLD},{BLACK_OUT},&H64000000,-1,0,0,0,100,100,0,0,1,4,2,5,260,260,150,1
Style: BADGE,Cairo,40,{WHITE},{WHITE},{BLACK_OUT},&H00000000,-1,0,0,0,100,100,1,0,1,2,0,7,90,90,70,1
Style: ROLE,Cairo,28,{GREYED},{GREYED},{BLACK_OUT},&H00000000,0,1,0,0,100,100,1,0,1,2,0,7,90,90,124,1
Style: TITLE,Cairo,96,{GOLD},{GOLD},{BLACK_OUT},&H00000000,-1,0,0,0,100,100,2,0,1,4,2,5,120,120,0,1
Style: PHRASE,Amiri,46,{GOLD},{GOLD},{BLACK_OUT},&H50000000,-1,0,0,0,100,100,0,0,1,3,1,2,200,200,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []

    def dialog(style, start, end, text, layer=0):
        ev.append(f"Dialogue: {layer},{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{text}")

    # title card during the intro sting (first ~3s the audio is the sting, so the
    # first line starts a touch later; we hold the title from 0 to first line start)
    first_start = master["lines"][0]["start"] if master["lines"] else 0
    # hold the title only until just before the first spoken line (no overlap)
    title_hold = max(min(first_start - 0.15, 2.4), 1.2)
    dialog("TITLE", 0.2, title_hold,
           "{\\fad(400,250)}Two Worlds\\N{\\fs52\\c" + GOLD + "}" +
           esc(master.get("title", "")))

    poe = master.get("phrase_of_episode") or {}
    for ln in master["lines"]:
        start, end = ln["start"], ln["end"]
        sp = ln["speaker"]
        color, label, role = speaker_style(sp)

        # speaker badge (top-left), accent-colored dot + name + role — held for
        # the whole line so it doesn't flicker between text chunks.
        badge = ("{\\c" + color + "}\u25CF {\\c" + WHITE + "}" + esc(label))
        dialog("BADGE", start, end, badge)
        dialog("ROLE", start, end, "{\\c" + GREYED + "}" + esc(role))

        # the line caption — long lines (esp. the ~30s Coach breaks) are split
        # into readable CHUNKS, each shown for its share of the line's time, so
        # text appears progressively instead of a wall of text.
        style = "AR" if ln["lang"] == "ar" else "EN"
        maxlen = 110 if ln["lang"] == "ar" else 90
        chunks = chunk_text(ln["text"], maxlen)
        span = (end - start) / len(chunks)
        for i, ch in enumerate(chunks):
            cs = start + i * span
            ce = start + (i + 1) * span if i < len(chunks) - 1 else end
            dialog(style, cs, ce, "{\\fad(120,120)}" + esc(ch))

        # phrase-of-episode lower third during Coach breaks (held whole line)
        if sp == "Coach" and poe.get("en"):
            dialog("PHRASE", start, end,
                   "{\\fad(200,200)}" + esc(poe["en"]) + "  \u2014  " + esc(poe.get("ar", "")))

    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(ev) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--dir", default=None)
    ap.add_argument("--home", default=os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"))
    args = ap.parse_args()

    ep = args.episode
    ep_dir = args.dir or os.path.join(args.home, "episodes", f"ep{ep:02d}")
    master_path = os.path.join(ep_dir, "timeline.master.json")
    audio_path = os.path.join(ep_dir, f"ep{ep:02d}_audio.m4a")
    for p in (master_path, audio_path):
        if not os.path.exists(p):
            print(f"ERROR: missing {p} (run audio assembly first)", file=sys.stderr)
            sys.exit(2)
    with open(master_path, encoding="utf-8") as f:
        master = json.load(f)

    font_dir = os.path.join(args.home, "assets", "fonts")
    workdir = tempfile.mkdtemp(prefix=f"ep{ep:02d}_vid_")
    try:
        ass_path = os.path.join(workdir, "captions.ass")
        build_ass(master, font_dir, ass_path)
        print(f"  built captions: {len(master['lines'])} lines, {master['duration']}s")

        dur = master["duration"]

        # 1) Render the branded background ONCE as a static PNG: brand near-black
        #    with a subtle lifted center (a soft dark-navy radial at low opacity
        #    OVER the black, not screen-blended — screen blew the colors out).
        bg_png = os.path.join(workdir, "bg.png")
        run(["ffmpeg", "-y",
             "-f", "lavfi", "-i", f"color=c={BG}:s={W}x{H}",
             "-f", "lavfi", "-i",
             (f"gradients=s={W}x{H}:c0=0x1a1726:c1={BG}"
              f":x0={W//2}:y0={int(H*0.42)}:type=radial"),
             "-filter_complex",
             "[1]format=rgba,colorchannelmixer=aa=0.35[g];[0][g]overlay",
             "-frames:v", "1", bg_png])

        # 2) Loop the still as the base and burn captions over it. Only the
        #    caption layer changes frame-to-frame, so x264 compresses easily.
        ass_esc = ass_path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        fontdir_esc = font_dir.replace("\\", "\\\\").replace(":", "\\:")
        vf = (f"subtitles='{ass_esc}':fontsdir='{fontdir_esc}'"
              f":original_size={W}x{H},format=yuv420p[v]")

        out = os.path.join(ep_dir, f"ep{ep:02d}_video.mp4")
        cmd = ["ffmpeg", "-y",
               "-loop", "1", "-framerate", "25", "-i", bg_png,
               "-i", audio_path,
               "-filter_complex", vf,
               "-map", "[v]", "-map", "1:a",
               "-t", f"{dur}",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
               "-tune", "stillimage",
               "-profile:v", "high", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", out]
        print("  encoding 1920x1080 H.264 (looped still + captions)...")
        run(["nice", "-n", "19", *cmd])

        # verify
        info = run(["ffprobe", "-v", "error", "-show_entries",
                    "format=duration:stream=codec_name,width,height,pix_fmt",
                    "-of", "default=noprint_wrappers=1", out]).stdout
        print(f"OK -> {out}\n{info.strip()}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
