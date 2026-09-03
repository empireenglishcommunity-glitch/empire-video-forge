# Project Status & Handoff — READ THIS FIRST

> **Purpose:** single source of truth for where the auto-edit + auto-publish
> project stands. Any new session or agent should read this first to resume
> without re-deriving context. Last updated: **2026-09-04**.

## The goal (in one line)

Turn the owner's long/raw videos into finished, captioned, viral-styled 9:16
clips **automatically and at $0**, then auto-publish them across social
platforms — organized by brand (EEC vs MACAL), with the safety rule that
**MACAL content must never reach EEC channels**.

## The pipeline, and what's built vs not

```
film → drop in inbox/<brand>/ → [Kaggle GPU: clip+caption+viral font] → Drive/output/<brand>/ → [n8n → post to platforms]
        (manual, 1 decision)      ✅ BUILT & PROVEN                       ✅ BUILT              🔲 NOT BUILT YET (next)
```

| Stage | Status |
|---|---|
| AI editing engine (OpenShorts on free Kaggle T4) | ✅ **Proven** on real Arabic video, owner-approved |
| Arabic transcription (`large-v3`) + correct fonts | ✅ Done |
| Viral font rotation (7 free fonts, per-video) | ✅ Done |
| Batch runner (inbox → Kaggle → Drive folders) | ✅ Built (`batch_runner/`) |
| **All publishing credentials** (Google/Meta/TikTok/R2) | ✅ **DONE 2026-09-04** |
| n8n publishing workflow (Drive → post to platforms) | 🔲 **NEXT — not started** |

## ⏭️ WHERE WE LEFT OFF / NEXT ACTION

**Credential setup is 100% complete.** The next work is **building the n8n
publishing workflow (Step 2b)** on the Hetzner box via the n8n-MCP server:
Drive trigger (watches `output/<brand>/`) → stage file to R2 → derive
caption/title from the clip's `_metadata.json` → post to YouTube + Instagram
(+ TikTok draft) → write to a ledger → purge staged file.

Start by reading `empire-server-forge/docs/SOCIAL-PUBLISHING-DESIGN.md` (the
full downstream design) — the credentials it lists as prerequisites now all
exist.

## Repos involved

- **`empire-video-forge`** (this repo) — the editing pipeline. Contains:
  - `docs/AUTO-EDIT-STAGE-DESIGN.md` — the design + build order
  - `docs/STEP1-FINDINGS.md` — proven Kaggle findings + exact fixes
  - `docs/VIRAL-FONTS.md` — the 7-font rotation mix
  - `kaggle/` — the setup notebook (`generate_notebook.py` → `.ipynb`) + reused `remote_exec_bridge.py`
  - `batch_runner/` — PC-side inbox→Kaggle→Drive script
- **`empire-server-forge`** — infra + the (design-only) social-publishing pipeline in `docs/SOCIAL-PUBLISHING-DESIGN.md` + `SOCIAL-PUBLISHING-SETUP.md`. n8n runs here on Hetzner (`bot.empireenglish.online`, 77.42.43.250, ~4GB RAM). n8n-MCP server available for building workflows.
- **`empire-annex`** — hosts the public legal pages (GitHub Pages), added for TikTok verification.
- Reused patterns from **`macal-empire-image-forge`** (Kaggle bridge) and **`macal-overseer`** (Windows/watchdog/Ollama).

## How the editing engine actually runs (proven recipe)

- **Compute:** free Kaggle GPU (2× T4), driven by `kaggle/remote_exec_bridge.py`
  (paste into a Kaggle cell → prints a `BRIDGE_URL` → agent controls the session).
- **Engine:** OpenShorts (`github.com/mutonby/openshorts`), runs as a **standalone
  CLI** (`python main.py -i <video> -o <dir> --format vertical`) — no Docker needed.
- **Required fixes baked into the notebook** (see STEP1-FINDINGS): pin
  `mediapipe==0.10.21` + uninstall TensorFlow (protobuf clash); install Noto +
  the 7 viral fonts; `WHISPER_MODEL=large-v3` on CUDA.
- **Moment-scoring:** Gemini free tier (key via Kaggle Secrets, ~$0.001/video)
  OR local Ollama (`LLM_BASE_URL`).
