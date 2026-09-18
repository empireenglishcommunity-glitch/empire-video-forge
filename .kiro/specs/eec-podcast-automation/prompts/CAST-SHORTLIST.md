# Two Worlds — Arabic Cast Shortlist (owner-filtered by pronunciation)

## Round 1: VoiceTut built-in voices — owner listened, filtered by mistakes
CLEAN (kept — no pronunciation errors, shippable candidates):
- **Sayed** — the COACH (full passage clean, owner liked it earlier too) ⭐
- Yasmin (F), Sarah (F) — female leads
- Omar, Essam, Ahmed, Abdullah (M) — male cast

HAD MISTAKES (filtered out — MSA-vs-Egyptian mispronunciation, fixable via
diacritized text and/or fine-tune):
- Abdelrahman, Kamal, Hossam, Mohamed, Zaki, Aly (M)
- Esraa, Hanan, Omnia (F)

## Decisions
- Sayed = Arabic Coach (lock as candidate pending full-episode confirmation).
- 7 clean voices already = a starting cast. Need a deeper bench (kids, old,
  Gulf, Levantine) -> more auditions from other models.

## Two owner questions -> plan
1. MORE voices to audition: yes — other VoiceTut settings + other Arabic models
   (Higgs-Egyptian, XTTS, SILMA, Gulf/Levantine voices). Build a bigger audition.
2. Fix the "mistake" voices: yes. Order of attack (cheap->heavy):
   a. Feed DIACRITIZED text (tashkeel fixes most MSA-vowel mistakes) — free, instant.
   b. Tune generation settings (num_step/guidance) — free.
   c. FINE-TUNE on Egyptian audio — fixes pronunciation at the source (heavier).
