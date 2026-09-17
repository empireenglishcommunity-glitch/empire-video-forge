#!/usr/bin/env python3
"""
EEC Probe — tiny always-on service that classifies an uploaded video by
ORIENTATION (the EEC rule): vertical => Short, horizontal => Long-form.

POST /probe  with the raw video bytes as the request body.
Returns JSON: {"ok":true,"orientation":"vertical|horizontal|square",
               "is_short":true|false,"width":W,"height":H,"duration":sec}

Binds to the docker gateway only (172.18.0.1) so n8n can reach it internally;
NOT exposed to the internet (ufw restricts to the docker subnet). Fail-soft:
any error returns {"ok":false,...} and n8n falls back to its default logic.
Runs ffprobe with a timeout and low priority (nice) to protect the box.
"""
import http.server, socketserver, json, subprocess, tempfile, os, sys

HOST = "172.18.0.1"     # docker gateway — internal only
PORT = 8902
MAX_BYTES = 600 * 1024 * 1024   # 600MB cap (safety)


def probe(path):
    cmd = ('nice -n 15 ffprobe -v error -select_streams v:0 '
           '-show_entries stream=width,height:format=duration '
           '-of json "%s"' % path)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    data = json.loads(r.stdout or "{}")
    st = (data.get("streams") or [{}])[0]
    w = int(st.get("width") or 0)
    h = int(st.get("height") or 0)
    dur = 0.0
    try:
        dur = float((data.get("format") or {}).get("duration") or 0)
    except Exception:
        dur = 0.0
    if w == 0 or h == 0:
        return {"ok": False, "reason": "no video stream dims"}
    if h > w:
        orient = "vertical"
    elif w > h:
        orient = "horizontal"
    else:
        orient = "square"
    return {
        "ok": True,
        "orientation": orient,
        "is_short": (orient == "vertical" or orient == "square"),
        "width": w, "height": h, "duration": round(dur, 2),
    }


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send({"ok": True, "service": "eec-probe"})
        else:
            self._send({"ok": False, "reason": "use POST /probe"}, 404)

    def do_POST(self):
        if self.path != "/probe":
            self._send({"ok": False, "reason": "unknown path"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BYTES:
                self._send({"ok": False, "reason": "bad length"}, 400)
                return
            tmp = tempfile.NamedTemporaryFile(prefix="eecprobe_", suffix=".bin", delete=False)
            remaining = length
            while remaining > 0:
                chunk = self.rfile.read(min(1 << 20, remaining))
                if not chunk:
                    break
                tmp.write(chunk)
                remaining -= len(chunk)
            tmp.close()
            try:
                result = probe(tmp.name)
            finally:
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass
            self._send(result)
        except Exception as e:
            self._send({"ok": False, "reason": str(e)[:200]}, 200)  # fail-soft: 200 so n8n reads it

    def log_message(self, *a):
        pass  # quiet


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server((HOST, PORT), Handler) as httpd:
        print("eec-probe listening on %s:%d" % (HOST, PORT), flush=True)
        httpd.serve_forever()