- **Input:** upload the source video to Kaggle as a **Dataset** and use `-i`
  (YouTube `-u` download is blocked by anti-bot from Kaggle IPs).
- **Caveat:** Kaggle sessions are ephemeral — re-run setup each session; the
  `large-v3` download adds ~90s once.

## ✅ Credentials completed (2026-09-04) — WHERE THE VALUES LIVE

**All secret VALUES are in the owner's local notepad only. NONE are in any
repo or chat.** When building n8n, they go **only** into n8n's encrypted
credential store. Non-secret identifiers recorded here for convenience:

| Provider | What exists | Non-secret IDs |
|---|---|---|
| **Google Cloud** project `empire-english-n8n` | YouTube Data API v3 + Drive API enabled; OAuth client `n8n-empire-video` (Web app); scopes `youtube.upload` + `drive`; test user added; Testing mode | redirect URI: `https://bot.empireenglish.online/rest/oauth2-credential/callback` |
| **Meta** app `Empire Video Publisher` | Instagram use case; scopes `instagram_business_basic` + `instagram_business_content_publish`; both IG accounts are Instagram Testers + **authorized** (via instagram.com/accounts/manage_access/, NOT the app); long-lived tokens generated | EEC IG user id `17841439275631104`; MACAL IG user id `17841475049428664` |
| **TikTok** app `Empire Video Publisher` (org created) | Login Kit + Content Posting API added; scope `video.upload` (draft/inbox flow); URLs verified; redirect URI set. **Sandbox `empire-video-sandbox` created** with BOTH TikTok accounts as target users — gives working test access with NO app review / NO demo video needed. Production submission is blocked only by the demo-video requirement (needs the built integration first). | — |
| **Cloudflare R2** | Bucket `empire-social-staging`; public custom domain `social-staging.empireenglish.online` (Active); scoped Object Read&Write API token. **Verified: object fetchable over HTTPS with NO User-Agent (200)** — Meta's fetcher will work. | public base: `https://social-staging.empireenglish.online`; S3 endpoint on bucket Settings page |

**Facebook: deliberately SKIPPED.** No EEC Facebook Page exists; a MACAL Page
exists but the design has no MACAL→Facebook destination. Deferred as a future
deliberate design change (would require updating the routing table + guards in
SOCIAL-PUBLISHING-DESIGN.md).

## Platform readiness for publishing

| Platform | Ready to build against? |
|---|---|
| YouTube (EEC) | ✅ Yes |
| Instagram (EEC + MACAL) | ✅ Yes (needs R2 staging — done) |
| TikTok (EEC + MACAL) | ✅ Yes, via **sandbox** (draft flow) |
| Facebook | ⏸️ Skipped |

## Safety-critical rule (do NOT violate)

**MACAL content must NEVER reach EEC channels.** Routing is by folder
(`01-EEC-only/`, `02-EEC-and-MACAL/`, `03-MACAL-only/`), folder-in→folder-out
one-to-one. The batch runner already enforces this. The n8n workflow must
enforce it via **credential isolation** (MACAL branch has no EEC token
reachable), a pre-publish assertion, and a ledger — see design doc §2.

## Standing rules for this project

- **Never commit or paste secrets.** Values → n8n credential store only. This
  org has leaked tokens before.
- Work **one step at a time** with the owner when doing console/UI setup; the
  owner is on Windows in a browser and shares screenshots.
- Prefer **free / commercial-safe** choices (no pirated fonts, no paid deps).
- Verify before claiming done; be honest about caveats.

## Honest caveats / open items

- **Not zero-touch:** owner makes one routing decision per video, and does a
  quick caption review before posting (English loanwords get transliterated
  oddly in Arabic). This is the honest ceiling of free+auto.
- **TikTok production** (public auto-posting) still needs a demo video → needs
  the working integration first → then days of review. Sandbox is enough to
  build/test now.
- **n8n runs on a ~4GB Hetzner box** — never put video processing there; that's
  why editing runs on Kaggle.
- **Kaggle session hygiene:** stop the session when done (Gemini key lives in
  its `.env` until then).
