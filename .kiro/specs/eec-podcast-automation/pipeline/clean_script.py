#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — script cleaner (audio-ready).

The story models sometimes write stage directions / narration inside a line,
e.g. "*I walk out and close the door.* Nour! Good to see you." For an AUDIO
drama we must NOT read stage directions aloud — only spoken dialogue. This
strips *...* narration and any leading/trailing prose, drops lines that become
empty (pure narration), and normalizes whitespace. Idempotent + safe to re-run.

Usage: python3 clean_script.py <script.json> [--out <out.json>]
"""
import sys, json, re, argparse


def clean_text(t):
    t = t or ""
    # remove *...* stage-direction spans
    t = re.sub(r"\*[^*]*\*", " ", t)
    # remove any stray lone asterisks
    t = t.replace("*", " ")
    # remove bracketed stage directions [like this] / (like this) if they are the
    # whole segment (keep parentheses that are part of speech—only strip if they
    # look like directions: start with a verb-ish cue). Conservative: strip [ ... ].
    t = re.sub(r"\[[^\]]*\]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    s = json.load(open(args.script, encoding="utf-8"))
    kept, dropped = [], 0
    for l in s.get("lines", []):
        ct = clean_text(l.get("text", ""))
        if not ct:                    # was pure narration -> drop
            dropped += 1
            continue
        l["text"] = ct
        kept.append(l)
    s["lines"] = kept
    s["word_count"] = sum(len(l["text"].split()) for l in kept)

    out = args.out or args.script
    json.dump(s, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"cleaned: {len(kept)} lines kept, {dropped} narration-only dropped, "
          f"{s['word_count']} words (~{round(s['word_count']/150,1)} min) -> {out}")


if __name__ == "__main__":
    main()
