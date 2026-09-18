# Two Worlds — Weekly automation (Task 6)

## What runs automatically
A weekly n8n schedule GENERATES the next episode's PLAIN audio and notifies the
owner. It never publishes — the owner adds video/music and hands back (for-youtube
/ for-platforms), which the separate publish steps handle.

## Pieces
- **Host trigger service:** `/opt/eec-podcast-trigger/eec_podcast_trigger.py`,
  systemd `eec-podcast-trigger.service` (Restart=always, Nice=18), binds
  **172.18.0.1:8904** only (ufw allows 172.18.0.0/16), same security model as the
  orientation probe. Endpoints:
    - GET  /health
    - POST /run   {"episode":N}   (omit episode -> next after last delivered)
    - GET  /status?episode=N      -> state: running|done|waiting|failed
  It runs run_podcast.py in the background (async) so n8n never blocks.
- **n8n workflow:** "Two Worlds — Weekly Podcast Generate" id **IRVBwGGJBF1SpePA**
  (currently INACTIVE): Weekly Schedule (Mon 9am) -> POST /run -> Wait 15m ->
  GET /status -> Telegram notify (YouTube Ops Bot -> chat 8924041557).
  Validated: 0 errors (only cosmetic typeVersion warnings).

## Weekly loop (how it actually works)
1. (periodic, owner) run the Kaggle English batch for upcoming episodes ->
   download ep folders into episodes/epNN/kaggle_en/. English is "banked".
2. (weekly, auto) schedule fires -> trigger -> run_podcast.py:
   script (if needed) -> verify Kaggle English present -> Coach TTS -> assemble
   --plain -> deliver to raw-audio. Telegram tells the owner "ready" / "waiting".
3. (owner) grab plain audio from raw-audio, make video+thumbnail+cover+music,
   drop finished files in for-youtube (video) and for-platforms (audio).
4. (owner runs / or a future step) publish_youtube.py --confirm  and
   publish_feed.py --confirm.

## To ACTIVATE (owner decision)
- Confirm the day/time (default Mon 9am) and that the Kaggle English batch will be
  kept ahead. Then activate workflow IRVBwGGJBF1SpePA in n8n (or ask me to).
