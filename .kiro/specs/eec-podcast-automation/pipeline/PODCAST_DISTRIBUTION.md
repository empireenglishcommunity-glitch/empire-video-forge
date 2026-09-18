# Two Worlds — Podcast Distribution Runbook (RSS → Spotify / Apple)

Podcast platforms don't take per-episode uploads. You publish **one RSS feed**
and submit its URL **once** to each platform; every episode you add to the feed
afterwards is auto-pulled by all of them.

## Current state (verified)
- **Feed generator**: `bin/publish_feed.py` — builds a valid RSS 2.0 + iTunes +
  Podcast-namespace feed. All 14 Apple/Spotify-required tags present; XML
  well-formed. Enclosure MIME now matches the real container (`.m4a` →
  `audio/x-m4a`, `.mp3` → `audio/mpeg`) — a earlier hardcoded `audio/mpeg`
  would have made platforms reject our `.m4a` audio.
- **Hosting**: Cloudflare R2 bucket `two-worlds-podcast`, fronted by the custom
  domain **`https://media.empireenglish.online`** (verified HTTP 200 for the
  cover). rclone remote `r2pod` is configured and writable.
- **Cover art**: `two-worlds-cover.jpg` already on R2, **3000×3000 (compliant)**.
  ⚠️ It is a **placeholder** (gold "TWO WORLDS" on black). Replace with final
  designed art before a public launch — see "Swap the cover" below.
- **Feed URL (once published)**: `https://media.empireenglish.online/two-worlds.xml`
  (currently 404 — not published yet; publish creates it).

## Publish an episode to the feed
1. Owner drops the **finished audio with music** (their edit) into Drive
   `output/Podcast/for-platforms`. **Filename must contain `EpNN`** (e.g.
   `Two Worlds - Ep01 ... .m4a`).
2. On the server:
   ```
   cd /opt/eec-podcast
   python3 bin/publish_feed.py --dry-run          # preview the feed XML
   python3 bin/publish_feed.py --host rclone \
       --remote r2pod:two-worlds-podcast \
       --public-base https://media.empireenglish.online \
       --cover https://media.empireenglish.online/two-worlds-cover.jpg \
       --confirm                                  # publish audio + feed to R2
   ```
3. Verify it's live:
   ```
   curl -sI https://media.empireenglish.online/two-worlds.xml     # expect 200
   curl -sI https://media.empireenglish.online/two-worlds-ep01.m4a # expect 200
   ```

## Submit the feed (owner action — one time)
> Requires the owner's own platform accounts.
- **Spotify for Creators** (podcasters.spotify.com): Add show → paste the feed
  URL → verify the ownership email sent to `empireenglishcommunity@gmail.com`.
- **Apple Podcasts Connect** (podcastsconnect.apple.com): + → paste feed URL →
  validate → submit for review (Apple review can take a few days).
- Optional wider reach: submit the same URL to YouTube Music (podcasts),
  Amazon/Audible, Pocket Casts, Overcast — all take the same RSS URL.

## Swap the cover (final art)
Replace the placeholder without changing the feed:
```
rclone copyto /path/to/final-cover.jpg r2pod:two-worlds-podcast/two-worlds-cover.jpg --s3-no-check-bucket
```
Keep it **square, 1400–3000px, JPG/PNG, RGB**. Platforms re-crawl and pick it up.

## Notes
- `feed_state.json` (in `/opt/eec-podcast`) tracks which episodes are already in
  the feed, so re-running is safe and only adds new ones.
- The `<guid>` is stable per episode (`two-worlds-epNN`) — never change it, or
  platforms will treat the episode as new.
