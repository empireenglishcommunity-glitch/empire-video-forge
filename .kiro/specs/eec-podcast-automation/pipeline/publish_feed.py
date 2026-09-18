#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — PODCAST RSS distribution (Spotify / Apple / etc.).

Podcast platforms don't take per-episode uploads; you publish ONE RSS feed and
submit it once. After that, every episode you add to the feed is auto-pulled by
all platforms. This script maintains that feed.

Flow:
  1. Owner finishes the episode audio (their own music/edit) and drops it in
     Drive: output/Podcast/for-platforms  (filename must contain 'EpNN').
  2. This script downloads new episodes, publishes each audio file to a PUBLIC
     host (so platforms can fetch it), records it in feed_state.json, and
     regenerates podcast.xml (RSS 2.0 + iTunes + Podcast namespace tags).
  3. The feed + audio are served at a public HTTPS base; owner submits that feed
     URL to Spotify for Creators + Apple Podcasts Connect ONCE.

Hosting is pluggable via --host:
  - rclone : copy audio + feed to an rclone remote (e.g. Cloudflare R2) whose
             objects are public at --public-base.  (needs a WRITE-capable token)
  - local  : write audio + feed into a local dir (--serve-dir) that a static web
             route / tunnel serves at --public-base.
The RSS generation itself is identical either way — only the upload step differs.

Show-level cover art (owner-made, 1400-3000px square) is read from --cover
(a local path or URL already public) and referenced in the feed.

Usage (server):
  python3 publish_feed.py --dry-run
  python3 publish_feed.py --host rclone --remote r2:empire-social-staging/podcast \
      --public-base https://social-staging.empireenglish.online/podcast \
      --cover https://.../two-worlds-cover.jpg --confirm
"""
import os, sys, json, re, argparse, subprocess, tempfile, html, datetime
import urllib.request, urllib.parse
from email.utils import format_datetime

FOR_PLATFORMS = "1hnvZAgI51-YsxXHIxnuS-mxqh2uFDDAM"   # owner's audio-with-music drops
STATE_NAME = "feed_state.json"
FEED_NAME = "two-worlds.xml"

SHOW = {
    "title": "Two Worlds — English with Empire English Community",
    "link": "https://empireenglish.online",
    "language": "ar",   # audience is Arabic speakers; episodes are bilingual
    "author": "Empire English Community",
    "owner_name": "Empire English Community",
    "owner_email": "empireenglishcommunity@gmail.com",
    "category": "Education",
    "subcategory": "Language Learning",
    "explicit": "false",
    "description": ("بودكاست Two Worlds من Empire English Community: قصة بالإنجليزي "
                    "الطبيعي في عالم دبي، مع شرح بالعربي المصري من الكوتش لكل جملة "
                    "ومصطلح. إنجليزي حقيقي بالمواقف — نظام مش حِيَل. "
                    "A bilingual English-learning story podcast for Arabic speakers."),
}
EP_TITLES = {
    1: "The Arrival", 2: "The Apartment", 3: "The Interview", 4: "First Day",
    5: "The Coffee Order", 6: "The Misunderstanding", 7: "The Meeting",
    8: "Making a Friend", 9: "The Phone Call", 10: "The Presentation",
}


# ---- Drive helpers (reuse the refreshed token) ---------------------------
def token():
    p = "/tmp/access_token.txt"
    if os.path.exists(p) and os.path.getsize(p):
        return open(p).read().strip()
    raw = subprocess.run(["docker", "exec", "empire-n8n", "n8n", "export:credentials",
                          "--id=FDFZdH8pQKLZQFzz", "--decrypted"],
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


def list_folder(at, fid):
    url = "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(
        {"q": f"'{fid}' in parents and trashed=false",
         "fields": "files(id,name,mimeType,size,modifiedTime)",
         "includeItemsFromAllDrives": "true", "supportsAllDrives": "true",
         "orderBy": "createdTime", "pageSize": "200"})
    return json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers={"Authorization": "Bearer " + at}), timeout=60)).get("files", [])


def download(at, fid, dst):
    url = f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media&supportsAllDrives=true"
    data = urllib.request.urlopen(
        urllib.request.Request(url, headers={"Authorization": "Bearer " + at}), timeout=600).read()
    open(dst, "wb").write(data)
    return len(data)


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
        return 0


def hms(sec):
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def episode_meta(ep, home):
    """Pull the phrase + story for a rich episode description."""
    poe, story = {}, ""
    d = os.path.join(home, "episodes", f"ep{ep:02d}")
    for fn in ("timeline.master.json", "script.json"):
        try:
            j = json.load(open(os.path.join(d, fn), encoding="utf-8"))
            poe = poe or j.get("phrase_of_episode", {}) or {}
            story = story or j.get("story_update", "")
        except Exception:
            pass
    return poe, story


def build_rss(state, public_base, cover_url):
    now = format_datetime(datetime.datetime.now(datetime.timezone.utc))
    esc = lambda s: html.escape(s or "", quote=True)
    items = []
    for ep in sorted(state["episodes"], key=lambda e: e["episode"]):
        enc_url = public_base.rstrip("/") + "/" + urllib.parse.quote(ep["file"])
        pub = ep.get("pub_date") or now
        desc = ep.get("description", "")
        items.append(f"""    <item>
      <title>{esc(ep['title'])}</title>
      <itunes:episode>{ep['episode']}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <description><![CDATA[{desc}]]></description>
      <itunes:summary><![CDATA[{desc}]]></itunes:summary>
      <enclosure url="{esc(enc_url)}" length="{ep.get('bytes',0)}" type="audio/mpeg"/>
      <guid isPermaLink="false">two-worlds-ep{ep['episode']:02d}</guid>
      <pubDate>{pub}</pubDate>
      <itunes:duration>{hms(ep.get('duration',0))}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
    items_xml = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>{esc(SHOW['title'])}</title>
    <link>{esc(SHOW['link'])}</link>
    <language>{SHOW['language']}</language>
    <copyright>© Empire English Community</copyright>
    <description><![CDATA[{SHOW['description']}]]></description>
    <itunes:author>{esc(SHOW['author'])}</itunes:author>
    <itunes:summary><![CDATA[{SHOW['description']}]]></itunes:summary>
    <itunes:type>episodic</itunes:type>
    <itunes:explicit>{SHOW['explicit']}</itunes:explicit>
    <itunes:image href="{esc(cover_url)}"/>
    <image><url>{esc(cover_url)}</url><title>{esc(SHOW['title'])}</title><link>{esc(SHOW['link'])}</link></image>
    <itunes:category text="{esc(SHOW['category'])}">
      <itunes:category text="{esc(SHOW['subcategory'])}"/>
    </itunes:category>
    <itunes:owner>
      <itunes:name>{esc(SHOW['owner_name'])}</itunes:name>
      <itunes:email>{esc(SHOW['owner_email'])}</itunes:email>
    </itunes:owner>
    <lastBuildDate>{now}</lastBuildDate>
{items_xml}
  </channel>
