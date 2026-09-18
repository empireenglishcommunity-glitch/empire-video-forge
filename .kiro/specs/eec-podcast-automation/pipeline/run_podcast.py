#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — PODCAST ORCHESTRATOR (audio-only, current architecture).

One command that chains the server-side steps for an episode and drops the
finished PLAIN audio (dry voices, no music/branding) into the owner's Drive
`raw-audio` folder. The owner then adds their own video/thumbnail/cover/music and
hands finished files back via for-youtube / for-platforms (published separately).

Pipeline (each stage fail-soft + logged):
  1. SCRIPT   — gen_episode.py writes episodes/epNN/script.json (skipped if present).
                Uses the OpenRouter LLM backend (EEC_LLM_*), NOT Gemini. [Gemini-free]
  2. VOICES   — ALL per-line WAVs (English Chatterbox + Arabic Coach VoiceTut) come
                from the two Kaggle GPU batches (synth_episode_en.py / _ar.py). We do
                NOT synthesize on the server (3.7GB RAM, no GPU). This stage VERIFIES
                episodes/epNN/synth/ has a merged manifest with every line rendered,
                and stops with a clear message if the owner hasn't run/downloaded them.
  3. ASSEMBLE — assemble_audio.py --plain stitches everything (manifest-driven) into
                epNN_audio_plain.m4a.
  4. DELIVER  — drive_upload.py pushes the plain .m4a into output/Podcast/raw-audio.

Why voices aren't synthesized here: VoiceTut + Chatterbox need a GPU and clash in one
kernel, so both run as Kaggle batches (two notebooks). This orchestrator automates
everything that CAN run unattended on the server. The OLD server-side Gemini-Kore
Coach step is REMOVED — the Coach is now a VoiceTut voice in the Arabic batch.

Usage:
  python3 run_podcast.py --episode 2 [--skip-deliver] [--script-only]
                         [--home /opt/eec-podcast]
