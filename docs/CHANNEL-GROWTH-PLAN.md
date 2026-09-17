# EEC Channel Growth & Conversion Plan

> Built from live channel data on 2026-09-17. Channel: @empireenglishcommunity
> (UCcHC1k-eFd1UMP_J3uWIVpw). 17 videos, 11 subs, ~8k views at time of audit.

## Monetization context (time-sensitive)

- **Until Feb 1, 2027:** YPP entry = 1,000 subs + **4,000** watch hours (long-form)
  OR 10M Shorts views/90 days.
- **After Feb 1, 2027:** bar doubles to **8,000** watch hours OR 20M Shorts views.
  (Sources: Forbes 2026-08-11; air.io YPP 2026 guide. Rephrased for compliance.)
- **~4.5-month window** to qualify at the easier threshold.
- Honest note: ad revenue at this size is modest. The real money is the **product
  funnel** (placement test -> 6-level system -> community), with YouTube as the funnel.

## Conversion audit findings (from video statistics)

- **Shorts get reach but shallow engagement (~1%)** -> views don't convert to subs.
- **The one long-form (Podcast Ep.1) had 44% engagement** but only 25 views -> long-form
  converts; it just lacks reach.
- **Top performers are specific pronunciation / accent / myth-busting tips**
  (Flap-T, Shadowing, "drop the accent obsession", practice-not-memorizing).
- **Motivational / mindset videos underperform** on views. Audience wants tactical.
- Comments near-zero on Shorts -> little community formation.

**Strategy:** Shorts = discovery engine funneling to long-form + community. Lean into
concrete pronunciation/accent content. Build an "Accent Lab" numbered series (matches
the brand guide's signature module) so viewers subscribe for the next part.

## Next 10 videos (data-driven)

1. The "TH" sound Arabs get wrong (th vs د)
2. "he go" -> "he goes": the one grammar fix
3. 3 English sounds that don't exist in Arabic  (Accent Lab #1)
4. Stop saying "بتاع" in English — say THIS
5. The American "R" — how to actually make it   (Accent Lab #2)
6. "P" vs "B" — the mistake that exposes your accent (Accent Lab #3)
7. 5-min lesson: fix your 5 most common speaking mistakes  (LONG-FORM, banks watch hours)
8. Shadowing done right — full walkthrough (long-form of the hit Short)
9. Podcast Ep.2 (Ep.1 had 44% engagement)
10. Reacting to Arab speakers' English mistakes (comment-bait -> community)

## Standardized CTAs (baked into the publishing pipeline 2026-09-17)

The `Build YT metadata` node in the "YouTube — Publishing" workflow now appends a fixed
funnel block to every auto-generated description + pinned comment:

- Subscribe prompt
- Telegram community: https://t.me/Empire_English_Community
- Free placement test: https://assessment.empireenglish.online
- Brand tagline

See `funnel/build_yt_metadata.js` for the exact node code (source of truth).
