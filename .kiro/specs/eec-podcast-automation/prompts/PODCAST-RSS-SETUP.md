# Two Worlds — Podcast RSS distribution (setup + how it works)

## Hosting (LIVE)
- Cloudflare R2 bucket: **two-worlds-podcast**
- Public base: **https://media.empireenglish.online** (R2 custom domain, verified 200)
- rclone remote on the server: **r2pod:** (write-capable token, chmod 600 in
  ~/.config/rclone/rclone.conf). Endpoint = the account R2 S3 endpoint.
- Feed URL (submit this once): **https://media.empireenglish.online/two-worlds.xml**
- Show cover: https://media.empireenglish.online/two-worlds-cover.jpg
  (placeholder now — owner replaces by dropping the real 3000x3000 cover; same URL)

## How to publish an episode to podcast platforms
1. Owner finishes the audio-with-music and drops it in Drive:
   output/Podcast/for-platforms  — filename MUST contain EpNN (e.g. "... Ep02 ...").
2. On the server:  python3 bin/publish_feed.py --confirm
   -> downloads new eps, uploads audio to R2, rebuilds two-worlds.xml, publishes it.
   (feed_state.json tracks what's already in the feed; only new eps are added.)

## One-time platform submission (owner, from EEC accounts)
- Spotify for Creators (podcasters.spotify.com) -> Add your podcast -> paste feed URL.
- Apple Podcasts Connect (podcastconnect.apple.com) -> + -> paste feed URL.
- (Optional) Google/YouTube Music, Amazon, Podcast Index — same feed URL.
Once submitted, every future `publish_feed.py --confirm` auto-appears on all of them.

## Security TODO
- The R2 write token was shared in chat during setup — rotate it in Cloudflare and
  re-run `rclone config update r2pod ...` with the fresh secret when convenient.
