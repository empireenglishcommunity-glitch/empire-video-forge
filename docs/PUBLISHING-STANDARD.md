# EEC Publishing Standard (2026)

> Researched from current (2026) YouTube best-practice sources and encoded into the
> "YouTube — Publishing" n8n workflow (RdtmJTVYU4jFFCvF). Content rephrased for
> licensing compliance; sources: vexub, teleprompter, metricool, alanspicer,
> hollyland, air.io, fliki, scalelab (all 2026).

## The core truth
- **Shorts** are ranked mostly by the **viewing experience** — the first ~3-second hook,
  watch-through/completion, replays, and engagement — NOT by metadata. Metadata only
  helps search/discovery. So the biggest lever is the VIDEO hook, not the pipeline.
- **Long-form** relies much more on metadata (title/description) + click-through +
  watch time. Chapters, captions, and a keyword-first description matter here.

## Field standard
| Field | Standard |
|---|---|
| Title | Front-load keyword/topic; curiosity hook; Shorts <= ~50 chars (mobile truncates); 1 emoji |
| Description first line | Keyword-rich hook + main English term (search/Google read this first) |
| Hashtags | 3-5 relevant (not more) |
| Tags | 5-8, minor for ranking now |
| Chapters (long-form) | Timestamped, first MUST be 0:00 — aids watch-time + SEO |
| Pinned comment | Post immediately; drives early engagement (first 48h decide distribution) |
| Category | Education (27) |

## How the engine implements it
Two Code nodes (source of truth in `funnel/`):

- **`Compose YT prompt`** (`funnel/compose_yt_prompt.js`)
  - Detects short vs long (same rule as Build) and sends a FORMAT-SPECIFIC prompt.
  - Requests keys: title, `first_line` (keyword lead), caption, topic, and — for
    long-form — `chapters` (timestamped).
  - Encodes brand voice + honesty guardrails (no "hack/secret/guaranteed").
- **`Build YT metadata`** (`funnel/build_yt_metadata.js`)
  - Shorts title tightened to <=50 chars with WORD-BOUNDARY-safe truncation, then #Shorts.
  - Description order: keyword first_line -> value caption -> chapters (long only) ->
    comment CTA -> funnel block (subscribe + Telegram + placement test) -> hashtags -> signature.
  - Long-form renders a "الفصول" (chapters) block only when >=2 valid stamps incl 0:00.
  - Everything else preserved: tags, pinned comment + funnel, scheduling, format
    detection, thumbnail/playlist routing.

## Deploy procedure (never break the live engine)
1. Pull current node code (source of truth = live workflow).
2. Edit locally; `node --check` + simulate short & long inputs.
3. Deactivate -> patch nodes -> `n8n_validate_workflow` (must be 0 errors) ->
   verify code landed via get_workflow -> reactivate -> confirm active.
4. Roll back if validation fails.

## What the pipeline CANNOT do (be honest)
- It cannot force Shorts to grow — that needs a strong first-3-second HOOK in the video
  (a content/editing job). See CHANNEL-GROWTH-PLAN.md.
- Video titles/descriptions of EXISTING videos can't be edited via the current
  credential (upload scope only -> 403 on videos.update). Those are dashboard edits.
