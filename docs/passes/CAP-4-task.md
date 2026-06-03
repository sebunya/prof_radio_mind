# CAP-4 Task Checklist

- [x] Confirm server is on latest origin/main
- [x] Confirm git status is clean
- [x] Confirm containers are healthy and endpoints return HTTP 200
- [x] Confirm safety flags are all false
- [x] Confirm rollback script exists and is executable
- [x] Confirm Capital play_events count before enablement (1 play event)
- [x] Confirm app logs show scheduler is disabled initially
- [x] Enable scheduler and Capital collector in server .env.production
- [x] Restart/recreate app container to start scheduler
- [x] Confirm scheduler started and only Capital job is registered
- [x] Monitor logs for 45-60 minutes to capture at least 2-3 runs (Completed: 3 runs observed)
- [x] Verify Capital play_events count after canary runs (Completed: 4 plays total, 3 new)
- [x] Check raw payload directory for new payloads (Completed: 3 new payloads stored)
- [x] Confirm no duplicate storm or review queue explosion (Completed: 0 items in review_items, 0 in no_track_events)
- [x] Write post-canary verification report `docs/passes/CAP-4-capital-monitored-canary-enable.md`

