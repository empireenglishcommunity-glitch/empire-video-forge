# Two Worlds — Arabic Voice: SOLVED ✅ (2026-09-18)

## The breakthrough
The Arabic quality problem is SOLVED without fine-tuning. Root cause was never the
voice — it was specific hard/colloquial words (e.g. "الجداد") that the model read
the MSA way. Fix: VoiceTut's built-in lexicon override — map each hard word to a
diacritized Egyptian spelling. Owner confirmed "amazing": with the lexicon applied,
the previously-failing words now pronounce correctly, in the good voices.

## What this means (big)
- The "mistake" voices weren't bad voices — they stumbled on words. With the lexicon
  they're USABLE. Our cast just got much bigger (potentially all/most of the 17).
- NO fine-tune needed for pronunciation. Fine-tune is now only an optional future
  enhancement (new dialects/voices VoiceTut lacks), not a blocker.
- The engine is settled: VoiceTut built-in voices + Egyptian lexicon = shippable
  Egyptian Coach + cast.

## The system (locked)
1. VoiceTut built-in voices as the cast (Sayed=Coach + the others).
2. egyptian_lexicon.json — growing pronunciation dictionary; applied via add_lexicon
   before every synth. Solve each hard word once -> whole cast says it right forever.
3. As scripts are written, new hard words get added to the lexicon (a quick review step).
4. Generation at num_step=64, guidance=2.5 (top quality).

## Next
- Re-audition the full 17 voices WITH the lexicon -> lock the final cast (Arabic).
- Build lexicon-aware synth into the pipeline (auto-apply lexicon to every line).
- Then: English cast (Chatterbox) + the 30-min story generator + produce Ep1.
