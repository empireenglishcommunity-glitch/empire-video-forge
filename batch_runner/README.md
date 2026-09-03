# Batch Runner (Step 2a)

The PC-side automation glue: **drop videos in an inbox folder → run one
command → finished, captioned clips appear in your Drive routing folders**,
organized by brand, ready for the social-publishing pipeline to pick up.

This is **build-order step 2** from `../docs/AUTO-EDIT-STAGE-DESIGN.md`. It
connects the proven Kaggle editing engine (step 1) to the Drive hand-off the
publishing pipeline expects.

## What it does

```
inbox/01-EEC-only/*.mp4       →  [Kaggle GPU: clip + caption + reframe]  →  output/01-EEC-only/
inbox/02-EEC-and-MACAL/*.mp4  →  [Kaggle GPU]                            →  output/02-EEC-and-MACAL/
inbox/03-MACAL-only/*.mp4     →  [Kaggle GPU]                            →  output/03-MACAL-only/
```

For each video it: uploads to the live Kaggle session, runs OpenShorts
(`large-v3` Whisper + the rotating viral font mix), downloads the finished
`subtitled_*.mp4` clips **plus** the `_metadata.json` (AI titles, hooks,
per-platform captions), and drops them in the matching Drive folder. The
source video is then moved to `processed/` so it won't run twice.

**Routing is folder-in → folder-out, one-to-one** — exactly the
safety-critical rule from the design doc (§6). The runner never looks at
destinations or re-routes; a MACAL video's clips can only ever land in the
MACAL output folder.

## Setup (one time)

1. Install Python deps:
   ```
   pip install -r requirements.txt
   ```
2. Edit `config.yaml`:
   - `inbox_dir` — where you'll drop raw videos
   - `output_dir` — **point this at your Google Drive sync folder** so clips
     auto-sync to Drive
   - `processed_dir` — where processed sources are archived
   - (optional) Telegram token/chat for zero-clip alerts — better to set via
     env vars `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` than commit them.

## Each run

1. **Start the Kaggle session:** open `../kaggle/AutoEdit_Kaggle_Setup.ipynb`,
   set GPU T4×2, run the setup cells + the bridge cell. Copy the `BRIDGE_URL`.
2. **Drop your videos** into the right `inbox/<brand>/` subfolder. The brand
   folder IS the routing decision.
3. **Run it:**
   ```
   python run_batch.py --bridge-url https://<...>.trycloudflare.com
   ```
   (or put the URL in `config.yaml` and just run `python run_batch.py`)
4. Watch it process. Finished clips land in `output/<brand>/`, which syncs to
   Drive. Get a Telegram ping when done.
5. **Stop the Kaggle session** when finished (hygiene — the Gemini key lives
   in that session).

Useful flags:
- `--dry-run` — list what would be processed, do nothing
- `--config <path>` — use a different config file

## What's still manual (and why)

This runner ends at "clips are in the Drive routing folder." The **posting**
half — n8n picking them up and publishing to TikTok/Reels/YouTube/etc. — is a
separate project (`empire-server-forge`'s social-publishing pipeline) that is
still design-only and needs owner-gated credential setup first. Until that
exists, you post the finished clips manually (they're ready-to-post, with
captions burned in and copy in the metadata JSON).

## Honest limitations

- **Not a daemon.** It's a one-shot batch script ("run before bed"), matching
  the Kaggle session model (spin up → drain the queue → tear down). A
  file-watcher that auto-triggers per drop is deliberately *not* built yet —
  it would open a fresh GPU session per file and waste the 30h/week quota.
- **Kaggle sessions are ephemeral.** You start one per batch and paste its
  URL. Automating session creation is possible later but out of scope here.
- **Large uploads take time.** A 90MB source over the tunnel is a minute or
  two before processing even starts.
