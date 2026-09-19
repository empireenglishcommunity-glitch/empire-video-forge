#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — SHORT EPISODE GENERATOR (5-10 min, "learn with fun").

A tight serialized drama that TEACHES without feeling like a lesson. Each
episode targets ~7 min (band 5-10 min; ~750-1500 words at 150 wpm), built
section-by-section so it stays coherent AND fits free-tier LLM pacing (each
section is one call; resumable). Length is a parameter (--minutes).

COMPACT STRUCTURE (the "sandwich that teaches", tight form):
  cold_open   - punchy dramatic hook (pure story, English; NO Coach here)
  coach_intro - Coach (Egyptian AR): "today watch for these phrases..."
  act1        - the main scene, natural level-appropriate English, plot advances
  coach_break1- Coach unpacks the key phrases from act1 + a common mistake
  act2        - short resolution + a light cliffhanger to next episode
  coach_outro - recap the phrases + phrase-of-episode + community CTA

Enforced gates: story/teaching separation (structure_check) + the 5-10 min
duration band (see main()).

Every line is tagged: {section, speaker, lang, text}. speaker must be a CAST id
(Coach, Macal, Nour, TaxiDriver, Barista, Landlord, Interviewer, Friend_M,
Friend_F, Official) so the synth routes it to the right voice. Coach lines are
Egyptian Arabic; story lines are English (natural, level-appropriate).

Continuity: season.json holds story-so-far + phrases-taught + current episode.
Difficulty scales across the season (A2 -> B1 -> B2).

Output: episodes/epNN/script.json (same contract the synth + assembly consume).

Usage: GEMINI_API_KEY=... python3 gen_episode.py --episode 1 [--level A2]
                                    [--out episodes/ep01/script.json]
