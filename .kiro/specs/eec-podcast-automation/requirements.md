# EEC Podcast Automation — Requirements

> **Product:** "Two Worlds" — a weekly, character-driven, bilingual mini-drama podcast
> that teaches real English to Arabic speakers through story, published automatically
> to the EEC YouTube channel via the existing publishing engine.
>
> **North star:** deliver REAL value that helps learners progress — and kill boredom.
> Not AI-slop; a show with a soul (recurring characters, a season arc, a signature segment).

## Vision

Each episode is a short story/conversation between recurring characters in a relatable
situation (job interview, coffee in Dubai, a misunderstanding, a work meeting). The
dialogue is real, situational English; an Egyptian-Arabic "Coach" voice steps in to
break down the key phrase, the common mistake, and the cultural note. Beginners lean on
the Arabic scaffolding; advanced learners ride the English. Episodes form a **season**
following the same cast, so students feel progression and return for the story.

## Personas
- **Beginner (A2):** needs heavy Arabic support, slow English, high-frequency phrases.
- **Intermediate (B1):** wants real conversation, common mistakes fixed, some Arabic.
- **Advanced (B2+):** wants natural/idiomatic English, minimal Arabic, nuance.

## Functional requirements

### R1 — Episode format & structure
- R1.1 Each episode has a **target level** (A2 / B1 / B2) that scales the English
  difficulty and the amount of Arabic scaffolding.
- R1.2 Fixed segment structure per episode:
  1. Cold-open hook (3s) — a line that creates curiosity/stakes.
  2. Story/dialogue scene (real English, recurring characters).
  3. Coach breakdown (Egyptian Arabic) — explains 2–4 key phrases + 1 common mistake.
  4. "Phrase of the Episode" — one takeaway phrase, drilled.
  5. Cliff-hook to next episode + CTA (subscribe / Telegram / placement test).
- R1.3 **Recurring characters** with consistent names/voices across the season.
- R1.4 **Season arc:** a light continuing storyline so episodes connect.

### R2 — Language & pedagogy
- R2.1 Dialogue in **real, level-appropriate English** (not textbook English).
- R2.2 Breakdown in **Egyptian Arabic**, following EEC brand voice + honesty guardrails
  (no "hack/secret/guaranteed"; "system, step by step, real").
- R2.3 CEFR-aligned difficulty; **not** presented as a certification.
- R2.4 Every episode teaches something concrete and reusable (phrases, not trivia).

### R3 — Voice generation (sustainable, automated)
- R3.1 **Primary engine: Piper TTS**, self-hosted on the server — free, unlimited, CPU,
  zero per-episode cost (enables true automation with no monthly credit wall).
- R3.2 **Multi-voice:** distinct voices per character + a separate Arabic Coach voice.
- R3.3 Per-line synthesis with timing metadata (for caption sync).
- R3.4 ElevenLabs remains an **optional premium upgrade** (config flag), not a dependency.
- R3.5 Fail-soft: if a voice fails, retry; never publish a broken/silent episode.

### R4 — Video assembly (YouTube-first, "a show not a clip")
- R4.1 Audio-first, rendered to **video** with a consistent visual world (character
  scenes/illustrations + branded frame).
- R4.2 **Karaoke captions:** English (and Arabic for key lines) synced to the audio.
- R4.3 Light music bed, ducked under speech; branded intro/outro sting.
- R4.4 Output **16:9 long-form** (per the orientation rule -> treated as long-form) plus
  optional **9:16 short clips** (highlights) for discovery.
- R4.5 All rendering throttled (nice) so it never disrupts the server's live containers.

### R5 — Publishing (reuse the hardened engine)
- R5.1 Finished video lands in the watched Drive folder -> the existing "YouTube —
  Publishing" workflow handles title/description/hashtags/CTA/thumbnail/playlist.
- R5.2 Episodes go to the **"Empire English Podcast"** playlist automatically.
- R5.3 Metadata reflects the podcast + episode number + level.

### R6 — Scheduling & automation
- R6.1 **Weekly** cadence (configurable). An n8n scheduled trigger kicks the chain.
- R6.2 End-to-end: schedule -> script -> voice -> video -> Drive -> publish, no human step.
- R6.3 A human-review gate is available (optional) before publish, per episode.

### R7 — Reliability & cost
- R7.1 Zero recurring cost for the core pipeline (Piper + ffmpeg + existing infra).
- R7.2 Fail-soft at every stage; a failure alerts (reuse the error workflow) and never
  publishes a broken episode.
- R7.3 Runs within the box's limits (1.7GB free RAM, 2 cores, 12GB disk) — throttled.

### R8 — Quality & anti-"AI-slop"
- R8.1 Consistent characters, voices, visual identity, and music across episodes.
- R8.2 Scripts reviewed for pedagogical value + brand voice before the format is locked.
- R8.3 Every episode must pass a quality bar (audio clear, captions synced, value present).

## Non-goals (for v1)
- Fully animated cartoon characters (start with stylized static scenes + captions).
- Live/real-person hosting.
- Separate per-level episode tracks (we layer within one episode instead).
