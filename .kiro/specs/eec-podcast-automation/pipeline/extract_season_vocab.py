#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W2a — SEASON ARABIC VOCAB EXTRACTOR (Egyptian pronunciation factory, stage 1).

Pulls every UNIQUE bare Arabic word spoken by the Coach (Mahmoud) across all
episode scripts, ranked by frequency, minus what the lexicon already covers.
Output = the exact work-list the tashkeel factory (W2b/W2c) must process.

Why Coach-only: Mahmoud's lines are the Arabic that VoiceTut renders. Story
English (Macal/Nour/guests) doesn't go through the Arabic lexicon.

Normalization note (Wave-2 edge case): we DON'T fold hamza/alef variants here —
we keep the surface form as written, but ALSO emit a 'normalized' key so the
factory can catch أنا vs انا duplicates.

Usage:
  python3 extract_season_vocab.py [--home .] [--out season_vocab.json]
Output JSON: {word, count, normalized, in_lexicon} sorted by count desc.
"""
import os, re, json, glob, argparse, unicodedata

AR = r"[\u0621-\u064A]"          # Arabic letters (no diacritics)
DIAC = r"[\u064B-\u0652\u0670]"  # tashkeel marks

def bare(text):
    return re.sub(DIAC, "", text or "")

def normalize(w):
    """fold hamza/alef + ta-marbuta/ya variants so أنا==انا, دبى==دبي, etc."""
    w = re.sub("[إأآ]", "ا", w)
    w = w.replace("ى", "ي").replace("ة", "ه")
    return w

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=".kiro/specs/eec-podcast-automation")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    lex_path = os.path.join(args.home, "pipeline/egyptian_lexicon.json")
    lex = set()
    if os.path.exists(lex_path):
        lex = set(json.load(open(lex_path, encoding="utf-8")).get("lexicon", {}).keys())

    counts, first_ep = {}, {}
    for p in sorted(glob.glob(os.path.join(args.home, "episodes/ep*/script.json"))):
        ep = int(re.search(r"ep(\d+)", p).group(1))
        d = json.load(open(p, encoding="utf-8"))
        for ln in d.get("lines", []):
            if ln.get("speaker") != "Coach":
                continue
            for w in re.findall(AR + "+", bare(ln.get("text", ""))):
                if len(w) < 2:
                    continue
                counts[w] = counts.get(w, 0) + 1
                first_ep.setdefault(w, ep)

    rows = [{"word": w, "count": c, "normalized": normalize(w),
             "in_lexicon": w in lex, "first_ep": first_ep[w]}
            for w, c in counts.items()]
    rows.sort(key=lambda r: (-r["count"], r["first_ep"]))

    remaining = [r for r in rows if not r["in_lexicon"]]
    out = args.out or os.path.join(args.home, "pipeline/season_vocab.json")
    json.dump({"total_unique": len(rows), "total_tokens": sum(counts.values()),
               "in_lexicon": len(rows) - len(remaining), "remaining": len(remaining),
               "words": rows}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{len(rows)} unique Coach words | {len(remaining)} remaining (not in lexicon) -> {out}")

if __name__ == "__main__":
    main()
