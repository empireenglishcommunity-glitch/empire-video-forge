# Two Worlds — Operations Runbook

> The single, authoritative "how do I actually run an episode" guide for the EEC
> "Two Worlds" podcast. Reflects the **audio-only, split-engine, manifest-driven**
> system as deployed (Sep 2026). For the *why* behind the design, see `design.md`;
> for the creative rules, `series-bible.md`.

## TL;DR — what the system does
The system turns an episode idea into a **professional PLAIN audio file** (clean
voices, no music/branding). **You** add music, video, thumbnail, and cover art,
then publish. The system never publishes on its own — it only produces + delivers
plain audio and gives you convenience forwarders for the publish step.

```
script (server, LLM)  →  voices (OFF-SERVER, Kaggle GPU ×2)  →  assemble plain audio
(server, ffmpeg)  →  deliver to Drive raw-audio  →  [you: music/video/cover]  →  publish
```

## Voice cast & synth (Phase C — CURRENT, 3 engines)
The locked cast (`pipeline/cast.json` v2) uses **three engines**, routed **by speaker**
(not by language) in `kaggle/synth_episode_v2.py`:
- **VoiceTut** — **Mahmoud** (Coach, voice `Omar`, Arabic) **and Macal** (voice `Abdullah`,
  **raw English** → real Egyptian accent, no transliteration). Both in the `PASS=voicetut` run.
- **Qwen3-TTS VoiceClone** — **Nour + guests + Ravi**, each cloned from its frozen
  `voice-refs/*.wav` (Option B, no drift). The `PASS=qwen` run.
- Run `synth_episode_v2.py` **twice** on Kaggle (PASS=voicetut, then PASS=qwen), download
  both zips, drop their contents into `episodes/epNN/synth/`; the assembler merges them.
- **Chatterbox is RETIRED** (old notebooks in `kaggle/_archive/`, not run).
- Macal's 3 "stages" are a **language** progression (fluency/confidence in the script),
  **not** an accent shift — his accent stays Egyptian all season. No per-stage voice refs.

## Ground rules (do not break these)
- **Never synth voices on the server.** No GPU + only ~1.7 GB free RAM. Voices are
  made on **Kaggle free GPU** — `synth_episode_v2.py` run twice (VoiceTut + Qwen passes).
- **Never disrupt the 12 live containers.** All server ffmpeg is low-priority; heavy
  work is off-box.
- **The manifest is the source of truth**, not filenames. Assembly refuses to run
  until every scripted line is `rendered`.
- **The automation is currently INACTIVE by design** — no weekly job fires until you
  activate it (see §6). Keep it off until Ep1 is posted.

---

## 0. Where everything lives
| Thing | Location |
|-------|----------|
| Server home | `/opt/eec-podcast` (SSH: the `eec-editor` host = `root@77.42.43.250`) |
| Server scripts | `/opt/eec-podcast/bin/` (mirror of repo `pipeline/`) |
| Episode data | `/opt/eec-podcast/episodes/epNN/` |
| Season memory | `/opt/eec-podcast/season.json` |
| Canonical voice refs (LIVE — never delete) | repo `voice-refs/*.wav` (Qwen clone sources: Nour/guests/Ravi) |
| Branding assets | `/opt/eec-podcast/assets/` (music/, sfx/, fonts/) |
| Secrets | `/opt/eec-podcast/.env` (chmod 600) |
| Kaggle notebooks | repo `.kiro/specs/eec-podcast-automation/kaggle/` |
| Trigger service | `/opt/eec-podcast-trigger/eec_podcast_trigger.py` (systemd: `eec-podcast-trigger.service`) |
| n8n weekly workflow | `Two Worlds — Weekly Podcast Generate` (id `IRVBwGGJBF1SpePA`, **inactive**) |
| Drive: plain audio out | `output/Podcast/raw-audio` (`1GLKvNq3LAKZ6BaACIMvYeUSJomFErav0`) |
| Drive: your finished video | `output/Podcast/for-youtube` |
| Drive: your audio-with-music | `output/Podcast/for-platforms` |

---

## 1. Generate the script (server)
```bash
ssh eec-editor
cd /opt/eec-podcast
# generate ONLY the short script for episode N (compact 6-section, ~7 min)
venv/bin/python3 bin/gen_episode.py --episode N --out episodes/epNN/script.json
#   --minutes 7     target length (band 5-10; default 7)
#   --no-advance    when REGENERATING an existing episode (don't bump season.json)
# (run_podcast.py --episode N --script-only also works for the full chain)
```
- Writes `episodes/epNN/script.json` — a TIGHT 5-10 min episode (compact 6 sections:
  cold_open, coach_intro, act1, coach_break1, act2, coach_outro).
