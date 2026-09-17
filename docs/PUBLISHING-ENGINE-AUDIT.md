# Publishing Engine — Audit & Hardening (2026-09-17)

Final reliability audit of the "YouTube — Publishing" workflow (`RdtmJTVYU4jFFCvF`,
24 nodes, active) and the hardening applied so it can be depended on daily.

## Verdict
**Strong, dependable engine.** Fail-soft on most external calls, a dedicated error
workflow, a fail-closed brand guard, quota guard, and `binaryMode: separate` (RAM-friendly).
The audit found a few reliability gaps on the critical path, now fixed.

## What was already strong (kept)
- Fail-soft (`continueRegularOutput`) on Gemini, sidecar fetch/download, thumbnail
  fetch/download/set, playlist add, pinned comment, notify — a non-critical failure
  never blocks the actual publish.
- `errorWorkflow` configured (`NbqmBrBczviSoQrB`) — failures are caught/notified.
- Fail-closed brand guard: MACAL content cannot publish to EEC.
- Quota guard node; trigger polls the watched folder every minute.
- Validates with 0 errors; not exposed in MCP.

## Gaps found & fixed
| # | Issue | Fix |
|---|-------|-----|
| 1 | Critical nodes had **no retry** (a transient blip = failed publish) | `retryOnFail`: Download clip (3×/2s), YouTube upload (3×/5s), Probe orientation (2×/1.5s) |
| 2 | **Probe node** could halt the run if the probe service was down (code was fail-soft, node was not) | `onError: continueRegularOutput` on Probe orientation |
| 3 | **Ledger** (dead-end) could error the run after upload on a Sheets hiccup | `onError: continueRegularOutput` on Ledger |
| 4 | Upload had no timeout (large long-form could hang) | `options.timeout: 600000` (10 min) on the upload node |

## Verified after deploy
- `n8n_validate_workflow` → **0 errors**
- Settings confirmed via get_workflow: Download retry 3/2s; Upload retry 3/5s + 600s
  timeout; Probe retry 2/1.5s + fail-soft; Ledger fail-soft.
- Reactivated: **active, 24 nodes**.

## Deploy procedure used (never break the live engine)
deactivate → patch (atomic partial ops) → `n8n_validate_workflow` (0 errors) →
verify each setting landed → reactivate → confirm active. Roll back if validation fails.

## Known follow-up (owner)
- Run one controlled end-to-end test (drop a real vertical + horizontal clip) to
  confirm the `clip` binary flows through the new `Probe orientation` HTTP node in a
  real execution before fully relying on orientation auto-detection.
