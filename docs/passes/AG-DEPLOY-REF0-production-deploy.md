# PASS: AG-DEPLOY-REF0 — Claude REF-0 Production Deployment Report

This report documents the production deployment of the merged Claude Code `REF-0` audit/refactor work.

## 1. Summary of Deployment

* **Pass Name**: `AG-DEPLOY-REF0`
* **Date**: June 4, 2026
* **PR #6 Merge Status**: **Merged** on GitHub into `main` branch.
* **Server Git Hash Before Deployment**: `68b91a58`
* **Server Git Hash After Deployment**: `e51331f8` (Merge pull request #6 from sebunya/chore/post-antigravity-refactor-audit)
* **Rebuild Action**: App container successfully rebuilt and force-recreated.

---

## 2. Safety Flags Configuration

Both the `.env.production` file on disk and the running application environment inside the container were verified to ensure all safety switches remain fully disabled:

| Config Variable | Value in `.env.production` | Value loaded inside container |
| :--- | :--- | :--- |
| `SCHEDULER_ENABLED` | `false` | `false` |
| `ENABLE_CAPITAL_COLLECTOR` | `false` | `false` |
| `ENABLE_NOVA_COLLECTOR` | `false` | `false` |
| `ENABLE_KIIS_COLLECTOR` | `false` | `false` |
| `ENABLE_NIGHTLY_RECONCILIATION` | `false` | `false` |

---

## 3. Database Migration & Schema Verification

* **Alembic Upgrade Head**: Executed successfully inside the container:
  `alembic upgrade head` (Upgraded `b3c9d1f04a2e -> c4e2a1f9b8d7`).
* **Current Alembic Version**: `c4e2a1f9b8d7` (head).
* **`play_events` Schema Verification**:
  * Added boolean column `is_duplicate` (defaults to `false`, non-nullable).
  * Added partial unique index `uq_play_events_station_fp_playedat` defined as:
    ```sql
    UNIQUE, btree (station_id, fingerprint, played_at) WHERE is_duplicate = false AND fingerprint IS NOT NULL
    ```
* **Historical Capital Events Preserved**: Checked the DB count and verified exactly **`4`** Capital play events remain completely intact (0 duplicates flagged, as expected).

---

## 4. Health and Endpoints Behavior

* **Public Root (`/`)**: Returns HTTP/2 200.
* **Health API (`/health`)**: Returns HTTP/2 200 with JSON:
  `{"status":"ok","service":"radio-music-intelligence","version":"0.1.0","components":{"scheduler":"stopped","review_queue_pending":0}}`
* **Interactive API Docs (`/docs` & `/openapi.json`)**: Returns HTTP/2 404. Documentation is successfully gated and hidden from public domains by default in production.
* **Admin Dashboard SPA (`/admin/`)**: Serves the admin web app dashboard cleanly.
* **Error Log Scan**: Checked 400 lines of app logs. Clean (no error logs, no traceback messages).

---

## 5. Final Verdict

> [!IMPORTANT]
> **REF-0 DEPLOYED — PRODUCTION STABLE**
> 
> The refactored codebase has been deployed from `main` to production. Database migrations have been applied safely, historical events are intact, and API docs are successfully gated. All background processing is paused.
> 
> **Next Recommended Pass**:
> `CAP-4R — Restart Capital FM UK monitored canary from clean REF-0 baseline`
