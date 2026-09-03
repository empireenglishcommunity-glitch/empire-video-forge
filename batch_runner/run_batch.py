"""
Empire Video Forge — Batch Runner (Step 2a)

One-shot script that processes all videos in the inbox through a live Kaggle
GPU session and drops the finished clips into the matching Drive routing
folder. Run this on your PC ("before bed" rhythm).

Workflow:
    inbox/01-EEC-only/*.mp4       → clips → output/01-EEC-only/
    inbox/02-EEC-and-MACAL/*.mp4  → clips → output/02-EEC-and-MACAL/
    inbox/03-MACAL-only/*.mp4     → clips → output/03-MACAL-only/

The "output/" base is your Google Drive sync folder (set in config.yaml),
so clips land in Drive automatically and the future n8n trigger picks them
up. The routing rule is folder-in → folder-out, one-to-one, exactly as the
design doc requires (§6).

Prerequisites:
    - A running Kaggle GPU session with the bridge alive (run the notebook,
      paste the BRIDGE_URL into config.yaml or pass --bridge-url).
    - OpenShorts + all fixes installed in the session (the notebook does this).
    - Google Drive Desktop syncing the output folder (or any local folder you
      manually upload from — the script just writes files).

Usage:
    python run_batch.py                          # uses config.yaml
    python run_batch.py --bridge-url <url>       # override bridge URL
    python run_batch.py --dry-run                # show what would be processed

Security:
    - The Gemini key lives in the Kaggle session's .env, not on your PC.
    - The bridge URL is an unauthenticated temporary shell — stop the Kaggle
      session when the batch is done.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Optional

import requests
import yaml

# ── Constants ────────────────────────────────────────────────────────────────

BRAND_FOLDERS = ["01-EEC-only", "02-EEC-and-MACAL", "03-MACAL-only"]
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
POLL_INTERVAL = 15  # seconds between job polls
UPLOAD_TIMEOUT = 600  # seconds to upload a large video
PROCESS_TIMEOUT = 900  # seconds max for one video to process


# ── Config ───────────────────────────────────────────────────────────────────

def load_config(config_path: Path) -> dict:
    """Load config.yaml and return the settings dict."""
    if not config_path.exists():
        print(f"⚠️  Config not found at {config_path} — using defaults.")
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def resolve_paths(cfg: dict) -> tuple[Path, Path, Path]:
    """Return (inbox_dir, output_dir, processed_dir) from config or defaults."""
    base = Path(cfg.get("base_dir", Path.home() / "empire-video-forge"))
    inbox = Path(cfg.get("inbox_dir", base / "inbox"))
    output = Path(cfg.get("output_dir", base / "output"))
    processed = Path(cfg.get("processed_dir", base / "processed"))
    return inbox, output, processed


# ── Bridge helpers ───────────────────────────────────────────────────────────

def bridge_health(url: str) -> bool:
    """Check if the Kaggle bridge is alive."""
    try:
        r = requests.get(f"{url}/health", timeout=10)
        return r.ok and r.json().get("status") == "ok"
    except Exception:
        return False


def bridge_upload(url: str, local_path: Path, remote_name: str) -> bool:
    """Upload a file to the Kaggle session via the bridge."""
    print(f"  ⬆️  Uploading {local_path.name} ({local_path.stat().st_size / 1e6:.1f} MB)...")
    with open(local_path, "rb") as f:
        r = requests.post(
            f"{url}/upload?path={remote_name}",
            data=f,
            headers={"Content-Type": "application/octet-stream"},
            timeout=UPLOAD_TIMEOUT,
        )
    if r.ok:
        info = r.json()
        print(f"  ✅ Uploaded ({info.get('bytes_written', 0) / 1e6:.1f} MB)")
        return True
    print(f"  ❌ Upload failed: {r.status_code} {r.text[:200]}")
    return False


def bridge_exec(url: str, cmd: str, background: bool = False,
                job_id: Optional[str] = None) -> dict:
    """Run a command on the Kaggle session. Returns the response dict."""
    payload = {"cmd": cmd, "background": background}
    if job_id:
        payload["job_id"] = job_id
    r = requests.post(f"{url}/exec", json=payload, timeout=300 if not background else 30)
    return r.json()


def bridge_poll(url: str, job_id: str, timeout: int = PROCESS_TIMEOUT) -> dict:
    """Poll a background job until it finishes or times out."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{url}/jobs/{job_id}", timeout=15)
            data = r.json()
            if not data.get("running", True):
                return data
            elapsed = data.get("elapsed_sec", 0)
            print(f"  ⏳ Processing... ({elapsed:.0f}s)", end="\r")
        except Exception as e:
            print(f"  ⚠️  Poll error: {e}")
        time.sleep(POLL_INTERVAL)
    return {"error": "timeout", "elapsed_sec": time.time() - start}


