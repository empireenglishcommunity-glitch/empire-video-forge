#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — YouTube publisher (forwarder for the owner's finished video).

The owner finishes the episode VIDEO + thumbnail themselves and drops them into
Drive: output/Podcast/for-youtube. This script bridges that convenience folder to
the LIVE publishing engine WITHOUT touching the engine: it reads the newest
finished video in for-youtube, builds the metadata sidecar (the exact contract
the "YouTube - Publishing" workflow expects), and copies the video + sidecar into
the folder the engine already watches (01-EEC-only). The engine then does the
rest: probe -> 16:9 long-form -> Gemini writes the AR title/description -> uploads
as a regular video (custom thumbnail shows) -> Empire English Podcast playlist.

Why a forwarder (not repointing the engine): the workflow is live and also used
for other EEC content; we never modify its trigger. We only feed its inbox.

FILENAME CONVENTION (so we can find the episode #):
  the video filename should contain "EpNN" or "Episode N" (case-insensitive),
  e.g. "Two Worlds - Ep01 - The Arrival.mp4". If a thumbnail is present it is
  uploaded too (name it with the same EpNN); the engine also makes its own.

SAFETY: copying into 01-EEC-only triggers a REAL publish within ~1 min. Requires
--confirm; without it, it does a DRY RUN (shows what it WOULD copy + the sidecar).

Usage (server):
  python3 publish_youtube.py                 # dry run: list + show sidecar
  python3 publish_youtube.py --confirm       # forward newest video -> publish
  python3 publish_youtube.py --episode 1 --confirm
"""
import os, sys, json, re, argparse, urllib.request, urllib.parse, subprocess, tempfile

FOR_YOUTUBE = "1zCDvLwgAZ9Ea61eNVs63FaN1HyJMcS81"   # owner's handback folder

# --- FAIL-CLOSED DESTINATION TABLE ----------------------------------------
# The live "YouTube — Publishing" workflow already routes by the folder a video
# lands in (its "Classify (folder -> brand + destinations)" node), with a
# fail-closed guard that aborts on an unknown folder or a MACAL->EEC leak.
# This forwarder mirrors that table so it can ONLY drop a podcast episode into a
# sanctioned EEC destination. Any other target must be added here EXPLICITLY;
# an unmapped --target is refused (fail-closed) rather than guessed.
DESTINATIONS = {
    "eec-only": {
        "folder_id": "19WOAX2ME-YWN477ipaMZhuRr5HXqwDOS",   # 01-EEC-only
        "label": "01-EEC-only", "brand": "EEC",
        "note": "EEC YouTube (long-form) + IG. The podcast's home.",
    },
    # 02-EEC-and-MACAL and 03-MACAL-only exist in the engine but are NOT valid
    # podcast targets — the podcast is an EEC-only property. Left out on purpose
    # so the forwarder cannot publish the podcast under MACAL.
}
DEFAULT_TARGET = "eec-only"   # the ONLY sanctioned podcast destination
EEC_WATCHED = DESTINATIONS[DEFAULT_TARGET]["folder_id"]   # back-compat alias

EP_META = {
    1: ("The Arrival", "A2"), 2: ("The Apartment", "A2"), 3: ("The Interview", "B1"),
    4: ("First Day", "B1"), 5: ("The Coffee Order", "A2"), 6: ("The Misunderstanding", "B1"),
    7: ("The Meeting", "B2"), 8: ("Making a Friend", "B1"), 9: ("The Phone Call", "B2"),
    10: ("The Presentation", "B2"),
}
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".webm")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")


def token():
    p = "/tmp/access_token.txt"
    if os.path.exists(p) and os.path.getsize(p):
        return open(p).read().strip()
    # fall back to the shared uploader's refresh path
    from importlib import util
    return _refresh()


def _refresh():
    raw = subprocess.run(["docker", "exec", "empire-n8n", "n8n",
                          "export:credentials", "--id=FDFZdH8pQKLZQFzz", "--decrypted"],
                         capture_output=True, text=True).stdout
    d = json.loads(next(l for l in raw.splitlines() if l.startswith("[")))[0]["data"]
    tok = d["oauthTokenData"]
    if isinstance(tok, str):
        tok = json.loads(tok)
    body = urllib.parse.urlencode({"client_id": d["clientId"], "client_secret": d["clientSecret"],
        "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"}).encode()
    at = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=30))["access_token"]
    open("/tmp/access_token.txt", "w").write(at)
    return at


def api(at, params):
    url = "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params)
    return json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers={"Authorization": "Bearer " + at}), timeout=60))


def list_folder(at, fid):
    r = api(at, {"q": f"'{fid}' in parents and trashed=false",
                 "fields": "files(id,name,mimeType,size,modifiedTime)",
                 "includeItemsFromAllDrives": "true", "supportsAllDrives": "true",
                 "orderBy": "modifiedTime desc", "pageSize": "100"})
    return r.get("files", [])


def download(at, fid, dst):
    url = f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media&supportsAllDrives=true"
    data = urllib.request.urlopen(
        urllib.request.Request(url, headers={"Authorization": "Bearer " + at}), timeout=300).read()
    open(dst, "wb").write(data)


def ep_from_name(name):
    m = re.search(r"ep\s*0*([0-9]{1,2})", name, re.I) or re.search(r"episode\s*0*([0-9]{1,2})", name, re.I)
    return int(m.group(1)) if m else None


def probe_duration(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=nokey=1:noprint_wrappers=1", path],
                             capture_output=True, text=True).stdout.strip()
        return int(float(out))
    except Exception:
        return None


def build_sidecar(ep, dur, home):
    title, level = EP_META.get(ep, (f"Episode {ep}", "A2"))
    poe = {}
    story = ""
    ep_dir = os.path.join(home, "episodes", f"ep{ep:02d}")
    for fn, key in (("timeline.master.json", "phrase_of_episode"), ("script.json", None)):
        try:
            with open(os.path.join(ep_dir, fn), encoding="utf-8") as f:
                j = json.load(f)
            poe = poe or j.get("phrase_of_episode", {}) or {}
            story = story or j.get("story_update", "")
        except Exception:
            pass
    en, ar = poe.get("en", ""), poe.get("ar", "")
    # Sidecar contract read by the engine's "Build YT metadata" node:
    #   meta.is_long / meta.format / meta.duration -> long-form (not a Short)
    #   meta.title / meta.video_title_for_youtube_short -> title fallback
    #   meta.caption -> caption fallback
    #   meta.hashtags -> merged with brand hashtags
    # topic is normally inferred by Gemini; "conversation" here is our intent so
    # a story episode lands in the Conversation playlist (engine falls back to
    # Tips if Gemini disagrees). Extra keys (episode/level/podcast/series) are
    # harmless metadata for our own traceability.
    return {
        "title": f"Two Worlds — الحلقة {ep}: {title} | تعلّم إنجليزي بالمواقف",
        "video_title_for_youtube_short": f"Two Worlds — الحلقة {ep}: {title}",
        "caption": (f"حلقة {ep} من بودكاست Two Worlds: قصة بالإنجليزي الطبيعي مع شرح "
                    f"بالعربي من الكوتش. جملة الحلقة: \"{en}\" — {ar}. {story}").strip(),
        "hook": f"إزاي تستخدم \"{en}\" صح؟ اتعلمها في سياق حقيقي.",
        "hashtags": ["TwoWorlds", "تعلم_الإنجليزية", "إنجليزي", "LearnEnglish", "Podcast"],
        "topic": "conversation", "format": "long", "is_long": True,
        "duration": dur or 120, "episode": ep, "level": level,
        "podcast": True, "series": "Two Worlds",
    }


def upload(at, name, parent, path, mime):
    meta = {"name": name, "parents": [parent]}
    b = "===EECB==="
    body = ("--" + b + "\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n").encode()
    body += (json.dumps(meta) + "\r\n").encode()
    body += ("--" + b + "\r\nContent-Type: " + mime + "\r\n\r\n").encode()
    body += open(path, "rb").read() + ("\r\n--" + b + "--").encode()
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true",
        data=body, headers={"Authorization": "Bearer " + at, "Content-Type": "multipart/related; boundary=" + b})
    return json.load(urllib.request.urlopen(req, timeout=600))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"))
    ap.add_argument("--episode", type=int, default=None)
    ap.add_argument("--target", default=DEFAULT_TARGET,
                    help="destination key from the fail-closed table "
                         f"(allowed: {', '.join(sorted(DESTINATIONS))})")
    ap.add_argument("--confirm", action="store_true",
                    help="actually forward into the target folder (triggers publish)")
    args = ap.parse_args()

    # FAIL-CLOSED: refuse any target not explicitly sanctioned for the podcast.
    dest = DESTINATIONS.get(args.target)
    if dest is None:
        print(f"REFUSED: '{args.target}' is not a sanctioned podcast destination.\n"
              f"Allowed targets: {', '.join(sorted(DESTINATIONS))}.\n"
              "The podcast is an EEC-only property; add a mapping in DESTINATIONS "
              "only if you truly intend a new destination.", file=sys.stderr)
        sys.exit(2)
    dest_folder = dest["folder_id"]

    at = token()
    files = list_folder(at, FOR_YOUTUBE)
    videos = [f for f in files if f["name"].lower().endswith(VIDEO_EXT)]
    if not videos:
        print("for-youtube is empty (no video). Drop your finished episode video there.")
        sys.exit(0)

    # pick the target video: by --episode, else the newest
    target = None
    if args.episode:
        target = next((v for v in videos if ep_from_name(v["name"]) == args.episode), None)
        if not target:
            print(f"No video for episode {args.episode} in for-youtube.", file=sys.stderr); sys.exit(2)
    else:
        target = videos[0]  # newest (orderBy modifiedTime desc)

    ep = args.episode or ep_from_name(target["name"])
    if not ep:
        print(f"Cannot detect episode number from '{target['name']}'. "
              "Name it with 'EpNN' (e.g. 'Two Worlds - Ep01 ...mp4').", file=sys.stderr)
        sys.exit(2)

    # matching thumbnail for the same episode (optional)
    thumb = next((f for f in files if f["name"].lower().endswith(IMAGE_EXT)
                  and ep_from_name(f["name"]) == ep), None)

    work = tempfile.mkdtemp(prefix=f"ytpub_ep{ep:02d}_")
    vpath = os.path.join(work, target["name"])
    download(at, target["id"], vpath)
    dur = probe_duration(vpath)
    sidecar = build_sidecar(ep, dur, args.home)

    base = f"Two Worlds - Ep{ep:02d} - {EP_META.get(ep, ('',))[0]}".strip()
    video_name = base + os.path.splitext(target["name"])[1]
    sidecar_name = base + "_metadata.json"
    spath = os.path.join(work, sidecar_name)
    with open(spath, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, ensure_ascii=False, indent=2)

    print(f"Episode {ep}: '{sidecar['title']}'")
    print(f"  destination: {args.target} -> {dest['label']} "
          f"(brand={dest['brand']}) [{dest_folder}]")
    print(f"  video:   {target['name']} ({dur}s) -> will publish as {video_name}")
    print(f"  thumb:   {thumb['name'] if thumb else '(none — engine makes one)'}")
    print(f"  sidecar: {sidecar_name}")
    print(f"  sidecar: {json.dumps(sidecar, ensure_ascii=False)[:300]}")

    if not args.confirm:
        print("\nDRY RUN — nothing forwarded. Re-run with --confirm to publish.")
        sys.exit(0)

    r1 = upload(at, video_name, dest_folder, vpath, "video/mp4")
    r2 = upload(at, sidecar_name, dest_folder, spath, "application/json")
    print(f"  forwarded video   id={r1.get('id')}")
    print(f"  forwarded sidecar id={r2.get('id')}")
    if thumb:
        tpath = os.path.join(work, thumb["name"])
        download(at, thumb["id"], tpath)
        r3 = upload(at, base + os.path.splitext(thumb["name"])[1], dest_folder, tpath, "image/jpeg")
        print(f"  forwarded thumb   id={r3.get('id')}")
    print(f"\nForwarded to {dest['label']}. The engine should publish within ~1 minute.")


if __name__ == "__main__":
    main()
