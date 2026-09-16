# Hybrid Editing Pipeline — Implementation Plan

> Implements `design.md` against `kaggle/generate_notebook.py` (source of truth
> for the `.ipynb`) and the n8n publishing workflow. Each task is built + tested
> on ONE real clip via the Kaggle bridge before moving on. Requirement refs in
> brackets. Ship each phase as its own PR with a test artifact.
>
> **Build status:** NOT STARTED — spec awaiting owner sign-off.

---

## Phase 0 — Foundations & sign-off gate

- [ ] **0.1 Approve spec.** Owner reviews requirements/design; confirms the 3
  open decisions (music variety depth; long-form burned vs soft CC; intro style).
- [ ] **0.2 Confirm recording format is landscape 16:9.** [C4, R1.1, R3.1]
- [ ] **0.3 Fetch + commit the channel logo** (from YouTube profile) into
  `assets/brand/` for intro/outro + thumbnails. [R6.1]

## Phase 1 — Shared pre-pass (helps BOTH tracks) ⭐ highest impact

- [ ] **1.1 Silence / dead-air removal.** [R2.2, R2.4]
  - Add `auto-editor` install + a pre-pass step producing `master_clean.mp4`.
  - Configurable gap threshold (default 0.5s) + speech margin; re-probe duration.
  - _Test: one clip; verify pacing tighter, audio in sync, no clipped words._
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
