#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Yalla Fluent" — pluggable, MULTI-ENGINE LLM backend for scripting.

Script-writing is just an LLM call, and we deliberately run it on TWO NAMED
WRITER ENGINES (owner directive: "we need 2 engines instead of saying one
engine... trying our best to make every engine the best" — same philosophy as
the two TTS engines, VoiceTut + Qwen3-TTS/MOSS-TTSD, applied to text):

  * "deepseek" — DeepSeek (api.deepseek.com, deepseek-chat/-reasoner). Our
                 primary writer to date; strong reasoning + long-context plotting.
  * "qwen"     — Qwen3 text (via OpenRouter, qwen/qwen3-max by default). A genuinely
                 separate model family, used as (a) an independent second writer for
                 blind A/B script comparison, and (b) the ADVERSARIAL DIALOGUE-POLISH
                 pass — a different model actively hunting the first writer's clichés/
                 stiff lines catches things a model can't see in its own prose.
                 Reuses the existing OPENROUTER_KEY (already in .env) — zero new infra.

Legacy generic backends (kept, unnamed/env-selected, for existing callers):
  1. "openai"  — any OpenAI-compatible endpoint. EEC_LLM_BASE_URL + EEC_LLM_KEY +
                 EEC_LLM_MODEL (+EEC_LLM_FALLBACKS). This is currently DeepSeek.
  2. "local"   — a local HuggingFace model on a GPU (Kaggle). Set EEC_LLM_MODEL.
  3. "gemini"  — old path, optional failover only.

Two ways to call:
  chat(prompt, temperature)                    -> unnamed/env-resolved (back-compat)
  chat(prompt, temperature, engine="qwen")      -> explicit NAMED engine (deepseek|qwen)
  available_engines() -> {"deepseek": bool, "qwen": bool}   (credentials present?)
