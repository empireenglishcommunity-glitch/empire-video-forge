#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEC "Two Worlds" — podcast trigger service (internal, for n8n weekly schedule).

A tiny always-on host service (mirrors the orientation probe) that n8n calls on a
weekly schedule to GENERATE the next episode's PLAIN audio. It runs run_podcast.py
in the background and reports status, so n8n never blocks on the multi-minute run.

By design this ONLY generates + delivers plain audio to output/Podcast/raw-audio.
It does NOT publish anything — the owner adds video/thumbnail/cover/music and hands
finished files back (for-youtube / for-platforms) for the separate publish steps.

Endpoints (bound to the docker gateway 172.18.0.1 only; ufw-restricted; never
internet-exposed — same security model as eec-probe):
  GET  /health                      -> {"ok":true,"service":"eec-podcast-trigger"}
  POST /run   {"episode":N}         -> starts a run; {"ok":true,"episode":N,"started":true}
                                       (if episode omitted, uses next after the last
                                        delivered episode in state)
  GET  /status?episode=N            -> {"ok":true,"episode":N,"state":"running|done|
                                        waiting|failed|unknown","tail":[...log lines]}

n8n flow: weekly Schedule -> POST /run -> (wait) -> GET /status -> Telegram notify
the owner: audio ready in raw-audio, or "waiting on Kaggle English / TTS quota".
"""
import http.server, socketserver, json, subprocess, os, threading, re, glob

HOST = "172.18.0.1"
PORT = 8904
HOME = os.environ.get("EEC_PODCAST_HOME", "/opt/eec-podcast")
PY = os.path.join(HOME, "venv", "bin", "python3")
RUN = os.path.join(HOME, "bin", "run_podcast.py")
LOGDIR = os.path.join(HOME, "logs")
ENVFILE = os.path.join(HOME, ".env")

_runs = {}          # episode -> {"state": ..., "returncode": ...}
_lock = threading.Lock()


def load_env():
    env = dict(os.environ)
    try:
        for line in open(ENVFILE):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k] = v
    except Exception:
        pass
    return env


def delivered_episodes():
    """Set of episode numbers that have already produced a plain-audio file."""
    done = set()
    for p in glob.glob(os.path.join(HOME, "episodes", "ep*", "ep*_audio_plain.m4a")):
        m = re.search(r"ep(\d{2})_audio_plain", os.path.basename(p))
        if m:
            done.add(int(m.group(1)))
    return done


def next_episode():
    """Next episode = (max produced plain audio) + 1, default 1."""
    done = delivered_episodes()
    return (max(done) + 1) if done else 1


def prior_gap(ep):
    """Return the first earlier episode (< ep) that has NOT produced plain audio,
    or None if every episode below `ep` is already done. Used to refuse skipping
    ahead (the 'jumped to Ep3 before Ep1 shipped' class of mistake) at the
    automation level. Episode 1 has no prerequisite."""
    if ep <= 1:
        return None
    done = delivered_episodes()
    for e in range(1, ep):
        if e not in done:
            return e
    return None


def do_run(ep):
    with _lock:
        _runs[ep] = {"state": "running", "returncode": None}
    env = load_env()
    try:
        r = subprocess.run([PY, RUN, "--episode", str(ep)],
                           capture_output=True, text=True, env=env, timeout=3600)
        rc = r.returncode
        # run_podcast exit codes: 0 delivered, 3 waiting (Kaggle/quota), 1 failed
        state = {0: "done", 3: "waiting", 1: "failed"}.get(rc, "failed")
    except Exception as e:
        rc, state = -1, "failed"
    with _lock:
        _runs[ep] = {"state": state, "returncode": rc}


def log_tail(ep, n=15):
    path = os.path.join(LOGDIR, f"ep{ep:02d}_run.log")
    try:
        with open(path, encoding="utf-8") as f:
            return [l.rstrip("\n") for l in f.readlines()[-n:]]
    except Exception:
        return []


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send({"ok": True, "service": "eec-podcast-trigger"})
        if self.path.startswith("/status"):
            m = re.search(r"episode=(\d+)", self.path)
            ep = int(m.group(1)) if m else next_episode() - 1
            with _lock:
                run = _runs.get(ep, {"state": "unknown", "returncode": None})
            return self._send({"ok": True, "episode": ep, "state": run["state"],
                               "returncode": run["returncode"], "tail": log_tail(ep)})
        return self._send({"ok": False, "reason": "unknown path"}, 404)

    def do_POST(self):
        if self.path != "/run":
            return self._send({"ok": False, "reason": "unknown path"}, 404)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b"{}"
            req = json.loads(body or b"{}")
        except Exception:
            req = {}
        ep = req.get("episode") or next_episode()
        # GUARD: don't skip ahead. Refuse ep N if an earlier episode never shipped
        # (prevents the 'jumped to Ep3 before Ep1 was posted' mistake). Override
        # with {"force": true} for a deliberate out-of-order run.
        gap = prior_gap(ep)
        if gap is not None and not req.get("force"):
            return self._send({"ok": False, "episode": ep, "started": False,
                               "reason": f"episode {gap} not delivered yet; refusing "
                                         f"to skip ahead to {ep}. Send {{\"force\":true}} "
                                         f"to override."}, 409)
        with _lock:
            already = _runs.get(ep, {}).get("state") == "running"
        if already:
            return self._send({"ok": True, "episode": ep, "started": False,
                               "note": "already running"})
        threading.Thread(target=do_run, args=(ep,), daemon=True).start()
        return self._send({"ok": True, "episode": ep, "started": True})

    def log_message(self, *a):
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server((HOST, PORT), Handler) as httpd:
        print(f"eec-podcast-trigger on {HOST}:{PORT}")
        httpd.serve_forever()
