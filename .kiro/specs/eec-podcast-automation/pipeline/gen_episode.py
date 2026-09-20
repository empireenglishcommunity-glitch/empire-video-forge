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

Every line is tagged: {section, speaker, lang, text, direction?}. speaker must be
a CAST id (Coach, Macal, Nour, TaxiDriver, Barista, Landlord, Interviewer,
Friend_M, Friend_F, Official) so the synth routes it to the right voice. Coach
lines are Egyptian Arabic; story lines are English (natural, level-appropriate).

NOTE — the "direction" field is FORWARD-LOOKING METADATA (scoped, not yet wired):
  Each line may carry an optional "direction" — a short acting note for the voice
  performance, e.g. "anxious, rapid" or "slow breath, long pause". It is NEVER
  spoken and NEVER shown. As of this generator, "direction" is generated and
  preserved in script.json but is NOT YET CONSUMED by any synth or assembly stage
  (a grep of pipeline/ + kaggle/ confirms no reader today). It exists so a FUTURE
  "direction -> params/prosody mapper" in the synthesis layer can translate these
  acting notes into actionable audio parameters (e.g. Chatterbox/Qwen exaggeration
  & cfg_weight, per-line pacing/silence, or DAW envelope automation). Tracked as
  Phase-C work; see the repo tracking issues. Treat it today as intent-capture:
  writing rich, correct directions now means the mapper has good data to act on
  later — but changing a "direction" value has ZERO effect on current audio output.

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

# Speaker ids (keep "Coach" as the id for Mahmoud so structure_check + pipeline are
# untouched; Mahmoud is the display name). Season-1 roster from the bible/season.json.
CAST_IDS = ["Coach", "Macal", "Nour", "Tarek", "TaxiDriver", "Barista", "Landlord",
            "Interviewer", "Official", "Friend_M", "Friend_F"]

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
    ("cold_open", "a punchy COLD OPEN (~15-20 sec): drop the listener straight into a tense/curious moment, then a beat of intrigue. 3-4 story lines, SHORT and gripping. PURE STORY — only in-world characters (Macal + guests), mostly English. ABSOLUTELY NO Coach line here (the Coach first speaks in coach_intro). Macal MAY code-switch to a short Egyptian-Arabic line (lang \"ar\") only if the hook is an intimate family moment — otherwise keep it English.", 55),
    ("coach_intro", "the COACH INTRO (Egyptian Arabic, Coach only): warmly welcome the listener in one breath, set today's situation, and name the 2-3 English phrases to listen for. 3-4 lines. Warm and fun, NO rambling.", 110),
    ("act1", "ACT 1 — the main scene: 8-12 lines of natural {level} English between Macal and the guest(s). Tight and real — establish the situation and land the target phrases in context. Keep it moving, no filler.", 220),
    ("coach_break1", "COACH BREAK 1 (Egyptian Arabic, Coach): unpack the 2-3 key English phrases from Act 1 (meaning + when to use + one quick example each) + 1 common mistake. 4-6 lines. Warm, concise, no padding.", 140),
    ("act2", "ACT 2 — short resolution + a hook to next episode: 7-10 lines of {level} English. The moment resolves (a small win or surprise), then end on a light cliffhanger. Tight, no rush-padding.", 190),
    ("coach_outro", "the COACH OUTRO (Egyptian Arabic, Coach): quickly recap the phrases, give the 'phrase of the episode', then a SPECIFIC TRACKABLE community CTA — challenge the listener to record a short voice note SAYING the phrase-of-the-episode out loud and send it to the Empire English Community Telegram, so we can hear their accent and cheer them on. 4-5 lines. Brief and warm.", 120),
]
BASE_TARGET_WORDS = 825   # sum of base floors ≈ ~5.5 min floor; ~7 min typical
BASE_MINUTES = 7          # the baseline the BASE_ACTS floors are tuned for
WPM = 150                 # spoken words per minute (for duration estimates)
MIN_MINUTES, MAX_MINUTES = 5, 10   # reference band only (duration gate REMOVED — informational)


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


