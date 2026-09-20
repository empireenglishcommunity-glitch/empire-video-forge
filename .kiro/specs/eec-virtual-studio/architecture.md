# EEC Virtual Studio — Architecture & Roadmap

> **The vision (owner):** not one podcast, but a **virtual studio** — a modular AI
> production platform that covers the whole pipeline (script → voice → clean → music →
> assemble → master → package → visual) with the best commercial-safe open-source tools,
> at ~$0, rivalling a real studio.
>
> **The reframe (how we actually get there):** the studio is a set of **pluggable STATIONS**
> on a shared timeline/asset bus. Each station has a clean interface, is added **one at a
> time, proven before the next**, and must pass a **LICENSE GATE** (commercial-safe) before
> it enters. This turns "a pile of tools" into a system, and lets the working core keep
> shipping while we expand. The current podcast pipeline (`eec-podcast-automation`) is
> **Station 1–2 already built** — we extend it, we don't restart.

---

## Guardrails (non-negotiable — same discipline that's protected the project)
1. **Commercial-safe or it doesn't enter.** "Open source" ≠ commercial. **Check the MODEL
   WEIGHTS license, not just the code license** (many models are MIT code + non-commercial
   weights — see MusicGen below). Verified per tool in the shortlist.
2. **~$0 default.** Free/open tools + free GPU (Kaggle T4). Paid escape hatches allowed only
   when explicitly chosen and cheap (e.g. DeepSeek direct API ~$0.01/season).
3. **Never disrupt the 12 live server containers.** Heavy GPU work runs on Kaggle, not prod.
4. **Human-in-the-loop, honest quality bar.** Target = "AI does ~90% of studio work at ~$0,
   a human adds the 10% polish, ships consistently" — NOT "indistinguishable-from-human,
   fully autonomous." The autonomous 3D-avatar studio is a north star, not the next sprint.
5. **Modular.** A station can be swapped/upgraded without rewriting the core. Clean I/O
   (WAV in / WAV out, JSON manifests) between stations.

## The station model (data flows left→right; each is independently upgradeable)
```
[1 SCRIPT]      DeepSeek (R1/V3) -> script.json (+ direction acting notes)     ✅ BUILT
     |
[2 VOICE]       VoiceTut (Mahmoud+Macal) + Qwen3-TTS (Nour/guests/Ravi)        ✅ BUILT (cast locked)
     |          -> per-line WAVs + manifest
     |
[3 ENHANCE]     DeepFilterNet -> Resemble Enhance (studio emulation)           ⬜ NEXT (Pillar 2)
     |          -> cleaned per-line WAVs
     |
[4 MUSIC/SFX]   YuE / Stable Audio Open -> beds, stings, SFX                   ⬜ LATER (Pillar 3)
     |
[5 ASSEMBLE]    assemble_audio.py (ffmpeg): order, gaps, duck music           ✅ BUILT
     |
[6 MASTER]      two-pass loudnorm + EQ (+ future Pedalboard VST chain, #53)    ◑ PARTIAL
     |
[7 PACKAGE]     metadata.py: SEO title, show notes, timestamps, quotes         ⬜ PLANNED (Phase C.5)
     |
[8 VISUAL]      LatentSync / LivePortrait / avatars (+ Unreal env, aspirational) ⬜ FUTURE (Pillar 4)
     |
[9 PUBLISH]     YouTube + podcast feed (n8n)                                    ✅ BUILT (live)
```
Legend: ✅ built · ◑ partial · ⬜ not yet.

---

## License-vetted tool shortlist (verified this session — weights + code)
> ✅ = adopt · ⚠️ = usable with a caveat · ❌ = rejected (license). Re-verify at adoption.

### Pillar 1 — Voice / TTS (Station 2) — **DONE**
| Tool | License | Verdict |
|---|---|---|
| **Qwen3-TTS** | Apache-2.0 (code + weights) | ✅ **ADOPTED** — our English engine (design + clone) |
| **VoiceTut** | (in use for Arabic + Macal English) | ✅ **ADOPTED** — Mahmoud + Macal |
| Chatterbox (Resemble) | watermark + messier license | ❌ rejected earlier (watermark; we chose Qwen) |
| Fish Audio S2 Pro | non-commercial | ❌ rejected (license) |
| ElevenLabs | paid + prohibits cloning its output | ❌ rejected (license/rights); quality bar only |

