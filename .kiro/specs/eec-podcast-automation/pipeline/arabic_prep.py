#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — ARABIC TEXT FRONT-END for Chatterbox (the missing pipeline).

Chatterbox is a world-class voice model but a RAW one: it has no Arabic text
front-end, so if you feed it bare undiacritized Arabic (with Latin-script English
mixed in) it GUESSES the vowels and chokes on the English -> mispronunciation.
Great Arabic TTS (Gemini, ElevenLabs, SESTEK) all run this front-end internally.
This module rebuilds it so Chatterbox only has to *perform*, not *guess*.

Pipeline (per Coach line):
  1. SEGMENT by language — split Arabic runs from English runs so each is spoken
     in its NATIVE language (the universal code-switching best practice). Bonus:
     the taught English phrase comes out in crisp native English (better teaching).
  2. DIACRITIZE each Arabic run (add tashkeel) with CATT (SOTA, Apache-2.0). This
     is THE fix for mispronunciation — it resolves which vowels to speak.
  3. NORMALIZE numbers/symbols in Arabic runs to spoken Arabic words.

Output: an ordered list of {"lang": "ar"|"en", "text": <ready-for-TTS>} segments.
The Kaggle notebook then generates each segment with the right language_id +
cfg_weight=0 (Resemble's cross-lingual recommendation) and stitches them.

CATT is optional at import time: if it's not installed (e.g. prototyping on a box
without it), diacritization is skipped with a clear warning — segmentation +
normalization still run, and the Kaggle side installs CATT for the real run.
"""
import re

# --- optional CATT diacritizer (loaded lazily; installed on Kaggle) --------
_CATT = None
_CATT_TRIED = False


def _get_catt():
    global _CATT, _CATT_TRIED
    if _CATT_TRIED:
        return _CATT
    _CATT_TRIED = True
    try:
        from catt_tashkeel import CATTEncoderDecoder  # ED = best accuracy
        _CATT = CATTEncoderDecoder()
        print("[arabic_prep] CATT diacritizer loaded (ED, best accuracy)")
    except Exception as e:
        _CATT = None
        print(f"[arabic_prep] WARNING: CATT not available ({str(e)[:80]}). "
              "Diacritization SKIPPED — install 'catt-tashkeel' for correct vowels.")
    return _CATT


# --- 1. code-switch segmentation ------------------------------------------
_LATIN = re.compile(r"[A-Za-z]")
# a run is either "contains latin letters" (english) or "no latin" (arabic/other)
_RUN = re.compile(r"[A-Za-z][A-Za-z0-9\s'’\-\.\,!\?:]*|[^A-Za-z]+")
_EDGE_PUNge = " '\"’‘`.,:;!?()[]{}«»…-\n\t"


def segment_by_language(text):
    """Return [(lang, clean_text), ...] merging adjacent same-language runs."""
    raw = []
    for m in _RUN.finditer(text):
        seg = m.group(0)
        if not seg.strip():
            continue
        lang = "en" if _LATIN.search(seg) else "ar"
        raw.append((lang, seg))
    # merge adjacent same-language runs
    merged = []
    for lang, seg in raw:
        if merged and merged[-1][0] == lang:
            merged[-1][1] += seg
        else:
            merged.append([lang, seg])
    # trim stray edge punctuation/quotes that belong to the boundary
    out = []
    for lang, seg in merged:
        s = seg.strip().strip(_EDGE_PUNge).strip()
        if s:
            out.append((lang, s))
    return out


# --- 2. Arabic diacritization (CATT) --------------------------------------
def diacritize_ar(text):
    catt = _get_catt()
    if not catt:
        return text
    try:
        # CATT batch API returns a list; keep only the diacritized string
        res = catt.do_tashkeel_batch([text], verbose=False)
        return res[0] if isinstance(res, list) and res else text
    except Exception as e:
        print(f"[arabic_prep] diacritize failed, using raw: {str(e)[:80]}")
        return text


# --- 3. Arabic number/symbol normalization (spoken forms) ------------------
_AR_ONES = ["صفر", "واحد", "اتنين", "تلاتة", "أربعة", "خمسة", "ستة", "سبعة",
            "تمانية", "تسعة", "عشرة"]
_SYMBOLS = {
    "%": " في المية ",
    "&": " و ",
    "+": " زائد ",
    "=": " يساوي ",
    "$": " دولار ",
    "@": " أت ",
}


def _num_to_ar_words(n):
    # small, dialect-friendly mapping for the common small numbers a story uses;
    # larger numbers are rare in dialogue — read digit-groups if needed.
    try:
        v = int(n)
    except Exception:
        return n
    if 0 <= v <= 10:
        return _AR_ONES[v]
    # fall back to digit-by-digit for anything bigger (clear + safe)
    return " ".join(_AR_ONES[int(d)] for d in str(v))


def normalize_ar(text):
    for sym, word in _SYMBOLS.items():
        text = text.replace(sym, word)
    # drop stray straight/smart quotes left over from code-switch boundaries
    text = re.sub(r"['\"’‘`]", "", text)
    # replace standalone integer tokens with spoken words
    text = re.sub(r"\b\d+\b", lambda m: _num_to_ar_words(m.group(0)), text)
    # collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


# --- top-level: prepare one Coach line for TTS ----------------------------
def prepare(text, diacritize=True):
    """Turn one raw Coach line into ordered TTS-ready segments.

    Returns: [{"lang":"ar","text":...}, {"lang":"en","text":...}, ...]
    """
    segments = []
    for lang, seg in segment_by_language(text):
        if lang == "ar":
            s = normalize_ar(seg)
            if diacritize:
                s = diacritize_ar(s)
            segments.append({"lang": "ar", "text": s})
        else:
            # English spoken as-is (native English segment) — trim stray quotes
            segments.append({"lang": "en", "text": seg})
    return segments


if __name__ == "__main__":
    import sys, json
    demo = ("أهلاً بيك في أول حلقة من Two Worlds! خد بالك من الجملة دي: "
            "'How long does it take?' يعني بياخد وقت قد إيه؟ الرقم 3 مهم.")
    text = sys.argv[1] if len(sys.argv) > 1 else demo
    for i, s in enumerate(prepare(text, diacritize=False)):  # no CATT in demo
        print(f"{i+1}. [{s['lang']}] {s['text']}")
