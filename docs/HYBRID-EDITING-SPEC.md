# Empire English — Hybrid Editing Pipeline (Spec / Plan)

> **Status: PLAN ONLY — nothing built yet.** This document is for review and
> sign-off before implementation. It defines how one recording becomes two
> polished, platform-correct outputs (a long-form video *and* short clips),
> grounded in a real analysis of a reference creator (@fatmhisoka) and the
> hard constraints we discovered in the YouTube publishing engine.

---

## 1. Why hybrid (the strategy)

From testing + research we established two hard facts:

1. **Vertical clips ≤ 3 min are auto-classified as Shorts** by YouTube,
   regardless of the `#Shorts` hashtag.
2. **Custom thumbnails only show on regular (non-Shorts) videos** unless the
   channel is in the YouTube Partner Program (1,000+ subs). Pre-YPP, a Short's
   thumbnail is ignored and a video frame is used.

And from analyzing the reference creator @fatmhisoka (real 11.6-min video,
1280×720, ~1 cut / 3.5s, soft warm grade, clean set, punchy thumbnails, soft
YouTube CC — no burned karaoke): her whole model is **long-form 16:9 where the
thumbnail does the heavy lifting**.

**Conclusion — do BOTH, from one recording:**

| Track | Format | Job | Thumbnail | Captions |
|---|---|---|---|---|
| **Shorts** | 9:16, ≤3 min | Reach / discovery → new subscribers | Not shown in feed (frame) | **Burned karaoke** (required — no CC in Shorts feed) |
| **Long-form** | 16:9, full | Depth / watch-time / YPP path | **Custom branded thumbnail (shows + matters)** | Soft CC (default) |

One filming session → two products → maximum value, and the branded thumbnail
finally pays off on the long-form track.

---

## 2. Decisions (defaults chosen; owner may veto any)

- **D1 — Record in landscape 16:9.** Required for the long-form track; Shorts
  are cropped *from* the landscape master. (If the owner films vertical, we lose
  the long-form track — so landscape is the recommended default.)
- **D2 — Shorts per video: up to 3.** The clip-picker already scores moments;
  take the top 1–3 that clear a quality threshold. Fewer if only one is strong.
- **D3 — Long-form captions: soft CC by default** (matches the reference
  creator; keeps the frame clean), with burned-in as an opt-in per video.
- **D4 — Both tracks get:** silence/dead-air removal, a light warm color grade,
  and topic-based background music. Branded intro/outro on long-form; short
  brand tag end-card on Shorts.

---

## 3. Pipeline flow

```
                 RAW landscape recording (one file)
                              │
                    ┌─────────┴──────────┐
                    │  Shared pre-pass    │
                    │  • transcribe (Whisper large-v3, word timings)
                    │  • silence / dead-air removal (auto-editor)
                    │  • light warm color grade (ffmpeg eq/curves)
                    └─────────┬──────────┘
              ┌───────────────┴────────────────┐
   ┌──────────▼───────────┐        ┌────────────▼─────────────┐
   │  LONG-FORM track      │        │  SHORTS track            │
   │  • keep 16:9          │        │  • pick top 1–3 moments  │
   │  • soft CC sidecar    │        │  • face-tracked 9:16 crop│
   │  • branded intro/outro│        │  • BURNED karaoke caps   │
   │  • topic music bed    │        │    (Arabic RTL-correct)  │
   │  • punchy thumbnail   │        │  • subtle zoom-in var.   │
   │  • → output/.../long/ │        │  • topic music bed       │
   └──────────┬───────────┘        │  • → output/.../shorts/  │
              │                     └────────────┬─────────────┘
              ▼                                  ▼
     n8n → regular video               n8n → Short
     (custom thumbnail shows)          (max reach)
```

---

## 4. The build blocks (all FREE / open-source)

Ordered by impact-per-effort. Each is independently testable.

### Block 1 — Silence / dead-air removal ⭐ (biggest pacing win, both tracks)
- **Tool:** `auto-editor` (open-source) — detects and cuts silence.
- **Why:** the reference creator's real "secret" is tight pacing (~1 cut/3.5s).
- **Risk:** low. Well-proven tool.

### Block 2 — Light warm color grade (both tracks)
- **Tool:** ffmpeg `eq`/`curves` — modest saturation + warmth + contrast lift.
- **Why:** the reference video is soft/warm, not heavily saturated. Light touch.
- **Risk:** low.

### Block 3 — Long-form track output (the new half)
- Keep 16:9, attach soft CC (from Whisper), add branded intro/outro, music bed,
  write to `output/<brand>/long/`.
- **Risk:** low–medium (mostly wiring + ffmpeg concat).

### Block 4 — Shorts burned karaoke captions (Arabic RTL) ⭐ HARD PART
- Word-by-word highlight, big Tajawal-Black Arabic, current word in brand gold.
- **THE risk:** libass defaults to LTR and has known RTL/bidi bugs; standard
  `\k` karaoke tags break on Arabic. **Approach:** render each word-state as its
  own reshaped ASS event using the raqm technique we already proved for
  thumbnails (pass raw Arabic, `direction=rtl`), NOT libass karaoke tags.
- **Plan:** build a PROOF-OF-CONCEPT on ONE clip and get owner sign-off on the
  look before wiring it into the pipeline. This is the one block that must be
  validated visually first.

### Block 5 — Subtle auto zoom-in variation (Shorts, optional long-form)
- ffmpeg `zoompan` — occasional slow push-in on the speaker for visual variety.
- **Risk:** low.

### Block 6 — Topic-based background music (both tracks)
- **Source:** Pixabay Music (royalty-free, no attribution). Pre-download a small
  library tagged by topic (pronunciation/grammar/vocab/conversation/tips).
- **Mixing:** ffmpeg `sidechaincompress` to auto-duck music under speech.
- **Risk:** low.

### Block 7 — Branded intro/outro + thumbnail upgrade
- Intro/outro sting from the channel logo (owner's YouTube profile pic).
- Thumbnail: subject cutout (`rembg`, free) on a vibrant gradient + bold
  two-tier Arabic + glow — matching the reference creator's punchy thumbnail
  formula (for the long-form track, where thumbnails show).
- **Risk:** low–medium.

---

## 5. Recommended build order

1. Block 1 (silence removal) — helps both tracks immediately
2. Block 2 (color grade) — quick, visible polish
3. Block 3 (long-form track) — unlocks the thumbnail payoff
4. Block 4 (karaoke captions) — **POC + sign-off first**
5. Block 6 (music) + Block 7 (intro/outro + thumbnail upgrade)
6. Block 5 (zoom variation) — final polish
7. n8n routing update: long-form → regular video; shorts → Short

Each block ships as its own PR with a test clip for review.

---

## 6. What we deliberately are NOT doing (honesty)

- **Cinematic color grading / LUT artistry** — marginal for talking-head lessons.
- **Motion graphics / animated lower-thirds** — needs After Effects; not
  automatable at quality on a free GPU.
- **Heavy AI B-roll** — high effort, low reliability for lesson content; may add
  simple keyword-based cutaways later if desired, not in the core build.

---

## 7. Open questions for owner

- **Music:** one signature track per topic, or rotate a few per topic? (D4 says
  topic-based; confirm variety depth.)
- **Long-form burned captions:** keep default soft-CC, or burn them in too?
- **Intro/outro:** design a simple animated sting from the logo, or keep just a
  static brand end-card to start?

---

*Reference analysis (frames, cut-rate, grade, captions) performed 2026-09 on a
real @fatmhisoka video. Third-party observations are described in our own words;
no third-party assets are copied — only the general approach is used as
inspiration.*