Exit codes: 0 ok (delivered) · 3 waiting on Kaggle voice batches · 1 a stage failed.
"""
import os, sys, json, subprocess, argparse, datetime

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


def verify_voices(ep_dir, script, logf):
    """Verify the unified Kaggle voice batch is present + complete.

    Source of truth = a merged manifest in episodes/epNN/synth/. We merge any
    manifest*.json we find (the ar-pass + en-pass copies) and require every
    scripted line to be 'rendered' with a WAV on disk. Returns True if ready."""
    bind = os.path.join(os.path.dirname(ep_dir), "..", "bin")
    synth = os.path.join(ep_dir, "synth")
    if not os.path.isdir(synth):
        log(logf, f"2. VOICES not ready: no {synth}/ — run the two Kaggle batches "
                  "(synth_episode_ar.py + synth_episode_en.py), drop both zips in "
                  "Drive raw-audio, and download/extract them here.")
        return False
    # merge manifests via the shared lib (kept next to assemble_audio.py)
    sys.path.insert(0, os.path.join(ep_dir, "..", "..", "bin"))
    try:
        import manifest_lib
    except Exception:
        # fall back: count WAVs vs. scripted lines
        wavs = [f for f in os.listdir(synth) if f.startswith("line") and f.endswith(".wav")]
        need = sum(1 for l in script["lines"] if l.get("lang") in ("ar", "en"))
        if len(wavs) < need:
            log(logf, f"2. VOICES not ready: {len(wavs)}/{need} line WAVs in {synth}.")
            return False
        log(logf, f"2. Voices ready: {len(wavs)}/{need} WAVs (no manifest_lib; counted).")
        return True
    import glob
    merged = manifest_lib.build_skeleton(script)
    for m in sorted(glob.glob(os.path.join(synth, "manifest*.json"))):
        try:
            merged = manifest_lib.merge_pass(merged, json.load(open(m, encoding="utf-8")))
        except Exception:
            pass
    s = manifest_lib.summary(merged)
    if s["pending"] or s["failed"]:
        log(logf, f"2. VOICES not ready: {s['rendered']}/{s['total']} rendered, "
                  f"{s['failed']} failed, {s['pending']} pending. "
                  f"Re-run the batch (or fix via the review app) for idx {s['pending_idx'][:15]}.")
        return False
    log(logf, f"2. Voices ready: {s['rendered']}/{s['total']} rendered (~{s['duration_min']}min).")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--home", default=os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"))
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--level", default=None, help="CEFR level hint for the generator")
    ap.add_argument("--skip-deliver", action="store_true", help="assemble but don't upload")
    ap.add_argument("--script-only", action="store_true",
                    help="only generate the script (to hand to the Kaggle voice batches)")
    ap.add_argument("--folder", default=RAW_AUDIO_FOLDER)
    args = ap.parse_args()

    ep, home = args.episode, args.home
    bind = os.path.join(home, "bin")
    ep_dir = os.path.join(home, "episodes", f"ep{ep:02d}")
    os.makedirs(os.path.join(home, "logs"), exist_ok=True)
    os.makedirs(ep_dir, exist_ok=True)
    logf = open(os.path.join(home, "logs", f"ep{ep:02d}_run.log"), "a", encoding="utf-8")
    env = dict(os.environ)
    py = args.python
    log(logf, f"=== run_podcast ep{ep:02d} start ===")

    # --- 1. SCRIPT (OpenRouter, Gemini-free) -------------------------------
    script_path = os.path.join(ep_dir, "script.json")
    if os.path.exists(script_path):
        log(logf, f"1. script exists — reuse {script_path}")
    else:
        if not (env.get("EEC_LLM_BASE_URL") and env.get("EEC_LLM_KEY")):
            log(logf, "!!! no LLM backend (set EEC_LLM_BASE_URL + EEC_LLM_KEY) and no "
                      "script.json — cannot generate")
            sys.exit(1)
        cmd = [py, os.path.join(bind, "gen_episode.py"), "--episode", str(ep),
               "--out", script_path]
        if args.level:
            cmd += ["--level", args.level]
        ok, _ = run_stage(logf, "1.script", cmd, env)
        if not ok or not os.path.exists(script_path):
            log(logf, "!!! script generation failed"); sys.exit(1)

    if args.script_only:
        log(logf, "script-only mode — done (hand script to the Kaggle voice batches)")
        sys.exit(0)

    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)

    # --- 2. VOICES (verify the Kaggle batches are present + complete) ------
    if not verify_voices(ep_dir, script, logf):
        sys.exit(3)  # distinct code: waiting on the owner's Kaggle batches

    # --- 3. ASSEMBLE (plain, manifest-driven) ------------------------------
    ok, _ = run_stage(logf, "3.assemble",
                      [py, os.path.join(bind, "assemble_audio.py"),
                       "--episode", str(ep), "--plain",
                       "--wav-dir", os.path.join(ep_dir, "synth")], env)
    out_audio = os.path.join(ep_dir, f"ep{ep:02d}_audio_plain.m4a")
    if not ok or not os.path.exists(out_audio):
        log(logf, "!!! audio assembly failed"); sys.exit(1)

    # --- 4. DELIVER to raw-audio ------------------------------------------
    if args.skip_deliver:
        log(logf, f"skip-deliver — plain audio at {out_audio}")
        sys.exit(0)
    title = EP_TITLES.get(ep, f"Episode {ep}")
    name = f"Two Worlds - Ep{ep:02d} - {title} (plain audio).m4a"
    ok, _ = run_stage(logf, "4.deliver",
                      [py, os.path.join(bind, "drive_upload.py"),
                       out_audio, name, "audio/mp4", args.folder], env)
    if not ok:
        log(logf, "!!! delivery failed (audio is still available locally)"); sys.exit(1)

    log(logf, f"=== ep{ep:02d} DONE — plain audio delivered to raw-audio ===")


if __name__ == "__main__":
    main()
