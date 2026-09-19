# Qwen3-TTS — engine verification (Phase B, task B.1)

> Verifies design.md §2 assumptions (V1–V6) against the **official** source before we
> build. Sources: [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) (official repo,
> Apache-2.0, ~13.5k★), the [technical report](https://arxiv.org/abs/2601.15621), and the
> HF model collection. Verified this session. _Content rephrased for licensing compliance._

## Timeline note
Qwen3-TTS was **open-sourced 2026-01-22** (0.6B + 1.7B, on the Qwen3-TTS-Tokenizer-12Hz).
Our design doc was written ahead of release with forward-looking assumptions — this doc
reconciles them to the shipped reality. **Every assumption held; a few specifics updated.**

## V1 — Model + license ✅ (confirmed, specifics updated)
- **License: Apache-2.0** — commercial-safe. This is the core reason we chose it (we
  rejected Breeze TTS 2 / Fish S2 Pro for non-commercial terms). ✅
- **The 1.7B tier is NOT one model — it's a FAMILY of task-specific models** (this is the
  key correction to our design). Released weights:
  | Model | Purpose | Instruct control |
  |---|---|---|
  | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | invent a voice from a text description | ✅ |
  | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | **3-sec voice CLONE** from a ref clip; also FT base | — |
  | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | 9 built-in premium timbres + style control | ✅ |
  | (same three at `0.6B`) | smaller/faster | varies |
  - **We use TWO of them:** `-VoiceDesign` (Phase B audition) + `-Base` (Phase C/D clone).
- **Variant choice:** **1.7B** (design/quality) — fits the Kaggle T4 (see V5). 0.6B is the
  fallback if VRAM/speed require it.

## V2 — Voice creation WITHOUT a reference clip ✅
- `Qwen3-TTS-12Hz-1.7B-VoiceDesign` + `model.generate_voice_design(text, language, instruct)`
  where `instruct` is a **natural-language voice description**. No reference audio needed. ✅
- This is exactly our Phase-B audition mechanism (invent candidate voices from text).

## V3 — Accent control ✅ (expressible)
- The model does natural-language control over **timbre, emotion, prosody, age, accent**
  via the `instruct` string, and adapts tone/rate/emotion to text semantics.
- **English is a first-class supported language** (10 major languages: ZH, **EN**, JA, KO,
  DE, FR, RU, PT, ES, IT). Accents (American / Indian / Egyptian-accented English) are
  expressed through the `instruct` description.
- **Macal's 3-stage arc** → expressed as **3 distinct `instruct` descriptions** (early L2 →
  confident near-native), each captured as its own canonical reference. The official
  "Voice Design then Clone" example literally demonstrates a nervous→confident young male
  ("gaining confidence… vowels still tighten when nervous") — direct precedent for the arc.
- ⚠️ **To de-risk in the audition (B.4–B.6):** accent *fidelity* for Egyptian-accented and
  Indian English is the one thing only the owner's ears can confirm. Design is sound; the
  audition exists to prove it. Fallback stays Kokoro (design note).

## V4 — Voice identity = Option B (VoiceDesign → VoiceClone) ✅ officially supported
- The repo documents our exact workflow as **"Voice Design then Clone"**:
  1. `-VoiceDesign` synthesizes a short reference clip matching the persona,
  2. `clone_model.create_voice_clone_prompt(ref_audio, ref_text)` builds a **reusable prompt**,
  3. `-Base` `generate_voice_clone(text, language, voice_clone_prompt=…)` renders new lines
     from that locked identity.
- This **locks pitch/timbre across all 10 episodes** and avoids re-parsing a description
  each call (the drift risk that made us pick Option B). Reusable prompt = faster on T4. ✅
- **Macal:** save **3 canonical refs** (one per stage); the episode's stage selects the ref.
- Clone API details: `ref_audio` accepts file path / URL / base64 / `(numpy, sr)` tuple;
  `ref_text` is the transcript of the ref (improves quality). `x_vector_only_mode=True`
  drops `ref_text` (speaker embedding only) but lowers quality — we keep `ref_text`.