"""
import os, json, urllib.request, urllib.error

BACKEND = os.environ.get("EEC_LLM_BACKEND", "auto")

# sensible defaults
DEFAULT_OPENAI_MODEL = os.environ.get("EEC_LLM_MODEL", "qwen/qwen3-32b")  # provider-named
DEFAULT_LOCAL_MODEL = os.environ.get("EEC_LLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")

# ---- named engine 1: DeepSeek (explicit, regardless of EEC_LLM_* env state) ----
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_FALLBACKS = os.environ.get("DEEPSEEK_FALLBACKS", "deepseek-reasoner")

# ---- named engine 2: Qwen3 text (via OpenRouter — same key as OPENROUTER_KEY) ----
QWEN_TEXT_BASE_URL = os.environ.get("QWEN_TEXT_BASE_URL", "https://openrouter.ai/api/v1")
QWEN_TEXT_MODEL = os.environ.get("QWEN_TEXT_MODEL", "qwen/qwen3-max")
QWEN_TEXT_FALLBACKS = os.environ.get("QWEN_TEXT_FALLBACKS", "qwen/qwen3-235b-a22b-2507")


# ---- backend 1: OpenAI-compatible free API (OpenRouter/Groq/Cerebras/...) --
# Comma-separated model list -> automatic failover (if one :free 429s, try next).
def _openai_models():
    m = os.environ.get("EEC_LLM_MODEL", DEFAULT_OPENAI_MODEL)
    extra = os.environ.get("EEC_LLM_FALLBACKS", "")  # comma-separated
    models = [m] + [x.strip() for x in extra.split(",") if x.strip()]
    return models


def _one_call(base, key, model, prompt, temperature):
    body = {"model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": int(os.environ.get("EEC_LLM_MAXTOK", "1500")),
            "reasoning": {"enabled": False}}  # skip slow "thinking" on reasoning models
    req = urllib.request.Request(base + "/chat/completions",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key,
                                          "X-Title": "EEC Two Worlds"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:   # fail fast -> rotate model
        data = json.loads(r.read().decode("utf-8"))
    # OpenRouter can return HTTP 200 with an {"error":...} body (upstream 429 etc.)
    if "error" in data and "choices" not in data:
        code = (data["error"] or {}).get("code", 0)
        raise urllib.error.HTTPError(base, code or 429,
                                     str(data["error"])[:200], None, None)
    return data["choices"][0]["message"]["content"]


def _chat_openai(prompt, temperature):
    """Transient 429/5xx on free models are per-MINUTE/capacity, not daily.
    Rotate across the model list AND retry with short backoff, so the caller
    rarely sees a failure. ~6 rounds over the models."""
    base = os.environ["EEC_LLM_BASE_URL"].rstrip("/")
    key = os.environ["EEC_LLM_KEY"]
    return _rotate_and_call(base, key, _openai_models(), prompt, temperature)


def _rotate_and_call(base, key, models, prompt, temperature):
    """Shared retry/rotation loop used by every named + generic OpenAI-compatible
    engine: try each model in the list, rotate on 429/502/503, backoff between rounds."""
    import time
    last_err = None
    for rnd in range(6):
        for model in models:
            try:
                return _one_call(base, key, model, prompt, temperature)
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code in (429, 502, 503):
                    continue          # try next model immediately
                raise
            except Exception as e:
                last_err = e
                continue
        time.sleep(min(8 * (rnd + 1), 40))  # all models busy -> short wait, retry round
    raise last_err if last_err else RuntimeError("all models busy")


# ---- NAMED engines: deterministic, explicit — NOT affected by EEC_LLM_* env ----
def _chat_deepseek(prompt, temperature):
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("EEC_LLM_KEY")
    if not key:
        raise RuntimeError("DeepSeek unavailable: set DEEPSEEK_API_KEY (or EEC_LLM_KEY)")
    models = [DEEPSEEK_MODEL] + [m.strip() for m in DEEPSEEK_FALLBACKS.split(",") if m.strip()]
    return _rotate_and_call(DEEPSEEK_BASE_URL.rstrip("/"), key, models, prompt, temperature)


def _chat_qwen_text(prompt, temperature):
    key = os.environ.get("OPENROUTER_KEY") or os.environ.get("QWEN_TEXT_KEY")
    if not key:
        raise RuntimeError("Qwen-text unavailable: set OPENROUTER_KEY (or QWEN_TEXT_KEY)")
    models = [QWEN_TEXT_MODEL] + [m.strip() for m in QWEN_TEXT_FALLBACKS.split(",") if m.strip()]
    return _rotate_and_call(QWEN_TEXT_BASE_URL.rstrip("/"), key, models, prompt, temperature)


NAMED_ENGINES = {"deepseek": _chat_deepseek, "qwen": _chat_qwen_text}


def available_engines():
    """Which NAMED engines have live credentials right now (no network call)."""
    return {
        "deepseek": bool(os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("EEC_LLM_KEY")),
        "qwen": bool(os.environ.get("OPENROUTER_KEY") or os.environ.get("QWEN_TEXT_KEY")),
    }


# ---- backend 2: local Qwen on GPU (Kaggle) — truly unlimited ---------------
_LOCAL = {}
def _chat_local(prompt, temperature):
    if "pipe" not in _LOCAL:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        model_id = os.environ.get("EEC_LLM_MODEL", DEFAULT_LOCAL_MODEL)
        tok = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id, torch_dtype="auto", device_map="auto")
        _LOCAL["tok"], _LOCAL["model"] = tok, model
        _LOCAL["pipe"] = True
    tok, model = _LOCAL["tok"], _LOCAL["model"]
    msgs = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tok(text, return_tensors="pt").to(model.device)
    out = model.generate(**inputs, max_new_tokens=2048,
                         temperature=max(temperature, 0.1), do_sample=True)
    gen = out[0][inputs["input_ids"].shape[1]:]
    return tok.decode(gen, skip_special_tokens=True)


# ---- backend 3: gemini (legacy failover) ----------------------------------
def _chat_gemini(prompt, temperature):
    key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("EEC_SCRIPT_MODEL", "gemini-3.6-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature,
                                 "response_mime_type": "application/json"}}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _resolve():
    if BACKEND != "auto":
        return BACKEND
    if os.environ.get("EEC_LLM_BASE_URL") and os.environ.get("EEC_LLM_KEY"):
        return "openai"
    if os.environ.get("EEC_FORCE_LOCAL"):
        return "local"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return "local"


def chat(prompt, temperature=0.95, engine=None):
    """engine=None            -> legacy env-resolved backend (unchanged behavior).
    engine="deepseek"|"qwen"  -> explicit NAMED writer engine, independent of
                                 EEC_LLM_* env state (used for the two-writer /
                                 adversarial-polish workflow)."""
    if engine is not None:
        if engine not in NAMED_ENGINES:
            raise ValueError(f"unknown engine {engine!r}; choose from {list(NAMED_ENGINES)}")
        return NAMED_ENGINES[engine](prompt, temperature)
    b = _resolve()
    return {"openai": _chat_openai, "local": _chat_local, "gemini": _chat_gemini}[b](prompt, temperature)


def which():
    return _resolve()


if __name__ == "__main__":
    print("backend:", which())
    print("named engines available:", available_engines())
