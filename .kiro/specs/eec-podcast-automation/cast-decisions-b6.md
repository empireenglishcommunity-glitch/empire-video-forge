# Yalla Fluent — cast picks & open items (Phase B, task B.6)

> Owner's audition picks from the B.5 Kaggle run (VoiceDesign, 36 clips). 8 of 10
> characters LOCKED-candidate. **2 sent back for rework** — Macal & TaxiDriver — because
> the described accent rendered as near-native American (the B.1-flagged VoiceDesign risk).

## ✅ Locked-candidate (owner-picked B.6) — 8 characters
| Character | Picked candidate | Accent target | Status |
|---|---|---|---|
| Nour | **cand2** | General American | locked-candidate |
| Tarek | **cand3** | polished Egyptian (near-native OK) | locked-candidate |
| Interviewer / Farida | **cand1** | Gulf English | locked-candidate |
| Barista / Aisha | **cand2** | Filipino English | locked-candidate |
| Landlord / Qureshi | **cand1** | Pakistani English | locked-candidate |
| Friend_F | **cand1** | light expat | locked-candidate |
| Official | **cand2** | Gulf formal | locked-candidate |
| Friend_M | **cand1** | light expat | locked-candidate |

_(Tarek is intentionally near-native/polished, so American-leaning is fine for him.)_

## ⚠️ REWORK — accent did not render (2 characters)
Owner feedback: **"no Egyptian accent at all — pronouncing perfect"** (Macal, all 3 stages)
and **"no Indian accent, pure American"** (TaxiDriver/Ravi). This is the documented
VoiceDesign limitation: a *described* non-native/regional accent tends to collapse to
clean American. These two need a stronger approach (see brainstorm below).

- **Macal** — needs a genuine Egyptian-L2 English colour, esp. **Stage 1** (Stage 3 near-
  native is fine; the ARC is the point, so S1→S3 must actually travel).
- **TaxiDriver / Ravi** — needs a genuine Indian (Kerala) English colour.

## Brainstorm — how to get the accents (decision pending owner)
See the chat for the full options discussion; candidate strategies:
1. **Real reference audio → VoiceClone** (strongest): clone from a short real Egyptian-
   English / Indian-English sample instead of designing from text. Qwen3-TTS clones accent
   from the ref. Needs a rights-clean reference clip per accent.
2. **CustomVoice built-in speakers**: the `-CustomVoice` model ships 9 premium timbres
   with dialect coverage — check if any fit, usable as-is or as clone seeds.
3. **Heavier acoustic-marker prompts + phonetic spelling** in VoiceDesign (cheapest;
   already the weakest lever — owner just proved plain descriptions fail).
4. **Script-level L2 reinforcement** (complementary): keep Macal's written L2 phrasing/
   hesitation so even a lighter accent still *reads* as a learner.
5. **Fallback engine** for these voices only (e.g. a TTS with explicit accent presets),
   if Qwen can't hit it.

**Decision:** _pending owner pick from the brainstorm._