Resumable: partial acts are cached in episodes/epNN/_acts/ so a quota stall
doesn't lose work; re-run to continue.
"""
import os, sys, json, re, argparse, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm_backend  # pluggable: local Qwen (Kaggle) / free OpenAI-compatible API / gemini
import structure_check  # LOCKED story/teaching separation rule (series-bible §10)

MODEL = os.environ.get("EEC_SCRIPT_MODEL", "gemini-3.6-flash")
HOME = os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast")
SEASON_PATH = os.path.join(HOME, "season.json")

CAST_IDS = ["Coach", "Macal", "Nour", "TaxiDriver", "Barista", "Landlord",
            "Interviewer", "Friend_M", "Friend_F", "Official"]

SEASON1 = [
    (1, "The Arrival", "A2", "airport + taxi: first steps in Dubai, small talk, directions"),
    (2, "The Apartment", "A2", "the landlord: numbers, requests, complaints, settling in"),
    (3, "The Coffee Order", "A2", "the fast-talking barista catches Macal off guard"),
    (4, "The Interview", "B1", "the big job interview — nerves, questions, first impression"),
    (5, "First Day", "B1", "meeting the team, introductions, office small talk"),
    (6, "The Misunderstanding", "B1", "Macal says the wrong thing; recovering politely"),
    (7, "Making a Friend", "B1", "social English, humor, a real connection"),
    (8, "The Meeting", "B2", "speaking up at work, giving an opinion under pressure"),
    (9, "The Phone Call", "B2", "a tricky service call, no visual cues, staying calm"),
    (10, "The Presentation", "B2", "the season payoff — Macal presents, everything on the line"),
]

# TARGET: a TIGHT 5-10 minute episode (default ~7 min). Spoken ~150 wpm.
# COMPACT 6-section template: hook → intro → scene → breakdown → short scene → outro.
# Each section has a small WORD FLOOR tuned so the total lands in the 5-10 min band.
# The floors are the ~7-min baseline; --minutes scales them (see build_acts).
# (act_key, brief, base_min_words)
BASE_ACTS = [
    ("cold_open", "a punchy COLD OPEN (~15-20 sec): drop the listener straight into a tense/curious moment, then a beat of intrigue. 3-4 story lines, SHORT and gripping. PURE STORY — only in-world characters (Macal + guests) speaking English. ABSOLUTELY NO Coach line and NO Arabic here; the Coach first speaks in coach_intro.", 55),
    ("coach_intro", "the COACH INTRO (Egyptian Arabic, Coach only): warmly welcome the listener in one breath, set today's situation, and name the 2-3 English phrases to listen for. 3-4 lines. Warm and fun, NO rambling.", 110),
    ("act1", "ACT 1 — the main scene: 8-12 lines of natural {level} English between Macal and the guest(s). Tight and real — establish the situation and land the target phrases in context. Keep it moving, no filler.", 220),
    ("coach_break1", "COACH BREAK 1 (Egyptian Arabic, Coach): unpack the 2-3 key English phrases from Act 1 (meaning + when to use + one quick example each) + 1 common mistake. 4-6 lines. Warm, concise, no padding.", 140),
    ("act2", "ACT 2 — short resolution + a hook to next episode: 7-10 lines of {level} English. The moment resolves (a small win or surprise), then end on a light cliffhanger. Tight, no rush-padding.", 190),
    ("coach_outro", "the COACH OUTRO (Egyptian Arabic, Coach): quickly recap the phrases, give the 'phrase of the episode', a short community CTA (Telegram/subscribe), and tease next time. 3-5 lines. Brief and warm.", 110),
]
BASE_TARGET_WORDS = 825   # sum of base floors ≈ ~5.5 min floor; ~7 min typical
BASE_MINUTES = 7          # the baseline the BASE_ACTS floors are tuned for
WPM = 150                 # spoken words per minute (for duration estimates)
MIN_MINUTES, MAX_MINUTES = 5, 10   # hard acceptance band (duration guard)


def build_acts(minutes):
    """Scale the base word floors to the requested target minutes, keeping the
    same compact 6-section shape. Story acts absorb most of the length change."""
    scale = max(0.6, min(1.6, minutes / BASE_MINUTES))
    acts = []
    for key, brief, base in BASE_ACTS:
        acts.append((key, brief, max(40, int(round(base * scale)))))
    return acts


def load_season():
    try:
        with open(SEASON_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"season": 1, "current_episode": 1,
                "story_so_far": ("Macal is an ambitious young Egyptian who just moved to "
                                 "Dubai to build a new life. He's warm and determined but "
                                 "nervous about his English. Nour is a confident friend "
                                 "already settled in Dubai who helps him. The Coach is the "
                                 "warm Egyptian-Arabic teacher voice guiding the audience."),
                "phrases_taught": []}


def save_season(s):
    os.makedirs(os.path.dirname(SEASON_PATH), exist_ok=True)
    with open(SEASON_PATH, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def call_gemini(prompt, api_key=None, temp=0.95):
    # backend-agnostic now: routes to local Qwen / free API / gemini via llm_backend
    return llm_backend.chat(prompt, temperature=temp)


def extract_json(raw):
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    # 1) straight parse
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else v.get("lines", v)
    except Exception:
        pass
    # 2) grab the outermost array
    m = re.search(r"\[[\s\S]*\]", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    # 3) SALVAGE: pull every {...} line-object individually (handles truncation,
    #    concatenation, trailing junk). Each object must have speaker+text.
    objs = []
    for om in re.finditer(r"\{[^{}]*\}", raw):
        try:
            o = json.loads(om.group(0))
            if isinstance(o, dict) and o.get("text"):
                objs.append(o)
        except Exception:
            continue
    if objs:
        return objs
    raise ValueError("no JSON objects found")


def act_prompt(ep, title, level, situation, act_key, act_desc, min_words, season, prev_lines, expand=False):
    prev = ""
    if prev_lines:
        prev = "STORY SO FAR IN THIS EPISODE (continue naturally, do not repeat):\n" + \
               "\n".join(f"[{l['section']}][{l['speaker']}] {l['text']}" for l in prev_lines[-18:])
    length = (f"LENGTH TARGET: about {min_words} words for this section (this is a "
              f"TIGHT 5-10 MINUTE episode — keep it punchy and moving; NO filler, NO "
              f"padding, no rambling). Quality over quantity.")
    if expand:
        length = (f"Your previous version was too thin. Add a few more natural dialogue "
                  f"turns to reach about {min_words} words — but stay TIGHT, no filler.")
    STORY_ACTS = {"cold_open", "act1", "act2", "act3", "act4"}
    if act_key in STORY_ACTS:
        sep_rule = ("SECTION TYPE: STORY (in-world scene). Speakers are ONLY story "
                    "characters (Macal, Nour, guests) speaking ENGLISH. The Coach does "
                    "NOT appear here and there is NO Arabic in this section — all teaching "
                    "happens later in the dedicated coach break, never mid-scene. Do NOT "
                    "insert any Coach line or any commentary about the English.")
    else:
        sep_rule = ("SECTION TYPE: COACH (teaching beat). The ONLY speaker is Coach, "
                    "speaking Egyptian Arabic (lang \"ar\"). No story characters speak "
                    "here.")
    return f"""You are the head writer for "Two Worlds", a serialized bilingual English-learning
