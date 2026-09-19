# EEC Podcast Automation — Design

> Implements `requirements.md`. Reuses existing infra: Hetzner server
> (`/opt/eec-podcast`, ffmpeg), the live n8n publishing engine
> (`RdtmJTVYU4jFFCvF`), Google Drive, and free-tier LLM/TTS. Everything runs at
> zero recurring cost, throttled to protect the 12 live containers.
>
> ⚠️ **AUDIO-ONLY PIVOT (current architecture).** The system produces a
> professional PLAIN audio episode; the **owner adds video / thumbnail / cover /
> music** and hands finished files back for publishing. Earlier revisions of this
> doc assumed Piper TTS, a Gemini-Kore Arabic coach, and in-house video assembly —
> **all three are superseded** and described here only where noted as historical.

## 1. High-level architecture (as shipped)

```
[owner trigger / n8n weekly]
   -> (1) Script Generator   (OpenRouter free LLM, brand voice + level + season memory)
   -> (2) Voice Synthesis     (OFF-SERVER on Kaggle GPU: VoiceTut ar + Chatterbox en,
                               two batches -> per-line WAVs + merge-safe manifest)
   -> (3) Audio Assembly      (server ffmpeg: manifest-driven concat + one loudnorm pass
                               -> epNN_audio_plain.m4a)   [--plain = dry voices]
   -> (4) Deliver to Drive    (upload plain audio to output/Podcast/raw-audio)
   -- owner adds music/video/cover, drops finished files back --
   -> (5a) YouTube            (publish_youtube.py forwards the owner's video into the
                               LIVE n8n engine's watched folder)
   -> (5b) Podcast platforms  (publish_feed.py maintains one RSS feed; submitted once
                               to Spotify/Apple)
```

Stages 1, 3, 4 run **unattended on the server**. Stage 2 (the GPU-heavy voice
synthesis) runs **off-server on free Kaggle GPU** because the box has no GPU and
only ~1.7 GB free RAM. n8n triggers the server-side chain and the owner-facing
publish forwarders feed the existing engine — the engine itself is never modified.

## 2. Components

### 2.1 Script Generator
- `pipeline/gen_episode.py` — compact 6-section generator targeting a TIGHT 5-10 min
  episode (default ~7 min via `--minutes`), with a duration guard, and per-section word floors
  and auto-expand; strips narration / stage directions so the output is audio-ready.
- `pipeline/llm_backend.py` — pluggable LLM. Default backend is **OpenRouter free
  tier** (`EEC_LLM_*` env: base URL + key + model + fallbacks), model Qwen with
  DeepSeek/Qwen fallbacks and model rotation. This **escaped the old Gemini daily
  quota wall**; Gemini is retained only as an optional failover.
- Output = strict JSON:
  ```json
  {
    "episode": 3, "level": "B1", "title": "...",
    "characters": ["Macal","Nour","Coach"],
    "lines": [
      {"speaker":"Macal","lang":"en","text":"...", "section":"act1"},
      {"speaker":"Coach","lang":"ar","text":"...", "section":"coach_break1"}
    ],
    "phrase_of_episode": {"en":"break the ice","ar":"يكسر الحاجز"},
    "shorts_highlight_hint": [start,end]
  }
  ```
- **Season memory:** `/opt/eec-podcast/season.json` tracks cast, story-so-far, and
  the current episode #, so episodes connect. It is advanced only by an explicit
  generation run.

### 2.2 Voice Synthesis — SPLIT ENGINE (locked 2026-09, owner-approved)
> Evaluated and REJECTED: Piper (robotic), Edge TTS (synthy), Kokoro (robotic),
> MSA-only models (SILMA/F5), and cloud TTS (quota walls). Winner = a split engine,
> each language on its best-fit open model. See `voice-casting.md`.

**Arabic (Coach + any Arabic role) → VoiceTut-TTS (Apache-2.0), on GPU:**
- Egyptian-first, 17 built-in voices. Coach = **"Sayed"** (owner-approved).
- Runs through the **shared pronunciation brain**: `pipeline/egyptian_lexicon.json`
  (`add_lexicon`) + CATT diacritizer + Whisper ASR-QA. Fix one hard colloquial word
  once → every cast voice says it correctly forever.

**English (Macal, Nour, guests) → Chatterbox Multilingual v3 (MIT), on GPU:**
- Beats ElevenLabs in ~65% of blind tests; commercial-safe.
- Each character is **cloned from a locked reference clip** (`voice-refs/`:
  `macal_ref.wav`, `nour_ref.wav`, guest refs), so voices are consistent every
  episode. Per line: `generate(text, audio_prompt_path=ref, exaggeration, cfg_weight)`.

**Why split, and why off-server:** each engine is best-in-class for its language and
free; VoiceTut and Chatterbox **clash on transformers/torch in one kernel**, so the
two passes run as **separate Kaggle notebooks** (`kaggle/synth_episode_ar.py`,
`kaggle/synth_episode_en.py`). Voices are DATA — swap a ref clip or a cast entry in
`pipeline/cast.json`; no code change. Fail-soft + crash-safe (manifest saved per line).

### 2.3 Audio Assembly (ffmpeg, manifest-driven) — `pipeline/assemble_audio.py`
- The **manifest is the single source of truth** for order (`pipeline/manifest_lib.py`;
  zero-padded `lineNNN_<speaker>.wav`, per-line status + text fingerprint). The two
  synth zips merge per-slot so they can never clobber each other.
- `--plain` (the current default use): concatenate the rendered line WAVs with
  natural micro-gaps → one **loudnorm** pass → `epNN_audio_plain.m4a` (48 kHz AAC).
  **Dry voices only — no music, no stings** (the owner adds those downstream).
