# Two Worlds — AI Image/Video Prompt Guide (for the owner)

You create the video, thumbnail, and cover; I generate the plain audio. This guide
gives you **ready-to-paste, per-episode prompts** with the correct platform sizes
baked in, tuned to the EEC brand and each episode's story.

---

## Which free AI to use (ranked, $0 / free-tier, commercial-use OK)

1. **Google Gemini (Nano Banana / Imagen)** — best all-round quality in 2026, ~20
   free images/day (more via Google AI Studio, resets midnight Pacific). You already
   have a Google account + Gemini key. Best at following long detailed prompts.
   *Small AI watermark on free app output — you crop/cover it, or use AI Studio.*
   → use for the **cover** and **video backgrounds**.
2. **Ideogram** — the best at rendering **text inside images** (clean spelling),
   commercial use on the free tier. → use for **thumbnails** if you want baked-in text.
3. **Adobe Firefly** — the only one whose free output is **explicitly commercially
   safe** (licensed training data). → use when you want zero licensing doubt.

### ⚠️ Read this before generating (saves you hours)
- **Do NOT ask the AI to write Arabic text** — every image AI still garbles Arabic
  letters. Generate a **clean background/scene with NO text (or only tiny English)**,
  then add your Arabic + English titles in your editor. It looks sharper anyway.
- Generate at the **largest size the tool allows**, then downscale to the exact
  target. Never upscale a small image to fill a size.
- If a face looks off, regenerate — don't ship distorted faces.
- Keep the characters **consistent** across episodes: reuse the same short character
  descriptions (below) every time so Macal/Nour look like themselves.

---

## Brand constants (paste these into every prompt as-is)