- **Reproducibility (the B.1 open question):** using a **fixed reference clip + reusable
  `voice_clone_prompt`** is the mechanism that yields run-to-run consistency (identity comes
  from the fixed ref, not a re-parsed description). Final proof is empirical — confirm on
  the audition takes in B.6 and on Ep1 in Phase C (GATE C).

## V5 — Kaggle install recipe ✅ (T4-viable, FA2 caveat resolved)
- **Package:** `pip install -U qwen-tts` (PyPI); pulls runtime deps. Load via
  `from qwen_tts import Qwen3TTSModel`.
- **Load:** `Qwen3TTSModel.from_pretrained(<hf-id>, device_map="cuda:0", dtype=torch.bfloat16, attn_implementation=…)`.
- ⚠️ **FlashAttention 2 caveat (important for Kaggle):** the README *recommends* FA2, but
  **FA2 needs Ampere+ (SM80). The Kaggle free T4 is Turing (SM75) → FA2 will NOT build/run.**
  - **Fix:** load with **`attn_implementation="sdpa"`** (PyTorch scaled-dot-product
    attention; works on Turing) — or `"eager"`. Do **not** `pip install flash-attn` on T4.
  - Evidence it runs FA2-free: `andimarafioti/faster-qwen3-tts` ("No Flash Attention, no
    vLLM, no Triton"); community ComfyUI node lists it as optional.
- **VRAM (1.7B):** community guidance = **8 GB min / 12 GB recommended**. Kaggle T4 = **16 GB**
  → comfortably fits **one** 1.7B model. NOTE: `-VoiceDesign` and `-Base` are *separate*
  models — **load them sequentially, not together** (same discipline as the current EN/AR
  sequential loading), or the audition step designs-then-frees before the clone step.
- **bf16** on T4: T4 supports bf16 compute (slower than fp16 but fine); if any op complains,
  fall back to `dtype=torch.float16`. Verify in the first Kaggle run.
- Weights auto-download by HF id on first load (or pre-download via `huggingface-cli`).

## V6 — Output format / rate ✅ (verify exact SR on first run)
- API returns `(wavs, sr)`; write with `soundfile.sf.write(path, wavs[0], sr)`.
- Our assembly chain normalizes every clip to **24 kHz mono** anyway
  (`assemble_audio.py` resamples with `-ar 24000 -ac 1`), so whatever `sr` Qwen emits is
  handled — but **record the actual `sr`** on the first Kaggle run and note it here (the
  12 Hz tokenizer implies a modern SR, commonly 24 kHz; confirm empirically).

## Net impact on the design / plan
- **No blocking surprises.** Option B is officially supported and documented.
- **Design updates to fold in (B.2 / C.2):**
  1. Two models, loaded sequentially: `-VoiceDesign` (audition) + `-Base` (clone).
  2. Kaggle install = `pip install -U qwen-tts`, **`attn_implementation="sdpa"`**, **no
     flash-attn**, 1.7B on the T4, models loaded one at a time.
  3. Macal arc = 3 `instruct` descriptions → 3 canonical refs.
- **The single real risk is accent *fidelity*** (Egyptian/Indian English), which the
  audition (B.4–B.6) is designed to prove with the owner's ears. Fallback: Kokoro.

## API cheat-sheet (for B.4 audition + C.2 production notebooks)
```python
from qwen_tts import Qwen3TTSModel
import torch, soundfile as sf

# --- Phase B: DESIGN a candidate voice from a text persona ---
dm = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa")
wavs, sr = dm.generate_voice_design(text=<season1 line>, language="English",
                                    instruct=<voice description>)
# save winning take as the canonical ref WAV  ->  voice-refs/<char>.wav

# --- Phase C/D: CLONE the locked identity for every line ---
cm = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa")
prompt = cm.create_voice_clone_prompt(ref_audio="voice-refs/<char>.wav", ref_text=<ref transcript>)
wavs, sr = cm.generate_voice_clone(text=<line>, language="English", voice_clone_prompt=prompt)
sf.write(out, wavs[0], sr)
```
