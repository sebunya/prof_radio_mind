# PASS: CAP-4 — Capital FM UK Monitored Canary Enablement Verification Report

This report documents the verification results of the **CAP-4: Capital FM UK Monitored Canary Enablement** pass on the Hetzner production server (`178.105.238.18`).

## 1. Canary Run Summary

A monitored canary window of approximately 60 minutes was completed on **June 3, 2026**. During this window, the Capital FM UK collector was scheduled at a **15-minute interval**.

* **Canary Window Start**: 21:24:57 UTC
* **Canary Window End**: 22:15:00 UTC
* **Total Runs Observed**: 3 scheduled runs

---

## 2. Verification Metrics

### Pre-Canary Event Count
* **Capital FM UK Play Events**: `1` (from the one-shot dry-run `dry_run_capital.py` execution)

### Post-Canary Event Count
* **Capital FM UK Play Events**: `4` (an increase of exactly `3` play events matching the 3 observed runs)

### Scheduled Attempts Observed
Exactly **3 scheduled runs** were executed by the APScheduler:
1. **Run 1**: 21:39:57 UTC — Success
2. **Run 2**: 21:54:57 UTC — Success
3. **Run 3**: 22:09:57 UTC — Success

### Latest Tracks Captured
The following play events were persisted in the production database:

| Time (UTC) | Artist | Title |
| :--- | :--- | :--- |
| **2026-06-03 22:09:57** | Dave | Raindance |
| **2026-06-03 21:54:57** | Benson Boone | Beautiful Things |
| **2026-06-03 21:39:57** | Robyn | With Every Heartbeat (With Kleerup) |
| **2026-06-03 21:10:08** (Dry Run) | Justin Bieber | Where Are Ü Now |

### Raw Payloads Created
Under the `/var/lib/docker/volumes/rmias_raw_payloads/_data/2026/06/03/` directory, the following raw HTML payloads were successfully saved on the host filesystem:
* `682288e7-c2d0-48d3-9997-07884f150558.bin` (Created Jun 3 21:10 — Dry-Run)
* `e7e84216-467d-496b-bb99-62593af64a7b.bin` (Created Jun 3 21:39 — Run 1)
* `c586a2a2-94b2-42db-a3dc-960ab543b0be.bin` (Created Jun 3 21:54 — Run 2)
* `95e8bb1a-4d22-4c80-b940-545d2510e1f1.bin` (Created Jun 3 22:09 — Run 3)

---

## 3. Safety and Health Status

### Errors / Exceptions
* **None**. Searching container logs for any errors, exceptions, or traceback stacktraces returned zero results.
* The `errors` and `no_track_events` tables in the production database remain at **0** records.

### Job Pauses
* **None**. No jobs were paused. The failure threshold controls did not trigger since all scheduled attempts completed with a `completed` status code and a successful parse.

### Nova / KIIS Collectors
* **Stayed Disabled**. App container logs show that both collectors (and the nightly reconciliation job) were explicitly skipped and not registered during startup:
  ```json
  {"ts": "2026-06-03T21:24:57Z", "level": "INFO", "logger": "app.infrastructure.scheduler.scheduler", "msg": "Scheduler skipped job: Nova 96.9 Radiowave diary (disabled)"}
  {"ts": "2026-06-03T21:24:57Z", "level": "INFO", "logger": "app.infrastructure.scheduler.scheduler", "msg": "Scheduler skipped job: KIIS-FM iHeart now-playing poll (disabled)"}
  {"ts": "2026-06-03T21:24:57Z", "level": "INFO", "logger": "app.infrastructure.scheduler.scheduler", "msg": "Scheduler skipped job: Nightly reconciliation (disabled)"}
  ```

### Production Endpoint Liveness
* The public root landing page (`/`) and the `/health` endpoint remained fully responsive:
  * `https://tenxradar.com/health` returns HTTP/2 200 with payload:
    ```json
    {"status":"ok","service":"radio-music-intelligence","version":"0.1.0","components":{"scheduler":"running","review_queue_pending":0}}
    ```

### Review Queue Check
* `review_items` table count: **0**. No duplicate storm or review items were created.

---

## 4. Final Verdict

> [!IMPORTANT]
> **CANARY PASSED**
>
> The Capital FM UK collector runs cleanly under scheduler orchestration with zero errors, proper raw payload storage, successful extraction, and no degradation to system stability.
