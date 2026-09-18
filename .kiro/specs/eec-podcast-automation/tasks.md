# EEC Podcast Automation — Implementation Plan

> Implements `design.md`. **Audio-only pivot** (owner makes video/thumbnail/cover/
> music themselves; we produce professional PLAIN audio only). All $0/open-source.
> Never disrupt the 12 live containers (throttle everything; heavy synth is off-server
> on Kaggle/Colab GPU).
>
> ⚠️ This file was rewritten to match the CURRENT architecture (post-pivot). Earlier
> revisions assumed cloud TTS (Gemini Kore) + in-house video; both are superseded.

## Phase 0 — Foundations & the "series bible"
- [x] 0.1 Approve spec — requirements + design signed off.
- [x] 0.2 Series bible (`series-bible.md`): cast, Season 1 arc "Landing in Dubai",
      tone, episode template. LOCKED.
- [x] 0.3 `/opt/eec-podcast/` workspace (venv, voices, assets, episodes, logs).

## Phase 1 — Voice engine ⭐ DONE (split engine, owner-approved)
> Rejected Piper/Edge/Kokoro (robotic), cloud (quota walls), SILMA/F5 (MSA-only),
> fine-tuning (lexicon solved pronunciation without it). LOCKED on a split engine.
- [x] 1.1 **Arabic → VoiceTut-TTS** (Egyptian-first, Apache-2.0, built-in 17 voices)
      through the **shared pronunciation brain** (`egyptian_lexicon.json` + CATT
      diacritizer + Whisper ASR-QA). Fix one word → applies to ALL cast forever.
- [x] 1.2 **English → Chatterbox Multilingual v3** (beats ElevenLabs, MIT), character
      reference + expressive settings per cast member.
- [x] 1.3 **GATE PASSED:** owner approved the cast — Coach=Sayed ("amazing and very
      near"), pronunciation fixes confirmed (الجداد, متنساش). Full 17-voice Arabic
      cast + English guests locked in `pipeline/cast.json`.
- [x] 1.4 Two synth notebooks (dependency conflict → split): `kaggle/synth_episode_ar.py`
      (VoiceTut) + `kaggle/synth_episode_en.py` (Chatterbox). Install bug root-caused
      + fixed (transformers>=5.3, don't reinstall torch).

## Phase 2 — Script generator ✅ DONE (Gemini-free)
- [x] 2.1 `pipeline/gen_episode.py`: multi-act 30-min generator with word floors +
      auto-expand. Audio-ready (narration/stage-directions stripped).
- [x] 2.2 **Escaped Gemini quota** → `pipeline/llm_backend.py` pluggable backend on
      **OpenRouter free tier** (GLM-5.2 primary + DeepSeek/Qwen fallbacks, model
      rotation, HTTP-200-with-error detection). 50 req/day free.
- [x] 2.3 **GATE PASSED:** Episode 1 "The Arrival" — 276 lines, ~50 min, owner-approved.
      Promoted to `episodes/ep01/script.json`.

## Phase 3 — Deterministic assembly ✅ DONE (manifest-driven)
- [x] 3.1 `manifest_lib.py`: zero-padded line naming + **merge-safe manifest** = single
      source of truth. Two synth zips can't clobber each other; merge → 276/276,
      order-independent. Text fingerprint per line for stale detection.
- [x] 3.2 `pipeline/assemble_audio.py --plain`: lossless concat + one loudnorm pass →
      `epNN_audio_plain.m4a`. Prefers the merged manifest; falls back to script+filename.
- [x] 3.3 **GATE PASSED:** Ep1 assembled 40.6 min (276/276, 0 skipped), delivered to
      Drive `raw-audio`. Audio validated (−17.1 dB mean / −1.1 dB peak, 48k AAC).

## Phase 4 — Human-in-the-Loop review ✅ DONE
> Replaces in-house video (owner makes video). Lets the owner fix a mispronounced
> clip WITHOUT re-generating the whole episode.
- [x] 4.1 `regen_engine.py`: re-synthesizes ONE line by idx with the exact engine/
      voice/params from the manifest (lazy-loaded VoiceTut/Chatterbox).
- [x] 4.2 `streamlit_review.py`: per-line player + editable text + status badges;
      regenerate one/all pending; re-assemble via ffmpeg. `review_app_launcher.py`
      runs it next to the GPU (Colab/Kaggle). Validated end-to-end.
- [x] 4.3 `REVIEW_WORKFLOW.md`: owner runbook.

## Phase 5 — Delivery + publish integration
- [x] 5.1 `run_podcast.py` orchestrator: script → verify EN batch → coach → assemble
      `--plain` → deliver to Drive `raw-audio`.
- [x] 5.2 **YouTube forwarder** (`publish_youtube.py`): owner's finished video in
      `for-youtube` → fail-closed DESTINATIONS table → live engine (workflow
      RdtmJTVYU4jFFCvF) → long-form + playlist. Dry-run default; `--confirm` to publish.
- [x] 5.3 **RSS distribution** (`publish_feed.py`): valid RSS2.0+iTunes feed on R2
      (media.empireenglish.online). MIME fixed for .m4a. `PODCAST_DISTRIBUTION.md`.
- [ ] 5.4 ⏳ **OWNER ACTION:** drop finished video → `publish_youtube.py --confirm`;
      drop music audio → `publish_feed.py --confirm` → submit feed URL to Spotify for
      Creators + Apple Podcasts Connect (one time). Replace placeholder cover art.

## Phase 6 — Automation & scheduling
- [x] 6.1 Weekly automation trigger wired (live n8n workflow).
- [ ] 6.2 Re-point the weekly automation at the NEW synth path (currently references
      the old Gemini-Kore coach step in `run_podcast.py`). Update to VoiceTut + the
      manifest assembly, or gate on the Kaggle batch being present.
- [ ] 6.3 Optional human-review gate before publish (Streamlit review = the gate).

## Phase 7 — Hardening & scale
- [x] 7.1 Security: `.gitignore` hardened; repo history clean; `SECURITY_ROTATION.md`.
- [ ] 7.2 ⏳ **OWNER ACTION:** rotate the 3 live tokens (n8n-mcp AUTH_TOKEN, n8n API
      key, R2 keys) per `SECURITY_ROTATION.md`. None internet-exposed → low urgency.
- [x] 7.3 Disk hygiene: archived stale Ep1 draft samples; working files kept lean.
- [ ] 7.4 Produce Episode 2 end-to-end to validate the full pipeline on a 2nd episode.
- [ ] 7.5 Update README + OPERATIONS with the audio-only workflow.

## What's actually left (agent-doable)
1. **6.2** — modernize `run_podcast.py`/weekly trigger for the VoiceTut + manifest path.
2. **7.4** — generate the Episode 2 script (proves the OpenRouter generator on ep2).
3. **7.5** — README/OPERATIONS docs for the current pipeline.

## Owner-only actions (can't be done from the sandbox)
- Publish Ep1 video + audio and submit the RSS feed (needs owner's accounts).
- Rotate the 3 live tokens; replace the placeholder cover with final art.

## Execution rules
1. Never mark a task done until its artifact is produced + verified on a real episode.
2. Throttle host compute; heavy synth stays off-server (Kaggle/Colab GPU).
3. Ship progress as PRs with the artifact linked.
