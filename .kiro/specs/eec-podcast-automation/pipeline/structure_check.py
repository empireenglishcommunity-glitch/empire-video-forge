#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — SCRIPT STRUCTURE VALIDATOR (the "never ship a messy episode" gate).

Root-cause fix for the "messy audio" problem: the audio was assembled in perfect
mechanical order, but the SCRIPT interleaved Coach (Arabic) teaching lines *inside*
live English story scenes — which sounds like language whiplash on playback.

This module is the single source of truth for the LOCKED structure rule
(see series-bible.md §10). It is a PURE function with no side effects, imported by
BOTH the generator (post-generation gate) and the assembler (pre-assembly gate), so
a violating script is caught the moment it's created and can never be assembled.

The rule:
  STORY sections  = cold_open, act1..act4      (in-world scene, English)
  COACH sections  = coach_intro, coach_break1..3, coach_outro  (teaching, Arabic)
  1. cold_open is pure story — no Coach line, no Arabic.
  2. Coach speaks ONLY in COACH sections (never inside a STORY section).
  3. Story characters speak ONLY in STORY sections (no leak into COACH sections).
  4. A COACH break must follow the STORY scene it explains (canonical order),
     never split a scene.

Usage (CLI):
  python3 structure_check.py path/to/script.json
  -> prints violations (with exact idx) and exits 0 (clean) or 1 (violations).
"""
import json
import sys

STORY_SECTIONS = {"cold_open", "act1", "act2", "act3", "act4"}
COACH_SECTIONS = {"coach_intro", "coach_break1", "coach_break2", "coach_break3",
                  "coach_outro"}
COACH_SPEAKER = "Coach"

# Canonical section sequence (scene → its breakdown). Episodes may OMIT trailing
# acts/breaks, but the sections that ARE present must appear in this relative order.
CANONICAL_ORDER = [
    "cold_open", "coach_intro",
    "act1", "coach_break1",
    "act2", "coach_break2",
    "act3", "coach_break3",
    "act4", "coach_outro",
]


def check_script(script):
    """Validate a script dict against the LOCKED structure rule.

    Returns a list of violation dicts: {"idx", "section", "speaker", "lang",
    "rule", "detail"}. An empty list means the script is structurally clean.
    idx is the 1-based GLOBAL line index (matches the synth/assembly index).
    """
    violations = []
    lines = script.get("lines", [])

    for i, ln in enumerate(lines, 1):
        sec = ln.get("section") or ""
        spk = ln.get("speaker") or ""
        lang = ln.get("lang") or ""

        # Rule 1: cold_open is pure story — no Coach, no Arabic.
        if sec == "cold_open" and (spk == COACH_SPEAKER or lang == "ar"):
            violations.append(_v(i, sec, spk, lang, "cold_open_pure_story",
                                 "cold_open must be pure in-world English scene "
                                 "(no Coach / no Arabic)"))
            continue

        # Rule 2: Coach speaks only in COACH sections.
        if sec in STORY_SECTIONS and (spk == COACH_SPEAKER or lang == "ar"):
            violations.append(_v(i, sec, spk, lang, "coach_in_story",
                                 f"Coach/Arabic line inside STORY section '{sec}' "
                                 "— move it to the adjacent coach section"))
            continue

        # Rule 3: story characters don't leak into COACH sections.
        if sec in COACH_SECTIONS and spk != COACH_SPEAKER:
            violations.append(_v(i, sec, spk, lang, "story_in_coach",
                                 f"non-Coach speaker '{spk}' inside COACH section "
                                 f"'{sec}'"))
            continue

        # Unknown section label (typo / new section not in the rule).
        if sec and sec not in STORY_SECTIONS and sec not in COACH_SECTIONS:
            violations.append(_v(i, sec, spk, lang, "unknown_section",
                                 f"section '{sec}' is not a known STORY or COACH "
                                 "section"))

    # Rule 4: canonical relative section order (of the sections actually used).
    seen = []
    for ln in lines:
        s = ln.get("section")
        if s and (not seen or seen[-1] != s):
            seen.append(s)
    # collapse repeats, keep first appearance order
    first_order = []
    for s in seen:
        if s not in first_order:
            first_order.append(s)
    rank = {s: idx for idx, s in enumerate(CANONICAL_ORDER)}
    known = [s for s in first_order if s in rank]
    for a, b in zip(known, known[1:]):
        if rank[a] > rank[b]:
            violations.append(_v(None, b, None, None, "section_order",
                                 f"section '{b}' appears after '{a}', violating the "
                                 "canonical scene→breakdown order"))

    return violations


def _v(idx, section, speaker, lang, rule, detail):
    return {"idx": idx, "section": section, "speaker": speaker, "lang": lang,
            "rule": rule, "detail": detail}


def format_report(violations):
    """Human-readable multi-line report string for logs / CLI / gate messages."""
    if not violations:
        return "structure OK — story/teaching separation clean"
    out = [f"STRUCTURE VIOLATIONS: {len(violations)}"]
    for v in violations:
        loc = f"idx {v['idx']:>4}" if v["idx"] is not None else "section"
        out.append(f"  [{loc}] {v['rule']}: {v['detail']}"
                   + (f"  ({v['speaker']}/{v['lang']}, section={v['section']})"
                      if v["idx"] is not None else ""))
    return "\n".join(out)


def is_clean(script):
    return len(check_script(script)) == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: structure_check.py <script.json>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        script = json.load(f)
    vs = check_script(script)
    print(format_report(vs))
    sys.exit(0 if not vs else 1)
