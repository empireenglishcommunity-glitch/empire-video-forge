#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — Episode Script Generator.

Calls Gemini (via GEMINI_API_KEY env, the same key n8n's googlePalmApi cred holds)
to write ONE episode as validated JSON, using:
  - the series bible (cast, tone, Season 1 arc, episode template)
  - season.json (story-so-far, current episode #, speaker->voice map)
  - the target CEFR level for the episode

Output: episodes/epNN/script.json  (+ updates season.json)
The JSON is the contract for the voice pipeline: every line is tagged with a
speaker (-> a cloned Chatterbox voice or the Gemini Arabic Coach) and a lang.

Fail-soft: validates the model output; on malformed JSON it retries once, then
writes nothing and exits non-zero (never emit a broken script).

Usage:  GEMINI_API_KEY=... python3 gen_script.py [--episode N] [--level A2|B1|B2]
"""
import os, sys, json, re, argparse, urllib.request, time

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.dirname(HERE)
SEASON_PATH = os.path.join(os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"), "season.json")
MODEL = os.environ.get("EEC_SCRIPT_MODEL", "gemini-3.6-flash")  # text model for scripting (TTS is a separate model)

# ---- Season 1 plan (from series-bible.md) --------------------------------
SEASON1 = [
    (1, "The Arrival", "A2", "airport + taxi: small talk, directions"),
    (2, "The Apartment", "A2", "landlord/agent: numbers, requests, complaints"),
    (3, "The Interview", "B1", "the big job interview"),
    (4, "First Day", "B1", "meeting the team, introductions, small talk"),
    (5, "The Coffee Order", "A2", "ordering, chit-chat with the barista"),
    (6, "The Misunderstanding", "B1", "says the wrong thing; recovering politely"),
    (7, "The Meeting", "B2", "speaking up, giving an opinion"),
    (8, "Making a Friend", "B1", "social English, humor"),
    (9, "The Phone Call", "B2", "a tricky service call, no visual cues"),
    (10, "The Presentation", "B2", "the season payoff"),
]

DEFAULT_SEASON = {
    "season": 1,
    "current_episode": 1,
    "cast": {
        "Macal": {"role": "learner-hero", "voice_engine": "chatterbox", "ref": "macal_ref.wav"},
        "Nour":  {"role": "guide",        "voice_engine": "chatterbox", "ref": "nour_ref.wav"},
        "Coach": {"role": "teacher",      "voice_engine": "gemini",     "voice": "Kore", "lang": "ar"},
    },
    "guest_voices": {
        "guest_m1": {"ref": "guest_m1_ref.wav"},
        "guest_f1": {"ref": "guest_f1_ref.wav"},
    },
    "story_so_far": "Macal has just landed in Dubai to start a new life. He is nervous but determined. Nour is a confident friend who already settled here and helps him. The Coach explains the key English to the audience.",
    "phrases_taught": [],
}


def load_season():
    try:
        with open(SEASON_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(DEFAULT_SEASON)


def save_season(s):
    os.makedirs(os.path.dirname(SEASON_PATH), exist_ok=True)
    with open(SEASON_PATH, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def build_prompt(ep_num, title, level, situation, season):
    cast_names = ", ".join(season["cast"].keys())
    taught = ", ".join(season.get("phrases_taught", [])[-15:]) or "(none yet)"
    return f"""You are the head writer for "Two Worlds", a bilingual English-teaching podcast
by Empire English Community (EEC) for Arabic speakers (Egypt/MENA).

BRAND VOICE (strict): a disciplined, warm, honest coach. Real English, not exam tricks.
System, not hype. NEVER use "hack", "secret", "guaranteed", or fear-shaming.
Content Arabic = EGYPTIAN Arabic (Coach lines). English = natural, native American.

CAST: {cast_names}.
- Macal: Egyptian learner-hero in Dubai; his English is natural/native (voice-cloned).
- Nour: confident, warm, encouraging friend who already settled in Dubai.
- Coach: NOT in the story — the Egyptian-Arabic voice that pauses to teach the audience.
- Guests: minor roles for this situation (interviewer, barista, landlord, etc.).

STORY SO FAR: {season.get('story_so_far','')}
ALREADY-TAUGHT PHRASES (do not repeat as the phrase of the episode): {taught}

WRITE EPISODE {ep_num}: "{title}" — target CEFR level {level}. Situation: {situation}.

FIXED STRUCTURE (follow exactly, in this order):
1. cold_open hook (1 Macal or Nour line, ~1 sentence, creates curiosity/stakes).
2. scene1: the situation in real level-{level} English (Macal + others), 4-8 short lines.
3. coach_break1: Coach (Egyptian Arabic) explains 2 key phrases + 1 common mistake.
4. scene2: the situation continues/resolves, 3-6 short lines.
5. coach_break2: Coach (Egyptian Arabic) explains 1-2 more phrases + a culture note.
6. phrase_of_episode: ONE reusable phrase, with EN + Egyptian-Arabic meaning.
7. outro: Coach (Arabic) 1-2 lines: quick recap + a cliff-hook to the next episode + a
   short CTA (subscribe / join Telegram).

Return STRICT JSON ONLY (no markdown), EXACTLY this shape:
{{
  "episode": {ep_num}, "title": "{title}", "level": "{level}",
  "lines": [
    {{"section":"cold_open","speaker":"Macal","lang":"en","text":"..."}},
    {{"section":"scene1","speaker":"guest_m1","lang":"en","text":"..."}},
    {{"section":"coach_break1","speaker":"Coach","lang":"ar","text":"...","teaches":["phrase one","phrase two"]}},
    ...
  ],
  "phrase_of_episode": {{"en":"...","ar":"..."}},
  "shorts_highlight_hint": "which 1-2 lines make the best 30s Short",
  "next_episode_teaser": "one sentence",
  "story_update": "1-2 sentences: what changed in Macal's story this episode (for continuity)"
}}

Rules:
- Every line MUST have section, speaker (one of the cast/guest ids), lang ("en" or "ar"), text.
- Coach lines are ALWAYS lang "ar" (Egyptian Arabic). Story lines are lang "en".
- Keep English at level {level}: {level}=short simple sentences if A2; richer if B2.
- Natural spoken English (contractions, fillers) — not textbook.
- Keep it tight: total ~18-28 lines, a 4-7 minute episode."""


def call_gemini(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "response_mime_type": "application/json"},
    }
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
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group(0))
        raise


def validate(script):
    assert isinstance(script.get("lines"), list) and len(script["lines"]) >= 10, "too few lines"
    sections = set()
    for ln in script["lines"]:
        for k in ("section", "speaker", "lang", "text"):
            assert k in ln and str(ln[k]).strip(), f"line missing {k}: {ln}"
        assert ln["lang"] in ("en", "ar"), f"bad lang {ln['lang']}"
        if ln["speaker"] == "Coach":
            assert ln["lang"] == "ar", "Coach must be Arabic"
        sections.add(ln["section"])
    for req in ("cold_open", "scene1", "coach_break1"):
        assert req in sections, f"missing core section: {req}"
    p = script.get("phrase_of_episode", {})
    assert p.get("en") and p.get("ar"), "phrase_of_episode needs en+ar"
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, default=None)
    ap.add_argument("--level", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY", file=sys.stderr); sys.exit(2)

    season = load_season()
    ep_num = args.episode or season.get("current_episode", 1)
    plan = next((p for p in SEASON1 if p[0] == ep_num), None)
    if not plan:
        print(f"ERROR: no plan for episode {ep_num}", file=sys.stderr); sys.exit(2)
    _, title, level, situation = plan
    level = args.level or level

    prompt = build_prompt(ep_num, title, level, situation, season)

    script = None
    for attempt in (1, 2):
        try:
            raw = call_gemini(prompt, api_key)
            script = extract_json(raw)
            validate(script)
            break
        except Exception as e:
            print(f"attempt {attempt} failed: {str(e)[:200]}", file=sys.stderr)
            script = None
            time.sleep(2)
    if not script:
        print("ERROR: could not produce a valid script", file=sys.stderr); sys.exit(1)

    out = args.out or os.path.join(os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast"),
                                   "episodes", f"ep{ep_num:02d}", "script.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    # update season memory (continuity)
    if script.get("story_update"):
        season["story_so_far"] = (season.get("story_so_far", "") + " " + script["story_update"]).strip()[-1200:]
    poe = script.get("phrase_of_episode", {}).get("en")
    if poe:
        season.setdefault("phrases_taught", []).append(poe)
    season["current_episode"] = ep_num + 1
    save_season(season)

    print("OK wrote", out, "| lines:", len(script["lines"]),
          "| phrase:", script.get("phrase_of_episode"))


if __name__ == "__main__":
    main()
