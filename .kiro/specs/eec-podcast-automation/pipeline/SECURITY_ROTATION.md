# Security — token rotation runbook (owner action)

Status from the last audit (no secrets committed to this repo; `.gitignore`
now blocks `.env`, keys, `rclone.conf`, `access_token.txt`, etc.). The items
below are **live infrastructure credentials** that should be rotated. None are
internet-exposed, so this is hygiene, not an active incident — but do it.

> ⚠️ These touch the 12 live containers. Do them one at a time and verify each
> before moving on. Do NOT paste the actual secret values into the repo.

## 1. n8n-MCP `AUTH_TOKEN` (old: `226bfba1…`)
- **Where**: `/opt/n8n-mcp/docker-compose.yml` → `services.n8n-mcp.environment.AUTH_TOKEN`.
- **Exposure**: port bound to `127.0.0.1:3001` only (localhost, not public). Low urgency.
- **Who holds it**: whatever MCP *client* config talks to this server (e.g. a
  desktop agent config). Rotating here breaks that client until its copy is updated.
- **Rotate**:
  1. Generate a new token: `openssl rand -hex 32`.
  2. Edit the compose file, replace `AUTH_TOKEN`, then:
     `cd /opt/n8n-mcp && docker compose up -d` (recreates just this container).
  3. Update the SAME token in the MCP client config that connects to `:3001`.
  4. Verify: the client can call the MCP again; `docker logs empire-n8n-mcp` clean.

## 2. n8n API key (JWT) in the same compose file
- **Where**: `/opt/n8n-mcp/docker-compose.yml` → `N8N_API_KEY` (a plaintext JWT).
- **Rotate**: n8n UI → Settings → **n8n API** → revoke the old key, create a new
  one → paste into the compose `N8N_API_KEY` → `docker compose up -d`.
- Verify the MCP still lists/executes workflows.

## 3. Cloudflare R2 tokens (rclone `r2` and `r2pod`)
- **Where**: rclone config (`access_key_id` / `secret_access_key` for remotes
  `r2` and `r2pod`). Used by `publish_feed.py` to push audio + feed to R2.
- **Rotate** (owner, in Cloudflare dashboard):
  1. Cloudflare → R2 → **Manage R2 API Tokens** → create a new token scoped to
     the `two-worlds-podcast` bucket (Object Read & Write) → note the new
     Access Key ID + Secret.
  2. On the server: `rclone config update r2pod access_key_id NEW secret_access_key NEW`
     (repeat for `r2` if it shares the token).
  3. **Revoke the old token** in Cloudflare.
  4. Verify: `rclone ls r2pod:two-worlds-podcast` still works.

## Hardening already applied in this repo
- `.gitignore` now ignores `.env`, `*.env`, `*.pem`, `*.key`, `id_rsa*`,
  `credentials.json`, `client_secret*.json`, `service-account*.json`,
  `rclone.conf`, `access_token.txt`, `*_token.txt`.
- Repo history scanned: the OpenRouter key and the old MCP token are **not**
  present in any tracked commit. Server `/opt/eec-podcast/.env` is `chmod 600`.
