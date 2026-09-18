#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — pluggable LLM backend (escape Gemini quota).

Script-writing is just an LLM call. This module abstracts WHICH model writes,
so the story generator no longer depends on Gemini's daily free cap. Three
backends, selected by env EEC_LLM_BACKEND (or auto):

  1. "openai"  — any OpenAI-compatible endpoint (Groq/Cerebras/OpenRouter/etc.,
                 all card-free free tiers serving Qwen/Llama/Gemma). Set
                 EEC_LLM_BASE_URL + EEC_LLM_KEY + EEC_LLM_MODEL. Runs anywhere
                 (server, no GPU). Rotate keys/providers for effectively unlimited.
  2. "local"   — a local HuggingFace model (Qwen instruct) on a GPU (Kaggle).
                 Truly unlimited; same workflow as our TTS. Set EEC_LLM_MODEL to
                 a HF id (default a T4-fittable Qwen).
  3. "gemini"  — the old path, kept ONLY as an optional failover.

All backends expose one function: chat(prompt, temperature) -> text.
Qwen (Apache-2.0) is our default model — the top open LLM for Arabic + multilingual.
"""
import os, json, urllib.request, urllib.error

BACKEND = os.environ.get("EEC_LLM_BACKEND", "auto")

# sensible defaults
DEFAULT_OPENAI_MODEL = os.environ.get("EEC_LLM_MODEL", "qwen/qwen3-32b")  # provider-named
DEFAULT_LOCAL_MODEL = os.environ.get("EEC_LLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")


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
    import time
    base = os.environ["EEC_LLM_BASE_URL"].rstrip("/")
    key = os.environ["EEC_LLM_KEY"]
    models = _openai_models()
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
    raise last_err if last_err else RuntimeError("all free models busy")


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


def chat(prompt, temperature=0.95):
    b = _resolve()
    return {"openai": _chat_openai, "local": _chat_local, "gemini": _chat_gemini}[b](prompt, temperature)


def which():
    return _resolve()


if __name__ == "__main__":
    print("backend:", which())