### Pillar 2 — Audio enhancement / studio emulation (Station 3) — **NEXT**
| Tool | License | Verdict | Role |
|---|---|---|---|
| **DeepFilterNet** | MIT / Apache-2.0 | ✅ **adopt** | real-time denoise + dereverb (48 kHz) |
| **Resemble Enhance** | MIT | ✅ **adopt** | audio super-resolution / "studio emulation" (restore highs + depth) |
| **VoiceFixer** | MIT | ✅ adopt (optional) | general recording repair / restoration |
| Adobe Podcast AI / Descript | paid SaaS, not self-host | ❌ not for the $0 pipeline (fine as a manual tool) |

**Note:** this station is the **highest-ROI next add** — it upgrades every episode and is
fully MIT. It also delivers the "REAPER-level mastering" wish (from the earlier DAW debate)
the free/in-stack way. Pipe order: synth WAV → DeepFilterNet (clean) → Resemble Enhance
(enrich) → assembly. Ear-tune on Ep1.

### Pillar 3 — Music & SFX (Station 4) — **LATER**
| Tool | Code | **Weights** | Verdict |
|---|---|---|---|
| **YuE** (lyrics→song w/ vocals) | Apache-2.0 | Apache-2.0 | ✅ **adopt** (heavy GPU; the commercial-safe song model) |
| **Stable Audio Open** (SFX/loops/beds) | MIT | Stability Community License | ⚠️ **usable while EEC < $1M/yr revenue**; revisit at scale |
| **MusicGen** (Meta) | MIT | **CC-BY-NC 4.0 (NON-COMMERCIAL)** | ❌ **REJECTED** — weights forbid commercial output (classic code≠weights trap) |
| Suno / Udio | closed/paid, metered | ❌ not self-host / not $0 |

**Easy win first:** branded intro/outro stings + ducked beds via Stable Audio Open (slots
into the existing `assemble_audio.py` music-bed hook). Full songs (YuE) later — GPU-heavy.

### Pillar 4 — Visual studio / avatars / lip-sync (Station 8) — **FUTURE**
| Tool | License | Verdict |
|---|---|---|
| **LatentSync** (bytedance) | Apache-2.0 | ✅ commercial-safe lip-sync |
| **LivePortrait** (Kwai) | NOASSERTION → **verify per-repo before adopting** | ⚠️ check license/weights |
| **SadTalker** | NOASSERTION → **verify before adopting** | ⚠️ check license/weights |
| Unreal Engine 3D env | EULA (royalty over threshold) | ⚠️ big separate project; aspirational |

**Reality check:** most mature, most GPU-hungry, most human-cleanup needed. A **separate
track** started only once audio is a polished machine. "Auto-built realistic 3D Unreal
studio" is the north star, not a near-term sprint.

---

## Roadmap (owner-approved sequencing)
1. **Phase C (current) — prove the core on Episode 1.** Finish the podcast pipeline
   end-to-end with the locked cast; GATE C. *Nothing new until Ep1 sounds great.*
2. **Station 3 — Audio Enhancement** (DeepFilterNet + Resemble Enhance). Highest ROI,
   MIT-clean, medium effort. Ear-tune on Ep1.
3. **Station 4 — Music/SFX** (Stable Audio Open beds/stings first; YuE songs later).
4. **Station 8 — Visual/Avatars** (LatentSync-led; separate track, later).
Each station: license-gate → Kaggle prototype → A/B vs current → adopt only on a clear win →
fold into the pipeline + docs. Same gated, proven-before-next discipline as the podcast spec.

## Relationship to the podcast spec
This doc is the **umbrella vision**. The `eec-podcast-automation` + `two-worlds-season-cast`
specs implement Stations 1–2, 5–7, 9 (the podcast). New stations get their own mini-specs
under this umbrella as we reach them. This file is the map; it is updated as stations land.

## Open verification TODOs (before adopting the ⚠️ tools)
- [ ] Confirm DeepFilterNet + Resemble Enhance run on the Kaggle T4 (VRAM, no torch clash).
- [ ] Confirm Stable Audio Open Community License terms at adoption (revenue threshold).
- [ ] Per-repo license check for LivePortrait & SadTalker (weights included).
- [ ] Confirm YuE GPU footprint vs a free/affordable tier.
