# Two Worlds — Script Engine: escape Gemini quota (decision)

> We solved the VOICE with open source (no quota). But scripts still depend on
> Gemini's free tier (10-ish/day) — a recurring headache. Same fix: replace Gemini
> with a free, open, quota-free LLM. Script-writing is just an LLM task, and open
> LLMs in 2026 are excellent (far more mature than open TTS).

## The two quota-free paths (we use BOTH for resilience)

### Path A — Run Qwen on the Kaggle GPU (truly unlimited) ⭐ primary
- **Qwen** is the consistent #1 open LLM for ARABIC + multilingual, Apache-2.0.
- A **quantized Qwen (~14GB, e.g. Qwen 27B FP4/INT4, or a fast MoE ~3B-active)**
  fits a single 16GB T4; Kaggle also offers **2x T4**. No quota, ever.
- HUGE bonus: scripts + voices generate in the SAME Kaggle workflow we already use.
  One place, no external dependency, unlimited.
- Runs via vLLM or transformers (4-bit). Unsloth/quantized builds make it easy.

### Path B — Free-API failover gateway (no GPU needed) — backup / server-side
- Card-free, OpenAI-compatible free tiers: **Groq, Cerebras, OpenRouter, NVIDIA
  NIM, Mistral, Cloudflare** — many serve Qwen/Llama/Gemma free.
- Open gateways (freelm / free-llm-hub) POOL these behind ONE endpoint with
  automatic key rotation + cross-provider failover: if one rate-limits, it rolls
  to the next. Effectively unlimited via rotation, and runs on the SERVER (light,
  no GPU) — good for the quota-patient background generation we already built.

## Decision
- **Primary: Qwen on Kaggle GPU** for episode generation (unlimited, Arabic-strong,
  same batch as voices). Model: a T4-fittable Qwen instruct (quantized).
- **Backup: free-API failover** (Groq/Cerebras/OpenRouter serving Qwen) for
  server-side/background generation without a GPU session.
- **Retire Gemini** for scripts (keep only as one more failover key if handy).
- Everything stays $0, commercial-safe (Qwen Apache-2.0), quota-free.

## What changes in our code
- gen_episode.py: swap the `call_gemini` function for a pluggable `call_llm` that
  targets (a) a local Qwen on Kaggle, or (b) an OpenAI-compatible free endpoint.
  Same prompts, same act-by-act + resumable design — just a different backend.
- Add a Kaggle "author + synth" notebook: Qwen writes the episode, then VoiceTut/
  Chatterbox voice it — all in one unlimited GPU session.

## Next
1. Build the pluggable LLM backend (local-Qwen + free-API), keep prompts identical.
2. Kaggle test: Qwen writes an Act of Ep1 -> confirm Arabic+English creative quality
   matches/beats Gemini. Owner gate on the writing quality.
3. Wire it as the default script engine; Gemini demoted to optional failover.

_Verified Sep 2026: Qwen = top open Arabic LLM (Apache-2.0); quantized fits T4;
Groq/Cerebras/OpenRouter = card-free OpenAI-compatible free tiers with failover._
