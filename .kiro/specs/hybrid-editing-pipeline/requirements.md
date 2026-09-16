# Hybrid Editing Pipeline — Requirements

> **Format-agnostic:** accept ANY input (vertical, landscape, or square) and
> automatically produce the right polished outputs — Shorts (9:16) always, plus
> a long-form 16:9 (where a proper landscape source exists, or a blurred-fill
> long-form from vertical if desired). Edited to a quality that matches strong
> Arabic-education creators. Grounded in a real analysis of
> reference creator @fatmhisoka and the constraints of the YouTube publishing
> engine (see `../youtube-publishing-engine/` in empire-server-forge).
>
> Format: EARS-style, testable. Each requirement has an ID used by `design.md`
> and `tasks.md`.

---

## Context & constraints (facts we must design around)

- **C1.** YouTube auto-classifies any vertical/square video ≤ 3 min as a Short,
  regardless of the `#Shorts` hashtag.
- **C2.** Custom thumbnails only display on regular (non-Shorts) videos unless
  the channel is in the YouTube Partner Program (1,000+ subs). The channel is
  currently pre-YPP (~13 subs).
- **C3.** The Shorts feed autoplays full-screen and never shows a thumbnail;
  captions must be **burned in** for Shorts (soft CC is not shown in-feed).
- **C4.** Editing runs on the free Kaggle GPU via the existing `remote_exec_bridge`
  + `run_batch.py` flow; all tools must be free / open-source.
- **C5.** Content is Egyptian-Arabic English lessons; Arabic text is RTL and must
  render with correct letter-joining (raqm), never garbled.

---

## R1 — Format-agnostic, adaptive output

- **R1.0** The system SHALL auto-detect the source orientation (from width/height)
  and adapt without any manual flag:
  - **Landscape (w>h):** long-form 16:9 (native) + Shorts 9:16 (face-tracked crop).
  - **Vertical (h>w):** Shorts 9:16 (native) + OPTIONAL long-form 16:9 via
    blurred-fill (vertical centered on a blurred 16:9 background).
  - **Square (w≈h):** Shorts native + optional blurred-fill 16:9 long-form.
- **R1.1** The system SHALL ALWAYS produce at least the Shorts output(s) (1–3
  clips) for any input, and SHALL produce a long-form output when the source is
  landscape (or when blurred-fill long-form is enabled for vertical/square).
- **R1.2** The system SHALL write long-form output to `output/<brand>/long/` and
  short output to `output/<brand>/shorts/`, preserving the brand-routing rule
  (folder-in → folder-out, one-to-one) already used by the batch runner.
- **R1.3** IF no moment clears the Shorts quality threshold, THEN the system
  SHALL still produce the long-form output and simply emit zero shorts (never
  fail the whole job).
- **R1.4** Each output SHALL have a matching `<name>_metadata.json` sidecar
  carrying title, hook, caption, topic, duration, and `format` (`long`/`short`).

## R2 — Shared pre-pass (applied once, before splitting)

- **R2.1** The system SHALL transcribe the source with Whisper large-v3 and
  retain **word-level** timestamps.
- **R2.2** The system SHALL remove silence / dead-air so no silent gap exceeds a
  configurable threshold (default 0.5s), tightening pace without cutting speech.
- **R2.3** The system SHALL apply a light, warm color grade (modest saturation +
  warmth + contrast) consistently to all outputs.
- **R2.4** The pre-pass SHALL be lossless-where-possible and never drop or
  desync the audio.

## R3 — Long-form track

- **R3.1** The long-form output SHALL remain 16:9 at the source resolution/fps.
- **R3.2** The system SHALL attach soft captions (SRT/VTT from Whisper, AR + EN)
  by default; burned-in captions SHALL be an opt-in per video.
- **R3.3** The long-form output SHALL include a branded intro and outro.
- **R3.4** The system SHALL generate a **punchy custom thumbnail** (subject
  cutout on a vibrant gradient + bold two-tier Arabic + glow) for the long-form
  video, sized **16:9 (1280×720)**.
- **R3.5** The long-form output SHALL be published by the n8n engine as a
  **regular video** (not a Short) so the custom thumbnail displays.

## R4 — Shorts track

- **R4.1** The system SHALL select the top 1–3 highest-scoring moments (existing
  Gemini clip scoring) that clear a quality threshold.
- **R4.2** Each short SHALL be reframed to 9:16 with face-tracked cropping.
- **R4.3** Each short SHALL have **burned-in word-level karaoke captions**:
  big Tajawal-Black Arabic, current word highlighted in brand gold.
- **R4.4** Karaoke captions SHALL render Arabic RTL correctly (letters joined,
  right-to-left order) — NOT via libass `\k` tags (which break on RTL), but via
  per-word reshaped ASS events using the proven raqm technique.
- **R4.5** Each short MAY include subtle auto zoom-in variation for visual
  interest; this SHALL be configurable and default on.
- **R4.6** Each short SHALL be `+faststart` remuxed (Instagram-ready) as today.

## R5 — Audio / music

- **R5.1** The system SHALL add a royalty-free background music bed, selected by
  the clip's **topic** (pronunciation / grammar / vocabulary / conversation /
  tips), from a pre-downloaded free library (Pixabay).
- **R5.2** Music SHALL be auto-ducked under speech (sidechain compression) so
  narration always stays intelligible.
- **R5.3** Music selection SHALL vary (rotate among a few tracks per topic) to
  avoid every video sounding identical.

## R6 — Branding & identity

- **R6.1** Intro/outro and thumbnails SHALL use the channel's own logo/brand
  colors (gold + navy) consistently across all outputs.
- **R6.2** No third-party creator's assets SHALL be copied; only general editing
  *approach* is used as inspiration.

## R7 — Non-functional

- **R7.1** All tooling SHALL be free / open-source and run on the free Kaggle GPU.
- **R7.2** Every block SHALL be independently runnable and testable on a single
  clip, and SHALL fail soft (a failed enhancement never blocks the core output).
- **R7.3** The pipeline SHALL remain driven by the existing
  `run_batch.py` + bridge flow — no new paid infrastructure.
- **R7.4** The hardest block (R4.3/R4.4 Arabic karaoke) SHALL be validated by a
  visual proof-of-concept and owner sign-off BEFORE integration.

## R8 — Publishing integration (n8n side)

- **R8.1** The n8n publishing engine SHALL route `output/<brand>/long/` items to
  a **regular-video** upload (custom thumbnail applied) and
  `output/<brand>/shorts/` items to a **Short** upload.
- **R8.2** Routing SHALL be derived from the folder, consistent with the existing
  classify node (which already iterates all items in a poll batch).

---

## Out of scope (explicit non-goals)

- Cinematic color grading / LUT artistry.
- Motion graphics / animated lower-thirds (needs After Effects-class tools).
- Heavy AI B-roll generation (may be revisited later as simple keyword cutaways).
- Multi-camera editing.
