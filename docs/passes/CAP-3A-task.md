# CAP-3A Task Checklist

- [x] Inspect `app/infrastructure/collectors/online_radio_box.py`
- [x] Inspect `app/infrastructure/scheduler/scheduler.py`
- [x] Inspect `scripts/rollback-capital.sh`
- [x] Confirm scheduler uses OnlineRadioBoxCollector for Capital FM UK
- [x] Confirm 15-minute polling interval trigger
- [x] Confirm failure threshold of 5 consecutive failures
- [x] Confirm rollback script disables ENABLE_CAPITAL_COLLECTOR and restarts app safely
- [x] Confirm SCHEDULER_ENABLED is the master switch
- [x] Inspect collector and parser test results (all 321 tests pass)
- [x] Confirm production safety configuration on Hetzner (.env.production)
- [x] Confirm latest commit 86b8eea is deployed on Hetzner server
- [x] Confirm endpoints / and /health return HTTP 200 in production
- [x] Confirm scheduler is disabled on Hetzner (checked docker logs rmias-app-1)
- [x] Write audit document `docs/passes/CAP-3A-production-collector-readiness-audit.md`
