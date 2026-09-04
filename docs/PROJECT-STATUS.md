# Project Status & Handoff — READ THIS FIRST

> **Purpose:** single source of truth for where the auto-edit + auto-publish
> project stands. Any new session or agent should read this first to resume
> without re-deriving context. Last updated: **2026-09-04 (session 2)**.

---

## ⏭️ RESUME HERE (session 2 checkpoint) — the n8n workflow is built & wired; 4 credentials remain

**What this session accomplished:** recovered n8n access, connected to it via
the MCP server, and **built + fixed + wired most of the Phase-1 publishing
workflow directly inside n8n.** The workflow validates clean (`valid: true,
0 errors`). What's left is creating/authorizing 4 credentials (owner-gated)
and testing.

### Exact next actions (in order)
1. **Create the YouTube credential.** Blocked last time because Google no
   longer lets you re-view a client secret, and "Add secret" glitched. **Plan:
   create a NEW OAuth client** in Google Cloud (project `empire-english-n8n`,
   Clients → + Create client → Web application → name `n8n-empire-video-2` →
   redirect URI `https://bot.empireenglish.online/rest/oauth2-credential/callback`).
   The creation dialog shows the secret once — SAVE IT. Then in n8n, open the
   "YouTube EEC: upload (Short)" node → create YouTube OAuth2 credential with
   that Client ID/Secret → Sign in with Google (empireenglishcommunity@gmail.com,
   accept the "unverified app" warning) → attach to the node.
2. **Instagram ×2 credentials.** Node "IG EEC: create REELS container" +
   "IG EEC: publish" need an HTTP Header Auth credential named `IG - EEC`
   (Header: `Authorization`, Value: `Bearer <EEC IG token from notepad>`).
   Same for `IG - MACAL` on the two MACAL IG nodes. Tokens are in the owner's
   notepad (generated last session). IG user IDs are already set as env vars.
3. **R2/S3 credential.** Nodes "R2 stage (EEC IG)" + "R2 stage (MACAL IG)"
   need an S3 credential named `R2 - social-staging`: endpoint = the S3 API URL
   from the R2 bucket Settings page, region `auto`, access key + secret from
   notepad. Bucket + public base already set as env vars.
4. **Ledger Google Sheet.** Create a Google Sheet with a tab named `ledger`,
   copy its ID, set it as env var `LEDGER_SHEET_ID` in `/opt/n8n/docker-compose.yml`
   (same method as the other env vars — see below), attach the existing
   `Google Sheets account` credential to the "Ledger: append row" node.
5. **Test** — put one clip in Drive `output/01-EEC-only/`, manually execute the
   workflow, watch YouTube upload first, then IG. Only after EEC works, test MACAL.
6. **Activate** the workflow (toggle active) once tested.

### How to reconnect to n8n via MCP (for the next agent)
- MCP endpoint: `https://mcp.empireenglish.online/mcp` (n8n-mcp v2.60.0).
- **NEW MCP AUTH_TOKEN** (rotated 2026-09-04, in owner's notepad — starts `226bfba1…`).
  Old token was rotated out for security.
- n8n API key for MCP: a key named `mcp-access` was created in n8n Settings →
  n8n API (owner `macalempire@gmail.com`). If reset again, create a fresh key
  and swap into `/opt/n8n-mcp/docker-compose.yml` `N8N_API_KEY`, then
  `cd /opt/n8n-mcp && docker compose up -d`.
- MCP call pattern (curl): POST /mcp with `Authorization: Bearer <token>`,
  `Accept: application/json, text/event-stream`; do `initialize` (capture the
  `mcp-session-id` response header), send `notifications/initialized` on that
  session, then `tools/call`. Key tools: `n8n_get_workflow`,
  `n8n_update_partial_workflow`, `n8n_validate_workflow`, `n8n_list_workflows`,
  `n8n_manage_credentials` (action:list/get — cannot read secret values).

### State of the workflow in n8n (already done — do NOT redo)
- Workflow **"Social Publishing — Phase 1"**, id **`RdtmJTVYU4jFFCvF`**, currently **inactive**. `valid: true, 0 errors, 28 (cosmetic) warnings`.
- Code nodes (Classify, Guard) — **fixed** (had imported empty; now populated with the routing + fail-closed guard logic).
- Switch node — **fixed** (brand `outputKey`s EEC/MACAL set).
- Drive Trigger + Download — **wired** to credential `Google Drive account`
  (id `FDFZdH8pQKLZQFzz`, already authorized & working). Trigger watches the
  `output` folder id `1bKV8ALl6luA31CKayW2O3loofEWWHmHh`.
- Env vars set in `/opt/n8n/docker-compose.yml` (n8n restarted, healthy):
  `DRIVE_OUTPUT_FOLDER_ID=1bKV8ALl6luA31CKayW2O3loofEWWHmHh`,
  `IG_EEC_USER_ID=17841439275631104`, `IG_MACAL_USER_ID=17841475049428664`,
  `R2_BUCKET=empire-social-staging`,
  `R2_PUBLIC_BASE=https://social-staging.empireenglish.online`.
  (`LEDGER_SHEET_ID` still TODO — action 4 above.)

### To add an env var to n8n (proven method — paste-safe with awk)
```
cd /opt/n8n && cp docker-compose.yml docker-compose.yml.bak-$(date +%s)
printf '      - LEDGER_SHEET_ID=YOUR_SHEET_ID\n' > /tmp/ne.txt
awk '{print} /- R2_PUBLIC_BASE=/{while((getline l < "/tmp/ne.txt")>0) print l}' docker-compose.yml > dc.new && mv dc.new docker-compose.yml
docker compose up -d
```
(Inline python heredocs with `\n` get mangled by paste — use awk from a temp file.)

### Drive folders
Owner created Google Drive `empire-video-forge/output/` with subfolders
`01-EEC-only`, `02-EEC-and-MACAL`, `03-MACAL-only`. `output` id above.

### n8n access recovery note (happened this session)
n8n owner login was lost; recovered via `docker exec -u node -it empire-n8n
n8n user-management:reset` → restart → re-claim owner via Owner Setup page in
an Incognito window. This detached the OLD n8n API key (it authenticated but
saw 0 workflows) — fixed by creating a fresh key under the new owner. 34
existing workflows survived (backup at `/root/wf-backup-20260904.json`).
New n8n owner password is in the owner's notepad.

### Workflow source of truth
The clean workflow JSON is in `empire-server-forge/n8n-workflows/social-publishing/`
(`social-publishing-phase1.json` + `BUILD-NOTES.md`). NOTE: the version now
running in n8n has the fixes above applied on top of that JSON — if re-importing
from the repo file, re-apply the Code-node/Switch/trigger fixes (or export the
live one from n8n and commit it, credential-stripped).

---

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