DRAMA podcast by Empire English Community for Egyptian/Arab learners. Mission:
LEARN WITH FUN — a story so good people binge it, that teaches English by living it.

{sep_rule}

BRAND VOICE: warm, honest, encouraging. NEVER "hack/secret/guaranteed" or shaming.
Egyptian Arabic for the Coach; natural, native, level-appropriate English for the story.

CHARACTERS (use ONLY these speaker ids): {", ".join(CAST_IDS)}.
- Macal: Egyptian learner-hero in Dubai; English is natural but improving.
- Nour: confident friend already settled in Dubai; warm, encouraging.
- Coach: NOT in the story — the Egyptian-Arabic voice that teaches the audience.
- Guests by role: TaxiDriver, Barista, Landlord, Interviewer, Friend_M, Friend_F, Official.

EPISODE {ep}: "{title}" — CEFR level {level}. Situation: {situation}.
SEASON STORY SO FAR: {season.get('story_so_far','')}

{prev}

WRITE ONLY THIS SECTION: {act_key} — {act_desc.format(level=level)}

{length}

Return STRICT JSON only: a list of line objects, each:
{{"section":"{act_key}","speaker":"<one of the cast ids>","lang":"en" or "ar","text":"..."}}
Rules: Coach lines are ALWAYS lang "ar" (Egyptian Arabic). Story lines are lang "en".
Keep English at level {level}. Natural spoken lines (contractions, real reactions).
CRITICAL: this is an AUDIO drama — write ONLY spoken dialogue. NO stage directions,
NO narration, NO asterisks (*...*), NO brackets ([...]). Every "text" must be words
a character actually SAYS out loud. Show action through what people SAY, not narration.
No markdown, no commentary — just the JSON list of lines for THIS section."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--level", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--minutes", type=float, default=float(os.environ.get("EEC_TARGET_MIN", 7)),
                    help="target spoken length in minutes (band 5-10; default 7)")
    ap.add_argument("--force", action="store_true",
                    help="save even if the episode falls outside the 5-10 min band")
    ap.add_argument("--no-advance", action="store_true",
                    help="do NOT advance season.json current_episode (use when "
                         "regenerating an existing episode)")
    args = ap.parse_args()

    # build the compact act template scaled to the requested length
    ACTS = build_acts(args.minutes)
    TARGET_WORDS = int(round(args.minutes * WPM))
    print(f"target: ~{args.minutes} min (~{TARGET_WORDS} words), band {MIN_MINUTES}-{MAX_MINUTES} min")

    # backend is pluggable now — need a usable one (local Qwen / free API / gemini)
    api_key = os.environ.get("GEMINI_API_KEY")
    backend = llm_backend.which()
    if backend == "gemini" and not api_key:
        print("ERROR: no LLM backend — set EEC_LLM_BASE_URL+EEC_LLM_KEY (free API), "
              "or EEC_FORCE_LOCAL=1 (Kaggle Qwen), or GEMINI_API_KEY.", file=sys.stderr)
        sys.exit(2)
    print(f"LLM backend: {backend}")

    ep = args.episode
    plan = next((p for p in SEASON1 if p[0] == ep), None)
    if not plan:
        print(f"ERROR: no plan for episode {ep}", file=sys.stderr); sys.exit(2)
    _, title, level, situation = plan
    level = args.level or level
    season = load_season()

    ep_dir = os.path.join(HOME, "episodes", f"ep{ep:02d}")
    acts_dir = os.path.join(ep_dir, "_acts")
    os.makedirs(acts_dir, exist_ok=True)

    def act_words(lines):
        return sum(len(l.get("text", "").split()) for l in lines)

    def clean_lines(lines, act_key):
        # keep only well-formed lines (speaker + text); fix lang; drop junk
        out = []
        for l in lines:
            if not isinstance(l, dict):
                continue
            sp = l.get("speaker"); tx = l.get("text")
            if not sp or not tx or not str(tx).strip():
                continue
            l["section"] = act_key
            l["lang"] = "ar" if sp == "Coach" else l.get("lang", "en")
            out.append({"section": act_key, "speaker": sp,
                        "lang": l["lang"], "text": str(tx).strip()})
        return out

    all_lines = []
    for act_key, act_desc, min_words in ACTS:
        cache = os.path.join(acts_dir, f"{act_key}.json")
        if os.path.exists(cache):  # resume: reuse already-generated acts
            lines = clean_lines(json.load(open(cache, encoding="utf-8")), act_key)
            all_lines += lines
            print(f"  [{act_key}] cached ({len(lines)} lines, {act_words(lines)}w)")
            continue
        lines = None
        attempt = 0
        deadline = time.time() + 6 * 3600
        expand = False
        while time.time() < deadline:
            attempt += 1
            prompt = act_prompt(ep, title, level, situation, act_key, act_desc,
                                min_words, season, all_lines, expand=expand)
            try:
                raw = call_gemini(prompt, api_key)
                got = extract_json(raw)
                assert isinstance(got, list) and got
                for ln in got:
                    ln["section"] = act_key
                    ln.setdefault("lang", "ar" if ln.get("speaker") == "Coach" else "en")
                    if ln.get("speaker") == "Coach":
                        ln["lang"] = "ar"
                # ENFORCE LENGTH: if the act is short, expand it (up to 2 tries)
                if act_words(got) < min_words and attempt <= 3:
                    print(f"  [{act_key}] {act_words(got)}w < {min_words}w — expanding...", flush=True)
                    lines = got  # keep best-so-far in case expand fails
                    expand = True
                    continue
                lines = got
                break
            except urllib.error.HTTPError as e:
                lines = None
                if e.code == 429:  # quota — wait long for reset
                    wait = min(120 * attempt, 900)
                    print(f"  [{act_key}] 429 (quota) attempt {attempt}; waiting {wait}s", file=sys.stderr)
                    time.sleep(wait)
                else:  # 5xx etc — shorter backoff
                    print(f"  [{act_key}] HTTP {e.code} attempt {attempt}", file=sys.stderr)
                    time.sleep(min(15 * attempt, 120))
            except Exception as e:
                lines = None
                print(f"  [{act_key}] attempt {attempt}: {str(e)[:80]}", file=sys.stderr)
                time.sleep(min(10 * attempt, 120))
        if not lines:
            print(f"  [{act_key}] gave up after ~6h — re-run to resume from here.", file=sys.stderr)
            sys.exit(1)
        lines = clean_lines(lines, act_key)
        json.dump(lines, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        all_lines += lines
        words = sum(len(l["text"].split()) for l in all_lines)
        print(f"  [{act_key}] +{len(lines)} lines (total {len(all_lines)}, ~{words} words)")
        time.sleep(1)

    # assemble the episode script (same contract as before)
    script = {
        "episode": ep, "title": title, "level": level,
        "lines": all_lines,
        "phrase_of_episode": {"en": "", "ar": ""},  # filled by a final pass or editor
        "word_count": sum(len(l["text"].split()) for l in all_lines),
        "cast_used": sorted({l["speaker"] for l in all_lines}),
    }
    # AUDIO-READY: strip any stray stage directions / narration (belt-and-braces)
    def _clean_text(t):
        t = re.sub(r"\*[^*]*\*", " ", t or "").replace("*", " ")
        t = re.sub(r"\[[^\]]*\]", " ", t)
        return re.sub(r"\s+", " ", t).strip()
    cleaned = []
    for l in script["lines"]:
        ct = _clean_text(l["text"])
        if ct:
            l["text"] = ct
            cleaned.append(l)
    script["lines"] = cleaned

    # STRUCTURE ENFORCEMENT (series-bible §10): acts are generated in isolation, so a
    # model can still leak a Coach/Arabic line into a STORY section. Auto-correct the
    # ONE safe way — drop any Coach/Arabic line that leaked into a STORY section (it's
    # stray commentary; real teaching lives in the coach sections) — then HARD-GATE on
    # the validator so a structurally-messy script can never be saved as final.
    STORY = structure_check.STORY_SECTIONS
    kept, dropped = [], []
    for l in script["lines"]:
        if l.get("section") in STORY and (l.get("speaker") == "Coach" or l.get("lang") == "ar"):
            dropped.append(l)
        else:
            kept.append(l)
    if dropped:
        print(f"  STRUCTURE: dropped {len(dropped)} stray Coach/Arabic line(s) that "
              f"leaked into STORY sections (teaching belongs in coach breaks):",
              flush=True)
        for l in dropped[:10]:
            print(f"    - [{l.get('section')}] {(l.get('text') or '')[:50]}")
    script["lines"] = kept
    script["word_count"] = sum(len(l["text"].split()) for l in script["lines"])

    violations = structure_check.check_script(script)
    if violations:
        print("\n" + structure_check.format_report(violations), file=sys.stderr)
        print("ERROR: generated script violates the LOCKED structure rule "
              "(series-bible §10) — NOT saving. Re-run to regenerate the offending "
              "section(s).", file=sys.stderr)
        sys.exit(4)
    print("  STRUCTURE OK — story/teaching separation clean")

    # DURATION GUARD: keep episodes in the 5-10 min band. A bloated (or too-thin)
    # episode can't slip through silently — fail unless --force.
    est_min = round(script["word_count"] / WPM, 1)
    if est_min < MIN_MINUTES or est_min > MAX_MINUTES:
        print(f"\n  DURATION: ~{est_min} min is OUTSIDE the {MIN_MINUTES}-{MAX_MINUTES} "
              f"min band (words={script['word_count']}).", file=sys.stderr)
        if not args.force:
            print("ERROR: episode length out of band — NOT saving. Re-run (the "
                  "generator will re-roll sections), adjust --minutes, or pass "
                  "--force to override.", file=sys.stderr)
            sys.exit(6)
        print("  --force: saving despite out-of-band length", file=sys.stderr)
    else:
        print(f"  DURATION OK — ~{est_min} min (band {MIN_MINUTES}-{MAX_MINUTES})")

    out = args.out or os.path.join(ep_dir, "script.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(script, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # update season memory (skip when regenerating an existing episode)
    if not args.no_advance:
        season["story_so_far"] = (season.get("story_so_far", "") +
                                  f" [Ep{ep}: {title} — see script]").strip()[-1500:]
        season["current_episode"] = ep + 1
        save_season(season)
    else:
        print("  --no-advance: season.json left unchanged")
    print(f"\nOK wrote {out}")
    print(f"  {len(all_lines)} lines, ~{script['word_count']} words (~{est_min} min spoken)")
    print(f"  cast used: {script['cast_used']}")


if __name__ == "__main__":
    main()
