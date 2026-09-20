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

## Accent-rework audition (B.6b) — BUILT: `kaggle/audition_accent_rework.py`
Owner chose the **C1 + Piper comparison**. The notebook A/B/C-tests three ways to get a
REAL accent for Macal (Egyptian/Arabic-L1) and Ravi (Indian/Hindi-L1):
- **A (C1)** — Qwen VoiceDesign as a *native Arabic / native Hindi speaker* speaking English
  (accent from L1 timbre, not a text label). Fully in-stack, Apache-2.0, no caveat.
- **B (Piper)** — real accented English from the **L2-ARCTIC** Piper voice
  (`en_US-l2arctic-medium`, 24 non-native speakers). **Arabic-L1:** ABA, YBAA, ZHAA, SKA;
  **Hindi-L1:** ASI, RRBI, TNI, SVBI. Accent is authentic (baked into the training data).
- **C (Piper→Qwen clone)** — clone the accented clip through Qwen VoiceClone (authentic
  accent + Qwen audio quality). Usually the winner. Also a C1→Qwen-clone variant (no Piper).

### Licensing findings (verified this session)
- **Qwen3-TTS** (A + the clone engine): **Apache-2.0** — clean, our default. The C1 and
  C1→clone routes are 100% clean.
- **Piper** `piper-tts` v1.8.0 = OHF-Voice `piper1-gpl`, **engine license GPL-3.0**. Running
  it server-side to *produce WAVs* is fine (audio output isn't a GPL derivative); we must NOT
  bundle/link piper's code into distributed software. Acceptable for our use.
- ⚠️ **L2-ARCTIC training data is research-licensed.** So a Piper-L2ARCTIC voice used
  DIRECTLY in commercial output is a gray area. Mitigation: prefer route **C1** (no L2-ARCTIC)
  or use Piper only as an **accent reference to clone from + concept proof**; CONFIRM the
  license before locking any Piper-derived voice for production (B.7). The audition itself
  is fine.

### Prior brainstorm (options considered)
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
