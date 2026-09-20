# Yalla Fluent — Voice-Design specs (Phase B, task B.2)

> The natural-language `instruct` descriptions fed to **Qwen3-TTS VoiceDesign**
> (`Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`, `generate_voice_design(text, language, instruct)`)
> to invent each character's voice in the audition (B.4). The owner (casting director)
> picks the winner per character (B.6); the winning take becomes the canonical `voice_ref`
> for VoiceClone in production (Option B).
>
> **All grounded in `series-bible.md`** (character origins/accents) + the locked Macal
> stage map. Each character has **3–4 candidates** so the owner has real choice.
> `language="English"` for all (Mahmoud/Arabic stays on VoiceTut — not designed here).
>
> **Accent-fidelity note (the primary audition risk, per design §risk-table):** L2 /
> regional English accents may render as plain American because they aren't native dialect
> profiles. Mitigation baked into every non-American description below: **explicit acoustic
> markers** (specific consonant/vowel/rhythm cues), not just a nationality label. Reinforced
> at the script level too (Stage-appropriate L2 phrasing already written into the lines).

Legend: 🎯 = the description that best matches the bible (recommended default to audition first).

---

## 1. Macal — learner-hero · Egyptian, 27, from Alexandria · **3 STAGE voices (one identity)**
One person, evolving. Audition all three stages; save 3 canonical refs. Keep a **consistent
core timbre** (same man) — only fluency/rhythm/confidence change across stages.

### Macal — Stage 1 (Eps 1–3): clear Egyptian L2, hesitant
- 🎯 **S1a:** `Young adult male, late twenties, native Arabic speaker from Alexandria Egypt speaking English as a second language. Clear Egyptian L2 accent: lightly rolled/tapped r's, crisp fully-released T sounds, pure un-reduced vowels (little schwa), syllable-timed Arabic rhythm. Deliberate, slightly slow pacing with small hesitations; earnest, warm, a little nervous. Avoids contractions.`
- **S1b (stronger accent):** `Egyptian man, ~27, speaking careful English. Noticeable Arabic-transfer accent — tapped r, hard T and D, /p/ drifting toward /b/, emphatic dark consonants, flat even stress. Speaks slowly and thoughtfully, as if translating in his head. Sincere and hopeful.`
- **S1c (subtler accent):** `Warm young Egyptian male voice speaking English with a mild, clear non-native accent and gentle hesitation. Understandable and likeable, slightly formal, avoids slang. Earnest tone.`

### Macal — Stage 2 (Eps 4–7): more fluent, softening
- 🎯 **S2a:** `The same young Egyptian man, now more fluent in English. Accent softening — some flap-T and linking appear, contractions ("I've", "I'm") used naturally, occasional quick self-correction. Faster, more relaxed rhythm but still a light Egyptian colouring. Growing confidence, warm.`
- **S2b:** `Young Egyptian male, upper-intermediate English. Mostly smooth with occasional L1-transfer rhythm on longer sentences; comfortable, conversational, mildly accented. Optimistic and steady.`

### Macal — Stage 3 (Eps 8–10): confident, near-American
- 🎯 **S3a:** `The same man, now confident and near-native in English. Rhythm close to General American — natural reductions ("gonna", "wanna"), smooth linking, native-like stress and intonation — with only a faint trace of his Egyptian origin. Can joke, persuade, negotiate. Assured, warm, grounded.`
- **S3b:** `Young Egyptian-American-sounding male, fluent and expressive English, subtle warmth of a non-native origin nearly polished away. Relaxed, charismatic, capable of emotional range from playful to sincere.`

---

## 2. Nour — American target-accent model · born & raised in Chicago, 29 · **native General American**
The pronunciation model the whole show teaches toward. Must be unmistakably American — NOT
British, NOT Egyptian-raised.
- 🎯 **N1:** `Adult female, 29, born and raised in Chicago, USA. Warm, confident, clear General American accent — natural flap-T (water→"wader"), full linking and reductions, relaxed native rhythm. Encouraging, friendly, articulate; the kind of voice you'd trust to teach you.`
- **N2:** `Confident young American woman, Midwestern General American accent, warm midrange, expressive and natural. Professional but approachable — a supportive colleague.`
- **N3:** `Warm, bright American female voice, clear neutral US accent, easy conversational pace, genuine and reassuring.`

---

## 3. Tarek El-Masry — the rival · Egyptian, 30, Cairo/AUC · **polished, fast, impressive English**
Egyptian like Macal, but the opposite delivery: fluent, slick, confident — hides
vulnerability behind charm. (Contrast with Macal S1/S2 is the point.)
- 🎯 **T1:** `Adult male, 30, Egyptian from Cairo, highly fluent and polished English with only a faint accent. Fast, articulate, charismatic and a little slick — a confident presenter who loves the room. Warm surface, competitive underneath.`
- **T2:** `Confident Egyptian man, near-native English, quick smooth delivery, persuasive and charming, subtle Cairo colouring. Impressive but guarded.`
- **T3:** `Smooth, energetic male voice, cosmopolitan lightly-accented English, salesman-charming, crisp and quick.`

---

## 4. Interviewer / Ms. Farida Al-Mansoori — Emirati HR lead · 40, Gulf English, dry humor
Recurring authority (24 lines). Gulf-Arabic-accented professional English, dry wit,
impatient with performance, wants truth.
- 🎯 **F1:** `Adult female, 40, Emirati from the Gulf, professional English with a light Gulf-Arabic accent — measured, precise, slightly clipped. Dry, composed, quietly authoritative; unimpressed by flattery. A senior executive who has heard every rehearsed answer.`
- **F2:** `Composed Gulf-Arab businesswoman, clear accented English, calm and direct with a hint of dry humor. Professional, discerning.`
- **F3:** `Mature female voice, subtle Middle-Eastern English accent, poised and measured, authoritative but not cold.`

