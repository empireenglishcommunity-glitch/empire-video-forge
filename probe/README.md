# EEC Probe — orientation-based Short/Long detection

Tiny always-on host service (`/opt/eec-probe`, systemd `eec-probe.service`) that the
publishing pipeline calls to classify each uploaded video by ORIENTATION:

- **vertical (portrait) => Short**
- **horizontal (landscape) => Long-form**

## Why
n8n's container has no ffprobe. The host does. This service runs ffprobe on the
POSTed video bytes and returns `{ok, orientation, is_short, width, height, duration}`.

## Wiring (workflow RdtmJTVYU4jFFCvF)
`Download clip (bytes)` -> **`Probe orientation`** (HTTP POST clip bytes to
`http://172.18.0.1:8902/probe`) -> `Switch: brand branch` -> ...
`Compose YT prompt` and `Build YT metadata` read `$('Probe orientation').item.json.orientation`
as the PRIMARY format signal, falling back (fail-soft) to sidecar meta flags, then
duration, then default Short. The Switch reads `brand_origin` via the Guard node
reference so it is immune to the probe response replacing `$json`.

## Network / security
Binds to the docker gateway only (172.18.0.1:8902); ufw allows only 172.18.0.0/16.
Not exposed to the internet. Fail-soft: any error returns ok:false and the pipeline
falls back to its default logic (never breaks publishing).
