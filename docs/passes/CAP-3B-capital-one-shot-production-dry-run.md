# CAP-3B — Capital FM UK One-Shot Production Dry Run

## Final Verdict
**SAFE FOR CANARY ENABLEMENT**

---

## 1. Dry Run Specifications
* **Commit Hash Audited & Deployed**: `1e8c237a858593a20df20cde8823f0ec682283bf` (main)
* **Target Source**: `https://onlineradiobox.com/uk/capitalfmuk/`
* **Audited Files**:
  * [dry_run_capital.py (dry run script)](file:///Users/robertsebunya/Documents/Prof_Mind/scripts/dry_run_capital.py)
  * [online_radio_box.py (collector)](file:///Users/robertsebunya/Documents/Prof_Mind/app/infrastructure/collectors/online_radio_box.py)
  * [scheduler.py (scheduler & failure threshold)](file:///Users/robertsebunya/Documents/Prof_Mind/app/infrastructure/scheduler/scheduler.py)

---

## 2. Dry Run Execution Logs
The one-shot test harness was executed inside the production FastAPI app container:
```bash
ssh root@178.105.238.18 "docker exec -i rmias-app-1 python dry_run_capital.py"
```

### Console Output
```text
2026-06-03 21:10:08,573 [INFO] capital_dry_run: Starting Capital FM UK One-Shot Dry Run...
2026-06-03 21:10:08,573 [INFO] capital_dry_run: Target Source: https://onlineradiobox.com/uk/capitalfmuk/
2026-06-03 21:10:08,573 [INFO] capital_dry_run: Database URL (masked): postgresql+asyncpg://****:****@db:5432/rmias
2026-06-03 21:10:08,573 [INFO] capital_dry_run: Storage root: /data/raw_payloads
2026-06-03 21:10:08,743 [INFO] httpx: HTTP Request: GET https://onlineradiobox.com/uk/capitalfmuk/ "HTTP/1.1 200 OK"
2026-06-03 21:10:08,795 [INFO] capital_dry_run: --- Execution Results ---
2026-06-03 21:10:08,795 [INFO] capital_dry_run: Collector status: completed
2026-06-03 21:10:08,795 [INFO] capital_dry_run: HTTP status: 200
2026-06-03 21:10:08,795 [INFO] capital_dry_run: Extracted Track: Justin Bieber - Where Are Ü Now (played_at=2026-06-03 21:10:08.795210+00:00, source_event_id=1873556328619906550)
2026-06-03 21:10:08,795 [INFO] capital_dry_run: Raw payload saved to disk: Yes (/data/raw_payloads/2026/06/03/682288e7-c2d0-48d3-9997-07884f150558.bin)
2026-06-03 21:10:08,795 [INFO] capital_dry_run: Raw payload size: 92002 bytes, SHA256: 53d283d3a5c52eeab3edfa90d0b91263154a019b825dc2507c30ff4a55266dea
2026-06-03 21:10:08,795 [INFO] capital_dry_run: Persisting results to database...
2026-06-03 21:10:09,121 [INFO] capital_dry_run: Database records successfully created.
2026-06-03 21:10:09,121 [INFO] capital_dry_run: One-Shot Dry Run Completed.
```

### Database Persistence Verification
Queried the production PostgreSQL database:
```text
                  id                  |              station_id              |  raw_artist   |    raw_title    |          played_at           |   source_event_id   
--------------------------------------+--------------------------------------+---------------+-----------------+------------------------------+---------------------
 260deb92-dd69-4603-995f-3094a8482f77 | 2e185654-47b8-5d32-aa2f-62ebc1f35b7a | Justin Bieber | Where Are Ü Now | 2026-06-03 21:10:08.79521+00 | 1873556328619906550
```
* Status: **Verified**. A play event record was created correctly.
* Payload storage: **Verified**. The raw html payload was written to `/data/raw_payloads/2026/06/03/682288e7-c2d0-48d3-9997-07884f150558.bin`.

---

## 3. Production Safety Validation
All post-execution checks confirm safety protocols remain 100% active:
* **Scheduler Gating**: `SCHEDULER_ENABLED=false` remains intact.
* **Collectors Gating**: All other collectors (`enable_nova_collector`, `enable_kiis_collector`, `enable_capital_collector`) remain `false`.
* **Container Health**: Production API endpoints (`/` and `/health`) are fully operational and healthy (HTTP 200).
* **Logs Inspection**: Uvicorn log files show no recurring scheduler job was started.

---

## 4. Rollback Command
To immediately disable the collector and restart the app service in production, run:
```bash
ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/id_ed25519 root@178.105.238.18 "bash /opt/rmias/scripts/rollback-capital.sh"
```
