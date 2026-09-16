# Hybrid Editing Pipeline — Implementation Plan

> Implements `design.md` against `kaggle/generate_notebook.py` (source of truth
> for the `.ipynb`) and the n8n publishing workflow. Each task is built + tested
> on ONE real clip via the Kaggle bridge before moving on. Requirement refs in
> brackets. Ship each phase as its own PR with a test artifact.
>
> **Build status:** Phase 0 signed off (2026-09-16). Executing Phase 1.
>
> **Owner decisions (Phase 0.1, locked):**
> - Music: **rotate a few tracks per topic** (variety). [R5.3]
> - Long-form captions: **soft CC by default**, burned-in as per-video opt-in. [R3.2]
> - Intro/outro: **animated logo sting** (2–3s, logo + gold/navy motion). [R3.3]

---

## Phase 0 — Foundations & sign-off gate

- [x] **0.1 Approve spec.** Owner signed off; 3 decisions locked (see header):
  music=rotate per topic; long-form=soft CC default (+opt-in burn); intro=animated sting.
- [ ] **0.2 Confirm recording format is landscape 16:9.** [C4, R1.1, R3.1]
  - _Pending: owner to confirm future recordings are shot landscape._
- [ ] **0.3 Fetch + commit the channel logo** (from YouTube profile) into
  `assets/brand/` for intro/outro + thumbnails. [R6.1]

## Phase 1 — Shared pre-pass (helps BOTH tracks) ⭐ highest impact

- [x] **1.0 Format-agnostic orientation detection.** [R1.0, R1.1]
  - `kaggle/editing/orientation.py` auto-detects landscape/vertical/square from
    dims and returns the track plan (no manual flag). Owner sends ANY video.
  - _✅ Verified on owner's raw clip: correctly detected vertical (0.562) →
    plan: shorts native 9:16 + optional blurred-fill 16:9 long-form._

- [x] **1.1 Silence / dead-air removal.** [R2.2, R2.4] — DONE, validated on real EEC content
  - Implemented in `kaggle/editing/silence_removal.py` using **pure ffmpeg**
    (`silencedetect` + trim/concat). NOTE: `auto-editor` rejected — its binary
    needs GLIBC 2.38 which the Kaggle image lacks (confirmed on box 2026-09).
  - Configurable noise floor (-30dB), min-silence (0.6s), margin (0.15s).
  - _✅ Verified on the owner's RAW clip (english-pronunciation-tip): 41.5s → 37.1s,
    removed 4.5s (10.7%) of dead air; output 1080×1920 preserved, AAC audio intact,
    in sync. Fail-soft returns original on any error._
- [ ] **1.2 Light warm color grade.** [R2.3]
  - Single reusable ffmpeg filter; apply in pre-pass.
  - _Test: before/after frames pulled via bridge; confirm subtle, not oversaturated._
- [ ] **1.3 Persist word-level timings once (`words.json`).** [R2.1]
  - Ensure Whisper word timestamps are saved for reuse by CC + karaoke.
  - _Test: words.json has {word,start,end}; counts match transcript._

## Phase 2 — Long-form track (unlocks the thumbnail payoff)

- [ ] **2.1 Emit 16:9 long-form output + soft CC (AR+EN SRT).** [R3.1, R3.2]
  - Keep source aspect; generate AR.srt + EN.srt from words.json; write to
    `output/<brand>/long/`.
  - _Test: long/ file + sidecars present; ffprobe confirms 16:9._
- [ ] **2.2 Punchy 16:9 thumbnail (rembg cutout + gradient + bold Arabic + glow).** [R3.4]
  - Reuse the fixed 1280×720 brand-card code; add rembg cutout + glow.
  - _Test: view thumbnail; Arabic correct; 1280×720; on-brand._
- [ ] **2.3 Branded intro/outro concat.** [R3.3, R6.1]
  - Prebuild sting from logo; concat with matched res/fps + audio crossfade.
  - _Test: intro+outro present, no A/V glitch at seams._

## Phase 3 — Shorts karaoke captions (HARD — POC + sign-off first)

- [ ] **3.1 POC: RTL word-level karaoke on ONE clip.** [R4.3, R4.4, R7.4]
  - Per-word reshaped ASS events (raqm, direction=rtl); current word gold+scaled;
    3–5 word chunks; Tajawal Black; heavy outline; lower-center.
  - _Gate: pull frames via bridge → OWNER VISUAL SIGN-OFF before 3.2._
- [ ] **3.2 Integrate karaoke into the Shorts track.** [R4.1–R4.3]
  - Apply to each selected short after 9:16 reframe.
  - _Test: 2 shorts render with correct animated Arabic captions._
- [ ] **3.3 Subtle auto zoom-in variation (configurable, default on).** [R4.5]
  - _Test: push-in visible, not nauseating; toggle works._

## Phase 4 — Audio / music

- [ ] **4.1 Build the topic music library.** [R5.1, R5.3]
  - Download 3–5 royalty-free tracks per topic (Pixabay) into `assets/music/<topic>/`.
- [ ] **4.2 Topic-selected, ducked music bed (both tracks).** [R5.1, R5.2]
  - Select by topic + rotate; `sidechaincompress` under voice.
  - _Test: music present, ducks under speech, narration clear._

## Phase 5 — Publishing integration (n8n)

- [ ] **5.1 Route long/ → regular video, shorts/ → Short.** [R8.1, R8.2]
  - Update classify/metadata so `format` drives Short vs regular upload; long
    keeps `#Shorts` OFF (thumbnail shows), shorts keep it ON.
  - _Validate workflow (0 errors); deactivate→edit→reactivate per MCP rule._
- [ ] **5.2 End-to-end: one landscape master → long + shorts published.** [R1, R8]
  - _Test: both outputs land in Drive; n8n publishes each on the correct path;
    long-form shows custom thumbnail._

## Phase 6 — Hardening

- [ ] **6.1 Fail-soft wrappers on every enhancement.** [R7.2]
- [ ] **6.2 Update `run_batch.py` to sync `long/` + `shorts/` subfolders + thumbs.** [R1.2]
- [ ] **6.3 Update docs (README + OPERATIONS-GUIDE) with the hybrid workflow.**

---

## Execution rules (so nothing is forgotten)

1. Do phases in order; within a phase, tasks in order.
2. Never mark a task `[x]` until its test passes on a real clip.
3. Karaoke (3.1) is a hard gate — no integration before visual sign-off.
4. Each phase = its own PR with a test artifact (frame/clip) linked.
5. Keep `generate_notebook.py` as source of truth; regenerate `.ipynb` after edits.
