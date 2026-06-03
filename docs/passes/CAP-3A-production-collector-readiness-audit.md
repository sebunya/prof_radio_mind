# CAP-3A — Production Collector Readiness Audit and Dry-Run Gate

## Verdict
**SAFE TO DRY-RUN**

---

## 1. Audit Specification
* **Audited Commit Hash**: `86b8eea181c188e9dcd76cc896bc1bd0d4be93b6` (aligned locally and on the Hetzner server)
* **Audited Files**:
  * [online_radio_box.py (collector)](file:///Users/robertsebunya/Documents/Prof_Mind/app/infrastructure/collectors/online_radio_box.py)
  * [scheduler.py (scheduler & threshold logic)](file:///Users/robertsebunya/Documents/Prof_Mind/app/infrastructure/scheduler/scheduler.py)
  * [rollback-capital.sh (rollback utility)](file:///Users/robertsebunya/Documents/Prof_Mind/scripts/rollback-capital.sh)
  * [test_online_radio_box_collector.py (unit tests)](file:///Users/robertsebunya/Documents/Prof_Mind/tests/unit/infrastructure/test_online_radio_box_collector.py)
  * `/opt/rmias/.env.production` (live on server `178.105.238.18`)

---

## 2. Safety State & Flag Audits
Confirmed that the server is in a strict safety-locked configuration:
* `SCHEDULER_ENABLED=false` (verified in `.env.production` and container logs: "Scheduler is disabled by configuration (SCHEDULER_ENABLED=false)")
* `ENABLE_NOVA_COLLECTOR=false` (verified in `.env.production`)
* `ENABLE_KIIS_COLLECTOR=false` (verified in `.env.production`)
* `ENABLE_CAPITAL_COLLECTOR=false` (verified in `.env.production`)
* `ENABLE_NIGHTLY_RECONCILIATION=false` (verified in `.env.production`)

No background collectors are active. The public endpoints `/` and `/health` return HTTP 200 indicating all containers are running and healthy.

---

## 3. Operational Analysis & Logic Audits
1. **OnlineRadioBoxCollector**:
   * Correctly utilizes `build_client(timeout=30.0)` which rotates realistic browser User-Agents and cycles through available proxies, preventing bot-detection blocks.
   * Leverages the verified BeautifulSoup parser logic to extract artist/title from the "Live" track row.
   * Respects robots.txt directives (only crawling the root station index, which has no disallow rule).
2. **Scheduler Frequency**:
   * Set to a low-impact cadence of **15 minutes** (IntervalTrigger(minutes=15)) instead of the typical 5-minute interval.
3. **Failure Threshold Safeguards**:
   * Counter increments on exceptions or `FAILED` status, and resets on `COMPLETED` or `NO_CONTENT`.
   * After 5 consecutive failures, the scheduler logs a critical `[MONITOR]` message and programmatically calls `_scheduler.pause_job("capital_now_playing")` to prevent overloading the target site during a failure loop.
4. **Rollback Shell Script**:
   * Verified `scripts/rollback-capital.sh` will set `ENABLE_CAPITAL_COLLECTOR=false` in `.env.production` and execute `docker compose restart app` to apply the disable change.

---

## 4. Verification Dry-Run & Rollback Commands

### Collector Dry-Run Command
Execute a manual, single-crawling operation directly inside the container on the Hetzner server. This tests the network loop and HTML parsing without writing to the database:
```bash
ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/id_ed25519 root@178.105.238.18 "docker exec -i rmias-app-1 python -c \"import asyncio; from app.infrastructure.collectors.online_radio_box import OnlineRadioBoxCollector; import uuid; c = OnlineRadioBoxCollector(uuid.uuid4(), uuid.uuid4()); print(asyncio.run(c.run()))\""
```

### Rollback Command
To immediately disable the Capital collector and restart the app service in production, run:
```bash
ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/id_ed25519 root@178.105.238.18 "bash /opt/rmias/scripts/rollback-capital.sh"
```
