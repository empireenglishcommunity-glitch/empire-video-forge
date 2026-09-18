# Two Worlds podcast — resume here (as of 2026-09-18, ~01:15)

## One-line status
Episode 1 is fully built (script → voices → audio+music → **video, owner-approved**)
and the delivery script is dry-run verified. We are **one step from publishing** —
holding for the owner's go, and for one missing Coach line to fill.

## Pick up tomorrow with ONE of these (owner chooses)
- **(A) RECOMMENDED:** fill the missing Coach outro line, re-render the complete
  video, then publish.
- **(B)** publish the current 14/15-line version now.
- **(C)** hold publishing; build Phase 6 (weekly automation) first.

## The one loose end — Coach outro line
- Ep1 has 15 lines; 14 are done. The final **Coach outro** (line "coach003") never
  rendered because Gemini free-tier TTS = **10 requests/DAY** and we hit the cap.
- The synth is **resumable** — just re-run it after the daily quota resets
  (~Pacific midnight). It will fill ONLY the missing line and keep the rest.
- Command (on the server, key already in /opt/eec-podcast/.env):
  ```
  cd /opt/eec-podcast && source venv/bin/activate
  set -a; source .env; set +a
  python3 bin/synth_coach.py --episode 1 --pace 6      # fills coach003
  python3 bin/assemble_audio.py --episode 1            # re-stitch (music+stings)
  python3 bin/assemble_video.py --episode 1            # re-render 1080p video
  ```

## To PUBLISH (only on owner "go" — triggers a REAL YouTube upload)
```
cd /opt/eec-podcast && source venv/bin/activate
# refresh Drive token from the n8n cred first (see deliver notes), then:
python3 bin/deliver_episode.py --episode 1 --confirm
```
- Live workflow `RdtmJTVYU4jFFCvF` "YouTube — Publishing" is **active**, watches
  Drive folder **01-EEC-only** (`19WOAX2ME-YWN477ipaMZhuRr5HXqwDOS`), polls every min.
- Engine: 16:9 → probe long-form → Gemini writes AR title/desc → regular upload →
  Empire English Podcast playlist. Sidecar only seeds it (`deliver_episode.py`).
- The review drafts in the `output` PARENT do NOT trigger publishing (only the
  01-EEC-only subfolder is watched) — safe.

## What's on the server (/opt/eec-podcast)
- `bin/`: gen (n8n did Ep1), synth_coach.py, assemble_audio.py, assemble_video.py,
  make_audio_brand.py, deliver_episode.py
- `episodes/ep01/`: script.json, kaggle_en/ (12 EN WAVs + timeline.en.json),
  coach001/002_Coach.wav (+ coach003 pending), timeline.ar.json, timeline.master.json,
  ep01_audio.m4a, ep01_video.mp4
- `assets/`: fonts (Cairo, Tajawal, **Amiri**=full Arabic), music/bed.wav, sfx/intro+outro
- `.env`: GEMINI_API_KEY (chmod 600, pulled from n8n cred)

## Open PRs (all on branch podcast-voice-synth = PR #29; #28 = script gen)
- #28 script generator + Ep1 script
- #29 voice synth + audio assembly + branding + **video** + delivery
  (both still OPEN — merge when ready; note: refs are read from `main`, so merging
  #28/#29 keeps the Kaggle raw-GitHub URLs valid for future episodes)

## Then: Phase 6 — weekly automation (not built yet)
run_episode.py orchestrator (script→coach→audio→video→deliver, fail-soft+log) →
host trigger endpoint (docker-gateway only, like the probe) → n8n weekly Schedule
Trigger → optional human-review gate before publish → Telegram notify.

## Standing reminders (long-deferred, owner's call)
- Rotate the leaked n8n MCP token.
- End-to-end test the orientation probe with a real vertical + horizontal clip.
