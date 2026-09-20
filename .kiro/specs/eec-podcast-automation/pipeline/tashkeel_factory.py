#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W2b — TASHKEEL FACTORY (Egyptian pronunciation factory, stage 2: DRAFT).

Takes season_vocab.json (the remaining bare Coach words) and drafts an EGYPTIAN-
COLLOQUIAL diacritized form for each, using DeepSeek (our Arabic-capable LLM, live
on the server). Batches the words so it's fast + cheap. Optionally cross-checks
against CATT (MSA) and FLAGS disagreements (CATT is MSA-biased, so disagreement is
expected on colloquial words — it's a *signal*, not an authority).

Output: season_tashkeel_draft.json = {word -> {deepseek, catt?, agree, count}}.
This is a DRAFT — stage 3 (ASR verify, on Kaggle) proves each one actually
synthesizes correctly before it's trusted. Owner reviews only the ASR-flagged ones.

Run ON THE SERVER (has DeepSeek in .env):
  set -a; . ./.env; set +a
  python3 bin/tashkeel_factory.py --vocab season_vocab.json --limit 820 --batch 40
"""
import os, sys, json, re, argparse, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import llm_backend
except Exception:
    llm_backend = None

PROMPT_HEAD = (
    "You are an expert in EGYPTIAN COLLOQUIAL Arabic (العامية المصرية) pronunciation for a "
    "warm Egyptian teacher speaking on a podcast, feeding a text-to-speech engine.\n"
    "For EACH bare word below, return its FULLY DIACRITIZED (tashkeel) form AS AN EGYPTIAN "
    "PRONOUNCES IT IN CASUAL SPEECH — NOT Modern Standard Arabic. Vowel every letter needed "
    "for correct pronunciation; use shadda where doubled; Egyptian colloquial voweling.\n"
    "Return STRICT JSON only: an object mapping each input word -> its tashkeel form. "
    "No commentary, no extra keys.\nWords: "
)

def deepseek_batch(words):
    raw = llm_backend.chat(PROMPT_HEAD + " ".join(words), temperature=0.2)
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    return json.loads(m.group(0) if m else raw)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocab", default="season_vocab.json")
    ap.add_argument("--out", default="season_tashkeel_draft.json")
    ap.add_argument("--limit", type=int, default=820)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--catt", action="store_true", help="also draft with CATT (MSA) and flag disagreements")
    args = ap.parse_args()

    if llm_backend is None:
        print("ERROR: llm_backend not importable (run on the server with .env sourced)", file=sys.stderr)
        sys.exit(2)

    voc = json.load(open(args.vocab, encoding="utf-8"))
    remaining = [w for w in voc["words"] if not w["in_lexicon"]][:args.limit]
    words = [r["word"] for r in remaining]
    count_of = {r["word"]: r["count"] for r in remaining}
    print(f"drafting tashkeel for {len(words)} words in batches of {args.batch}...", flush=True)

    draft = {}
    for i in range(0, len(words), args.batch):
        chunk = words[i:i + args.batch]
        for attempt in range(1, 4):
            try:
                res = deepseek_batch(chunk)
                for w in chunk:
                    if w in res and res[w]:
                        draft[w] = {"deepseek": res[w], "count": count_of[w]}
                print(f"  batch {i//args.batch+1}: +{sum(1 for w in chunk if w in res)}/{len(chunk)}", flush=True)
                break
            except Exception as e:
                print(f"  batch {i//args.batch+1} attempt {attempt}: {str(e)[:70]}", flush=True)
                time.sleep(4 * attempt)
        time.sleep(1)

    # optional CATT cross-check (MSA) — disagreement flags a colloquial word to watch
    if args.catt:
        try:
            from catt_tashkeel import diacritize  # name may differ; wrapped in try
            for w, d in draft.items():
                try:
                    c = diacritize(w)
                    d["catt"] = c
                    d["agree"] = (c == d["deepseek"])
                except Exception:
                    pass
        except Exception:
            print("  (CATT not available here — skipping MSA cross-check; do it on Kaggle)", flush=True)

    json.dump({"count": len(draft), "words": draft},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"drafted {len(draft)} -> {args.out}")

if __name__ == "__main__":
    main()
