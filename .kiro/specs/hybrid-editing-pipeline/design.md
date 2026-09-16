# Hybrid Editing Pipeline — Design

> Implements `requirements.md`. Tools are free/open-source, run on the free
> Kaggle GPU via the existing `remote_exec_bridge` + `run_batch.py` flow. The
> editing logic lives in the Kaggle notebook generator
> (`kaggle/generate_notebook.py`) which is the source of truth for the `.ipynb`.

---

## 1. High-level architecture

```
RAW landscape master (one file, 16:9)
        │
        ▼  ── SHARED PRE-PASS (once) ─────────────────────────────
        │   S1 transcribe (Whisper large-v3, word timings)  [R2.1]
        │   S2 silence/dead-air removal (auto-editor)        [R2.2]
        │   S3 light warm color grade (ffmpeg eq/curves)     [R2.3]
        │       → produces: master_clean.mp4 + words.json
        └───────────────┬───────────────────────────────────────
        ┌───────────────┴─────────────────┐
   LONG-FORM track [R3]              SHORTS track [R4]
   L1 keep 16:9                      H1 pick top 1–3 moments (Gemini score)
   L2 soft CC (AR+EN SRT/VTT)        H2 face-tracked 9:16 crop
   L3 branded intro/outro            H3 burned RTL karaoke captions  ← HARD
   L4 topic music bed (ducked)       H4 subtle zoom-in variation
   L5 punchy 16:9 thumbnail          H5 topic music bed (ducked)
   L6 → output/<brand>/long/         H6 +faststart remux
                                     H7 → output/<brand>/shorts/
        └───────────────┬───────────────────────────────────────
                        ▼
        n8n publishing engine [R8]:
          long/  → regular video (thumbnail shows)
          shorts/→ Short
```

## 2. Tool choices (with rationale)

| Need | Tool | Why |
|---|---|---|
| Transcription + word timings | faster-whisper large-v3 (already in pipeline) | proven, GPU, Arabic-capable |
| Silence removal | `auto-editor` | mature, ffmpeg-based, configurable thresholds |
| Reframe 9:16 | existing OpenShorts face-track reframe | already working |
| Clip scoring | existing Gemini 2-pass scoring | already working |
| Color grade | ffmpeg `eq`/`curves` | zero-dep, fast |
| Karaoke captions | PIL/raqm per-word ASS events + libass burn | ONLY reliable RTL path (see §4) |
| Zoom variation | ffmpeg `zoompan` | zero-dep |
| Music | Pixabay library (pre-downloaded) + ffmpeg `sidechaincompress` | free, no attribution, auto-duck |
| Thumbnail cutout | `rembg` (free, local) | background removal for punchy thumbs |
| Intro/outro | ffmpeg `concat` of a prebuilt sting | zero-dep at runtime |

## 3. Shared pre-pass detail

- **S1 transcribe** → `words.json` = `[{word, start, end}]`. Reused by BOTH the
  long-form soft-CC and the Shorts karaoke captions (single source of timing).
- **S2 silence removal** with `auto-editor --edit audio:threshold=…` and a
  margin so speech isn't clipped; keep video+audio in sync; re-probe duration
  after. [R2.2, R2.4]
- **S3 color grade**: a single reusable ffmpeg filter string, e.g.
  `eq=saturation=1.15:contrast=1.06:brightness=0.02, curves=preset=lighter` —
  tuned light + warm to match the reference creator's soft look. [R2.3]

## 4. The hard part — Arabic RTL karaoke captions [R4.3, R4.4, R7.4]

**Problem:** libass defaults to LTR and its `\k` karaoke tags mis-handle RTL
bidi; word-level highlight on Arabic garbles (disconnected/reversed letters).

**Design (proven approach):**
- Do NOT use libass `\k`. Instead, for each spoken word window, render a full
  **ASS event** where the whole caption line is drawn correctly RTL and only the
  **current word** is styled (color = brand gold, ~1.2–1.3× size).
- Arabic is passed as **raw text with `direction=rtl`/`language=ar`** (the raqm
  technique already proven in the thumbnail generator) so letters join and order
  correctly — no `arabic_reshaper`/`bidi` pre-shaping (that double-shapes).
- Group into short chunks (e.g. 3–5 words) so the line fits 9:16 and reads fast.
- Font: Tajawal Black (installed), heavy outline, lower-center anchor.
- **Validation gate:** build a POC on ONE clip, render 3–4 seconds, pull frames
  back through the bridge, and get owner visual sign-off BEFORE wiring into the
  pipeline. [R7.4]

## 5. Long-form track detail

- **L2 soft CC**: emit `AR.srt` + `EN.srt` from `words.json`; attach as sidecar
  (n8n/YouTube can ingest). Burned-in only if `burn_captions:true` in metadata.
- **L3 intro/outro**: prebuilt 2–3s stings (logo + brand colors) concatenated
  via ffmpeg with matching resolution/fps; audio crossfade to avoid pops.
- **L5 thumbnail**: `rembg` cutout of a good speaker frame → composite on a
  vibrant gradient → bold two-tier Arabic (hook + kicker) + gold glow, **1280×720**.
  Reuses the 16:9 brand-card code already fixed in the thumbnail generator.

## 6. Music [R5]

- Pre-download ~3–5 royalty-free tracks per topic into
  `assets/music/<topic>/` (committed or fetched once on the box).
- Select by `metadata.topic`; rotate by a hash of the file id so consecutive
  videos differ. [R5.3]
- Mix: `sidechaincompress` keyed on the voice track so music ducks under speech;
  target music bed ~ -20 dB under narration. [R5.2]

## 7. Metadata & routing [R1.4, R8]

- Each output's sidecar gets `format: long|short`, `duration`, `topic`, `title`,
  `hook`, `caption`. The n8n **Build YT metadata** node already reads these; the
  publishing engine's classify already iterates all items and routes by folder.
- New: n8n distinguishes `long/` vs `shorts/` subfolders → regular vs Short
  upload path. [R8.1]

## 8. Failure behavior [R7.2]

- Every enhancement (grade, music, zoom, thumbnail, intro) is wrapped so a
  failure logs and falls back to the un-enhanced output — the core clip/video is
  always produced. Mirrors the current thumbnail fallback pattern.

## 9. Testing strategy

- Per block: run on ONE real clip via the bridge, pull frames/audio back, verify
  visually + by ffprobe (duration, resolution, audio present).
- Karaoke block: explicit POC + sign-off gate (§4).
- End-to-end: one landscape master → confirm `long/` + `shorts/` outputs land in
  Drive and n8n publishes each on the correct path.
