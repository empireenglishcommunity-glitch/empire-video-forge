#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — DELIVER an episode to the publishing engine.

Uploads the finished 16:9 episode video PLUS its metadata sidecar to the Drive
folder that the live "YouTube — Publishing" workflow (id RdtmJTVYU4jFFCvF)
watches. The engine then: probe -> 16:9 => long-form -> Gemini writes the
bilingual title/description -> uploads to YouTube as a regular video (custom
thumbnail shows, no #Shorts) -> Empire English Podcast playlist.

CONTRACT (verified against funnel/compose_yt_prompt.js + build_yt_metadata.js):
- The video MUST be horizontal (16:9) so the orientation probe -> long-form.
- A companion sidecar named "<video-basename>_metadata.json" is uploaded next to
  the video; n8n exposes it as the `sideMeta` binary. It only SEEDS Gemini
  (title/caption/hook + topic) and provides fail-soft format flags — the engine
  writes the final published copy itself.
- The workflow watches the EEC brand folder 01-EEC-only. MACAL content must never
  reach EEC channels — this script only ever targets the EEC podcast folder.

SAFETY: dropping into the watched folder triggers a REAL YouTube publish within
~1 minute. This script therefore requires --confirm to write to the live folder;
without it, it targets --staging-folder (a non-watched folder) so you can review
exactly what would be delivered.

Uses the same Drive OAuth token the n8n cred holds (refreshed into
/tmp/access_token.txt by the pipeline). Run on the server.

Usage:
  # prepare + inspect (safe): uploads to the staging/output parent, not watched
  python3 deliver_episode.py --episode 1 --token /tmp/access_token.txt

  # real delivery (triggers publish):
  python3 deliver_episode.py --episode 1 --token /tmp/access_token.txt --confirm
"""
import os, sys, json, argparse, urllib.request

# EEC-eligible watched folder (01-EEC-only) — the live trigger polls this.
EEC_WATCHED_FOLDER = "19WOAX2ME-YWN477ipaMZhuRr5HXqwDOS"
# output parent (NOT watched) — safe place to stage/inspect a delivery.
OUTPUT_PARENT = "1bKV8ALl6luA31CKayW2O3loofEWWHmHh"

# Episode plan (title seeds + level). Mirrors SEASON1 in gen_script.py.
EP_META = {
    1: ("The Arrival", "A2", "conversation"),
    2: ("The Apartment", "A2", "conversation"),
    3: ("The Interview", "B1", "conversation"),
    4: ("First Day", "B1", "conversation"),
    5: ("The Coffee Order", "A2", "conversation"),
    6: ("The Misunderstanding", "B1", "conversation"),
    7: ("The Meeting", "B2", "conversation"),
    8: ("Making a Friend", "B1", "conversation"),
    9: ("The Phone Call", "B2", "conversation"),
    10: ("The Presentation", "B2", "conversation"),
}


def api_upload(token, name, parent, path, mime):
    meta = {"name": name, "parents": [parent]}
    b = "===EECBOUNDARY==="
    body = b""
    body += ("--" + b + "\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n").encode()
    body += (json.dumps(meta) + "\r\n").encode()
    body += ("--" + b + "\r\nContent-Type: " + mime + "\r\n\r\n").encode()
    with open(path, "rb") as f:
        body += f.read()
    body += ("\r\n--" + b + "--").encode()
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true",
        data=body, headers={"Authorization": "Bearer " + token,
                            "Content-Type": "multipart/related; boundary=" + b})
    return json.load(urllib.request.urlopen(req, timeout=300))


def probe_duration(path):
    import subprocess
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                              "format=duration", "-of",
                              "default=nokey=1:noprint_wrappers=1", path],
                             capture_output=True, text=True).stdout.strip()
        return int(float(out))
    except Exception:
        return None


def build_sidecar(episode, ep_dir, video_path):
    title, level, topic = EP_META.get(episode, (f"Episode {episode}", "A2", "conversation"))
    dur = probe_duration(video_path)
    # pull the phrase of the episode + story from the script/master timeline for a
    # richer Gemini seed (title/caption/hook). Fail-soft to plan title.
    poe = {}
    story = ""
    try:
        with open(os.path.join(ep_dir, "timeline.master.json"), encoding="utf-8") as f:
            m = json.load(f)
        poe = m.get("phrase_of_episode", {}) or {}
    except Exception:
        pass
    try:
        with open(os.path.join(ep_dir, "script.json"), encoding="utf-8") as f:
            s = json.load(f)
        story = s.get("story_update", "") or ""
        if not poe:
            poe = s.get("phrase_of_episode", {}) or {}
    except Exception:
        pass

    en_phrase = poe.get("en", "")
    ar_phrase = poe.get("ar", "")
    # Arabic-first seed title (Gemini will refine, but this steers topic/keyword)
    seed_title = f"Two Worlds — الحلقة {episode}: {title} | تعلّم إنجليزي بالمواقف"
    caption = (f"حلقة {episode} من بودكاست Two Worlds: قصة بالإنجليزي الطبيعي "
               f"مع شرح بالعربي من الكوتش. جملة الحلقة: \"{en_phrase}\" — {ar_phrase}. "
               f"{story}").strip()
    hook = f"إزاي تستخدم \"{en_phrase}\" صح؟ اتعلمها في سياق حقيقي."

    return {
        "title": seed_title,
        "caption": caption,
        "hook": hook,
        "topic": topic,             # normalizes to one of the 5 engine keys
        "format": "long",           # fail-soft long-form flag (probe is primary)
        "is_long": True,
        "duration": dur if dur is not None else 120,
        "episode": episode,
        "level": level,
        "podcast": True,            # playlist hint: Empire English Podcast
        "series": "Two Worlds",
        "phrase_en": en_phrase,
        "phrase_ar": ar_phrase,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--home", default=os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"))
    ap.add_argument("--token", default="/tmp/access_token.txt")
    ap.add_argument("--confirm", action="store_true",
                    help="deliver to the LIVE watched folder (triggers publish). "
                         "Without this, upload to the non-watched staging parent.")
    ap.add_argument("--staging-folder", default=OUTPUT_PARENT)
    args = ap.parse_args()

    ep = args.episode
    ep_dir = os.path.join(args.home, "episodes", f"ep{ep:02d}")
    video = os.path.join(ep_dir, f"ep{ep:02d}_video.mp4")
    if not os.path.exists(video):
        print(f"ERROR: no video {video}", file=sys.stderr); sys.exit(2)
    with open(args.token) as f:
        token = f.read().strip()

    # sidecar with the exact <video-basename>_metadata.json naming
    base = f"Two Worlds - Ep{ep:02d} - {EP_META.get(ep, ('',))[0]}".strip()
    video_name = base + ".mp4"
    sidecar_name = base + "_metadata.json"
    sidecar = build_sidecar(ep, ep_dir, video)
    sidecar_path = os.path.join(ep_dir, sidecar_name)
    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, ensure_ascii=False, indent=2)

    target = EEC_WATCHED_FOLDER if args.confirm else args.staging_folder
    where = "LIVE watched folder (WILL PUBLISH)" if args.confirm else "staging parent (no publish)"
    print(f"Episode {ep}: '{sidecar['title']}'")
    print(f"  video:   {video_name}  ({sidecar['duration']}s)")
    print(f"  sidecar: {sidecar_name}")
    print(f"  target:  {target}  [{where}]")
    print("  sidecar contents:")
    print("   ", json.dumps(sidecar, ensure_ascii=False)[:400])

    if not args.confirm:
        print("\nDRY MODE — uploading to staging (not the watched folder). "
              "Re-run with --confirm to deliver for real.")

    r1 = api_upload(token, video_name, target, video, "video/mp4")
    r2 = api_upload(token, sidecar_name, target, sidecar_path, "application/json")
    print(f"  uploaded video   id={r1.get('id')}")
    print(f"  uploaded sidecar id={r2.get('id')}")
    if args.confirm:
        print("\nDELIVERED to the live folder. The engine should publish within ~1 minute.")
    else:
        print("\nStaged. Inspect, then deliver for real with --confirm.")


if __name__ == "__main__":
    main()
