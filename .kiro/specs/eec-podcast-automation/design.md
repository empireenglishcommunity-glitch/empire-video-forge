# EEC Podcast Automation — Design

> Implements `requirements.md`. Reuses the existing infra: Hetzner server
> (`/opt/...`, ffmpeg, Piper), n8n publishing engine (`RdtmJTVYU4jFFCvF`), the
> orientation probe, Google Drive + Gemini creds. Everything runs on the box at
> zero recurring cost, throttled to protect live containers.

## 1. High-level architecture

```
[n8n weekly trigger]
   -> (1) Script Generator  (Gemini, brand voice + level target + season memory)
   -> (2) Voice Synthesis   (Piper multi-voice, per-line WAV + timing)
   -> (3) Audio Assembly    (ffmpeg: stitch lines, music bed ducked, intro/outro)
   -> (4) Video Assembly    (ffmpeg: character scene + karaoke captions -> 16:9 mp4)
   -> (5) Deliver to Drive  (upload to watched folder)
   -> (6) Existing engine publishes (title/desc/CTA/thumbnail/playlist)
```

Stages 1–4 run on the server (a `eec-podcast` workspace + a small orchestrator).
n8n triggers and delivers; the heavy lifting is host-side (like the editor was).

## 2. Components

### 2.1 Script Generator
- Gemini (existing `googlePalmApi` cred) with a structured prompt: inputs = episode
  number, target level, season-state (characters, where the story left off), the fixed
  segment structure (R1.2). Output = strict JSON:
  ```json
  {
    "episode": 3, "level": "B1", "title": "...",
    "characters": ["Omar","Sara","Coach"],
    "lines": [
      {"speaker":"Omar","lang":"en","text":"...", "note":null},
      {"speaker":"Coach","lang":"ar","text":"...", "phrase":"break the ice"}
    ],
    "phrase_of_episode": {"en":"break the ice","ar":"يكسر الحاجز"},
    "cliffhanger":"...", "shorts_highlight":[start,end]
  }
  ```
- **Season memory:** a small JSON state file on the server (`season.json`) tracks cast +
  story progress so episodes connect. Updated after each episode.
- Guardrails: brand voice, honesty rules, level-appropriate difficulty.

### 2.2 Voice Synthesis (Piper)
- Piper installed in the podcast venv; voice models downloaded once to
  `/opt/eec-podcast/voices/` (en_US + ar). Map each character -> a voice model.
- For each line: synth WAV, measure duration -> build a timeline (start/end per line)
  used for caption sync and audio stitching.
- Coach (Arabic) uses an Arabic Piper voice; characters use distinct English voices
  (different speakers / speeds for variety).
- Fail-soft + retry per line; if Arabic voice quality is inadequate in testing, fall
  back to a chosen alternative (documented decision in tasks 1.x).

### 2.3 Audio Assembly (ffmpeg)
- Concatenate line WAVs with natural micro-gaps; normalize loudness (loudnorm).
- Music bed selected per mood, **ducked under speech** (sidechaincompress).
- Prepend intro sting / append outro (branded, gold-on-black audio ident).
- Output a single mixed WAV/AAC + the final line-timeline JSON.

### 2.4 Video Assembly (ffmpeg)
- Base: a branded 1920x1080 scene per speaker (stylized character card / illustration
  set) that switches as the speaker changes (driven by the timeline).
- **Karaoke captions:** ASS subtitles generated from the timeline — English line on
  top; Arabic translation for key/Coach lines; current line highlighted.
- Mux audio + scenes + captions -> `yuv420p`, High profile, faststart (the encoding
  rules proven earlier). Throttled with `nice`.
- Optional: cut the `shorts_highlight` span into a 9:16 highlight for discovery.

### 2.5 Delivery + Publish
- Upload the finished 16:9 mp4 to the watched Drive folder with a sidecar meta
  (episode #, level, "podcast" topic hint). The orientation probe sees 16:9 ->
  long-form -> thumbnail shows, no #Shorts. The publishing engine does the rest and
  files it under the **Empire English Podcast** playlist.
- Optional 9:16 highlight uploaded separately -> auto-Short.

### 2.6 Orchestration
- A single host script `run_episode.py` chains stages 1–5 with fail-soft + logging.
- n8n **weekly Schedule Trigger** -> calls the host (internal webhook, same pattern as
  the probe) -> `run_episode.py` -> reports status back (Telegram notify on done/fail).
- Optional review gate: pipeline can pause after video assembly and post the file for
  approval before delivering to Drive.

## 3. Data & state
- `/opt/eec-podcast/season.json` — cast, voice map, current episode #, story state.
- `/opt/eec-podcast/episodes/epNN/` — script.json, line WAVs, timeline.json, ass, mp4, log.
- `/opt/eec-podcast/assets/` — music, intro/outro stings, character scene images, fonts.

## 4. Security & resource model
- Any new host endpoint binds to the docker gateway only + ufw-restricted (like the
  probe); never internet-exposed.
- All ffmpeg/Piper runs `nice -n 15`, single/low thread, so the 10 live containers are
  never starved. Disk watched (episodes pruned/archived after publish).

## 5. Cost model
- **$0 recurring:** Piper (free), ffmpeg (free), Gemini (existing cred/free tier),
  Drive + n8n (existing). ElevenLabs is an optional paid upgrade flag only.

## 6. Key decisions (to confirm during Phase 1)
- Piper Arabic voice quality bar (test before locking; fallback options documented).
- Character scene visual style (stylized cards v1; richer later).
- Exact cast + season premise (write the "series bible" in Phase 1).
