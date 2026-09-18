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
- [x] 1.3 Build the synth steps:
      - `kaggle/synth_english.py` (Kaggle/GPU batch): reads committed script.json + refs
        (raw GitHub) -> per-line WAV via Chatterbox voice cloning. Speaker map: recurring
        chars explicit, any `guest_*` id resolved to the guest library by gender heuristic.
        Emits `timeline.en.json`. Fail-soft per line (retry once, skip, never abort batch).
      - `pipeline/synth_coach.py` (server): Coach (Arabic) lines -> Gemini Kore (existing
        cred), 429/5xx backoff, **RESUMABLE** (keeps already-good WAVs so a re-run only
        fills gaps). Emits `timeline.ar.json`. **TESTED on real Ep1** — produced valid
        24kHz WAVs. [R3.3, R3.5]
      - ⚠️ **Quota reality (measured):** free-tier Gemini TTS =
        `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, **limit 10 requests/DAY**
        (not per-minute). Ep1 has 3 Coach lines; a weekly cadence fits easily, but the
        Coach step must be resumable across days (done) and paced. Options if we scale:
        rotate to `gemini-2.5-flash-lite`/other free model, or a tiny paid bump.

## Phase 2 — Script generator ✅ DONE (PR #28, owner-approved)
- [x] 2.1 Build `pipeline/gen_script.py`: Gemini prompt (brand voice + level + season
      memory + fixed segment structure) -> validated script.json. Fail-soft (validate +
      retry once, never emit a broken script). Model env-overridable
      (`EEC_SCRIPT_MODEL`, default `gemini-3.6-flash`). [R1.1, R1.2, R2]
- [x] 2.2 `season.json` state read/update (cast + voice map + story continuity +
      phrases-taught). [R1.4]
- [x] 2.3 **GATE PASSED:** Episode 1 "The Arrival" (A2) generated + owner-approved.
      Committed at `episodes/ep01/script.json`. [R2.4, R8.2]

## Phase 3 — Audio assembly
- [ ] 3.1 Build `assemble_audio.py`: stitch line WAVs + micro-gaps, loudnorm,
      music bed ducked (sidechaincompress), intro/outro sting -> mixed audio. [R3, R4.3]
- [ ] 3.2 Source royalty-free music + create the branded intro/outro sting. [R4.3]
- [ ] 3.3 Render Episode 1 AUDIO end-to-end; owner listens. [gate]

## Phase 4 — Video assembly
- [x] 4.1 Branded 16:9 frame (v1 = typographic scene cards): brand near-black + subtle
      radial, per-SPEAKER accent-dot badge (name + role) that switches by timeline. [R4.1]
- [x] 4.2 Build `assemble_video.py`: looped static branded bg (cheap) + libass ASS
      captions (EN centered white / Coach AR large gold, RTL) with per-line CHUNKING so
      long Coach breaks appear progressively; phrase-of-episode lower-third; title card
      on the intro. Mux -> H.264 High, yuv420p, +faststart, nice -19. [R4.1,R4.2]
      - ⚠️ **Arabic font:** MUST use **Amiri** (fonts-hosny-amiri, full presentation-form
        coverage). Cairo/Tajawal subsets render hamza/alef combos as tofu boxes. Installed
        Amiri on the box + copied to assets/fonts. Latin stays Cairo.
      - ⚠️ **Perf:** never regenerate the bg per-frame (gradients+blend was slow + spiked
        load, risking live containers) — render bg ONCE as PNG, loop it, burn captions.
- [ ] 4.3 Render Episode 1 VIDEO (16:9) — DONE, delivered to Drive as 'VIDEO draft'.
      **GATE: awaiting owner visual sign-off.** [R8.3]
- [ ] 4.4 Optional: auto-cut the 9:16 shorts highlight from `shorts_highlight`. [R4.4]

## Phase 5 — Delivery + publish integration
- [x] 5.0 Build `deliver_episode.py`: writes the `<basename>_metadata.json` sidecar
      (Arabic-first seed title + caption from phrase/story, topic=conversation,
      format=long/is_long fail-soft flags, podcast=true playlist hint) and uploads
      video+sidecar to Drive. SAFETY: requires --confirm to hit the LIVE watched
      folder; without it stages to a non-watched folder. **Dry-run verified** on Ep1.
- [x] 5.0a Verified live engine: workflow `RdtmJTVYU4jFFCvF` "YouTube — Publishing"
      is **active**, Drive Trigger polls **01-EEC-only** (`19WOAX2ME-...WDOS`) every
      minute (NOT the output parent — review uploads there are safe/non-triggering).
- [ ] 5.1 **GATE: owner go/no-go** to deliver Ep1 to the LIVE folder (real YouTube
      publish). On go: run deliver_episode.py --confirm; confirm probe->long-form,
      publish OK, lands in **Empire English Podcast** playlist. [R5]
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