**STYLE:** premium, cinematic, warm and credible — like a respected language academy,
NOT a flashy influencer. Brand palette: deep near-black background (#0d0c0d) with warm
**gold** accents (#e9c456) and subtle warm light. Soft depth, gentle film grain, high
production value. Avoid: harsh neon, cheap stock-photo look, cluttered composition,
busy text, distorted hands/faces, logos of other brands.

**CHARACTERS (reuse verbatim for consistency):**
- **Macal** — a warm, determined Egyptian/Arab man in his late 20s, short dark hair,
  neat short beard, friendly approachable face, smart-casual modern clothes.
- **Nour** — a confident, warm Egyptian/Arab woman in her late 20s, elegant modern
  smart-casual style, natural makeup, kind expressive eyes (no hijab unless you prefer).
- **Setting world:** modern **Dubai** — clean, sunlit, aspirational but real.

---

## 1) PODCAST COVER ART  (make ONCE, reuse for all episodes)
**Size: 3000 × 3000 px, square (1:1).** Apple/Spotify standard (min 1400, max 3000).
Leave the AI text OFF — add "Two Worlds" + your logo in your editor.

**PROMPT (paste to Gemini/Firefly):**
> A premium square podcast cover, 3000x3000, 1:1. Cinematic split composition symbolizing
> "two worlds": on one side a warm modern Dubai cityscape at golden hour, on the other a
> softer abstract world of language and connection, meeting at a glowing golden seam down
> the middle. Deep near-black background (#0d0c0d) with elegant warm gold (#e9c456) light
> and accents. Sophisticated, calm, aspirational — like a respected academy, not flashy.
> Subtle film grain, soft depth of field, high production value. Clean empty space in the
> center-lower third for a title to be added later. NO text, NO letters, no logos.
> Negative: neon, cheap stock look, clutter, watermark, distorted shapes, any text.

---

## 2) YOUTUBE THUMBNAIL  (per episode)
**Size: 1280 × 720 px, 16:9.** Keep faces/subject on the LEFT ~2/3; leave the RIGHT
~1/3 cleaner for your big Arabic headline (added in your editor).

**TEMPLATE** (fill the {{slots}} from the episode):
> A bold cinematic YouTube thumbnail, 1280x720, 16:9, high contrast, eye-catching for
> mobile. Scene: {{EPISODE_SCENE}}. Feature {{CHARACTER(S)}} — [paste the character
> description(s)] — with a clear, readable facial expression showing {{EMOTION}}. Deep
> near-black + warm gold (#e9c456) brand lighting, dramatic rim light on the subject, a
> shallow-depth Dubai backdrop. Subject placed on the LEFT two-thirds; keep the RIGHT
> third simpler/darker as empty space for a headline to be added later. Punchy, premium,
> curiosity-driving. NO text, no letters, no logos, no watermark.
> Negative: clutter, distorted face/hands, cheap stock look, neon, busy background, text.

**WORKED EXAMPLE — Ep1 "The Arrival":**
> A bold cinematic YouTube thumbnail, 1280x720, 16:9, high contrast, eye-catching for
> mobile. Scene: a man just arrived at a bright modern Dubai airport, pulling a suitcase,
> looking slightly overwhelmed but hopeful, a taxi and the Dubai skyline softly blurred
> behind him. Feature Macal — a warm determined Egyptian/Arab man in his late 20s, short
> dark hair, neat short beard, friendly face, smart-casual modern clothes — with a clear
> readable expression of nervous excitement. Deep near-black + warm gold (#e9c456) brand
> lighting, dramatic rim light on him, shallow-depth Dubai airport backdrop. Subject on
> the LEFT two-thirds; RIGHT third simpler/darker for a headline later. Premium,
> curiosity-driving. NO text, no letters, no logos, no watermark.
> Negative: clutter, distorted face/hands, cheap stock look, neon, busy background, text.
> _(Editor overlay idea: big gold Arabic headline "أول يوم في دبي!" + small "How long does it take?")_

---

## 3) EPISODE VIDEO VISUAL  (per episode — background the audio plays over)
**Size: 1920 × 1080 px, 16:9.** If you want a few scene backgrounds per episode,
generate one per major beat (arrival / taxi / meeting). Composition can be centered
since captions/waveform sit over it in your editor.

**TEMPLATE** (fill the {{slots}}):
> A cinematic 16:9 background image, 1920x1080, for a language-learning podcast video.
> Scene: {{EPISODE_SCENE}}, in modern sunlit Dubai. Mood: {{MOOD}}. Warm, premium,
> slightly dreamy storytelling atmosphere; deep near-black edges with warm gold (#e9c456)
> light so captions read clearly on top; soft depth of field, gentle film grain, subtle
> vignette. Composition calm and uncluttered with breathing room in the center for
> captions. Optionally include {{CHARACTER(S)}} [paste description] small within the
> scene. NO text, no letters, no logos, no watermark.
> Negative: busy detail, harsh neon, distorted faces/hands, cheap stock look, any text.

**WORKED EXAMPLE — Ep1 "The Arrival":**
> A cinematic 16:9 background image, 1920x1080, for a language-learning podcast video.
> Scene: the back seat / window view of a taxi driving from the airport into Downtown
> Dubai, the Burj Khalifa and skyline glowing warmly through the window at golden hour,
> in modern sunlit Dubai. Mood: hopeful new beginning, a little nervous, aspirational.
> Warm premium slightly dreamy atmosphere; deep near-black edges with warm gold (#e9c456)
> light so captions read clearly on top; soft depth of field, gentle film grain, subtle
> vignette. Calm uncluttered composition with breathing room in the center for captions.
> NO text, no letters, no logos, no watermark.
> Negative: busy detail, harsh neon, distorted faces/hands, cheap stock look, any text.

---

## Per-episode fill-in cheat sheet
For each new episode, I'll give you the values to drop into the {{slots}}:
`EPISODE_SCENE`, `CHARACTER(S)`, `EMOTION`, `MOOD`, and an editor-overlay headline
suggestion (Arabic + the English phrase of the episode). Episode 1's values are the
worked examples above.

| Slot | Ep1 "The Arrival" |
|---|---|
| EPISODE_SCENE (thumb) | Macal just arrived at a bright Dubai airport with a suitcase |
| EPISODE_SCENE (video) | taxi window view from airport into Downtown Dubai, golden hour |
| CHARACTER(S) | Macal (+ Nour appears at the end) |
| EMOTION (thumb) | nervous excitement / hopeful |
| MOOD (video) | hopeful new beginning, aspirational |
| Headline overlay idea | AR "أول يوم في دبي!" · phrase "How long does it take?" |
