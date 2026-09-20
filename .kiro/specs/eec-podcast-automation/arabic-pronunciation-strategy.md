# Arabic Pronunciation — root-cause strategy (Mahmoud / VoiceTut)

> Fixing Egyptian pronunciation at the ROOT, not word-by-word. Consolidates the owner's
> feedback, a developer review, and deep research. **Decision gated on one diagnostic test.**

## The mistakes the owner heard (Mahmoud)
- **جماعة / إنجليزي:** ج pronounced soft "j" — but **Egyptian ج = hard "g"** (like "game").
- **يلا:** the mad/alif vowel too open ("a" like apple) — should be the "o/aw" (like "mom").
- **معاكم:** off.
- **وقفة:** ق pronounced hard "q" — Egyptian urban = **glottal stop (hamza)**, "wa'fa".
- **متفهمش:** robotic, "spelled-out" — wrong syllabification.

## Two competing root-cause hypotheses
- **H1 (what we first assumed):** VoiceTut is MSA-biased; we must add tashkeel + phoneme rules.
- **H2 (new evidence — likely the truth):** **VoiceTut is ALREADY an Egyptian model** —
  fine-tuned on **~380 h of Egyptian podcasts**, ships its **own "robust Egyptian normalization
  pipeline + diacritics dictionary"**, and its own docs feed it **BARE** text ("ازيك عامل ايه
  النهاردة؟"). So it *natively* knows ج=g, ق=ʾ. **Our `prepare_ar()` heavy MSA-style tashkeel
  may be FIGHTING the model and CAUSING the errors** (the old يلا→يَاللَّا bug was exactly this:
  OUR entry was wrong, not the model). We may be "correcting" it into mistakes at scale.

**This must be tested before we build anything** — building phoneme rules on top of H1 when H2
is true would make things worse. Test = `kaggle/diagnose_arabic_pronunciation.py`: each problem
word rendered BARE vs OUR-LEXICON vs IN-SENTENCE; owner reports which is correct.

## Deep-research findings (verified)
- **Egyptian ج → hard /g/** almost always (the g/ǧ question; urban Cairene = /g/).
- **Egyptian ق → glottal stop /ʔ/ (hamza)** in colloquial words — BUT **NOT always**:
  MSA loanwords, religious & classical/formal vocabulary KEEP the qaf: **قرآن، ثقافة، قانون،
  القاهرة، مستقبل، دقيقة**, etc. (sources: Egyptian Arabic phonology; multiple refs.)
  → **A blind ق→ء rule is WRONG** (would say "الئاهرة", "ئانون") — the developer's key catch.
- **VoiceTut = Apache-2.0**, Egyptian-first, code-switching, 17 voices, its own normalization.

## Developer review — 3 upgrades to the phoneme-rule idea (adopted)
1. **ق needs a HYBRID: general rule + EXCEPTIONS dictionary.** Convert ق→hamza colloquially,
   but keep a small list of classical/loan words (قانون، قاهرة، ثقافة، قرآن، مستقبل، دقيقة…) as qaf.
2. **Prefer SSML / phonetic tags over character-hacking** IF VoiceTut supports them (cleaner,
   pro-grade — forces "hard G" without mangling spelling). Verify support; else fall back to respelling.
3. **Radical option = a fine-tuned Egyptian model.** Not needed if VoiceTut (already Egyptian)
   + a thin filter works. Kept as a documented fallback, not the plan.

## The decision tree (after the diagnostic test)
- **If BARE is correct** (H2 confirmed): **STOP over-tashkeeling.** Feed VoiceTut bare/lightly-
  normalized text; SHRINK the lexicon to only genuine fixes; drop the 818-word tashkeel factory
  as mostly unnecessary. Biggest, simplest win.
- **If OUR-LEX is correct** (H1): keep the lexicon, fix bad entries, and add the hybrid
  ق-rule + ج→g handling (SSML if supported, else careful respelling + exceptions list).
- **If NEITHER** (some words): targeted phoneme rules for those, hybrid + exceptions, verified by ASR.

## What we do NOT do
- ❌ No blind ق→hamza (breaks قانون/قاهرة/ثقافة).
- ❌ No word-by-word grind for systematic sounds (the owner's rejected "shit, waste of time").
- ❌ No ElevenLabs/proprietary source (licensing).
- ❌ No building rules on an unverified hypothesis — the diagnostic decides first.

## Alternative Egyptian TTS engines found (documented, in case)
Commercial-safe options if VoiceTut can't be tuned: **EGTTS (XTTS-v2 Egyptian)**, **F5-TTS
Egyptian**, MMS. XTTS core is non-commercial (CPML) — verify per-checkpoint before adopting.

## Status
Diagnostic test built (`diagnose_arabic_pronunciation.py`). **Owner runs it → reports which
variant is correct per word → we pick the strategy branch above.** Mahmoud speed = 0.80 (locked).
