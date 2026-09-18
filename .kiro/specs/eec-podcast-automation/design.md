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
    "characters": ["Macal","Nour","Coach"],
    "lines": [
      {"speaker":"Macal","lang":"en","text":"...", "note":null},
      {"speaker":"Coach","lang":"ar","text":"...", "phrase":"break the ice"}
    ],
    "phrase_of_episode": {"en":"break the ice","ar":"يكسر الحاجز"},
    "cliffhanger":"...", "shorts_highlight":[start,end]
  }
  ```
- **Season memory:** a small JSON state file on the server (`season.json`) tracks cast +
  story progress so episodes connect. Updated after each episode.
- Guardrails: brand voice, honesty rules, level-appropriate difficulty.

### 2.2 Voice Synthesis — SPLIT ENGINE (locked 2026-09, owner-approved)
> We evaluated Piper (robotic), Edge TTS (synthy), Kokoro (robotic), and cloud
> options. Winner = a split engine, each language on its best-fit engine. See
> `voice-casting.md` for the full brief. This is the OFFICIAL voice design.

**English cast (Macal, Nour, guests) -> Chatterbox (Resemble AI), on GPU:**
- Chatterbox beats ElevenLabs in ~65% of blind tests; MIT-licensed (commercial-safe).
- It needs a GPU, which our server lacks -> run it on **Kaggle free GPU in BATCH**
  (see 2.6b). Each character voice is **cloned from a locked reference clip**, so
  voices are consistent across every episode.
- **Locked references** (`voice-refs/`): `macal_ref.wav` = the OWNER'S OWN VOICE
  (cloned); `nour_ref.wav` = Emma (Edge neural, warm US female); guest refs by role.
- Per line: `model.generate(text, audio_prompt_path=ref, exaggeration, cfg_weight)`
  -> WAV; measure duration -> timeline for caption sync + stitching.

**Arabic Coach -> Gemini TTS (`gemini-2.5-flash-preview-tts`), voice "Kore":**
- Runs via the existing `googlePalmApi` cred (no new account). Natural Egyptian
  Arabic, controllable style ("warm encouraging Egyptian coach"). Free tier is
  tight but the Coach is only ~1/3 of lines, so it fits; pace + retry on 429.

**Why split:** English quality (Chatterbox) + Arabic quality (Gemini) + $0, and
neither engine's free limit is a bottleneck because the load is divided.
- Fail-soft + retry per line. Voices are DATA (swap a ref clip to change a voice;
  no code change). Speaker->voice map lives in `season.json`.

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
- A single host script `run_episode.py` chains the server-side stages (script,
  Coach voice, audio assembly, video, deliver) with fail-soft + logging.
- n8n **weekly Schedule Trigger** -> calls the host (internal webhook, same pattern as
  the probe) -> `run_episode.py` -> reports status back (Telegram notify on done/fail).
- Optional review gate: pipeline can pause after video assembly and post the file for
  approval before delivering to Drive.

### 2.6b English voice — Kaggle BATCH pattern (solves session-expiry)
The English voices (Chatterbox) need GPU, so they are generated on Kaggle in a
**decoupled batch**, NOT called live each week (Kaggle sessions expire):
1. `gen_script.py` produces script.json for the next N episodes -> pushed to the repo
   (or Drive).
2. **Owner runs the Kaggle notebooks** (`kaggle/synth_episode_en.py` for English
   Chatterbox, `kaggle/synth_episode_ar.py` for Arabic VoiceTut) periodically (e.g.
   once per few weeks): they read the pending scripts + the locked reference clips /
   Egyptian lexicon, synthesize each character's lines, and push the per-line WAVs +
   manifest back to Drive/GitHub.
3. The **server pipeline** then picks up the ready audio (both languages produced on
   Kaggle now), assembles audio+video, and auto-publishes on schedule.
This keeps publishing fully automated while GPU voice is "banked" in short sessions.
Future upgrade path (optional): a paid GPU endpoint (or Chatterbox turbo) to make
even the English step fully unattended.

## 3. Data & state
- `/opt/eec-podcast/season.json` — cast, voice map, current episode #, story state.
- `/opt/eec-podcast/episodes/epNN/` — script.json, line WAVs, timeline.json, ass, mp4, log.
- `/opt/eec-podcast/assets/` — music, intro/outro stings, character scene images, fonts.

## 4. Security & resource model
- Any new host endpoint binds to the docker gateway only + ufw-restricted (like the
  probe); never internet-exposed.
- All ffmpeg runs `nice -n 15`, single/low thread, so the 10+ live containers are
  never starved. Disk watched (episodes pruned/archived after publish). Chatterbox
  runs on Kaggle GPU (off-server), so it never loads the box.

## 5. Cost model
- **$0 recurring:** Chatterbox (free, on Kaggle GPU), Gemini Coach (existing cred,
  free tier), ffmpeg (free), Drive + n8n (existing). No ElevenLabs, no cloud TTS bill.
- Optional future spend: a paid GPU endpoint to make the English step fully unattended
  (only if weekly cadence outgrows the Kaggle-batch pattern).

## 6. Key decisions — RESOLVED (2026-09)
- Voice engine: **split — Chatterbox (English, Kaggle GPU, cloned voices) + Gemini
  Kore (Arabic Coach).** LOCKED. (Piper/Edge/Kokoro rejected as robotic/synthy.)
- Cast: **Macal = owner's cloned voice; Nour = Emma clone; Coach = Gemini Kore;
  guests = Chatterbox clones by role.** LOCKED + owner-approved.
- Series bible (cast/premise/arc) written + locked (`series-bible.md`).
- Still open: character scene VISUAL style (stylized cards v1 -> Phase 4 gate).