def act_prompt(ep, title, level, situation, act_key, act_desc, min_words, season, prev_lines,
               expand=False, show="Yalla Fluent", voice_stage="1", arc_beat="",
               phrases_theme="", cliffhanger="", phonetic_focus=None):
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

    # --- Macal voice-stage markers (design §3.4 CRAFT-2) ---
    stage = str(voice_stage or "1")
    MACAL_STAGE = {
        "1": ("MACAL VOICE = STAGE 1 (early, Egyptian L2 learner). Write his English "
              "grammatical BUT accented in RHYTHM: uncontracted forms ('I am not sure', "
              "'I do not know'), explicit micro-pauses '...', simple tenses, deliberate/"
              "earnest pacing. He is understandable, just clearly a learner."),
        "2": ("MACAL VOICE = STAGE 2 (mid, more fluent). Contractions now appear "
              "('I've been', 'I'm not sure'); occasional self-correction ('I mean...'); "
              "basic linking; emerging present-perfect/conditionals. Growing confidence."),
        "3": ("MACAL VOICE = STAGE 3 (late, fluent & confident — but STILL an Egyptian "
              "speaker, NOT native). Uses casual reductions ('gonna','wanna'), idioms, "
              "humor, can joke/negotiate; complex sentences and strong rhythm. His growth "
              "is in FLUENCY and CONFIDENCE, not losing his accent."),
    }.get(stage, "")

    STORY_ACTS = {"cold_open", "act1", "act2", "act3", "act4"}
    if act_key in STORY_ACTS:
        sep_rule = ("SECTION TYPE: STORY (in-world scene). Speakers are story characters "
                    "(Macal, Nour, guests) — mostly ENGLISH. Mahmoud/Coach does NOT appear "
                    "(no teaching mid-scene). LANGUAGE REALISM: characters speak English where "
                    "it's realistic (Dubai work/social/mixed settings, or Macal practicing/"
                    "recording English). Macal is BILINGUAL and may CODE-SWITCH to Egyptian "
                    "ARABIC when the moment is intimate/with family (e.g. answering his mother's "
                    "call) — write those lines in natural Egyptian Arabic with lang \"ar\". Do "
                    "NOT stage an all-Egyptian family conversation in English. Guests stay English.")
        craft = (
            "SCRIPTING CRAFT (mandatory):\n"
            "- START IN-MEDIA-RES: drop into a scene ALREADY in motion. No 'hello, my "
            "name is' setup; exposition emerges through the conflict.\n"
            f"- {MACAL_STAGE}\n"
            "- GUESTS keep authentic Dubai accents (Indian/Filipino/Pakistani/Gulf as "
            "cast) BUT stay CLEAR and level-appropriate — no dense slang, no rapid-fire.\n"
            "- LANGUAGE REALISM (mandatory): characters speak English ONLY where it's "
            "realistic in-world — Dubai's mixed-nationality work/social life (office, taxi, "
            "cafe, interviews, networking), OR when Macal is deliberately PRACTICING/RECORDING "
            "his English. Macal is BILINGUAL: he performs polished English for the image/work, "
            "but CODE-SWITCHES to natural EGYPTIAN ARABIC in intimate family moments (write "
            "those lines in Egyptian Arabic with lang \"ar\" — his VoiceTut voice speaks both). "
            "So a private call home to his Arabic-speaking mother is either (a) staged as Macal "
            "answering IN ARABIC, or (b) reframed as him rehearsing/recording an English voice "
            "note (anxious learner performing success for family who think he 'made it'). NEVER "
            "stage an intimate all-Egyptian family conversation in ENGLISH — that breaks the "
            "world. Mahmoud (Coach) still never appears in a story scene.\n"
            "- Land the episode's TARGET PHRASES naturally in dialogue (don't announce them)."
        )
        if act_key == "act1":
            craft += (
                "\n- PLANTED MISTAKE (required): Macal makes ONE realistic L2 mistake here "
                "(often an Arabic→English transfer, e.g. 'I live here since two years'). "
                "Exactly ONE, natural, not a pile of broken English — the coach corrects it next."
            )
        if act_key == "act2":
            craft += (
                "\n- TRIUMPH BEAT (required): Macal REUSES the corrected form from the coach "
                "break in a new context — a small win showing he learned.\n"
                f"- END ON THE CLIFFHANGER: {cliffhanger}"
            )
    else:
        sep_rule = ("SECTION TYPE: COACH (teaching beat). The ONLY speaker is Coach "
                    "(the host Mahmoud), speaking Egyptian Arabic (lang \"ar\"). No story "
                    "characters speak here.")
        craft = (
            "ARABIC TTS-READY TEXT (mandatory — this is fed to an Arabic TTS engine):\n"
            "- FULL TASHKEEL: write Mahmoud's Arabic with full diacritics (حَرَكَات) so the "
            "engine doesn't guess. Egyptian colloquial voweling, NOT stiff MSA.\n"
            "- SPELL OUT NUMBERS in Arabic words (تِسْعِين), never digits (90).\n"
            "- ARABIZE incidental English loan-words in Arabic script (سِشْن، فِيدْبَاك) — BUT "
            "when Mahmoud quotes the TARGET ENGLISH PHRASE being taught, keep it in real "
            "English/Latin (that's what the learner must hear correctly).\n"
            "- PROSODIC PUNCTUATION as acoustic cues: '...' for a suspense/breath before a "
            "key point; commas every ~4-7 words as breath groups; '!' for warm energy on "
            "greetings. Mahmoud introduces himself by name in coach_intro."
        )
        if act_key == "coach_break1":
            craft += (
                "\n- CORRECT MACAL'S MISTAKE from act1: name it, explain WHY it happens "
                "(the Arabic→English transfer), then give the natural American form. Plus "
                "unpack the 2-3 target phrases. Under ~60s, ZERO shaming — mistakes are normal."
            )
            if phonetic_focus and phonetic_focus.get("target"):
                craft += (
                    "\n- ACCENT LAB DRILL (required, the EEC signature): after the phrases, "
                    "Mahmoud runs a short, focused pronunciation drill on TODAY'S SOUND — "
                    f"\"{phonetic_focus.get('target')}\". Coach note: {phonetic_focus.get('note','')} "
                    "Pull 1-2 example WORDS from the actual Act-1 dialogue that contain this "
                    "sound, say the wrong (Arabic-transfer) way vs. the correct American way, "
                    "and have the listener repeat. Keep the target English example words in real "
                    "English/Latin script (the learner must hear them correctly); the rest in "
                    "full-tashkeel Egyptian Arabic. Warm, playful, ~20-30s — this is the part "
                    "learners come for."
                )
        if act_key == "coach_outro":
            craft += (
                "\n- TRACKABLE VOICE-NOTE CHALLENGE (required): end with a specific, "
                "actionable CTA — Mahmoud picks the PHRASE OF THE EPISODE, asks the listener "
                "to record themselves saying it out loud (applying today's sound) as a short "
                "voice note, and send it to the Empire English Community on Telegram so we can "
                "hear their accent and cheer them on. Name the community by name, make it feel "
                "like belonging, not homework. Keep the target English phrase in Latin script."
            )

    return f"""You are the head writer for "{show}", a serialized bilingual English-learning
DRAMA podcast by Empire English Community for Egyptian/Arab learners. Mission:
LEARN WITH FUN — a story so good people binge it, that teaches English by living it.

{sep_rule}

BRAND VOICE: warm, honest, encouraging. NEVER "hack/secret/guaranteed" or shaming.
Egyptian Arabic for Mahmoud (the coach); natural, level-appropriate English for the story.

CHARACTERS (use ONLY these speaker ids): {", ".join(CAST_IDS)}.
- Macal: Egyptian learner-hero in Dubai; English improving across the season (see stage).
- Nour: American-born (Chicago) colleague/friend; warm, confident, native American English.
- Coach: the host MAHMOUD — NOT in the story; the Egyptian-Arabic voice that teaches.
- Guests by role (Dubai-real): TaxiDriver, Barista, Landlord, Interviewer, Official, etc.

EPISODE {ep}: "{title}" — CEFR level {level}.
SITUATION: {situation}
ARC BEAT (advance this): {arc_beat}
TARGET-PHRASE THEME: {phrases_theme}
SEASON STORY SO FAR: {season.get('story_so_far','')}

{prev}

WRITE ONLY THIS SECTION: {act_key} — {act_desc.format(level=level)}

{craft}

{length}

Return STRICT JSON only: a list of line objects, each:
{{"section":"{act_key}","speaker":"<one of the cast ids>","lang":"en" or "ar","text":"...","direction":"<short acting note, e.g. 'anxious, rapid' or 'warm, reassuring'>"}}
Rules: Coach/Mahmoud lines are ALWAYS lang "ar". Story lines are lang "en".
The "direction" field is an acting note for the voice engine — it is NEVER spoken and
NEVER shown; keep it short. Keep English at level {level}.
CRITICAL: this is an AUDIO drama — "text" is ONLY spoken words. NO stage directions,
NO narration, NO asterisks, NO brackets inside "text". Put performance notes in "direction".
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
    print(f"target: ~{args.minutes} min (~{TARGET_WORDS} words) — no hard gate")

    # backend is pluggable now — need a usable one (local Qwen / free API / gemini)
    api_key = os.environ.get("GEMINI_API_KEY")
    backend = llm_backend.which()
    if backend == "gemini" and not api_key:
        print("ERROR: no LLM backend — set EEC_LLM_BASE_URL+EEC_LLM_KEY (free API), "
              "or EEC_FORCE_LOCAL=1 (Kaggle Qwen), or GEMINI_API_KEY.", file=sys.stderr)
        sys.exit(2)
    print(f"LLM backend: {backend}")

    ep = args.episode
    season = load_season()
    # PLAN SOURCE = season.json (the locked Season-1 plan). Fall back to the legacy
    # hardcoded SEASON1 only if season.json has no episodes[] entry for this ep.
    ep_plan = next((e for e in season.get("episodes", []) if e.get("n") == ep), None)
    if ep_plan:
        title = ep_plan["title"]; level = ep_plan.get("level", "A2")
        situation = ep_plan.get("situation", "")
        arc_beat = ep_plan.get("arc_beat", "")
        phrases_theme = ep_plan.get("phrases", "")
        cliffhanger = ep_plan.get("cliffhanger", "")
        phonetic_focus = ep_plan.get("phonetic_focus")  # {target, note} per season plan
        voice_stage = str(ep_plan.get("voice", "S1")).replace("S", "")  # "S1"->"1"
    else:
        plan = next((p for p in SEASON1 if p[0] == ep), None)
        if not plan:
            print(f"ERROR: no plan for episode {ep} (not in season.json or SEASON1)",
                  file=sys.stderr); sys.exit(2)
        _, title, level, situation = plan
        arc_beat = phrases_theme = cliffhanger = ""
        phonetic_focus = None
        # derive stage from the season stage map if present
        sm = season.get("macal_stage_map", {"1":[1,2,3],"2":[4,5,6,7],"3":[8,9,10]})
        voice_stage = next((s for s, eps in sm.items() if ep in eps), "1")
    level = args.level or level
    show = season.get("show", "Yalla Fluent")

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
            rec = {"section": act_key, "speaker": sp,
                   "lang": l["lang"], "text": str(tx).strip()}
            d = l.get("direction")
            if d and str(d).strip():
                rec["direction"] = str(d).strip()   # acting note, never spoken (design §3.3)
            out.append(rec)
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
                                min_words, season, all_lines, expand=expand,
                                show=show, voice_stage=voice_stage, arc_beat=arc_beat,
                                phrases_theme=phrases_theme, cliffhanger=cliffhanger,
                                phonetic_focus=phonetic_focus)
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
    # model can still leak the COACH (Mahmoud) into a STORY section. Auto-correct the ONE
    # safe way — drop any COACH line that leaked into a STORY section (it's stray teaching
    # commentary; real teaching lives in the coach sections). NOTE: a STORY CHARACTER
    # speaking Arabic (e.g. Macal code-switching with family) is ALLOWED — bilingual realism
    # — so we drop on speaker=="Coach" only, NOT on lang=="ar". Then HARD-GATE on the validator.
    STORY = structure_check.STORY_SECTIONS
    kept, dropped = [], []
    for l in script["lines"]:
        if l.get("section") in STORY and l.get("speaker") == "Coach":
            dropped.append(l)
        else:
            kept.append(l)
    if dropped:
        print(f"  STRUCTURE: dropped {len(dropped)} stray Coach line(s) that "
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

    # PHRASE OF THE EPISODE (#2): fill en/ar. The coach_outro was written to name it;
    # ask the model to extract the single phrase-of-the-episode from the final script as
    # {en, ar}. Deterministic fallback: first target-phrase theme (en) + a simple AR gloss.
    def fill_phrase_of_episode(script, phrases_theme):
        transcript = "\n".join(
            f"[{l['section']}][{l['speaker']}/{l['lang']}] {l['text']}" for l in script["lines"]
        )
        prompt = (
            "From this bilingual English-learning drama episode, identify the SINGLE "
            "'phrase of the episode' — the one short, high-value English phrase the coach "
            "(Mahmoud) most wants the learner to walk away using. It must be a real English "
            "phrase spoken/taught in the episode (2-6 words, natural spoken English).\n\n"
            "Return STRICT JSON only, no commentary:\n"
            '{"en":"<the English phrase exactly>","ar":"<a short Egyptian-Arabic gloss of what it means, full tashkeel>"}\n\n'
            f"TARGET-PHRASE THEME (hint): {phrases_theme}\n\n"
            f"EPISODE TRANSCRIPT:\n{transcript}"
        )
        try:
            raw = call_gemini(prompt, temp=0.3)
            raw = raw.strip().replace("```json", "").replace("```", "").strip()
            m = re.search(r"\{[\s\S]*\}", raw)
            obj = json.loads(m.group(0) if m else raw)
            en = str(obj.get("en", "")).strip()
            ar = str(obj.get("ar", "")).strip()
            if en:
                return {"en": en, "ar": ar}
        except Exception as e:
            print(f"  phrase_of_episode: extraction failed ({str(e)[:60]}) — using fallback",
                  file=sys.stderr)
        # deterministic fallback: first phrase-theme token as the phrase, empty AR
        first = (phrases_theme or "").split(",")[0].strip()
        return {"en": first, "ar": ""}

    if not (script["phrase_of_episode"].get("en") and script["phrase_of_episode"].get("ar")):
        script["phrase_of_episode"] = fill_phrase_of_episode(script, phrases_theme)
    print(f"  phrase_of_episode: en='{script['phrase_of_episode'].get('en','')}' "
          f"ar='{script['phrase_of_episode'].get('ar','')[:30]}'")

    # record the phonetic focus in the saved script for downstream (packaging/coach notes)
    if phonetic_focus:
        script["phonetic_focus"] = phonetic_focus

    # Duration is INFORMATIONAL only (the 5-10 min hard gate was removed per owner
    # decision). We still print the estimate for awareness, but never block/save-fail.
    est_min = round(script["word_count"] / WPM, 1)
    print(f"  duration: ~{est_min} min (~{script['word_count']} words) — informational, no gate")

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
