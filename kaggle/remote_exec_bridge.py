"""
Empire Video Forge — Remote Execution Bridge for Kaggle

VERBATIM REUSE of macal-empire-image-forge/kaggle/remote_exec_bridge.py
(only this docstring's task-specific bullets were re-pointed at the video
workload). The server logic below is unchanged — it is a generic, path-safe
remote shell, not image- or video-specific. Keep the two copies in sync; if
the bridge is improved, improve it there and copy it here.

Paste this ENTIRE script into a single Kaggle notebook cell and run it.
It starts a tiny HTTP server (stdlib only, no extra installs needed) and
exposes it via a Cloudflare quick tunnel, giving Kiro direct remote control
of this Kaggle session — the same pattern proven for the ComfyUI/LoRA phase.

Once running, copy the printed tunnel URL back into the chat. From there,
Kiro will directly:
  - upload a long source video into this session (no manual upload needed)
  - install + start OpenShorts (the auto-edit engine) on the GPU
  - launch the clip-generation run (long-running, backgrounded)
  - poll processing progress/logs periodically
  - list + download the finished 9:16 clips when done

Endpoints:
  GET  /health                         -> {"status": "ok"}
  POST /upload?path=<relative path>    -> raw request body written to that
                                           path under /kaggle/working/
  POST /exec   {"cmd": str,
                "cwd": str (optional),
                "background": bool (optional),
                "job_id": str (optional, required if background)}
                                        -> runs a shell command. If
                                           background=false (default), waits
                                           for it to finish and returns full
                                           stdout/stderr + returncode. If
                                           background=true, starts it and
                                           returns immediately; poll with
                                           GET /jobs/<job_id>
  GET  /jobs/<job_id>                  -> {"running": bool, "returncode": ...,
                                            "log_tail": "<last ~4000 chars>"}
  GET  /download?path=<relative path>  -> streams the file back as bytes
  GET  /list?path=<relative path>      -> JSON list of files/dirs at that path

Security note: this has NO auth — anyone with the tunnel URL can run
arbitrary commands in this Kaggle session. The URL is only shared in this
chat session and Cloudflare quick tunnel URLs are unguessable, but treat it
like a temporary root shell: don't leave it running longer than needed, and
the Kaggle session itself is sandboxed/ephemeral so worst case is just
losing that session's work.
"""
import http.server
import json
import os
import re
import socketserver
import subprocess
import threading
import time
import urllib.parse
from pathlib import Path

WORK_DIR = Path("/kaggle/working")
WORK_DIR.mkdir(parents=True, exist_ok=True)

JOBS = {}  # job_id -> {"proc": Popen, "log_path": Path, "started": float}
JOBS_LOCK = threading.Lock()


def _job_log_path(job_id: str) -> Path:
    return WORK_DIR / f".bridge_job_{job_id}.log"


class BridgeHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _resolve_safe_path(self, rel_path: str) -> Path:
        # Prevent escaping WORK_DIR via ../ tricks
        candidate = (WORK_DIR / rel_path).resolve()
        if not str(candidate).startswith(str(WORK_DIR.resolve())):
            raise ValueError("Path escapes working directory")
        return candidate

    def log_message(self, fmt, *args):
        pass  # silence default request logging (Kaggle cell output stays clean)

    # -------------------------------------------------------------- GET ----
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        try:
            if parsed.path == "/health":
                self._send_json({"status": "ok"})

            elif parsed.path == "/list":
                rel = qs.get("path", [""])[0]
                try:
                    target = self._resolve_safe_path(rel)
                except ValueError as e:
                    self._send_json({"error": str(e)}, 400)
                    return
                if not target.exists():
                    self._send_json({"error": f"not found: {rel}"}, 404)
                    return
                if target.is_dir():
                    entries = []
                    for p in sorted(target.iterdir()):
                        entries.append({
                            "name": p.name,
                            "is_dir": p.is_dir(),
                            "size": p.stat().st_size if p.is_file() else None,
                        })
                    self._send_json({"path": rel, "entries": entries})
                else:
                    st = target.stat()
                    self._send_json({"path": rel, "size": st.st_size})

            elif parsed.path == "/download":
                rel = qs.get("path", [""])[0]
                target = self._resolve_safe_path(rel)
                if not target.exists() or not target.is_file():
                    self._send_json({"error": f"file not found: {rel}"}, 404)
                    return
                size = target.stat().st_size
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(size))
                self.end_headers()
                with open(target, "rb") as f:
                    while True:
                        chunk = f.read(1024 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)

            elif parsed.path.startswith("/jobs/"):
                job_id = parsed.path.split("/jobs/", 1)[1]
                with JOBS_LOCK:
                    job = JOBS.get(job_id)
                if job is None:
                    self._send_json({"error": f"unknown job_id: {job_id}"}, 404)
                    return
                proc = job["proc"]
                running = proc.poll() is None
                log_path = job["log_path"]
                log_tail = ""
                if log_path.exists():
                    data = log_path.read_text(encoding="utf-8", errors="replace")
                    log_tail = data[-4000:]
                self._send_json({
                    "job_id": job_id,
                    "running": running,
                    "returncode": None if running else proc.returncode,
                    "elapsed_sec": round(time.time() - job["started"], 1),
                    "log_tail": log_tail,
                })

            else:
                self._send_json({"error": "unknown endpoint"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ------------------------------------------------------------- POST ----
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        content_length = int(self.headers.get("Content-Length", 0))

        try:
            if parsed.path == "/upload":
                rel = qs.get("path", [""])[0]
                if not rel:
                    self._send_json({"error": "missing ?path="}, 400)
                    return
                target = self._resolve_safe_path(rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                with open(target, "wb") as f:
                    remaining = content_length
                    while remaining > 0:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        f.write(chunk)
                        written += len(chunk)
                        remaining -= len(chunk)
                self._send_json({"path": rel, "bytes_written": written})

            elif parsed.path == "/exec":
                raw = self.rfile.read(content_length)
                payload = json.loads(raw.decode("utf-8"))
                cmd = payload["cmd"]
                cwd = payload.get("cwd", str(WORK_DIR))
                background = payload.get("background", False)

                if background:
                    job_id = payload.get("job_id") or f"job_{int(time.time())}"
                    log_path = _job_log_path(job_id)
                    log_file = open(log_path, "w", encoding="utf-8")
                    proc = subprocess.Popen(
                        cmd, shell=True, cwd=cwd,
                        stdout=log_file, stderr=subprocess.STDOUT,
                    )
                    with JOBS_LOCK:
                        JOBS[job_id] = {"proc": proc, "log_path": log_path, "started": time.time()}
                    self._send_json({"job_id": job_id, "started": True})
                else:
                    result = subprocess.run(
                        cmd, shell=True, cwd=cwd,
                        capture_output=True, text=True, timeout=300,
                    )
                    self._send_json({
                        "returncode": result.returncode,
                        "stdout": result.stdout[-8000:],
                        "stderr": result.stderr[-8000:],
                    })

            else:
                self._send_json({"error": "unknown endpoint"}, 404)

        except subprocess.TimeoutExpired:
            self._send_json({"error": "command timed out (foreground exec limited to 300s — use background:true for long jobs)"}, 504)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def _start_tunnel(port: int):
    """Start a fresh cloudflared quick tunnel process and return (proc, url)."""
    tunnel_proc = subprocess.Popen(
        ["./cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    url = None
    for _ in range(60):
        line = tunnel_proc.stdout.readline()
        if not line:
            if tunnel_proc.poll() is not None:
                break
            continue
        match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
        if match:
            url = match.group(0)
            break
    return tunnel_proc, url


def _tunnel_watchdog(port: int):
    """
    Cloudflare quick tunnels can silently die during long sessions (observed:
    DNS stops resolving entirely, no warning). This loop checks tunnel health
    every 20s and transparently restarts it if it's gone, printing a fresh
    BRIDGE_URL each time — so a dead tunnel no longer means losing the whole
    training run, just a quick URL refresh.
    """
    current_proc, current_url = _start_tunnel(port)
    if current_url:
        print(f"\nBRIDGE_URL: {current_url}\n")
        print("Paste that URL back into the Kiro chat to hand over control.")
    else:
        print("Tunnel URL did not appear in time on first attempt — will keep retrying in background.")

    while True:
        time.sleep(20)
        dead = current_proc.poll() is not None
        if not dead:
            # Extra check: quick tunnels sometimes stay listed as "running"
            # as a process but stop actually resolving. A lightweight local
            # health check against our own server (not through the tunnel)
            # can't detect that, so we just also verify the process is still
            # alive as a first-line signal and rely on the user reporting
            # dead requests as the second signal.
            continue
        print("\n[watchdog] Tunnel process died — restarting cloudflared...")
        current_proc, current_url = _start_tunnel(port)
        if current_url:
            print(f"\n[watchdog] NEW BRIDGE_URL: {current_url}\n")
            print("Paste that fresh URL back into the Kiro chat.")
        else:
            print("[watchdog] Restart attempt did not produce a URL — will retry again shortly.")


def main():
    port = 8189  # different from ComfyUI's 8188 so both can run if needed
    server = ThreadingHTTPServer(("0.0.0.0", port), BridgeHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Remote exec bridge running on 0.0.0.0:{port}")

    if not os.path.exists("./cloudflared"):
        os.system("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared")
        os.system("chmod +x cloudflared")

    print("Waiting for tunnel URL...")
    print("\nBridge is live with auto-restarting tunnel watchdog. Leave this cell running.")
    _tunnel_watchdog(port)  # blocks forever, restarting the tunnel as needed


if __name__ == "__main__":
    main()
