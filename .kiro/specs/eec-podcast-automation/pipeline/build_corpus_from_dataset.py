#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — TRAINING CORPUS from a real Egyptian dataset (no Gemini quota).

Alternative / complement to build_training_corpus.py. Instead of generating lines
with Gemini (rate-limited), this pulls REAL human Egyptian sentences from an open
HuggingFace dataset via the datasets-server API (rows endpoint — no full download,
no auth). Real human Egyptian text is excellent training material and removes the
Gemini bottleneck.

We only use the TEXT (the target voice's audio is generated separately with ONE
consistent voice, keeping the dataset a single coherent speaker). Filtering keeps
clean, well-formed, right-length Egyptian lines; de-dupes; tags length/code-switch.

Output: same schema as build_training_corpus.py so downstream steps are identical:
  {"id","text","style","lang":"ar","has_codeswitch","len_words","source"}

Default source: MAdel121/arabic-egy-cleaned (colloquial Egyptian lines, ~seconds
each). We can blend multiple datasets by re-running with --append.

Usage:
  python3 build_corpus_from_dataset.py --count 150 --out training_corpus.jsonl
  python3 build_corpus_from_dataset.py --count 150 --append   # add more, resume-safe
"""
import os, sys, json, re, argparse, urllib.request, urllib.parse, time

AR = re.compile(r"[\u0600-\u06FF]")
LAT = re.compile(r"[A-Za-z]")
# reject lines that are mostly non-Egyptian / MSA-formal markers or noisy
BAD = re.compile(r"[0-9]{4,}|www|http|@|\|")


def fetch_rows(dataset, split, offset, length, config="default"):
    q = urllib.parse.urlencode({"dataset": dataset, "config": config,
                                "split": split, "offset": offset, "length": length})
    url = f"https://datasets-server.huggingface.co/rows?{q}"
    req = urllib.request.Request(url, headers={"User-Agent": "eec-corpus"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("rows", [])


def clean(t):
    t = (t or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t


def good_line(t):
    if not t or not AR.search(t) or BAD.search(t):
        return False
    w = len(t.split())
    if not (3 <= w <= 20):
        return False
    # must be mostly Arabic characters
    ar = len(AR.findall(t))
    return ar >= max(6, len(t) // 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=150)
    ap.add_argument("--out", default="training_corpus.jsonl")
    ap.add_argument("--dataset", default="MAdel121/arabic-egy-cleaned")
    ap.add_argument("--split", default="train")
    ap.add_argument("--text-col", default="text")
    ap.add_argument("--append", action="store_true")
    args = ap.parse_args()

    seen, rows = set(), []
    if args.append and os.path.exists(args.out):
        for line in open(args.out, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                rows.append(r); seen.add(re.sub(r"\s+", "", r.get("text", "")))
            except Exception:
                pass
        print(f"  append mode: {len(rows)} existing")

    mode = "a" if args.append else "w"
    out_f = open(args.out, mode, encoding="utf-8")
    offset, page, stalls = 0, 100, 0
    while len(rows) < args.count and stalls < 8:
        try:
            batch = fetch_rows(args.dataset, args.split, offset, page)
        except Exception as e:
            print(f"  fetch failed at {offset}: {str(e)[:80]}", file=sys.stderr)
            stalls += 1; time.sleep(3); continue
        if not batch:
            print("  reached end of dataset"); break
        offset += len(batch)
        added = 0
        for item in batch:
            row = item.get("row", {})
            t = clean(row.get(args.text_col) or row.get("sentence") or "")
            key = re.sub(r"\s+", "", t)
            if not good_line(t) or key in seen:
                continue
            seen.add(key)
            r = {"id": f"line{len(rows)+1:04d}", "text": t, "style": "natural",
                 "lang": "ar", "has_codeswitch": bool(LAT.search(t)),
                 "len_words": len(t.split()), "source": args.dataset}
            rows.append(r)
            out_f.write(json.dumps(r, ensure_ascii=False) + "\n"); out_f.flush()
            added += 1
            if len(rows) >= args.count:
                break
        stalls = 0 if added else stalls + 1
        print(f"  collected {len(rows)}/{args.count} (+{added}, offset {offset})", flush=True)
    out_f.close()

    if not rows:
        print("No lines collected."); return
    cs = sum(1 for r in rows if r["has_codeswitch"])
    print(f"\nOK wrote {len(rows)} lines -> {args.out}")
    print(f"  code-switch: {cs} | avg words: {sum(r['len_words'] for r in rows)/len(rows):.1f}")


if __name__ == "__main__":
    main()
