#!/usr/bin/env python3
"""Upload a file to a Drive folder using the n8n cred's refreshed token.
Usage: drive_upload.py <path> <name> <mime> <folder_id> [--token /tmp/access_token.txt]
Refreshes /tmp/access_token.txt from the n8n Drive cred if it is missing/stale."""
import json, urllib.request, urllib.parse, sys, os, subprocess

def refresh_token(path="/tmp/access_token.txt"):
    raw = subprocess.run(["docker","exec","empire-n8n","n8n","export:credentials",
                          "--id=FDFZdH8pQKLZQFzz","--decrypted"],
                         capture_output=True, text=True).stdout
    line = next(l for l in raw.splitlines() if l.startswith("["))
    d = json.loads(line)[0]["data"]
    tok = d["oauthTokenData"]
    if isinstance(tok, str): tok = json.loads(tok)
    body = urllib.parse.urlencode({"client_id":d["clientId"],"client_secret":d["clientSecret"],
        "refresh_token":tok["refresh_token"],"grant_type":"refresh_token"}).encode()
    at = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=body,
        headers={"Content-Type":"application/x-www-form-urlencoded"}), timeout=30))["access_token"]
    open(path,"w").write(at)
    return at

def main():
    path, name, mime, folder = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    tpath = "/tmp/access_token.txt"
    at = open(tpath).read().strip() if os.path.exists(tpath) and os.path.getsize(tpath) else refresh_token(tpath)
    meta = {"name": name, "parents": [folder]}
    b = "===EECB==="
    body = b""
    body += ("--"+b+"\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n").encode()
    body += (json.dumps(meta)+"\r\n").encode()
    body += ("--"+b+"\r\nContent-Type: "+mime+"\r\n\r\n").encode()
    body += open(path,"rb").read()+b"\r\n"
    body += ("--"+b+"--").encode()
    def do(tok):
        req = urllib.request.Request(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true",
            data=body, headers={"Authorization":"Bearer "+tok,"Content-Type":"multipart/related; boundary="+b})
        return json.load(urllib.request.urlopen(req, timeout=300))
    try:
        r = do(at)
    except urllib.error.HTTPError as e:
        if e.code in (401,403):
            r = do(refresh_token(tpath))
        else:
            raise
    print("UPLOADED:", r.get("name"), r.get("id"))

if __name__ == "__main__":
    main()
