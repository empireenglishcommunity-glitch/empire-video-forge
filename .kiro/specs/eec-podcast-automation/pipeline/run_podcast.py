#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — PODCAST ORCHESTRATOR (audio-only pivot).

One command that chains the server-side generation for an episode and drops the
finished PLAIN audio (dry voices, no music/branding) into the owner's Drive
`raw-audio` folder. The owner then adds their own video/thumbnail/cover/music and
hands finished files back via the for-youtube / for-platforms folders (published
by separate steps).

Pipeline (each stage fail-soft + logged):
  1. SCRIPT   — gen_script.py writes episodes/epNN/script.json (skipped if present).
  2. ENGLISH  — the Chatterbox English WAVs come from the Kaggle BATCH (owner runs
                it; GPU off-server). We do NOT synthesize English here — we VERIFY
                episodes/epNN/kaggle_en/ has the line WAVs + timeline.en.json, and
                stop with a clear message if the owner hasn't run/downloaded them.
  3. COACH    — synth_coach.py renders the Arabic Coach lines (Gemini Kore).
                Resumable + quota-aware (free tier = 10 TTS req/day).
  4. ASSEMBLE — assemble_audio.py --plain stitches everything into ep NN_audio_plain.m4a.
  5. DELIVER  — drive_upload.py pushes the plain .m4a into output/Podcast/raw-audio.

Why English isn't run here: Kaggle sessions expire and need a GPU + the owner's
account, so English is "banked" in periodic batches (design 2.6b). This
orchestrator automates everything that CAN run unattended on the server.

Usage:
  GEMINI_API_KEY=... python3 run_podcast.py --episode 1 [--skip-deliver]
                        [--script-only] [--home /opt/eec-podcast]