---

## 5. Barista / Aisha Santos — Filipina, 24, Manila · Filipino English
Bright café worker, over-apologizes, secretly studying for IELTS.
- 🎯 **A1:** `Young female, 24, Filipina from Manila, friendly Filipino English accent — clear syllable-timed rhythm, crisp consonants, gently melodic intonation, occasional rising tone. Bright, upbeat, eager to please, slightly apologetic.`
- **A2:** `Cheerful young Filipina, clear Filipino-accented English, warm and helpful, quick friendly pace.`
- **A3:** `Bright young female voice, light Southeast-Asian English accent, sunny and polite service tone.`

---

## 6. Landlord / Mr. Qureshi — Pakistani, 55, in Dubai since 1985 · Pakistani English
Rigid about rules; sees his estranged son in Macal; tests responsibility.
- 🎯 **Q1:** `Older male, 55, Pakistani, speaking English with a Pakistani/Urdu accent — retroflex t/d, rolled r, deliberate measured delivery, formal older-generation phrasing. Steady, mature, a bit stern but not unkind; a man used to being obeyed.`
- **Q2:** `Mature Pakistani man, clear South-Asian English accent, slow authoritative pace, formal and firm with underlying warmth.`
- **Q3:** `Older male voice, Urdu-accented English, grave and steady, patriarchal.`

---

## 7. TaxiDriver / Ravi Menon — Indian, 42, from Kerala · Indian English
Warm working-man; 12 years in Dubai; writes Malayalam poetry; tests small talk with kindness.
- 🎯 **R1:** `Adult male, 42, Indian from Kerala, warm Indian English accent — retroflex consonants, rolled/tapped r, melodic sing-song intonation, syllable-timed rhythm, monophthong vowels. Friendly, chatty, easygoing working-man warmth.`
- **R2:** `Middle-aged South-Indian man, clear Indian English accent, relaxed talkative and kind, gentle humor.`
- **R3:** `Warm male voice, Indian English accent (Kerala colouring), easygoing and good-natured.`

---

## 8. Friend_F — minor female friend (11 lines)
No fixed bible identity → cast for warmth + realism (Dubai-expat peer). **Owner decision:
gets its OWN designed voice** (no reuse), distinct from Nour/Aisha/Farida.
- 🎯 **FF1:** `Young adult female, warm friendly English with a light international/expat accent, natural conversational pace, upbeat and supportive peer.`
- **FF2:** `Bright young woman, neutral mildly-accented English, casual and warm.`
- **FF3:** `Friendly female voice, clear English, relaxed and encouraging.`

---

## 9. Official — minor role (2 lines)
Airport/office official; composed, formal. **Owner decision: gets its OWN designed voice**
(no reuse), distinct from Qureshi/Farida.
- 🎯 **O1:** `Adult male, composed formal English with a light Gulf accent, polite and businesslike, neutral authority.`
- **O2:** `Mature male voice, professional accented English, courteous and efficient.`

---

## 10. Friend_M — minor male friend (1 line)
No fixed identity. **Owner decision: gets its OWN designed voice** (no reuse), distinct
from Macal/Tarek/Ravi.
- 🎯 **FM1:** `Young adult male, casual friendly English with a light expat accent, easygoing peer tone.`
- **FM2:** `Relaxed young man, neutral mildly-accented English, warm and informal.`

---

## Casting summary (what the audition renders)
| # | Character | Voice(s) needed | Accent target | Fidelity risk |
|---|---|---|---|---|
| 1 | **Macal** | **3** (S1/S2/S3) | Egyptian L2 → near-American arc | **HIGH** (primary risk) |
| 2 | **Nour** | 1 | General American | low |
| 3 | Tarek | 1 | polished Egyptian | med |
| 4 | Interviewer/Farida | 1 | Gulf English | med |
| 5 | Barista/Aisha | 1 | Filipino English | med |
| 6 | Landlord/Qureshi | 1 | Pakistani English | med |
| 7 | TaxiDriver/Ravi | 1 | Indian English | med |
| 8 | Friend_F | 1 (own) | light expat | low |
| 9 | Official | 1 (own) | Gulf formal | low |
| 10 | Friend_M | 1 (own) | light expat | low |

✅ **Owner decision (B.3): every role — including the minor ones (Official / Friend_M /
Friend_F) — gets its OWN designed voice. No reuse.**

**Count:** 10 English speaking characters. Macal = **3** stage voices; the other 9 = **1**
each → **12 distinct English voices** to design/audition. (Mahmoud/Arabic is separate on
VoiceTut — not auditioned here.)

## B.3 review — OUTCOME (owner-approved)
✅ **B.3 SIGNED OFF.** Owner approved Macal's 3-stage arc + all guest personalities as
drafted, with ONE change: **each minor role (Official / Friend_M / Friend_F) gets its own
designed voice — no reuse.** Roster is now **12 distinct English voices** (Macal ×3 + 9).
Proceeding to B.4 (build the audition notebook).

## Notes carried into the audition (B.4–B.6)
- **Macal's arc is the make-or-break.** If S1's Egyptian L2 accent renders as plain American
  in the audition, that's the flagged risk — we'll strengthen the acoustic markers, lean on
  script-level L2 phrasing, or (last resort) discuss a fallback. Worth listening to Macal S1
  first and hardest.
- Guest accents are kept **clear and level-appropriate** (bible rule) — authentic but never
  so thick they block an A2/B1 learner.
