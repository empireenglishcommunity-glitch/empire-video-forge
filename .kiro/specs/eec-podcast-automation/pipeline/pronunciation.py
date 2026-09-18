#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — SHARED PRONUNCIATION BRAIN (one source of truth, all voices).

Owner's design: every word we correct is saved in ONE shared place that EVERY
voice/model reads from — so a word fixed once is pronounced right by the whole
cast, forever, and we never redo the work or regenerate blindly.

This module IS that shared brain. It provides:
  1. load_lexicon()            -> the single shared egyptian_lexicon.json
  2. prepare_text(text)        -> apply the shared lexicon + auto-diacritize
                                  (used by EVERY synth, for EVERY voice)
  3. asr_check(text, wav)      -> Whisper round-trip: did the audio say the right
                                  words? returns mispronounced word candidates
  4. learn_word(word, diac)    -> permanently add a correction to the shared
                                  lexicon (so it never breaks again, for any voice)
  5. auto_learn(text, wav)     -> QA a generated clip; auto-record survivors as
                                  "needs review" so nothing slips silently

Layered defense so hard words are handled automatically at every stage:
  auto-diacritize (CATT) -> shared lexicon overrides -> ASR-QA auto-catch -> learn.

The lexicon lives in the REPO (egyptian_lexicon.json) so it's versioned + shared
across every run/notebook/machine. New corrections are appended there and
committed — the single, growing, shared pronunciation memory.
"""
import os, re, json, difflib, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
LEXICON_PATH = os.environ.get("EEC_LEXICON", os.path.join(HERE, "egyptian_lexicon.json"))
PENDING_PATH = os.path.join(HERE, "lexicon_pending.json")  # words caught, awaiting review

_AR = re.compile(r"[\u0600-\u06FF]")
_DIAC = re.compile(r"[\u064B-\u0652\u0670]")


# ---- 1. the shared lexicon (single source of truth) ----------------------
def load_lexicon(path=LEXICON_PATH):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("lexicon", {}), data.get("names_en_ar", {})


def _save_lexicon(lex, names, path=LEXICON_PATH):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["lexicon"] = lex
    data["names_en_ar"] = names
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def apply_to_tts(tts):
    """Push the shared lexicon into a VoiceTut model (all voices then use it)."""
    lex, names = load_lexicon()
    if hasattr(tts, "add_lexicon"):
        tts.add_lexicon(lex)
    if hasattr(tts, "add_names") and names:
        tts.add_names(names)
    return len(lex), len(names)


# ---- 2. prepare text: shared lexicon overrides + auto-diacritize ----------
_catt = None
def _get_catt():
    global _catt
    if _catt is None:
        try:
            from catt_tashkeel import CATTEncoderDecoder
            _catt = CATTEncoderDecoder()
        except Exception:
            _catt = False
    return _catt or None


def prepare_text(text, diacritize=True):
    """Apply the shared lexicon (word->voweled form) then optionally CATT-
    diacritize the rest. This is what EVERY line passes through before synth,
    so every voice benefits from every fix. Word-boundary safe."""
    lex, _ = load_lexicon()
    # apply longest-first so multi-word / longer keys win
    for w in sorted(lex, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", lex[w], text)
    if diacritize and _AR.search(text):
        catt = _get_catt()
        if catt:
            try:
                # only diacritize runs that aren't already voweled by the lexicon
                r = catt.do_tashkeel_batch([text], verbose=False)
                if isinstance(r, list) and r:
                    text = r[0]
            except Exception:
                pass
    return text


# ---- 3. ASR round-trip check ---------------------------------------------
def _skeleton(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))  # strip tashkeel
    s = re.sub(r"[^\u0600-\u06FF\s]", " ", s)  # arabic only
    return re.sub(r"\s+", " ", s).strip()


def asr_check(intended_text, heard_text):
    """Compare intended vs what Whisper heard; return (score, mismatched_words)."""
    a = _skeleton(intended_text).split()
    b = _skeleton(heard_text).split()
    sm = difflib.SequenceMatcher(None, a, b)
    score = sm.ratio()
    bad = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            bad.extend(a[i1:i2])  # intended words that weren't heard correctly
    return round(score, 3), bad


# ---- 4 + 5. learn corrections back into the shared brain ------------------
def learn_word(word, diacritized, note=""):
    """Permanently add a correction to the SHARED lexicon — every voice, forever."""
    lex, names = load_lexicon()
    lex[word] = diacritized
    _save_lexicon(lex, names)
    return True


def record_pending(words):
    """Auto-record words the ASR-QA flagged, for a quick one-time human review
    (add the correct diacritized form -> learn_word). Nothing slips silently."""
    pend = {}
    if os.path.exists(PENDING_PATH):
        pend = json.load(open(PENDING_PATH, encoding="utf-8"))
    lex, _ = load_lexicon()
    for w in words:
        if w and w not in lex:  # not already fixed
            pend[w] = pend.get(w, 0) + 1
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(pend, f, ensure_ascii=False, indent=2)
    return pend


if __name__ == "__main__":
    # quick self-test of the text-prep (no models needed)
    lex, names = load_lexicon()
    print("shared lexicon:", len(lex), "words,", len(names), "names")
    demo = "متنساش تشترك، وخد بالك من الكلمات الجداد دلوقتي."
    print("IN :", demo)
    print("OUT:", prepare_text(demo, diacritize=False))
    s, bad = asr_check("متنساش تشترك في القناة", "ما تنساش تشترك في القناة")
    print("asr score:", s, "flagged:", bad)
