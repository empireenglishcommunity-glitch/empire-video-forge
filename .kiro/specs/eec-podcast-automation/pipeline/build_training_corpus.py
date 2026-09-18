#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — TRAINING CORPUS generator (step 1 of the voice fine-tune).

Builds the TEXT half of the voice-training dataset: a rich, on-brand set of
Egyptian-Arabic "coach" sentences that the target voice will later be trained to
speak. The audio half (generating + quality-scoring clips of these sentences on
Kaggle GPU) is a separate step; this produces the script those clips read.

Design goals (why this beats a generic word list):
- ON-BRAND: sentences sound like the EEC Coach actually talks — warm, explaining,
  teaching, with English terms code-switched in ("يعني 'How long does it take?'").
  Train on the *kind* of speech the voice will perform => on-brand from day one.
- EXPRESSIVE RANGE: each sentence tagged with an emotion/style (warm, excited,
  curious, reassuring, playful, serious) so the fine-tuned voice can ACT, not just
  narrate — the "learn with fun" factor.
- PHONETIC COVERAGE: deliberately include the hard Egyptian sounds (ض ظ ذ ث ق غ ع ح),
  numbers, common code-switch English terms, questions + exclamations, so the voice
  learns the full sound space.
- LENGTH SPREAD: short (2-4 words) to medium (12-18 words) so the model learns pacing.

Output: training_corpus.jsonl — one row per sentence:
  {"id","text","style","lang":"ar","has_codeswitch":bool,"len_words":int}
Gemini writes the sentences (via GEMINI_API_KEY); we validate + de-dupe + balance.

Usage:  GEMINI_API_KEY=... python3 build_training_corpus.py --count 300 \
            --out training_corpus.jsonl
"""
import os, sys, json, re, argparse, time, urllib.request

MODEL = os.environ.get("EEC_SCRIPT_MODEL", "gemini-3.6-flash")

STYLES = ["warm", "excited", "curious", "reassuring", "playful", "serious",
          "encouraging", "storytelling"]

# thematic buckets so the corpus covers the show's real range
THEMES = [
    "welcoming the listener to the episode",
    "explaining what an English phrase means and when to use it",
    "pointing out a common mistake learners make, kindly",
    "a quick culture note about life/English in Dubai or the Gulf",
    "encouraging the learner to keep going / not give up",
    "recapping the episode and teasing the next one",
    "a warm reaction to something in the story (surprise, delight)",
    "giving a small challenge or homework for the community",
]


def build_prompt(n, theme, styles):
    return f"""You are the head writer for "Two Worlds", a bilingual English-teaching
podcast by Empire English Community for EGYPTIAN Arabic speakers. Write {n} short
spoken lines for the Coach character, in NATURAL EGYPTIAN ARABIC (اللهجة المصرية),
on this theme: {theme}.

Voice: a warm, honest, encouraging Egyptian coach. NEVER use "hack", "secret",
"مضمون", or fear/shaming. Real, human, friendly.

Rules for the lines:
- EGYPTIAN dialect (دلوقتي، عايز، إزاي، خد بالك) — NOT Modern Standard Arabic.
- Some lines MUST code-switch an English teaching term inside the Arabic, written
  with the English in Latin letters in single quotes, e.g. يعني 'How long does it take?'.
- Vary length: some 2-4 words, some 12-18 words.
- Include questions and exclamations (for expressive range).
- Natural, spoken — like talking to a friend, not reading a textbook.

Return STRICT JSON only: a list of objects, each:
{{"text": "<the Egyptian Arabic line>", "style": "<one of: {', '.join(styles)}>"}}
No markdown, no commentary — just the JSON array."""


def call_gemini(prompt, api_key):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent?key={api_key}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 1.0,
                                 "response_mime_type": "application/json"}}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["candidates"][0]["content"]["parts"][0]["text"]


def extract_json(raw):
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\[[\s\S]*\]", raw)
        if m:
            return json.loads(m.group(0))
        raise


AR = re.compile(r"[\u0600-\u06FF]")
LAT = re.compile(r"[A-Za-z]")


def valid_line(t):
    if not t or not AR.search(t):
        return False
    w = len(t.split())
    return 2 <= w <= 22


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=300, help="target total lines")
    ap.add_argument("--out", default="training_corpus.jsonl")
    ap.add_argument("--per-call", type=int, default=25)
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY", file=sys.stderr); sys.exit(2)

    seen = set()
    rows = []
    theme_i = 0
    while len(rows) < args.count:
        theme = THEMES[theme_i % len(THEMES)]
        theme_i += 1
        prompt = build_prompt(args.per_call, theme, STYLES)
        try:
            items = extract_json(call_gemini(prompt, api_key))
        except Exception as e:
            print(f"  gen failed ({str(e)[:80]}), retrying...", file=sys.stderr)
            time.sleep(3)
            continue
        for it in items:
            t = (it.get("text") or "").strip()
            style = (it.get("style") or "warm").strip()
            key = re.sub(r"\s+", "", t)
            if not valid_line(t) or key in seen:
                continue
            seen.add(key)
            rows.append({
                "id": f"line{len(rows)+1:04d}",
                "text": t, "style": style if style in STYLES else "warm",
                "lang": "ar",
                "has_codeswitch": bool(LAT.search(t)),
                "len_words": len(t.split()),
            })
            if len(rows) >= args.count:
                break
        print(f"  collected {len(rows)}/{args.count} (theme: {theme[:30]})", flush=True)
        time.sleep(1)

    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # quick balance report
    cs = sum(1 for r in rows if r["has_codeswitch"])
    styles = {}
    for r in rows:
        styles[r["style"]] = styles.get(r["style"], 0) + 1
    print(f"\nOK wrote {len(rows)} lines -> {args.out}")
    print(f"  code-switch lines: {cs} ({100*cs//len(rows)}%)")
    print(f"  styles: {styles}")
    print(f"  avg words: {sum(r['len_words'] for r in rows)/len(rows):.1f}")


if __name__ == "__main__":
    main()
