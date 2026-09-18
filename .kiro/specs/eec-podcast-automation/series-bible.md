# "Two Worlds" — Series Bible (v1)

> The creative source of truth for the EEC podcast. Everything the script generator,
> voices, and visuals must stay consistent with. Brand: Empire English Community —
> mindset-first, "real English not exam tricks," honest, Egyptian-Arabic audience.

## 1. The premise (one line)
**Macal, a smart, ambitious Egyptian who just moved to Dubai for a fresh start, has to
survive and rise in an all-English world — one real conversation at a time. A Coach
(our voice in his ear, and yours) breaks down what actually happened, so you learn the
exact English Macal needed.**

Why this premise works:
- **Relatable + aspirational** — mirrors the founder story and the audience's dream
  (a Gulf opportunity, a better life). Learners see themselves in Macal.
- **Real, situational English** — every episode is a real place a learner will actually
  be: a job interview, a landlord, a coffee shop, a team meeting, a first friendship.
- **Built-in stakes + continuity** — Macal has a goal (land the job, build a life), so
  each episode has a reason to exist AND a reason to return (season arc).
- **The Coach = the EEC brand** — honest, encouraging, "we fix the fear first."

## 2. The cast

### Macal — the learner-hero (English, learner-level, improving)
- Egyptian, late 20s. Sharp, funny, a little proud, sometimes nervous. Makes the exact
  mistakes Arabic speakers make (so the learner sees their own errors, safely).
- His English visibly improves across the season (an emotional payoff = motivation).
- Voice: warm male, slight accent early on, clearer over time.

### Nour — the confident guide (English, natural/fluent)
- Egyptian-British, grew up between Cairo and London. Macal's colleague/friend who already
  made it. Kind but direct. Models natural, idiomatic English.
- Voice: confident female, neutral clear accent.

### The Coach — the teacher (Egyptian Arabic; the EEC voice)
- Not a character in the story — the voice that pauses the scene and explains: the key
  phrase, the mistake Macal made, the cultural note, the "phrase of the episode."
- Warm, funny, honest coach. Egyptian Arabic. Never "hack/secret/guaranteed."
- Voice: warm Egyptian-Arabic male (the founder-style mentor).

### Rotating guest voices (per situation)
- The interviewer, the barista, the landlord, the taxi driver, the boss. 1–2 per
  episode, distinct voices, small roles. Keeps the world alive without new regulars.

## 3. Tone & rules
- **Funny but never silly.** Real situations, light humor, genuine warmth.
- **English is real, not textbook** — contractions, fillers, idioms at the right level.
- **The Coach speaks the audience's language** (Egyptian Arabic) and respects their
  intelligence — encouraging, honest, practical. Follows EEC honesty guardrails.
- **Every episode leaves the learner with something reusable** (phrases, not trivia).
- **Progress is visible** — Macal gets a little better; the learner feels it's possible.

## 4. Season 1 arc (10 episodes) — "Landing in Dubai"
A light throughline so episodes connect (each still works standalone):
1. **The Arrival** — airport + taxi. Small talk, directions. (A2)
2. **The Apartment** — dealing with a landlord/agent. Numbers, requests, complaints. (A2)
3. **The Interview** — the big job interview. (B1) [tent-pole episode]
4. **First Day** — meeting the team, introductions, small talk. (B1)
5. **The Coffee Order** — casual English, ordering, chit-chat with the barista. (A2)
6. **The Misunderstanding** — Macal says the wrong thing; how to recover politely. (B1)
7. **The Meeting** — speaking up in a work meeting, giving an opinion. (B2)
8. **Making a Friend** — Nour invites Macal out; social English, humor. (B1)
9. **The Phone Call** — a tricky customer/service call (no visual cues). (B2)
10. **The Presentation** — Macal presents; the payoff of the season. (B2) [finale]

Difficulty rises across the season (A2 -> B2) so learners grow with Macal.

