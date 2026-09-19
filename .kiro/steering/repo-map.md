# empire-video-forge — Repo Map & Memory

> Durable orientation for any Kiro session working in this repo. Single source of
> truth for status is `docs/PROJECT-STATUS.md`; this is the fast index.

## What this repo is
The **$0 video content-production pipeline** for the Empire ecosystem (parent brand:
Empire English Community / EEC, sibling: MACAL). Turns long/raw footage into finished,
captioned 9:16 short clips automatically on **free Kaggle GPU**, then hands them to the
downstream social-publishing pipeline (which lives in `empire-server-forge`, not here).

**Scope boundary:** this repo owns everything UPSTREAM of "a finished clip appears in a
Drive routing folder." It is NOT infra/server ops (that's `empire-server-forge`), and it
is cross-brand (EEC + MACAL) so it lives in neither brand's repo.

**Safety-critical rule (never violate):** MACAL content must NEVER reach EEC channels.
Routing is folder-in → folder-out, one-to-one: `01-EEC-only/`, `02-EEC-and-MACAL/`,
`03-MACAL-only/`. The pipeline never infers destination from content.

## The pipeline in one line
```
long video → drop in inbox/<brand>/ → [Kaggle GPU: cut · reframe 9:16 · caption · hook]
           → Drive/output/<brand>/ → [empire-server-forge n8n: stage · approve · fan out]
```

## Directory guide
| Path | What it is |
|---|---|
| `docs/PROJECT-STATUS.md` | **START HERE** — handoff/status, credential state, next action. |
| `docs/AUTO-EDIT-STAGE-DESIGN.md` | Full design of the auto-edit stage (why OpenShorts, why Kaggle). |
| `docs/STEP1-FINDINGS.md` | Proven live Kaggle run (2026-09-03) + the 3 required fixes. |
| `docs/VIRAL-FONTS.md` | 7-font OFL rotating caption mix (no paid Foda Kufi). |
| `docs/CHANNEL-GROWTH-PLAN.md` | YT growth strategy, next-10-videos, standardized funnel CTAs. |
| `docs/PUBLISHING-STANDARD.md` | 2026 YT best-practice encoded into the publishing engine. |
| `docs/PUBLISHING-ENGINE-AUDIT.md` | Reliability audit + hardening of the live publishing workflow. |
| `docs/HYBRID-EDITING-SPEC.md` | Hybrid editing spec. |
| `funnel/compose_yt_prompt.js` | **YT engine node 1** — format-specific (short/long) Gemini prompt. |
| `funnel/build_yt_metadata.js` | **YT engine node 2** — builds title/desc/hashtags/tags/pin/schedule + EEC funnel block. |
| `probe/eec_probe.py` | Tiny host service: classifies video by ORIENTATION (vertical=Short, horizontal=Long). Binds 172.18.0.1:8902, fail-soft. |
| `batch_runner/` | Step 2a — PC-side one-shot script: inbox → Kaggle bridge → Drive routing folders. |
| `kaggle/` | Free-GPU setup notebook (`generate_notebook.py` → `.ipynb`), `remote_exec_bridge.py`, editing modules, `RUN_GUIDE.md`. |
| `scripts/accent-lab/` | Ready-to-record Accent Lab pronunciation Shorts scripts (PDFs + `_generate.py`). |
| `assets/brand/` | `BRAND.md` (gold-on-black, `#D4AF37`) + `eec-logo.jpg`. |
| `.kiro/specs/eec-podcast-automation/` | EEC podcast automation spec (audio-only pivot, VoiceTut + Chatterbox, short 5-10min format). |
| `.kiro/specs/hybrid-editing-pipeline/` | Hybrid editing pipeline spec. |
| `.kiro/specs/two-worlds-season-cast/` | "Two Worlds" podcast season/cast spec (active WIP; PR #43 open). |

## The YouTube Publishing Engine (key context)
- Lives as the n8n workflow **"YouTube — Publishing"** (`RdtmJTVYU4jFFCvF`, 24 nodes,
  active) on the Hetzner box. The **code source of truth for its two Code nodes is
  `funnel/*.js` in this repo.**
- Flow: `Download clip (bytes)` → `Probe orientation` (POST to eec-probe) →
  `Switch: brand branch` → `Compose YT prompt` → Gemini → `Build YT metadata` → upload.
- Format detection PRIMARY signal = probe orientation; fail-soft → sidecar meta →
  duration (>180s=long) → default Short.
- Shorts: title ≤50 chars + `#Shorts`; Long: title ≤95 chars, chapters block if ≥2
  valid stamps incl 0:00.
- Every description + pinned comment gets the EEC funnel block: subscribe + Telegram
  (https://t.me/Empire_English_Community) + free placement test
  (https://assessment.empireenglish.online) + tagline.
- Honesty guardrails enforced in prompts: never "hack/secret/guaranteed"; prefer
  "system/step by step/real". Content = Egyptian Arabic + English term.
- Privacy is data-driven (fixed 2026-09-19): `Build YT metadata` emits `yt_privacy` =
  'private' only when a `publishAt` schedule is set (YouTube needs private+publishAt to
  auto-publish later), else 'public'. Upload node privacyStatus = `{{ $json.yt_privacy || 'public' }}`.
  A sidecar `meta.privacy` (public|private|unlisted) overrides. NEVER hardcode privacyStatus
  to private — that leaves auto-dropped clips private forever (Studio shows "Oops" on the
  public edit page).
- KNOWN LIMIT: existing videos' titles/descriptions/PRIVACY can't be edited via current
  credential (upload scope only → 403 on videos.update); those are dashboard edits. So
  videos uploaded before the privacy fix must be flipped to Public manually in YouTube Studio.

## Deploy discipline for the live engine (from the docs)
deactivate → patch nodes → `n8n_validate_workflow` (must be 0 errors) → verify code
landed via get_workflow → reactivate → confirm active. Roll back if validation fails.
`node --check` + simulate short & long inputs locally before deploying node code.

## Standing rules
- Never commit/paste secrets; values go to the n8n credential store only (org has
  leaked tokens before).
- Prefer free / commercial-safe deps (no pirated fonts, no paid SaaS).
- Verify before claiming done; be honest about caveats.
- Heavy video processing runs on Kaggle, never on the ~4GB Hetzner box.

## Branch/PR notes
- Default branch: `main`. Many topic branches exist (accent-lab, podcast-*, two-worlds-*,
  fix/*, feat/*). Open PR at time of mapping: #43 (Two Worlds Series Bible v2 review).
- Use `gh api` REST for PRs (not `gh pr create`).