- Full-branding mode also exists (music bed ducked via sidechaincompress + branded
  intro/outro stings from `assets/`); kept available but not used in the audio-only
  flow.

### 2.4 Video & branding — OWNER-OWNED (design change)
> The original plan (in-house ffmpeg video: character scenes + karaoke ASS captions
> + 9:16 shorts) is **superseded.** The owner produces the video, thumbnail, cover
> art, and music themselves for a higher-quality, on-brand result. The system's job
> ends at professional PLAIN audio. (The old `ep01_video.mp4` draft is obsolete.)

### 2.5 Delivery + Publish
- **Deliver:** `pipeline/drive_upload.py` pushes `epNN_audio_plain.m4a` into Drive
  `output/Podcast/raw-audio`. The owner edits/masters it and drops finished files into
  `for-youtube` (video) and `for-platforms` (audio-with-music).
- **YouTube — `pipeline/publish_youtube.py`:** a **forwarder** (not a re-point). It
  reads the owner's finished video from `for-youtube`, builds the exact metadata
  sidecar the live "YouTube — Publishing" workflow expects, and copies both into the
  folder that engine already watches. Fail-closed destination table; **dry-run unless
  `--confirm`.** The engine then probes 16:9 → long-form → titles/desc → upload →
  Empire English Podcast playlist. The live workflow is never edited.
- **Podcast platforms — `pipeline/publish_feed.py`:** platforms take ONE RSS feed,
  not per-episode uploads. This maintains a valid RSS 2.0 + iTunes + Podcast-namespace
  feed, hosts audio + `podcast.xml` on a public HTTPS base (R2 via rclone, or local),
  and records episodes in `feed_state.json`. The owner submits the feed URL to Spotify
  for Creators + Apple Podcasts Connect **once**; every later episode auto-pulls.

### 2.6 Orchestration — `pipeline/run_podcast.py`
- One command chains the server-side stages: **script → verify voices → assemble
  `--plain` → deliver.** Each stage is fail-soft + logged (`logs/epNN_run.log`).
- **The voice stage does NOT synthesize on the server** — it VERIFIES that
  `episodes/epNN/synth/` holds a merged manifest with **every scripted line
  rendered** (with its WAV on disk) and stops with a clear message + exit code 3 if
  the owner hasn't run/downloaded the two Kaggle batches yet. This is the guard that
  prevents assembling an incomplete episode.
- n8n **weekly Schedule Trigger** calls the server chain and reports status. An
  optional review gate can pause before deliver/publish for owner approval.

### 2.6b Voice synthesis — Kaggle BATCH pattern (solves session-expiry)
Kaggle sessions expire, so voices are "banked" in short GPU sessions, not called
live each week:
1. `run_podcast.py --script-only` (or `gen_episode.py`) writes `episodes/epNN/script.json`.
2. Owner runs the two Kaggle notebooks (`synth_episode_ar.py`, `synth_episode_en.py`),
   which fetch the script + `cast.json` + `egyptian_lexicon.json` + voice-refs from the
   repo, synthesize their language's lines, and produce per-line WAVs + a pass manifest.
3. Owner downloads/extracts both into `episodes/epNN/synth/`; the server verifies the
   merged manifest, assembles the plain audio, and delivers it.
Future optional upgrade: a paid GPU endpoint to make the voice step fully unattended.

## 3. Data & state
- `/opt/eec-podcast/season.json` — cast, current episode #, story-so-far, phrases taught.
- `/opt/eec-podcast/episodes/epNN/` — `script.json`, `synth/` (line WAVs + manifests),
  `epNN_audio_plain.m4a`, `timeline.master.json`, `logs`.
- `/opt/eec-podcast/voice-refs/` (a.k.a. `voices/refs/` on the server) — the locked
  Chatterbox reference clips. **Live asset — never prune.**
- `/opt/eec-podcast/assets/` — music bed, intro/outro stings, fonts (Amiri for Arabic).

## 4. Security & resource model
- No new internet-exposed endpoint; the server chain is invoked internally (same
  pattern as the existing probe) and n8n-gated.
- All ffmpeg runs low-priority/single-thread so the 12 live containers are never
  starved. Voice synthesis is off-server (Kaggle GPU), so it never loads the box.
- Disk watched; episodes archived after publish. Secrets in `.env` (chmod 600);
  rotation runbook in `SECURITY_ROTATION.md`.

## 5. Cost model
- **$0 recurring:** VoiceTut + Chatterbox (free, Kaggle GPU), OpenRouter free-tier LLM,
  ffmpeg, Drive + n8n (existing). No ElevenLabs, no cloud-TTS bill.
- Optional future spend: a paid GPU endpoint to make the voice step fully unattended
  (only if cadence outgrows the Kaggle-batch pattern).

## 6. Key decisions — RESOLVED (2026-09)
- **Delivery model:** audio-only — system makes PLAIN audio; owner makes video/cover/
  music. LOCKED.
- **Voice engine:** split — **VoiceTut (Arabic, Coach = Sayed) + Chatterbox (English,
  cloned refs)**, both on Kaggle GPU. LOCKED + owner-approved. (Piper/Edge/Kokoro/
  Gemini-Kore all rejected/superseded.)
- **Script LLM:** OpenRouter free-tier (Qwen + fallbacks), Gemini only as failover.
- **Assembly:** manifest-driven, merge-safe. LOCKED.
- **Publishing:** forwarder into the existing live engine (never modified) + a single
  RSS feed. LOCKED.
- Series bible (cast/premise/arc) written + locked (`series-bible.md`).