</rss>
"""


def host_put(host, local_path, remote_name, remote, serve_dir):
    """Publish one file to the public host. Returns True on success."""
    if host == "rclone":
        r = subprocess.run(["rclone", "copyto", local_path,
                            f"{remote.rstrip('/')}/{remote_name}",
                            "--s3-no-check-bucket"], capture_output=True, text=True)
        return r.returncode == 0, (r.stderr or r.stdout)
    else:  # local
        os.makedirs(serve_dir, exist_ok=True)
        dst = os.path.join(serve_dir, remote_name)
        subprocess.run(["cp", local_path, dst], check=True)
        return True, dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"))
    ap.add_argument("--host", choices=["rclone", "local"], default="rclone")
    ap.add_argument("--remote", default="r2pod:two-worlds-podcast")
    ap.add_argument("--serve-dir", default="/opt/eec-podcast/public/podcast")
    ap.add_argument("--public-base", default="https://media.empireenglish.online")
    ap.add_argument("--cover", default="", help="show cover URL (public) or local path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()

    home = args.home
    state_path = os.path.join(home, STATE_NAME)
    state = {"episodes": []}
    if os.path.exists(state_path):
        state = json.load(open(state_path, encoding="utf-8"))
    have = {e["episode"] for e in state["episodes"]}

    at = token()
    files = [f for f in list_folder(at, FOR_PLATFORMS)
             if f["name"].lower().endswith((".mp3", ".m4a", ".wav", ".aac"))]
    new = [(ep_from_name(f["name"]), f) for f in files]
    new = [(ep, f) for ep, f in new if ep and ep not in have]

    if not new:
        print(f"No new episodes in for-platforms (feed has {len(have)}: {sorted(have)}).")
        if not state["episodes"]:
            sys.exit(0)

    work = tempfile.mkdtemp(prefix="feed_")
    for ep, f in sorted(new):
        local = os.path.join(work, f["name"])
        nbytes = download(at, f["id"], local)
        dur = probe_duration(local)
        poe, story = episode_meta(ep, home)
        en, ar = poe.get("en", ""), poe.get("ar", "")
        title = f"الحلقة {ep}: {EP_TITLES.get(ep, '')} — Two Worlds"
        desc = (f"حلقة {ep} من بودكاست Two Worlds. قصة بالإنجليزي الطبيعي مع شرح "
                f"بالعربي من الكوتش. جملة الحلقة: \"{en}\" — {ar}. {story}").strip()
        # publish name: keep it clean + stable
        pub_name = f"two-worlds-ep{ep:02d}.mp3" if f["name"].lower().endswith(".mp3") \
                   else f"two-worlds-ep{ep:02d}{os.path.splitext(f['name'])[1]}"
        print(f"  + Ep{ep:02d} '{EP_TITLES.get(ep,'')}' {hms(dur)} {nbytes//1024}KB -> {pub_name}")
        if not (args.dry_run or not args.confirm):
            ok, info = host_put(args.host, local, pub_name, args.remote, args.serve_dir)
            if not ok:
                print(f"    !! host upload failed: {str(info)[:160]}", file=sys.stderr)
                continue
        state["episodes"].append({
            "episode": ep, "title": title, "description": desc, "file": pub_name,
            "duration": dur, "bytes": nbytes,
            "pub_date": format_datetime(datetime.datetime.now(datetime.timezone.utc)),
        })

    cover_url = args.cover or (args.public_base.rstrip("/") + "/two-worlds-cover.jpg")
    rss = build_rss(state, args.public_base, cover_url)
    feed_local = os.path.join(work, FEED_NAME)
    open(feed_local, "w", encoding="utf-8").write(rss)

    if args.dry_run or not args.confirm:
        print("\nDRY RUN — feed preview (first 900 chars):\n")
        print(rss[:900])
        print(f"\n(feed would publish to {args.public_base}/{FEED_NAME})")
        print("Re-run with --confirm (and a working --host) to publish.")
        sys.exit(0)

    ok, info = host_put(args.host, feed_local, FEED_NAME, args.remote, args.serve_dir)
    json.dump(state, open(state_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if ok:
        print(f"\nFEED PUBLISHED: {args.public_base}/{FEED_NAME}  ({len(state['episodes'])} episodes)")
        print("Submit that URL once to Spotify for Creators + Apple Podcasts Connect.")
    else:
        print(f"\n!! feed upload failed: {str(info)[:160]}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main()