def bridge_download(url: str, remote_path: str, local_path: Path) -> bool:
    """Download a file from the Kaggle session to a local path."""
    try:
        r = requests.get(f"{url}/download?path={remote_path}",
                         timeout=UPLOAD_TIMEOUT, stream=True)
        if not r.ok:
            print(f"  ❌ Download failed: {r.status_code}")
            return False
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
        print(f"  ⬇️  Downloaded {local_path.name} ({local_path.stat().st_size / 1e6:.1f} MB)")
        return True
    except Exception as e:
        print(f"  ❌ Download error: {e}")
        return False


def bridge_list(url: str, path: str = "") -> list[dict]:
    """List files at a remote path."""
    try:
        r = requests.get(f"{url}/list?path={path}", timeout=15)
        return r.json().get("entries", [])
    except Exception:
        return []


# ── Telegram alert ───────────────────────────────────────────────────────────

def send_telegram_alert(cfg: dict, message: str):
    """Send a Telegram message via the bot. Fails silently if not configured."""
    token = cfg.get("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = cfg.get("telegram_chat_id") or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        pass  # alert is best-effort


# ── Core processing ─────────────────────────────────────────────────────────

def find_inbox_videos(inbox: Path) -> dict[str, list[Path]]:
    """Scan inbox subfolders and return {brand_folder: [video_paths]}."""
    result = {}
    for brand in BRAND_FOLDERS:
        folder = inbox / brand
        if not folder.is_dir():
            continue
        videos = [
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        ]
        if videos:
            result[brand] = sorted(videos)
    return result


def process_one_video(bridge_url: str, video_path: Path, brand: str,
                      output_dir: Path) -> list[Path]:
    """Upload, process, and download clips for one video. Returns local clip paths."""
    name = video_path.stem
    remote_input = f"inbox_{name}{video_path.suffix}"
    remote_out_dir = f"batch_out_{name}"

    # 1. Upload
    if not bridge_upload(bridge_url, video_path, remote_input):
        return []

    # 2. Process (background)
    job_id = f"batch_{name}_{int(time.time())}"
    cmd = (
        f"cd /kaggle/working/openshorts && "
        f"rm -rf /kaggle/working/{remote_out_dir} && "
        f"mkdir -p /kaggle/working/{remote_out_dir} && "
        f"export WHISPER_MODEL=large-v3 WHISPER_DEVICE=cuda WHISPER_COMPUTE=float16 && "
        f"python main.py -i /kaggle/working/{remote_input} "
        f"-o /kaggle/working/{remote_out_dir} --format vertical 2>&1 ; "
        f"echo PROCESS_EXIT=$?"
    )
    bridge_exec(bridge_url, cmd, background=True, job_id=job_id)

    # 3. Poll until done
    result = bridge_poll(bridge_url, job_id)
    if result.get("error") == "timeout":
        print(f"  ❌ Processing timed out for {video_path.name}")
        return []

    # 4. List + download the subtitled clips
    entries = bridge_list(bridge_url, remote_out_dir)
    clip_entries = [e for e in entries if e["name"].startswith("subtitled_") and e["name"].endswith(".mp4")]
    metadata_entries = [e for e in entries if e["name"].endswith("_metadata.json")]

    downloaded = []
    brand_out = output_dir / brand
    brand_out.mkdir(parents=True, exist_ok=True)

    for entry in clip_entries:
        remote = f"{remote_out_dir}/{entry['name']}"
        local = brand_out / entry["name"]
        if bridge_download(bridge_url, remote, local):
            downloaded.append(local)

    # Also download metadata (titles, hooks, per-platform captions)
    for entry in metadata_entries:
        remote = f"{remote_out_dir}/{entry['name']}"
        local = brand_out / entry["name"]
        bridge_download(bridge_url, remote, local)

    return downloaded


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Empire Video Forge — Batch Runner (Step 2a)")
    parser.add_argument("--bridge-url", type=str, help="Override the Kaggle bridge URL")
    parser.add_argument("--config", type=str, default="config.yaml",
                        help="Path to config.yaml (default: config.yaml)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without doing it")
    args = parser.parse_args()

    # Load config
    cfg = load_config(Path(args.config))
    inbox, output, processed = resolve_paths(cfg)
    bridge_url = (args.bridge_url or cfg.get("bridge_url", "")).rstrip("/")

    # Ensure inbox structure exists
    for brand in BRAND_FOLDERS:
        (inbox / brand).mkdir(parents=True, exist_ok=True)
    print(f"📂 Inbox:    {inbox}")
    print(f"📂 Output:   {output}")
    print(f"📂 Processed:{processed}")

    # Scan for videos
    queue = find_inbox_videos(inbox)
    total = sum(len(v) for v in queue.values())

    if total == 0:
        print("\n📭 Inbox is empty — nothing to process.")
        return

    print(f"\n📋 Found {total} video(s) across {len(queue)} brand folder(s):")
    for brand, videos in queue.items():
        for v in videos:
            print(f"   {brand}/{v.name} ({v.stat().st_size / 1e6:.1f} MB)")

    if args.dry_run:
        print("\n🔍 Dry run — stopping here.")
        return

    # Validate bridge
    if not bridge_url:
        print("\n❌ No bridge URL. Either:")
        print("   - Set 'bridge_url' in config.yaml")
        print("   - Pass --bridge-url <url>")
        print("   (Start a Kaggle notebook, run the bridge cell, paste the URL)")
        sys.exit(1)

    print(f"\n🔗 Bridge: {bridge_url}")
    if not bridge_health(bridge_url):
        print("❌ Bridge is not reachable. Is the Kaggle session running?")
        sys.exit(1)
    print("✅ Bridge is alive.\n")

    # Process each video
    batch_start = time.time()
    total_clips = 0
    failed = []

    for brand, videos in queue.items():
        print(f"━━━ {brand} ({len(videos)} video(s)) ━━━")
        for video in videos:
            print(f"\n🎬 Processing: {video.name}")
            clips = process_one_video(bridge_url, video, brand, output)

            if clips:
                total_clips += len(clips)
                print(f"  ✅ {len(clips)} clip(s) → {output / brand}/")
                # Move source to processed/ so it's not re-processed
                dest = processed / brand
                dest.mkdir(parents=True, exist_ok=True)
                shutil.move(str(video), str(dest / video.name))
                print(f"  📦 Source moved to processed/{brand}/")
            else:
                failed.append(f"{brand}/{video.name}")
                print(f"  ❌ No clips produced for {video.name}")

    # Summary
    elapsed = time.time() - batch_start
    print(f"\n{'━' * 50}")
    print(f"🏁 Batch complete in {elapsed / 60:.1f} min")
    print(f"   Total clips produced: {total_clips}")
    print(f"   Failed: {len(failed)}")
    if failed:
        print(f"   Failed videos: {', '.join(failed)}")

    # Telegram alert
    if total_clips == 0 and total > 0:
        send_telegram_alert(
            cfg,
            f"⚠️ *Empire Video Forge*\nBatch ran but produced *0 clips* "
            f"from {total} video(s). Check the Kaggle session logs."
        )
    elif total_clips > 0:
        send_telegram_alert(
            cfg,
            f"✅ *Empire Video Forge*\n{total_clips} clip(s) from "
            f"{total} video(s) in {elapsed / 60:.1f} min. "
            f"Ready in Drive routing folders."
        )


if __name__ == "__main__":
    main()
