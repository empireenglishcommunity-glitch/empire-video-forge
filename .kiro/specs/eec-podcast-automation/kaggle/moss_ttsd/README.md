# MOSS-TTSD (candidate second English engine) — verified working recipe

**Status:** AUDITIONED as a second candidate English TTS engine (owner directive:
2 engines per language, VoiceTut=Arabic locked, Qwen3-TTS=English locked+production,
MOSS-TTSD=English CANDIDATE for a future head-to-head).

## What's verified (real Kaggle runs, not docs)
- Installs cleanly on Kaggle after pinning `numpy==2.0.2` + `numba==0.60.0`
  (the `pip install -e .` step otherwise upgrades numpy/numba to versions that
  break Kaggle's pre-installed torch/transformers stack — same class of bug as
  every other from-source TTS install we've hit).
- Kaggle's `enable_gpu: true` gives **T4×2** (2x Tesla T4, ~15.6GB each, ~31GB
  combined) on this account — confirmed via `torch.cuda.device_count()`.
- `device_map="auto"` is BROKEN for this model: it scatters `emb_ext` (the
  extra multi-codebook audio embedding table) onto a DIFFERENT GPU than
  `language_model.embed_tokens`. The model's `get_input_embeddings()` sums
  these two tensors directly with no device move -> `RuntimeError: Expected
  all tensors to be on the same device, but found... cuda:0 and cuda:1`.
- **Fix:** build a device_map manually via `accelerate.infer_auto_device_map`
  with an ASYMMETRIC `max_memory` budget (`{0: "8GiB", 1: "13GiB"}` — GPU0
  hosts the embedding/head tables so it needs a SMALLER layer budget), then
  force `emb_ext` onto the SAME device as `embed_tokens` before loading.
  This is the ONLY module that needs manual pinning; everything else (the 36
  transformer layers) can stay wherever `infer_auto_device_map` puts it.
- Single-GPU loading (fp16 or naive bitsandbytes 8-bit) OOMs on a single T4
  (~14.5GB usable) — the model + its custom loading path needs >14.5GB even
  compressed, so T4×2 (or an equivalent multi-GPU/bigger-GPU setup) is
  REQUIRED for this model on our stack.
- **First successful generation:** 2-speaker English dialogue (interview
  panic scene, [S1]/[S2] tags, cloned from the repo's own demo reference
  clips), 11.4s wall-clock, 3.12s of 24kHz mono audio.

## Reusable pattern (see kaggle/moss_ttsd/gen_ttsd.py)
```python
config = AutoConfig.from_pretrained(MODEL_ID, trust_remote_code=True)
with init_empty_weights():
    empty_model = AutoModel.from_config(config, trust_remote_code=True, dtype=torch.bfloat16)
auto_map = infer_auto_device_map(empty_model, max_memory={0: "8GiB", 1: "13GiB"},
                                 no_split_module_classes=empty_model._no_split_modules)
embed_dev = auto_map.get("language_model.embed_tokens", 0)
for k in list(auto_map):
    if "emb_ext" in k:
        auto_map[k] = embed_dev
model = AutoModel.from_pretrained(MODEL_ID, trust_remote_code=True,
                                  attn_implementation="sdpa", dtype=torch.bfloat16,
                                  device_map=auto_map)
```

## License & languages
Apache 2.0 (verified: fetched the actual LICENSE file from OpenMOSS/MOSS-TTS on
GitHub). MOSS-TTSD's own README/model-card lists 20 languages INCLUDING Arabic
(ar) — this CONTRADICTS an earlier (wrong) note that said Arabic wasn't
supported; that earlier note was based on secondary sources, not the primary
README, and is superseded by this one. Whether MOSS-TTSD's Arabic is good
enough to matter (vs. our locked, diagnosed, UTMOS-verified VoiceTut+Essam) is
an OPEN QUESTION for the owner — not something to pursue without asking, since
VoiceTut is already production-proven for Arabic.

## Architecture difference from our current pipeline (worth the audition)
MOSS-TTSD generates a WHOLE multi-speaker EXCHANGE in one continuation-style
call (reference clips + transcripts as a prefix, then [S1]/[S2]-tagged dialogue
text) rather than rendering one speaker's line at a time and stitching, which
is what Qwen3-TTS-VoiceClone does in our pipeline today. This could plausibly
produce more natural turn-taking/overlap — the actual reason to audition it.

## Next steps (not yet done)
- Generate a full ~5min multi-character English test (the Engine Proof target)
  and score it with the same diagnostic (UTMOS/WhisperX/Praat) used for VoiceTut,
  for a fair head-to-head vs. Qwen3-TTS on the SAME stress-test script.
- Confirm license text on the actual MOSS-TTSD-v1.0 HF model card page directly
  (only the GitHub code LICENSE file was fetched with certainty so far).
