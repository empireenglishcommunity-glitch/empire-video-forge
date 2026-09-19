# Two Worlds — Ep1 Status & Session Handoff

> Checkpoint to resume cleanly. **Current focus: finish the NEW SHORT Ep1
> (~6.6 min) → owner reviews → post.** All work is committed to `main`.
> Last updated: 2026-09-19 (end of session — everything synced & locked).

## ⏸️ WHERE WE STOPPED (resume here tomorrow)
**Next action is OWNER's: run the two Kaggle voice notebooks for the new short
Ep1, drop the WAVs on the server, then tell the agent "synth done."** The agent
then re-assembles + delivers. Details in "THE IMMEDIATE NEXT STEP" below.

## THE BIG DECISION THIS SESSION: short episodes
- The old 40-min Ep1 was **abandoned** (too long to review/produce; also had
  Arabic pronunciation mistakes). The whole system moved to a **TIGHT 5-10 min
  format (default ~7 min)**.
- **Ep1 was regenerated short**: `episodes/ep01/script.json` = **51 lines, ~991
  words, ~6.6 min**, title "The Arrival", level A2. It PASSES both gates
  (structure + duration). Script was reviewed + 3 text fixes applied (Macal name
  →ماكال, "first episode" wording, stripped a stray stage direction).
- The old long Ep1 is preserved on the server at
  `episodes/_abandoned_ep01_long_20260919000034/` (script, synth WAVs, the 40-min
  audio, timelines — nothing deleted).

## THE IMMEDIATE NEXT STEP (owner → then agent)
1. **OWNER (Kaggle GPU):** two notebooks, each = new Kaggle notebook, GPU T4,
   Internet ON, paste the whole file, Run All. They auto-fetch the new 51-line
   script from `main`:
   - `kaggle/synth_episode_ar.py` → Arabic Coach lines (VoiceTut, voice "Sayed"). ~11 lines.
   - `kaggle/synth_episode_en.py` → English lines (Chatterbox). ~40 lines.
   Download each notebook's `ep01/` output (`lineNNN_*.wav` + `manifest.ar.json` /
   `manifest.en.json`) and drop BOTH into `/opt/eec-podcast/episodes/ep01/synth/`.
2. **AGENT (after "synth done"):** re-assemble through the structure gate
   (`run_podcast.py --episode 1 --skip-deliver` or `assemble_audio.py`), verify
   ~5-10 min + 51/51 rendered + clean, then deliver to Drive `raw-audio`
   (`drive_upload.py`). Then commit final state.
3. **OWNER:** review the finished plain audio → add music/video/cover → publish
   (YouTube forwarder + RSS feed).

## WHAT'S LOCKED (all merged to `main`)
- **Short-episode format** — `gen_episode.py`: compact 6-section template
  (cold_open, coach_intro, act1, coach_break1, act2, coach_outro) via
  `build_acts(minutes)`; `--minutes` (default 7), `--force`, `--no-advance`;
  **DURATION GUARD** (won't save outside 5-10 min unless `--force`).
- **Story/teaching STRUCTURE GATE** — `structure_check.py` (series-bible §10):
  cold_open is pure story; Coach speaks ONLY in coach sections; no Coach line
  inside a story scene. Enforced in BOTH `gen_episode.py` (post-gen) and
  `assemble_audio.py` (pre-assembly, fail-closed; `--force` to override). This
  fixed the earlier "messy audio" root cause (it was a script-order bug, NOT an
  assembler bug — assembly is mechanically sound).
- **Automation** — n8n workflow `Two Worlds — Weekly Podcast Generate`
  (id `IRVBwGGJBF1SpePA`) is **INACTIVE** (correct; don't activate until Ep1
  ships). It calls `eec-podcast-trigger.service` (172.18.0.1:8904) →
  `run_podcast.py` (modern VoiceTut+manifest path). Trigger has a **no-skip-ahead
  guard** (refuses ep N if an earlier episode never shipped; `force` override).
- **Ep2 removed / season rolled back** to `current_episode: 2`.
- Docs synced to reality: `design.md`, `OPERATIONS.md` (runbook), `series-bible.md`
  (§5 short template + §10 structure rule).

## STATE SNAPSHOT (verified at session end)
- Repo `main`: clean, all work merged (PRs #33, #34, #35 merged). Nothing pending.
- Server `/opt/eec-podcast/bin` ↔ repo `pipeline/`: **hash-matched** for
  gen_episode, assemble_audio, structure_check, manifest_lib, run_podcast.
- Server `episodes/ep01/`: new short `script.json` (+ `.pretextfix` backup, `_acts/`
  cache). **`synth/` is EMPTY** — waiting on the owner's Kaggle run.
- `season.json`: `current_episode: 2`.
- Drive `raw-audio`: old long Ep1 audio TRASHED; still holds `ep01_english.zip` +
  `ep01_arabic.zip` (old long-Ep1 batches — harmless, will be superseded).
- **12 containers: all UP.** Disk 80% (7.4 GB free).

## VOICE ENGINE (locked)
- Arabic = VoiceTut (Coach = "Sayed") via shared `egyptian_lexicon.json`.
- English = Chatterbox (cloned refs in `voice-refs/` = server `voices/refs/`).
- Both on Kaggle GPU (clash in one kernel → two notebooks). Server has NO GPU —
  never synth on the server. Notebooks fetch script/config from `BRANCH = "main"`.

## STILL OPEN (owner findings, deferred by the short-episode decision)
The owner earlier raised: (#2) drop Macal's cloned voice, (#3) weak/uncreative
character choices, (#4) review burden. The move to short episodes set these aside
for now (short + regenerated Ep1 makes review tractable). Revisit AFTER Ep1 ships
if still desired.

## KEY PATHS & GOTCHAS
- Repo: `/projects/sandbox/empire-video-forge`, spec dir
  `.kiro/specs/eec-podcast-automation/`.
- Server: `ssh eec-editor` = `root@77.42.43.250`. ⚠️ **fail2ban** bans rapid
  reconnects — use SINGLE sessions, wait ~45s after a "Connection refused".
- SSH key for this sandbox is authorized on the server (added this session).
- No ffmpeg/soundfile locally in the sandbox — heavy audio ops run on the server.
- File edits are LOCAL to the repo; push to the server with
  `cat file | ssh eec-editor 'cat > /path'`.
- **GitHub PRs merge fast on this repo** — push ALL commits BEFORE opening a PR
  (a PR merged early once, splitting commits; fixed via a follow-up PR).