Exit codes: 0 ok (delivered) · 3 waiting on Kaggle English · 1 a stage failed.
"""
import os, sys, json, subprocess, argparse, time, datetime

RAW_AUDIO_FOLDER = "1GLKvNq3LAKZ6BaACIMvYeUSJomFErav0"  # output/Podcast/raw-audio

EP_TITLES = {
    1: "The Arrival", 2: "The Apartment", 3: "The Interview", 4: "First Day",
    5: "The Coffee Order", 6: "The Misunderstanding", 7: "The Meeting",
    8: "Making a Friend", 9: "The Phone Call", 10: "The Presentation",
}


def log(logf, msg):
    line = f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    if logf:
        logf.write(line + "\n"); logf.flush()


def run_stage(logf, name, cmd, env=None):
    """Run a subprocess stage; return (ok, output). Fail-soft (never raises)."""
    log(logf, f">>> {name}: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
        out = (r.stdout or "") + (r.stderr or "")
        for ln in out.strip().splitlines()[-12:]:
            log(logf, f"    {ln}")
        if r.returncode != 0:
            log(logf, f"!!! {name} exited {r.returncode}")
            return False, out
        log(logf, f"<<< {name} OK")
        return True, out
    except Exception as e:
        log(logf, f"!!! {name} crashed: {str(e)[:200]}")
        return False, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--home", default=os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"))
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--skip-deliver", action="store_true",
                    help="assemble but do not upload to Drive")
    ap.add_argument("--script-only", action="store_true",
                    help="only generate the script (for the next Kaggle batch)")
    ap.add_argument("--folder", default=RAW_AUDIO_FOLDER)
    args = ap.parse_args()

    ep = args.episode
    home = args.home
    bind = os.path.join(home, "bin")
    ep_dir = os.path.join(home, "episodes", f"ep{ep:02d}")
    os.makedirs(os.path.join(home, "logs"), exist_ok=True)
    logf = open(os.path.join(home, "logs", f"ep{ep:02d}_run.log"), "a", encoding="utf-8")

    env = dict(os.environ)
    py = args.python
    log(logf, f"=== run_podcast ep{ep:02d} start ===")

    # --- 1. SCRIPT ---------------------------------------------------------
    script_path = os.path.join(ep_dir, "script.json")
    if os.path.exists(script_path):
        log(logf, f"1. script exists — reuse {script_path}")
    else:
        if not env.get("GEMINI_API_KEY"):
            log(logf, "!!! no GEMINI_API_KEY and no script.json — cannot generate")
            sys.exit(1)
        ok, _ = run_stage(logf, "1.script",
                          [py, os.path.join(bind, "gen_script.py"),
                           "--episode", str(ep), "--out", script_path], env)
        if not ok or not os.path.exists(script_path):
            log(logf, "!!! script generation failed"); sys.exit(1)

    if args.script_only:
        log(logf, "script-only mode — done (hand script to the Kaggle English batch)")
        sys.exit(0)

    # --- 2. ENGLISH (verify Kaggle batch output is present) ----------------
    en_dir = os.path.join(ep_dir, "kaggle_en")
    en_tl = os.path.join(en_dir, "timeline.en.json")
    en_wavs = [f for f in os.listdir(en_dir)] if os.path.isdir(en_dir) else []
    en_wavs = [f for f in en_wavs if f.startswith("line") and f.endswith(".wav")]
    # how many EN lines does the script expect?
    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)
    need_en = sum(1 for l in script["lines"] if l.get("lang") == "en")
    if not os.path.exists(en_tl) or len(en_wavs) < need_en:
        log(logf, f"2. ENGLISH not ready: found {len(en_wavs)}/{need_en} line WAVs "
                  f"in {en_dir}.")
        log(logf, "    -> Run the Kaggle notebook (kaggle/synth_english.py) for this "
                  "episode, download the ep folder into kaggle_en/, then re-run.")
        sys.exit(3)  # distinct code: waiting on the owner's Kaggle batch
    log(logf, f"2. English ready: {len(en_wavs)}/{need_en} line WAVs present")

    # --- 3. COACH (Gemini Kore, server) ------------------------------------
    if not env.get("GEMINI_API_KEY"):
        log(logf, "!!! no GEMINI_API_KEY — cannot synthesize the Arabic Coach")
        sys.exit(1)
    ok, out = run_stage(logf, "3.coach",
                        [py, os.path.join(bind, "synth_coach.py"),
                         "--episode", str(ep), "--pace", "6"], env)
    # synth_coach exits 1 on PARTIAL success (some lines hit the daily quota).
    # That's fail-soft: keep going only if ALL coach lines are present.
    need_ar = sum(1 for l in script["lines"] if l.get("lang") == "ar")
    have_ar = len([f for f in os.listdir(ep_dir)
                   if f.startswith("coach") and f.endswith(".wav")])
    if have_ar < need_ar:
        log(logf, f"!!! Coach incomplete: {have_ar}/{need_ar} lines (TTS daily quota?). "
                  "Re-run after the quota resets — synth is resumable.")
        sys.exit(3)
    log(logf, f"3. Coach ready: {have_ar}/{need_ar} lines")

    # --- 4. ASSEMBLE (plain) ----------------------------------------------
    ok, _ = run_stage(logf, "4.assemble",
                      [py, os.path.join(bind, "assemble_audio.py"),
                       "--episode", str(ep), "--plain"], env)
    out_audio = os.path.join(ep_dir, f"ep{ep:02d}_audio_plain.m4a")
    if not ok or not os.path.exists(out_audio):
        log(logf, "!!! audio assembly failed"); sys.exit(1)

    # --- 5. DELIVER to raw-audio ------------------------------------------
    if args.skip_deliver:
        log(logf, f"skip-deliver — plain audio at {out_audio}")
        sys.exit(0)
    title = EP_TITLES.get(ep, f"Episode {ep}")
    name = f"Two Worlds - Ep{ep:02d} - {title} (plain audio).m4a"
    ok, _ = run_stage(logf, "5.deliver",
                      [py, os.path.join(bind, "drive_upload.py"),
                       out_audio, name, "audio/mp4", args.folder], env)
    if not ok:
        log(logf, "!!! delivery failed (audio is still available locally)"); sys.exit(1)

    log(logf, f"=== ep{ep:02d} DONE — plain audio delivered to raw-audio ===")


if __name__ == "__main__":
    main()
