# RECON-2A — PR #3 Branch Hygiene and Extraction Plan

**Date:** 2026-06-04  
**Pass:** RECON-2A  
**Verdict:** `RECON-2A COMPLETE — PR #3 EXTRACTION PLAN READY`

---

## 1. Executive Verdict

PR #3 (`claude/sweet-archimedes-DFSWo`) contains **40 unique commits**, **136 changed files**, **11 unapplied migrations**, and roughly **14,000 lines of new or modified code**. It cannot be safely rebased wholesale. It is contaminated with docs-only commits at its HEAD that do not belong in a feature PR. 

The **recommended strategy is Option A**: close PR #3 after extracting valuable work into multiple smaller, independently reviewable PRs. The first extraction must focus solely on the parser and collector library — pure Python logic with no migrations, no scheduler changes, and no UI modifications. Each subsequent extraction slice must be a separate pass.

---

## 2. Why RECON-2A Was Needed

PR #3 was created from an old baseline (before REF-0, AntiGravity, SEC-AUTH-1B, PR #9). It accumulated 40 commits over many weeks, mixing:

- **New radio station collectors** (BBC, Heart, Z100, WKSC, KIIS iHeart)
- **Email reporting system** (new schema tables, SMTP, hourly dispatcher)
- **ARIA chart persistence** (new DB table, scheduler)
- **Trend alerts**
- **Sentry monitoring**
- **Observability stack** (PgHero, Uptime Kuma, Grafana/Loki)
- **UI bug fixes and accessibility passes** (largely superseded by PR #9)
- **Documentation commits** (RECON-1 and POST-MERGE-STABILITY-1 accidentally placed here)

A wholesale rebase would risk overwriting SEC-AUTH-1B, PR #9 UI work, the REF-0 dedup model, and the AntiGravity metadata readiness architecture.

---

## 3. Main State

| Field | Value |
|-------|-------|
| Latest main SHA | `1ec18c00550cb7dc8e0415abe3611ed80e990a1e` |
| Commit message | feat: UIUX admin console redesign |
| PR #9 merge confirmed | YES (`1ec18c00`) |
| Working tree | Clean |
| Tests | 390 passed, 2 skipped |
| Ruff | Clean |
| Mypy | Clean |

---

## 4. Feature Baselines Confirmed in Main

### REF-0 Baseline
| File | Status |
|------|--------|
| `app/tools/dry_run_capital.py` | EXISTS |
| `app/tools/prune_raw_payloads.py` | EXISTS |
| `scripts/rollback-capital.sh` | EXISTS |
| `ENABLE_DOCS_IN_PRODUCTION` gating | Present in operations.js + test_docs_gating.py |
| `RAW_PAYLOAD_RETENTION_DAYS` support | Present in settings, tools, UI |
| `exists_by_fingerprint` dedup | Present in repo, scheduler, tests |

### SEC-AUTH-1B Baseline
| Check | Status |
|-------|--------|
| `_is_protected_admin_path` guard | Present in `admin_auth.py` |
| `/api/admin/overview` protected | Confirmed in test |
| `/api/admin/metadata-readiness` protected | Confirmed in test |
| `/administrator` NOT protected (boundary-safe) | Confirmed in test |
| Auth tests | 28/28 pass |

### UIUX/Metadata Readiness Baseline
| Item | Status |
|------|--------|
| `operations-guardrails.js` (AntiGravity PR #7) | Present |
| `play-events.js` (AntiGravity PR #7) | Present |
| `spotify-metadata.js` (AntiGravity PR #7) | Present |
| `operations.js` (PR #9) | Present |
| `/api/admin/metadata-readiness` endpoint | Present and tested |
| MusicBrainz/Spotify/Cover Art readiness display | Present in dashboard.js |

---

## 5. POST-MERGE-STABILITY Docs: Contamination Analysis

| Question | Answer |
|----------|--------|
| POST-MERGE-STABILITY-1-report.md in `main`? | **NO** |
| POST-MERGE-STABILITY-1-report.md in PR #3? | **YES** — HEAD commit `58238f1` |
| RECON-1 docs in `main`? | NO |
| RECON-1 docs in PR #3? | YES — commit `7f4bb72` |
| Is PR #3 contaminated by docs? | **YES** — top 2 commits are docs-only |
| Should these docs go to main? | Eventually yes, but separately |
| Action required in this pass | Record here; exclude from extraction |

**Root cause:** During the RECON-1 and PR9-STABILISE-1 passes, `claude/sweet-archimedes-DFSWo` was used as both a docs staging branch AND is tracked as PR #3. The docs commits were pushed to that branch before the RECON-2A audit clarified the contamination.

**Recommended resolution:** When creating the first extraction branch, cherry-pick only the code/test commits and explicitly exclude commits `7f4bb72` and `58238f1`. The docs can be cherry-picked to `main` in a separate docs-only commit after extraction is complete.

---

## 6. PR #3 State

| Field | Value |
|-------|-------|
| PR #3 branch | `claude/sweet-archimedes-DFSWo` |
| PR #3 HEAD | `58238f1a1e94134e3d2cae948c4007d846511c75` |
| Unique commits vs main | **40** |
| Changed files vs main | **136** |
| Total insertions | +13,965 |
| Total deletions | -689 |
| Migration files | **11** |

---

## 7. High-Risk Files Touched by PR #3

| File | Risk |
|------|------|
| `app/main.py` | HIGH — Sentry init, CORS, 2 new routers |
| `app/core/settings.py` | HIGH — 8 new flags, SMTP settings, Sentry DSN |
| `app/infrastructure/scheduler/scheduler.py` | HIGH — email reporting integrated, job-store persistence |
| `migrations/versions/e1f2a3b4c5d6_*` | HIGH — creates webhook_subscriptions table; dedup index differs from main |
| `migrations/versions/f1g2h3i4j5k6_*` through `o6p7q8r9s0t1_*` | MEDIUM-HIGH — 10 more migrations |
| `docker-compose.hetzner.yml` | MEDIUM — adds PgHero/Grafana/Loki services |
| `app/static/css/app.css` | MEDIUM — extensive edits that conflict with PR #9 |
| `app/static/index.html` | MEDIUM — conflicts with PR #9 |
| `app/static/js/app.js` | MEDIUM — conflicts with PR #9 routing |
| `app/static/js/pages/dashboard.js` | MEDIUM — conflicts with PR #9 version |
| `app/application/source_config/source_seeds.py` | MEDIUM — station data changes |
| `app/application/source_config/station_seeds.py` | MEDIUM — station data changes |

---

## 8. Migration Chain Analysis

### Main's Current Chain (5 migrations)
```
ade166ae8d36 (Phase A: initial schema)
└── 2fa7e19610e8 (Phase B: events schema)
    └── 45770ddee81b (Phase C: reports schema)
        └── b3c9d1f04a2e (Phase D: review items notes)
            └── c4e2a1f9b8d7 (Phase E: play_events dedup index) ← HEAD
```

### PR #3's Migration DAG (11 additional migrations)
```
b3c9d1f04a2e (Phase D) — both branches from here
├── c4e2a1f9b8d7 (main's Phase E: 3-col dedup index on station_id+fingerprint+played_at)
└── e1f2a3b4c5d6 (PR3 Phase E: webhook_subscriptions + 2-col dedup on station_id+fingerprint)
    └── f1g2h3i4j5k6 (Phase F: email_recipients + email_send_log tables)
        └── g1h2i3j4k5l6 (Phase G: timezone column on email_recipients)
            └── h1i2j3k4l5m6 (Phase H: chart_entries table)
                ↑
i2j3k4l5m6n7 (MERGE: c4e2a1f9b8d7 + h1i2j3k4l5m6 → single head)
└── j1k2l3m4n5o6 (Phase I: Capital FM station correction)
    └── k2l3m4n5o6p7 (Phase J: KIIS-FM LA station correction)
        └── l3m4n5o6p7q8 (Phase K: BBC Radio 1 insert)
            └── m4n5o6p7q8r9 (Phase L: Heart FM insert)
                └── n5o6p7q8r9s0 (Phase M: Z100/WHTZ insert)
                    └── o6p7q8r9s0t1 (Phase N: WKSC 103.5 Chicago insert)
```

### Key Conflict: Phase E Dedup Index

| | Main (`c4e2a1f9b8d7`) | PR #3 (`e1f2a3b4c5d6`) |
|-|----------------------|----------------------|
| Index name | `uq_play_events_station_fp_playedat` | `uq_play_events_station_fingerprint` |
| Columns | (station_id, fingerprint, **played_at**) | (station_id, fingerprint) |
| Where clause | WHERE is_duplicate=false AND fingerprint IS NOT NULL | WHERE fingerprint IS NOT NULL |
| Semantics | Allows same song at different times (legitimate replay) | Blocks same station+fingerprint forever |
| Status in production | **Applied (current alembic head)** | Unapplied |

**Risk:** PR #3's 2-column index would block legitimate replays of the same song. Main's 3-column design was a deliberate REF-0 decision. If `e1f2a3b4c5d6` were applied, production would have BOTH indexes, with the 2-column being more restrictive. This could cause data integrity issues.

**Recommended action:** If webhook persistence is ever needed, create a NEW migration that only adds `webhook_subscriptions` without the dedup index (which is already handled by `c4e2a1f9b8d7`).

---

## 9. Commit Classification Table

| SHA (short) | Message | Category | Risk | Keep? | Reason |
|-------------|---------|----------|------|-------|--------|
| `feaaac1` | pass 33: ruff cleanup | code quality | Low | maybe | Some fixes may be superseded by PR #9 UI changes |
| `d9a8d4b` | fix(backend/high): static path, tz bugs, iheart... | multi-area fix | Medium | maybe | Backend fixes worth reviewing; scheduler/UI parts superseded |
| `4b5de86` | fix(frontend/js): Chart.js leaks, accessibility | UI fix | Medium | drop | UI work superseded by PR #9 |
| `0a4c8a5` | pass 34: full refactor — backend/UI/UX | multi-area refactor | High | drop | UI superseded; backend parts need cherry-pick review |
| `fd75202` | fix(backend/med): blocking IO, lucene escape... | backend fix | Medium | maybe | Specific backend fixes may be valuable; needs review |
| `1e23c03` | fix(frontend/polish): reports CSS, setBtnLoading | UI fix | Low | drop | UI work superseded by PR #9 |
| `ff24b2c` | fix(prod): phase-e production hardening | multi-feature | High | **drop** | Phase E migration conflicts with main; webhook_subscriptions overlaps |
| `e88c610` | feat: email reporting | large feature | High | deferred | Entire feature — extract as EXTRACT-EMAIL-1 |
| `847c43b` | Phase G: fix rolling-window period definitions | reports | Medium | deferred | Part of email reporting feature |
| `bfa25ba` | Phase H: scheduler job store, trend alerts | scheduler+feature | High | deferred | Scheduler job-store + trend alerts — complex extraction |
| `9ee1f91` | docs: ZeptoMail SMTP provider examples | docs | Low | maybe | Safe docs-only, low value |
| `aef4f33` | docs: ZeptoMail sender domain | docs | Low | drop | Hardcoded domain, replace with placeholder |
| `5cadf55` | Phase I: plain-text email, unsubscribe | email | Medium | deferred | Part of email reporting feature |
| `65b5df8` | Phase J: collector health, pagination, rate limit | multi-feature | Medium | deferred | Collector health UI + pagination helper — extract separately |
| `2059834` | Add Sentry monitoring | observability | Medium | deferred | Operational decision; extract via INFRA-SENTRY-1 |
| `50d6c91` | Add PgHero, Uptime Kuma, Grafana/Loki | observability | Medium | deferred | Infrastructure config; extract via INFRA-OBS-1 |
| `f28413c` | Add Semgrep SAST, Snyk, Sentry releases | CI/CD | Medium | deferred | CI tooling; extract via CI-SAST-1 |
| `5f2a964` | Refactor: pagination helper, dedup models | refactor | Medium | maybe | Pagination helper is reusable; dedup model review needed |
| `7ccd304` | fix: resolve CI failures (mypy + scheduler test) | CI fix | Low | drop | Fixes for conflicts that no longer exist on current main |
| `8aae3b8` | merge: resolve 13-file conflict with main | merge commit | None | drop | Merge of old baseline; all files since re-resolved by PR #9 |
| `d887607` | fix: ruff E501 + semgrep false positive | code quality | Low | drop | May duplicate changes in main or conflict with PR #9 changes |
| `88bb17f` | fix(security): remove wildcard CORS fallback | security | Low | drop | CORS now handled via `cors_origins` setting in PR #3 settings; review needed against main's approach |
| `315bce9` | feat(email): attach report data as CSV | email | Medium | deferred | Part of email reporting feature |
| `72caa0c` | docs: NEXT_STEPS for timezones, ARIA, Capital | docs | Low | drop | Outdated NEXT_STEPS; superseded by current state |
| `087f424` | feat(email): per-recipient timezones | email | Medium | deferred | Part of email reporting feature |
| `f6cf03a` | feat(charts): persist ARIA chart + weekly refresh | charts | Medium | deferred | ARIA persistence — extract as EXTRACT-ARIA-1 |
| `3260f55` | fix: merge orphaned Phase E branches | migration | High | **drop** | Migration bookkeeping for a conflict that no longer exists |
| `dd53045` | feat: Capital FM enablement | station config | Medium | **keep** | Capital FM station correction; migration j1k2l3m4n5o6 is a data fix |
| `4e86f30` | fix: log snapshot persistence failure | backend fix | Low | **keep** | Safe bugfix in reports endpoint |
| `a4edb70` | feat: KIIS-FM 102.7 LA — Radiowave Monitor | collector+migration | Medium | **keep** | Radiowave collector + station correction; migration idempotent |
| `3faf840` | test: expand source-config and scheduler | tests | Low | maybe | Tests may need adaptation to current main |
| `e2165cc` | feat: KIIS-FM iHeart recently-played | collector | Low | **keep** | Generic iHeart recently-played collector; pure Python |
| `ffd1ebc` | feat: BBC Radio 1 — BBC Sounds RMS | collector+migration | Low | **keep** | BBC collector + idempotent station insert migration |
| `de449c8` | feat: Heart FM — HTML collector | collector+migration | Low | **keep** | Heart FM collector + idempotent station insert migration |
| `02c236c` | Phase M: add Z100 (WHTZ) iHeart collectors | collector+migration | Low | **keep** | Z100 collector + idempotent station insert migration |
| `e8c141d` | Phase N: add WKSC 103.5 iHeart collectors | collector+migration | Low | **keep** | WKSC collector + idempotent station insert migration |
| `b879434` | Add iHeart top-songs chart collector | collector | Low | **keep** | Generic top-songs; settings flags default false |
| `d3ec7d5` | Refactor: consolidate iHeart collectors | refactor | Low | **keep** | Consolidates per-station into generic; reduces duplication |
| `7f4bb72` | docs: RECON-1 | docs | Low | **exclude from extraction** | Docs-only contamination |
| `58238f1` | docs: POST-MERGE-STABILITY-1 | docs | Low | **exclude from extraction** | Docs-only contamination |

---

## 10. Valuable Work Identified

### Category A: Collector / Parser Library (Priority 1 — SAFE)
Commits: `e2165cc`, `b879434`, `d3ec7d5`, (parts of `a4edb70`, `ffd1ebc`, `de449c8`, `02c236c`, `e8c141d`)

Files (exclude migrations, scheduler, settings):
- `app/infrastructure/parsers/iheart.py` — generic iHeart JSON parser
- `app/infrastructure/parsers/bbc_sounds.py` — BBC Sounds segments parser
- `app/infrastructure/parsers/heart.py` — Heart FM HTML parser
- `app/infrastructure/parsers/radiowave.py` — Radiowave diary parser
- `app/infrastructure/collectors/base.py` — base collector improvements
- `app/infrastructure/collectors/iheart_now_playing.py` — generic iHeart now-playing
- `app/infrastructure/collectors/iheart_recently_played.py` — generic iHeart recently-played
- `app/infrastructure/collectors/iheart_top_songs.py` — generic iHeart top-songs
- `app/infrastructure/collectors/bbc_radio_1.py` — BBC Radio 1 (uses BBCSoundsParser)
- `app/infrastructure/collectors/heart_radio.py` — Heart FM (uses HeartParser)
- `app/infrastructure/collectors/kiis_radiowave.py` — KIIS Radiowave (uses RadiowaveParser)
- Test fixtures: `tests/fixtures/json/iheart_*.json`, `tests/fixtures/html/heart_fm_*.html`, `tests/fixtures/html/radiowave_kiis_diary.html`, `tests/fixtures/json/bbc_radio1_segments.json`
- Unit tests: `tests/unit/infrastructure/test_iheart_parser.py`, `test_iheart_top_songs_collector.py`, `test_kiis_iheart_history_collector.py`, `test_wksc_iheart_collector.py`, `test_z100_iheart_collector.py`, `test_bbc_radio1_collector.py`, `test_heart_radio_collector.py`, `test_kiis_radiowave_collector.py`

New settings needed: `enable_bbc_radio1_collector`, `enable_heart_collector`, `enable_z100_collector`, `enable_wksc_collector`, `enable_iheart_top_songs` — all default `False`

**Migration required for tests?** NO. Tests use fixtures. No DB needed.

### Category B: Station Seeds + Data Corrections (Priority 2 — MEDIUM)
Commits: `dd53045` (Capital FM), `a4edb70` (KIIS-FM LA), `ffd1ebc` (BBC), `de449c8` (Heart), `02c236c` (Z100), `e8c141d` (WKSC)
Extract separately as `feat/recon2-station-seeds-new-stations`
Note: Migrations K-N are idempotent (`ON CONFLICT DO NOTHING`) — safe for production.

### Category C: Backend Bugfixes (Priority 3 — LOW-MEDIUM)
Commits: `4e86f30` (reports download snapshot fix)
Extract: single cherry-pick to `fix/recon2-report-snapshot-fix`

### Category D: Email Reporting (Priority 4 — LARGE FEATURE)
Commits: `e88c610`, `847c43b`, `5cadf55`, `315bce9`, `087f424`
Extract separately as `feat/recon2-email-reporting` — requires migration F, G

### Category E: ARIA Chart Persistence (Priority 5)
Commit: `f6cf03a`
Extract separately as `feat/recon2-aria-chart-persistence` — requires migration H

---

## 11. Superseded Work

| Commits | Reason Superseded |
|---------|-------------------|
| `4b5de86`, `0a4c8a5`, `1e23c03`, `feaaac1` (partial) | UI/CSS/JS work overwritten by PR #9 merge |
| `8aae3b8` | Merge of old baseline; context no longer valid |
| `7ccd304` | CI fixes for a conflict set that no longer exists |
| `3260f55` | Migration merge that referenced a branch in a pre-main migration state |
| `88bb17f` | CORS wildcard removal already in main through REF-0 |
| `d887607` | Ruff/semgrep fixes for code that has since changed shape |

---

## 12. Risky Work

| Item | Risk | Reason |
|------|------|--------|
| `e1f2a3b4c5d6` migration | **HIGH** | Creates 2-column dedup index that conflicts logically with main's 3-column design; also creates `webhook_subscriptions` which hasn't been planned yet |
| `scheduler.py` changes | **HIGH** | Email reporting intertwined; job-store persistence requires psycopg2 dependency |
| `app/main.py` changes | **HIGH** | Sentry, CORS, 2 new routers — all conflict with current main |
| `ff24b2c` prod hardening | **HIGH** | Migration conflict; also bundles multiple schema changes |
| `docker-compose.hetzner.yml` | **MEDIUM** | Production infrastructure changes (PgHero, Grafana, Loki) |
| `app/application/webhooks/service.py` | **MEDIUM** | Changed from in-memory to DB-backed; migration needed |

---

## 13. Static Safety Scan Results

| Scan | Result | Classification |
|------|--------|----------------|
| Unsafe enabled flags | `rollback-capital.sh` line 7-8 — `ENABLE_CAPITAL_COLLECTOR=true` in comment showing what to set it TO FALSE from | Safe — rollback script comment |
| Secret-like patterns | None found | Safe |
| Risky operation language (`drop table`, `truncate table`, etc.) | `prune_raw_payloads.py` references only | Safe — REF-0 tool, already in main |
| Live collector enable flags | None found in code | Safe |
| Spotify/MusicBrainz misuse | Only in historical audit docs | Safe — documentation |
| `docker-compose.hetzner.yml` changes | Internal-only services (127.0.0.1 binding), SSH tunnel only | Safe — no internet exposure |

**Scan verdict: CLEAN.** No unsafe patterns, no secrets, no live-enable code, no destructive operations.

---

## 14. Recommended Strategy: Option A

**Close PR #3 after extracting valuable work into smaller, independently reviewable PRs.**

Rationale:
1. PR #3 is too large (136 files, 14k lines) for a safe wholesale rebase
2. The migration chain has structural conflicts with main's current Phase E
3. UI changes are 100% superseded by PR #9
4. Email, observability, Sentry are large independent features that deserve separate PRs
5. Only 8–10 commits are clearly worth extracting first; the rest need individual review
6. A small first PR is safer, more reviewable, and can be deployed incrementally

---

## 15. Recommended First Extraction Slice

**Branch:** `feat/recon2-parser-collector-library`  
**Pass name:** `EXTRACT-1`  
**Scope:** Parser + collector library only — no migrations, no scheduler, no email, no UI

### Files to manually port (do NOT cherry-pick whole commits):

**New files (copy from PR #3 tree):**
- `app/infrastructure/parsers/iheart.py`
- `app/infrastructure/parsers/bbc_sounds.py`
- `app/infrastructure/parsers/heart.py`
- `app/infrastructure/parsers/radiowave.py`
- `app/infrastructure/collectors/iheart_now_playing.py`
- `app/infrastructure/collectors/iheart_recently_played.py`
- `app/infrastructure/collectors/iheart_top_songs.py`
- `app/infrastructure/collectors/bbc_radio_1.py`
- `app/infrastructure/collectors/heart_radio.py`
- `app/infrastructure/collectors/kiis_radiowave.py`
- `tests/fixtures/json/iheart_kiis_recently_played.json`
- `tests/fixtures/json/iheart_kiis_top_songs.json`
- `tests/fixtures/json/iheart_wksc_200.json`
- `tests/fixtures/json/iheart_wksc_recently_played.json`
- `tests/fixtures/json/iheart_wksc_top_songs.json`
- `tests/fixtures/json/iheart_z100_200.json`
- `tests/fixtures/json/iheart_z100_recently_played.json`
- `tests/fixtures/json/iheart_z100_top_songs.json`
- `tests/fixtures/json/bbc_radio1_segments.json`
- `tests/fixtures/html/heart_fm_last_played.html`
- `tests/fixtures/html/heart_fm_last_played_empty.html`
- `tests/fixtures/html/radiowave_kiis_diary.html`
- `tests/unit/infrastructure/test_iheart_parser.py`
- `tests/unit/infrastructure/test_iheart_top_songs_collector.py`
- `tests/unit/infrastructure/test_kiis_iheart_history_collector.py`
- `tests/unit/infrastructure/test_wksc_iheart_collector.py`
- `tests/unit/infrastructure/test_z100_iheart_collector.py`
- `tests/unit/infrastructure/test_bbc_radio1_collector.py`
- `tests/unit/infrastructure/test_heart_radio_collector.py`
- `tests/unit/infrastructure/test_kiis_radiowave_collector.py`

**Modified files (apply only the collector/parser additions):**
- `app/infrastructure/collectors/base.py` — apply only the generic base improvements
- `app/core/settings.py` — add ONLY the 5 new collector flags (all default `False`)

**Excluded (do NOT include):**
- Any `migrations/` files
- `app/infrastructure/scheduler/scheduler.py` (email-intertwined)
- `app/main.py` (Sentry, CORS, routers)
- `app/application/source_config/source_seeds.py` (station data — separate slice)
- `app/application/source_config/station_seeds.py` (station data — separate slice)
- All `app/static/` files (superseded by PR #9)
- `app/application/reports/`, `app/infrastructure/email/`, `app/application/alerts/` (email feature — separate)
- `docker-compose*` files (infra)
- `.github/workflows/` files (CI — separate)

### Expected tests after EXTRACT-1:
- All 9+ new infrastructure tests should pass
- All 390 existing tests must still pass
- Ruff and mypy must stay clean
- No migrations required for tests

### Scheduler wiring (for later):
After EXTRACT-1 merges, a follow-on `EXTRACT-1B` pass should add the scheduler entries for the new collectors (5 new enable flags → 5 new scheduler jobs), ensuring they're all gated and default to disabled.

---

## 16. Full Extraction Roadmap

| Pass | Branch | Scope | Migrations? | Risk |
|------|--------|-------|-------------|------|
| EXTRACT-1 | `feat/recon2-parser-collector-library` | Parsers + collectors + tests | None | Low |
| EXTRACT-1B | `feat/recon2-scheduler-collector-wiring` | Scheduler entries for new collectors | None | Medium |
| EXTRACT-2 | `feat/recon2-station-seeds-new-stations` | Station seeds + migrations K-N | 4 idempotent inserts | Medium |
| EXTRACT-3 | `fix/recon2-capital-kiis-station-corrections` | Capital FM + KIIS-FM data corrections | j, k migrations | Medium |
| EXTRACT-4 | `feat/recon2-webhook-persistence` | Webhook DB persistence (new design) | New migration only | Medium-High |
| EXTRACT-5 | `feat/recon2-email-reporting` | Full email feature | F, G migrations | High |
| EXTRACT-6 | `feat/recon2-aria-chart-persistence` | ARIA chart DB persistence | H migration | Medium |
| EXTRACT-7 | `feat/recon2-collector-health-ui` | Collector health dashboard UI | None | Low |
| INFRA-SENTRY-1 | `feat/infra-sentry` | Sentry integration | None | Medium |
| INFRA-OBS-1 | `feat/infra-observability` | PgHero/Grafana/Loki | None | Medium |
| CI-SAST-1 | `feat/ci-semgrep-snyk` | Semgrep SAST, Snyk | None | Low |

**Do NOT start more than one extraction pass at a time.**

---

## 17. Production Safety

| Concern | Status |
|---------|--------|
| Production deployment happened | NO |
| Production env modified | NO |
| Migrations applied | NO |
| Scheduler enabled | NO |
| Any collector enabled | NO |
| Any enrichment enabled | NO |
| Spotify live calls | NO |
| MusicBrainz live calls | NO |
| main force-pushed | NO |
| `git add .` used | NO |

---

## 18. What Remains Blocked

- RECON-2 (PR #3 full extraction) — requires EXTRACT-1 to complete first
- PR #3 closure — should happen AFTER EXTRACT-1 through EXTRACT-3 are merged
- Production deployment of collector changes — requires EXTRACT-1 + EXTRACT-2 to merge AND EXTRACT-1B scheduler wiring
- Spotify backend and worker PRs — remain on hold (separate track, unrelated to PR #3)
- MusicBrainz implementation — blocked until METADATA-1 pass is defined

---

## 19. Next Pass Recommendation

**EXTRACT-1: Parser + Collector Library**

Create branch `feat/recon2-parser-collector-library` from latest `main`.  
Manually port the parser and collector files listed in Section 15.  
Add 5 new settings flags (all `False` by default).  
Run full test suite to confirm 390+ pass.  
Commit as a single atomic PR with a focused description.  
Do not include migrations, scheduler, email, UI, or docs.

After EXTRACT-1 merges: proceed to EXTRACT-1B (scheduler wiring), then EXTRACT-2 (station seeds + migrations).
