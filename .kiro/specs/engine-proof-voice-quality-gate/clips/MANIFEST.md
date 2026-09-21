# Engine Proof — Phase C generation manifest

Generated 2026-09-21, all three clips rendered autonomously via Kaggle (push/poll/pull).
Audio itself lives on the server (`/tmp/*.m4a`) and will be delivered to Drive in Phase E —
not committed to git (binary audio, large files). This manifest is the record of what ran.

## 1. Arabic proof clip (VoiceTut) — `ar_proof_clip.m4a`
- Kernel: `empireenglish/yalla-fluent-proof-arabic`
- Script: `scripts/arabic_stress_test.json` (96 lines, 663 words)
- Cast: Mahmoud→Essam (locked, gs1.5, atempo 0.80) | Esraa→Esraa (Phase A winner, gs1.5,
  atempo 0.85) | Nadia→Asmaa (Phase A 2nd place, gs1.5, atempo 0.85)
- Result: **96/96 lines rendered, 333.99s (~5.6 min)**
- Pipeline: natural text (no injected pauses, FIX-007 discipline) → VoiceTut synth →
  ffmpeg atempo post-processing → concat with 0.35s gaps

## 2. English proof clip — Qwen3-TTS (production engine) — `en_qwen_proof_clip.m4a`
- Kernel: `empireenglish/yalla-fluent-proof-english-qwen`
- Script: `scripts/english_stress_test.json` (66 lines, 765 words) — IDENTICAL to #3 below
- Cast: Nour, Tarek, Qureshi — existing locked `voice-refs/*.wav` via
  `create_voice_clone_prompt` + `generate_voice_clone` (per-line clone-and-stitch, our
  current production path)
- Result: **66/66 lines rendered, 282.8s (~4.7 min)**

## 3. English proof clip — MOSS-TTSD (candidate engine) — `en_ttsd_proof_clip.m4a`
- Kernel: `empireenglish/yalla-fluent-proof-english-ttsd`
- Script: `scripts/english_stress_test.json` — SAME script and SAME 3 voice-refs as #2,
  for a fair head-to-head
- Cast: Nour→S1, Tarek→S2, Qureshi→S3 (native multi-speaker tags), reference audio =
  the SAME `voice-refs/*.wav` files (no new voice assets needed)
- Method: chunked continuation (MOSS-TTSD generates a whole multi-speaker exchange per
  call, not per-line) — 7 chunks of ~10 lines each, using the custom device_map fix from
  `kaggle/moss_ttsd/gen_ttsd.py` (T4x2, asymmetric max_memory, emb_ext pinned to
  embed_tokens's device)
- Result: **7/7 chunks rendered, 270.8s (~4.5 min)**

## Next: Phase D — objective diagnostic on all 3, then Phase E — owner ear-test
