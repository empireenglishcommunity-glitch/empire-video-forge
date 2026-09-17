# EEC Podcast Automation — Implementation Plan

> Implements `design.md`. Phased, each task tested on a REAL episode artifact before
> moving on. Reuses the hardened publishing engine + orientation probe. $0 recurring.
> Build order matters: prove voice quality first (the biggest unknown), then assembly,
> then automation. Never disrupt the 10 live containers (throttle everything).

## Phase 0 — Foundations & the "series bible"
- [x] 0.1 Approve spec — requirements + design signed off. [R8]
- [x] 0.2 Write the **series bible** (`series-bible.md`): cast (Macal/Nour/Coach +
      guests), Season 1 arc "Landing in Dubai", tone, episode template. LOCKED. [R1.3,R1.4]
- [x] 0.3 Create `/opt/eec-podcast/` workspace (venv, voices, assets, episodes, logs).

## Phase 1 — Voice engine ⭐ DONE (split engine, owner-approved)
> Evaluated Piper/Edge/Kokoro (robotic) and cloud (account/quota walls). LOCKED on a
> split engine — see `voice-casting.md` + design 2.2/2.6b.
- [x] 1.1 Voice engine chosen: **Chatterbox (English, Kaggle GPU, cloned voices) +
      Gemini Kore (Arabic Coach)**. Chatterbox beats ElevenLabs in blind tests, MIT.
- [x] 1.2 **GATE PASSED:** owner heard + approved the cloned cast — Macal = owner's own
      voice; Nour = Emma clone; Coach = Gemini Kore. Locked reference clips in
      `voice-refs/`. Kaggle notebook `kaggle/chatterbox_cast.py` proven working.
- [ ] 1.3 Build the synth steps:
      - `synth_english.py` (Kaggle/GPU batch): script.json + refs -> per-line WAV via
        Chatterbox voice cloning (per-character ref map). Batch pattern (design 2.6b).
      - `synth_coach.py` (server): Coach lines -> Gemini Kore (existing cred),
        retry/pace on 429.
      - Both emit per-line WAV + timeline.json. Fail-soft per line. [R3.3, R3.5]

## Phase 2 — Script generator
- [ ] 2.1 Build `gen_script.py`: Gemini prompt (brand voice + level + season memory +
      segment structure) -> validated script.json. [R1.1, R1.2, R2]
- [ ] 2.2 Implement `season.json` state read/update (cast + story continuity). [R1.4]
- [ ] 2.3 Generate + review **Episode 1 script** on the real template. Owner approves
      pedagogical value + voice. [R2.4, R8.2]

## Phase 3 — Audio assembly
- [ ] 3.1 Build `assemble_audio.py`: stitch line WAVs + micro-gaps, loudnorm,
      music bed ducked (sidechaincompress), intro/outro sting -> mixed audio. [R3, R4.3]
- [ ] 3.2 Source royalty-free music + create the branded intro/outro sting. [R4.3]
- [ ] 3.3 Render Episode 1 AUDIO end-to-end; owner listens. [gate]

## Phase 4 — Video assembly
- [ ] 4.1 Design character scene cards + branded 16:9 frame (stylized v1). [R4.1]
- [ ] 4.2 Build `assemble_video.py`: scenes switch by speaker (timeline) + karaoke ASS
      captions (EN top, AR for key lines) + mux, yuv420p/High/faststart, nice. [R4.1,R4.2]
- [ ] 4.3 Render Episode 1 VIDEO (16:9). **GATE: owner visual sign-off.** [R8.3]
- [ ] 4.4 Optional: auto-cut the 9:16 shorts highlight from `shorts_highlight`. [R4.4]

## Phase 5 — Delivery + publish integration
- [ ] 5.1 Deliver Episode 1 to the watched Drive folder + sidecar meta (episode/level/
      podcast). Confirm orientation probe -> long-form, engine publishes correctly,
      lands in the **Empire English Podcast** playlist. [R5]
- [ ] 5.2 End-to-end dry run: one manual trigger -> published episode, verified. [R6.2]

## Phase 6 — Automation & scheduling
- [ ] 6.1 `run_episode.py` orchestrator: chains 1->5, fail-soft, logging, Telegram
      notify on done/fail (reuse error workflow). [R6.2, R7.2]
- [ ] 6.2 Host trigger endpoint (docker-gateway-only, ufw-restricted) like the probe. [R7.3]
- [ ] 6.3 n8n **weekly Schedule Trigger** -> calls the endpoint -> full auto episode. [R6.1]
- [ ] 6.4 Optional human-review gate before publish (config flag). [R6.3]

## Phase 7 — Hardening & scale
- [ ] 7.1 Disk hygiene: archive/prune episode working files after publish. [R7.3]
- [ ] 7.2 Resource guardrails: confirm throttling never starves live containers. [R4.5,R7.3]
- [ ] 7.3 Run 3 episodes to validate consistency (voices, visuals, quality bar). [R8]
- [ ] 7.4 Update docs (README + OPERATIONS) with the podcast workflow + how to tune.

## Execution rules
1. Phases in order; within a phase, tasks in order.
2. Voice quality (1.2), Ep1 script (2.3), audio (3.3), video (4.3) are GATES — owner
   signs off before proceeding.
3. Never mark a task done until its artifact is produced + verified on a real episode.
4. Throttle all host compute; never disrupt live containers.
5. Ship progress as PRs with the artifact (sample/clip) linked.
