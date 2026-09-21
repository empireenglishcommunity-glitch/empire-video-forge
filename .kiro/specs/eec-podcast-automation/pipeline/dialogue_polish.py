#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Yalla Fluent" — ADVERSARIAL DIALOGUE-POLISH PASS.

Owner directive (no deferrals): every script starts a clip, so script quality is
just as mandatory as voice quality. A model reliably misses its OWN clichés and
stiff lines — but a SECOND, independent model reading cold catches them. This
module runs that second pass: DeepSeek writes the episode (gen_episode.py), then
Qwen-text (a genuinely different model family, via llm_backend's named "qwen"
engine) reads the STORY dialogue and hunts for exactly the failure modes generic
LLM dialogue falls into (on-the-nose lines, exposition-as-dialogue, every
character sounding the same, dead greetings, stiff idiom).

SCOPE — STORY LINES ONLY, never Coach/Arabic teaching lines:
    We learned this the hard way (FIX-004/FIX-009): a second model rewriting
    full-tashkeel Egyptian Arabic risks re-introducing exactly the diacritic/
    spelling mispronunciation bugs we spent real effort fixing (هنعيش, دبي).
    The polish pass is scoped to structure_check.STORY_SECTIONS (English +
    Macal's occasional Arabic code-switch is left untouched too — same reason).
    Coach lines get a SEPARATE, narrower Arabic-safe polish (tone/pacing notes
    only, never touching the diacritized text) — see polish_coach_direction().

SAFETY — the critic PROPOSES, it does not silently apply:
    Qwen returns {"idx": <line index>, "issue": "...", "rewrite": "..."} objects.
    Each rewrite is length-bounded (must stay a plausible spoken line, not an
    essay) and speaker-identity-preserving (the JSON contract doesn't allow it
    to change who's speaking). Callers can log rewrites and skip any that look
    unsafe; gen_episode.py applies them by default but keeps the pre-polish
    cache (_acts/*.json) so a bad polish pass is always revertible.

Usage (library):
    from dialogue_polish import polish_story_lines
    lines, report = polish_story_lines(all_lines, title, situation)
"""
import os, sys, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import llm_backend
import structure_check

STORY_SECTIONS = structure_check.STORY_SECTIONS
COACH_SPEAKER = getattr(structure_check, "COACH_SPEAKER", "Coach")

MAX_REWRITE_WORD_RATIO = 2.2  # a rewrite claiming to be a spoken line can't balloon


def _story_indices(lines):
    """Indices of lines eligible for polish: STORY section AND not Coach AND lang=='en'
    (Macal's Arabic code-switch lines are intentionally left untouched — same reasoning
    as Coach Arabic: a second model must not casually rewrite diacritized/scripted Arabic)."""
    out = []
    for i, l in enumerate(lines):
        if l.get("section") in STORY_SECTIONS and l.get("speaker") != COACH_SPEAKER \
                and l.get("lang") == "en":
            out.append(i)
    return out


def _critic_prompt(numbered_lines, title, situation):
    body = "\n".join(f"{i}: [{spk}] {txt}" for i, spk, txt in numbered_lines)
    return f"""You are a BLUNT, ADVERSARIAL script editor for a serialized audio drama
("{title}", scene: {situation}). Your ONLY job is to find lines that sound like
GENERIC AI DIALOGUE, not real human speech, and propose a punchier rewrite.

Hunt SPECIFICALLY for:
- On-the-nose lines that state a feeling instead of showing it ("I'm so nervous
  about this interview") — real people deflect, joke, or change the subject instead.
- Exposition disguised as dialogue ("As you know, we've been friends since college").
- Every character sounding the same register/vocabulary — flatten one, sharpen another.
- Dead, functional greetings/transitions that add nothing ("Hello, how are you today?").
- Clichéd idioms or dialogue-writing-101 phrases ("at the end of the day", "to be honest").
- A line that's too long/formal for how a real person would actually say it out loud.

DO NOT touch: line content that's plot-critical (the planted mistake, the corrected
form, the target phrase, the cliffhanger) — you may tighten HOW it's said, never
remove WHAT happens. DO NOT change who is speaking. Keep each rewrite roughly the
same LENGTH as the original (this is timed audio, not a rewrite of the scene).

Numbered lines (format "idx: [speaker] text"):
{body}

Return STRICT JSON only, a list of ONLY the lines that need a fix (skip anything
already good — most lines should need NOTHING):
[{{"idx": <int>, "issue": "<one short phrase: what's wrong>", "rewrite": "<ONLY the improved spoken words, same speaker, similar length>"}}]
CRITICAL: "rewrite" must be ONLY the words the character speaks out loud — this is
fed DIRECTLY to a text-to-speech engine. Do NOT prefix it with "[Speaker]", a name,
a colon, quotes, or any label — that label text would be spoken aloud as an error.
If every line is already good, return an empty list []."""


def _strip_speaker_label(text, speaker):
    """Belt-and-braces: a critic model sometimes echoes '[Speaker] ...' or 'Speaker: ...'
    from the prompt's own numbering format back into the rewrite. That label text would
    otherwise be SPOKEN by the TTS engine — strip it defensively (same spirit as
    gen_episode.py's _clean_text stripping stray brackets/asterisks from writer output)."""
    t = text.strip()
    t = re.sub(r"^\[\s*" + re.escape(speaker) + r"\s*\]\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\[[^\]]{1,40}\]\s*", "", t)          # any other bracketed label
    t = re.sub(r"^" + re.escape(speaker) + r"\s*:\s*", "", t, flags=re.IGNORECASE)
    return t.strip()


def _extract_json_list(raw):
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except Exception:
        m = re.search(r"\[[\s\S]*\]", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return []


def polish_story_lines(all_lines, title="", situation="", engine="qwen", critic_temp=0.4):
    """Run the adversarial critic over STORY lines only. Returns (new_lines, report).

    report = {"reviewed": int, "flagged": int, "applied": int, "skipped": [...]}
    Fail-soft: if the critic engine is unavailable or returns garbage, returns the
    ORIGINAL lines unchanged with an explanatory report — never blocks script generation."""
    idxs = _story_indices(all_lines)
    report = {"reviewed": len(idxs), "flagged": 0, "applied": 0, "skipped": [], "engine": engine}
    if not idxs:
        return all_lines, report

    numbered = [(i, all_lines[i]["speaker"], all_lines[i]["text"]) for i in idxs]
    prompt = _critic_prompt(numbered, title, situation)
    try:
        raw = llm_backend.chat(prompt, temperature=critic_temp, engine=engine)
    except Exception as e:
        report["error"] = f"critic engine unavailable: {str(e)[:120]}"
        return all_lines, report

    proposals = _extract_json_list(raw)
    report["flagged"] = len(proposals)
    idx_set = set(idxs)
    new_lines = list(all_lines)
    for p in proposals:
        try:
            i = int(p.get("idx"))
            rewrite = str(p.get("rewrite", "")).strip()
            issue = str(p.get("issue", "")).strip()
        except Exception:
            report["skipped"].append({"reason": "malformed proposal", "raw": p})
            continue
        if i not in idx_set or not rewrite:
            report["skipped"].append({"idx": i, "reason": "out of scope or empty"})
            continue
        orig = all_lines[i]["text"]
        rewrite = _strip_speaker_label(rewrite, all_lines[i]["speaker"])
        # safety bound: reject a "rewrite" that's really a rescoped essay
        if len(rewrite.split()) > max(3, len(orig.split()) * MAX_REWRITE_WORD_RATIO):
            report["skipped"].append({"idx": i, "reason": "rewrite too long vs original",
                                      "orig_words": len(orig.split()),
                                      "rewrite_words": len(rewrite.split())})
            continue
        new_lines[i] = dict(all_lines[i])
        new_lines[i]["text"] = rewrite
        new_lines[i]["_polish_note"] = issue  # kept for the fix-log / review, never spoken
        report["applied"] += 1
    return new_lines, report


def polish_coach_direction(coach_lines, engine="qwen", critic_temp=0.3):
    """NARROW Arabic-safe polish for Coach lines: the critic may ONLY suggest a
    'direction' (acting/pacing note, e.g. 'warmer, slower on the drill word') — it
    NEVER rewrites the diacritized Arabic text itself. This keeps FIX-004/FIX-009
    (light-touch lexicon, correct diacritics) fully intact while still getting a
    second opinion on delivery. Returns (new_lines, report)."""
    report = {"reviewed": len(coach_lines), "applied": 0, "engine": engine}
    if not coach_lines:
        return coach_lines, report
    body = "\n".join(f"{i}: {l['text']}" for i, l in enumerate(coach_lines))
    prompt = (
        "You are a warm podcast director reviewing an Egyptian-Arabic teaching host's "
        "lines. You may ONLY suggest a short DELIVERY note per line (pacing/warmth/energy, "
        "e.g. 'slower and warmer on the drill word', 'bright energy, quick pace'). "
        "You must NEVER rewrite, translate, or alter the Arabic text itself — only "
        "comment on HOW it should be performed.\n\n"
        f"Lines:\n{body}\n\n"
        'Return STRICT JSON only: [{"idx": <int>, "direction": "<short delivery note>"}]. '
        "Only include lines that need a specific note; skip lines that are already fine."
    )
    try:
        raw = llm_backend.chat(prompt, temperature=critic_temp, engine=engine)
    except Exception as e:
        report["error"] = f"critic engine unavailable: {str(e)[:120]}"
        return coach_lines, report
    proposals = _extract_json_list(raw)
    new_lines = [dict(l) for l in coach_lines]
    for p in proposals:
        try:
            i = int(p.get("idx"))
            direction = str(p.get("direction", "")).strip()
        except Exception:
            continue
        if 0 <= i < len(new_lines) and direction:
            new_lines[i]["direction"] = direction  # acting note only; never spoken (design contract)
            report["applied"] += 1
    return new_lines, report


if __name__ == "__main__":
    # tiny smoke test with obviously-bad lines, using the real engine
    demo = [
        {"section": "act1", "speaker": "Macal", "lang": "en",
         "text": "I am so nervous about this interview, to be honest."},
        {"section": "act1", "speaker": "Interviewer", "lang": "en",
         "text": "Hello, how are you today? Please, sit down."},
        {"section": "coach_intro", "speaker": "Coach", "lang": "ar", "text": "أَهْلًا بِيكُم"},
    ]
    out, rep = polish_story_lines(demo, title="Demo", situation="job interview")
    print(json.dumps({"report": rep, "lines": out}, ensure_ascii=False, indent=2))
