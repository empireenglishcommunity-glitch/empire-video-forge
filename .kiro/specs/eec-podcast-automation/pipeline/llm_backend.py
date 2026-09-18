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


# ---- backend 1: OpenAI-compatible free API (Groq/Cerebras/OpenRouter/...) --
def _chat_openai(prompt, temperature):
    base = os.environ["EEC_LLM_BASE_URL"].rstrip("/")   # e.g. https://api.groq.com/openai/v1
    key = os.environ["EEC_LLM_KEY"]
    model = os.environ.get("EEC_LLM_MODEL", DEFAULT_OPENAI_MODEL)
    body = {"model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature}
    req = urllib.request.Request(base + "/chat/completions",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


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
