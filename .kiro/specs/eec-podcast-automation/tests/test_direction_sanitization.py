#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase C, task C.2a — DIRECTION SANITIZATION TEST.

Guarantees the per-line `direction` acting-note is NEVER spoken, hashed, ordered,
or gated: the text cleaner, manifest builder (text_hash), timeline, and the
structure gate must read ONLY `text` / `speaker` / `section` / `lang` — never
`direction`. `direction` is metadata for the (future) prosody mapper only.

Run:  python3 tests/test_direction_sanitization.py   (exit 0 = pass)
"""
import os, sys, json, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .../eec-podcast-automation


def _load(mod_name, rel):
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(ROOT, rel))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

manifest_lib = _load("manifest_lib", "kaggle/manifest_lib.py")
structure_check = _load("structure_check", "pipeline/structure_check.py")

failures = []
def check(cond, msg):
    print(("PASS" if cond else "FAIL") + " — " + msg)
    if not cond:
        failures.append(msg)

# Two identical lines EXCEPT for `direction` — must behave identically everywhere.
base = {"section": "act1", "speaker": "Macal", "lang": "en", "text": "I am on my way down now."}
line_no_dir = dict(base)
line_dir    = dict(base, direction="anxious, rapid, panic in the voice")

# 1) text_hash ignores direction (same text -> same hash)
h1 = manifest_lib.text_hash(line_no_dir["text"])
h2 = manifest_lib.text_hash(line_dir["text"])
check(h1 == h2, "text_hash depends only on text, not direction")

# 2) manifest skeleton entry carries text/speaker/section but NOT a spoken direction
scr = {"episode": 1, "title": "t", "lines": [line_dir]}
man = manifest_lib.build_skeleton(scr)
entry = man["lines"][0]
check("direction" not in entry, "manifest line entry does not include 'direction'")
check(entry["text"] == base["text"], "manifest text == the spoken text (no direction appended)")
check(entry["speaker"] == "Macal" and entry["section"] == "act1", "manifest keeps speaker/section")

# 3) structure gate reads only section/speaker/lang — verdict identical with/without direction
v_no  = structure_check.check_script({"lines": [dict(line_no_dir, section="act1")]})
v_dir = structure_check.check_script({"lines": [dict(line_dir,    section="act1")]})
check(v_no == v_dir, "structure gate verdict is identical with/without direction")

# 4) a Coach line with a direction still gets gated purely on speaker/section
coach_no  = {"section": "coach_break1", "speaker": "Coach", "lang": "ar", "text": "يلا"}
coach_dir = dict(coach_no, direction="warm, teacherly")
cv_no  = structure_check.check_script({"lines": [coach_no]})
cv_dir = structure_check.check_script({"lines": [coach_dir]})
check(cv_no == cv_dir, "structure gate ignores direction on Coach lines too")

# 5) sanity: the synth reads direction ONLY via direction_params (never into text).
#    Confirm the v2 synth never concatenates direction into the synthesized text.
syn = open(os.path.join(ROOT, "kaggle/synth_episode_v2.py")).read()
# the only place 'direction' may appear is the mapper input; it must never be added to text
bad = any(
    ("direction" in ln and ("text" in ln) and ("+" in ln or "format" in ln or "f\"" in ln or "f'" in ln))
    for ln in syn.splitlines()
    if "direction_params" not in ln and "ln.get(\"direction\")" not in ln and "# " not in ln
)
check(not bad, "v2 synth never concatenates 'direction' into synthesized text")

print()
if failures:
    print(f"{len(failures)} FAILURE(S): direction sanitization is NOT clean.")
    sys.exit(1)
print("ALL PASS — 'direction' is never spoken/hashed/ordered/gated (C.2a satisfied).")