## 5. Fixed episode template (~4-7 min long-form)
1. **Cold-open hook (3s)** — a punchy line/stakes ("Macal's interview starts in 60
   seconds — and he just forgot the word for 'experience'").
2. **Scene 1** — the situation plays out in real English (Macal + others).
3. **Coach break 1** — pause: the key phrase + why + the mistake to avoid (Arabic).
4. **Scene 2** — the situation continues / resolves.
5. **Coach break 2** — 1-2 more phrases + cultural note (Arabic).
6. **Phrase of the Episode** — one takeaway phrase, said 3 ways, drilled.
7. **Cliff-hook + CTA** — tease next episode + subscribe/Telegram/placement test.

## 6. Recurring signatures (the "show" feel)
- **"Phrase of the Episode"** — same segment every time; becomes a habit/expectation.
- **The Coach's catchphrase** open/close (e.g. a warm Egyptian-Arabic sign-off).
- **Consistent intro/outro sting** (gold-on-black brand ident).
- **Consistent character scene cards** + captions style.
- Episode titles follow a pattern: "Two Worlds · EpN — <Situation> (Level)".

## 7. What we lock now vs. test later
- **Lock:** premise, cast roles, tone, season arc, episode template, signatures.
- **Test in Phase 1:** exact Piper voices per character (the voice sample sheet gate) —
  including whether the Arabic Coach voice is good enough or needs a fallback.
- **Test in Phase 4:** visual style of the character scene cards.

## 8. Locked decisions (owner-approved)
- Cast: **Macal** (learner-hero — ties to the MACAL EMPIRE brand) / **Nour** (fluent
  guide) / **the Coach** (Egyptian-Arabic EEC voice). LOCKED.
- City: **Dubai**. LOCKED.
- Season length: **10 episodes**, weekly (~one season per quarter). LOCKED.

## 9. Still tested later (not creative — technical)
- Exact Piper voices per character (Phase 1 voice sample sheet gate).
- Character scene visual style (Phase 4 gate).


## 10. STRUCTURE RULE — story vs. teaching separation (LOCKED, machine-enforced)

> Why this exists: an episode is audio. If the Coach's Arabic commentary is
> sprinkled *inside* a live English scene, the listener gets language whiplash
> (English tension → sudden Arabic aside → English) and it sounds messy. The fix
> is a hard rule, enforced by `pipeline/structure_check.py` at generation time AND
> before assembly — a violating script can never be assembled/shipped.

**Two kinds of section:**
- **STORY sections** (in-world scene, English drama): `cold_open`, `act1`, `act2`,
  `act3`, `act4`.
- **COACH sections** (teaching, Egyptian Arabic): `coach_intro`, `coach_break1`,
  `coach_break2`, `coach_break3`, `coach_outro`.

**The rules (all enforced):**
1. **`cold_open` is a PURE story hook** — only in-world characters (Macal, guests),
   English. **No Coach line, no Arabic, in the cold_open.** The Coach first speaks
   in `coach_intro`.
2. **The Coach speaks ONLY in COACH sections.** No Coach line may appear inside any
   STORY section. Teaching happens in its own beat, never mid-scene.
3. **Story characters speak ONLY in STORY sections.** No in-world dialogue leaks into
   a COACH section.
4. **Canonical section order** (a scene, then its breakdown, repeating):
   `cold_open → coach_intro → act1 → coach_break1 → act2 → coach_break2 → act3 →
   coach_break3 → act4 → coach_outro`. (Episodes may use fewer acts/breaks, but a
   COACH break must follow the STORY scene it explains — never split a scene.)
5. A COACH breakdown may be several consecutive Coach lines (that's fine — it's one
   teaching beat); what's forbidden is putting those lines *inside* a story section's
   idx range.

**Result:** playback is always "full English scene → clean cut to Coach breakdown →
next scene," which is the professional format the series was designed around (§5).