- Uses the OpenRouter free-tier backend (`EEC_LLM_*` in `.env`); no Gemini quota.
- **Two gates run automatically:** the story/teaching structure rule (series-bible §10)
  and the 5-10 min duration band — generation FAILS (won't save) if either is violated,
  unless `--force`.
- Advancing `season.json` happens here (skip with `--no-advance` when regenerating).
- **Review the short script** before spending GPU time synthesizing it — it's small
  enough to read end-to-end.

## 2. Make the voices (Kaggle GPU — two notebooks)
VoiceTut (Arabic) and Chatterbox (English) clash in one kernel, so run **two
separate** Kaggle notebooks. Each fetches the script + `cast.json` +
`egyptian_lexicon.json` + voice-refs from the repo automatically.

1. Kaggle → New Notebook → **GPU T4**, **Internet ON**.
2. Paste **all** of `kaggle/synth_episode_ar.py` → Run All → download the `epNN/`
   output (line WAVs + `manifest.ar.json`).
3. Repeat with `kaggle/synth_episode_en.py` → download (`manifest.en.json` + WAVs).
4. Put **both** downloads into `episodes/epNN/synth/` on the server (the WAVs and
   both `manifest.*.json` land in the same folder).

> The two manifests are merge-safe: ar-pass owns the Arabic lines, en-pass owns the
> English lines; merged they must total 100% `rendered`.

## 3. Assemble + deliver (server, one command)
```bash
cd /opt/eec-podcast
venv/bin/python3 bin/run_podcast.py --episode N
```
This runs: verify voices (merged manifest must be fully rendered) → assemble
`--plain` → deliver `epNN_audio_plain.m4a` to Drive `raw-audio`.
- To assemble **without** uploading: add `--skip-deliver`.
- Exit codes: **0** delivered · **3** waiting on the Kaggle voice batches (manifest
  incomplete) · **1** a stage failed. Details in `logs/epNN_run.log`.

## 4. Fix a mispronounced Arabic word (permanent)
1. Add the word (fully-voweled Egyptian form) to `pipeline/egyptian_lexicon.json`
   (push to repo so Kaggle fetches it).
2. Re-run `kaggle/synth_episode_ar.py` for the episode (re-synth affected lines).
3. Re-download into `episodes/epNN/synth/`, re-run `run_podcast.py --episode N`.
One fix → every cast voice says it correctly, forever. `synth_arabic_qa.py`
auto-flags candidate words during synth.

## 5. Publish (owner-driven; the system only forwards)
After you master the audio and make the video/cover:
- **YouTube:** drop your finished video (filename contains `EpNN`) into Drive
  `for-youtube`, then:
  ```bash
  venv/bin/python3 bin/publish_youtube.py            # DRY RUN (shows what it'd do)
  venv/bin/python3 bin/publish_youtube.py --confirm  # forward → live engine publishes
  ```
  It forwards into the existing "YouTube — Publishing" n8n engine (never modifies it).
- **Podcast platforms (Spotify/Apple):** drop audio-with-music (filename contains
  `EpNN`) into Drive `for-platforms`, then:
  ```bash
  venv/bin/python3 bin/publish_feed.py --dry-run
  venv/bin/python3 bin/publish_feed.py --host rclone --remote r2pod:... \
      --public-base https://media.empireenglish.online/... --cover <cover> --confirm
  ```
  Generates/updates one RSS feed. **Submit the feed URL to Spotify for Creators +
  Apple Podcasts Connect ONCE**; every later episode auto-pulls.

## 6. Weekly automation (leave OFF until you want it)
- The n8n workflow `Two Worlds — Weekly Podcast Generate` (id `IRVBwGGJBF1SpePA`)
  is **inactive**. When active, every Monday 09:00 it calls the trigger service
  → generates + delivers the next episode's plain audio → Telegram notifies you.
- The trigger service (`172.18.0.1:8904`, internal only) runs `run_podcast.py` and
  reports status. It has a **no-skip-ahead guard**: it refuses to generate episode N
  if an earlier episode never produced plain audio (override with `{"force":true}`).
- **To activate later:** n8n UI → open the workflow → toggle Active. Don't do this
  until Ep1 is posted and you actually want a weekly cadence.
- Health/manual check:
  ```bash
  curl -s http://172.18.0.1:8904/health
  curl -s -X POST -H 'Content-Type: application/json' -d '{"episode":2}' \
      http://172.18.0.1:8904/run
  ```

## 7. Safety / troubleshooting
- **"waiting" (exit 3):** the Kaggle batches aren't fully downloaded into
  `episodes/epNN/synth/`. Check the merged manifest has 0 pending/failed.
- **Server disk:** watch `df -h /` (kept lean; archive episodes after publish).
- **Secrets rotation:** see `SECURITY_ROTATION.md` (n8n-mcp token, n8n API key, R2).
- **Never** commit `.env`, keys, or `rclone.conf` (`.gitignore` already blocks them).
