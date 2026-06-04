# EXTRACT-1 Task — Parser and Collector Library Extraction From PR #3

**Date:** 2026-06-04  
**Branch:** `feat/recon2-parser-collector-library`  
**Source branch:** `claude/sweet-archimedes-DFSWo` (PR #3)  
**Status:** COMPLETE — see `EXTRACT-1-parser-collector-library.md`

---

## Objective

Extract only the safe parser/collector library work from PR #3 into a clean branch
based on latest `main`. This is a code-extraction-and-test-coverage pass only.

---

## Hard Rules

- Do NOT rebase PR #3 wholesale
- Do NOT cherry-pick whole commits
- Do NOT copy any migration files
- Do NOT copy UI files
- Do NOT copy scheduler changes
- Do NOT copy source/station seeds
- Do NOT copy deployment files
- Do NOT enable any collector
- Do NOT register any collector in the scheduler
- Do NOT seed any source in DB
- Do NOT deploy

---

## Checklist

- [x] main verified at `1ec18c00`, clean, 390 tests
- [x] RECON-2A docs reviewed (Section 15 file list)
- [x] All candidate files inspected individually before porting
- [x] Imports audited (no scheduler, no DB session, no live HTTP)
- [x] Extraction branch created from clean main
- [x] Parser files ported (bbc_sounds, heart, iheart update, radiowave update)
- [x] Collector files ported (bbc_radio_1, heart_radio, iheart_now_playing, iheart_recently_played, iheart_top_songs, kiis_radiowave)
- [x] base.py async _store_payload applied
- [x] Test fixtures ported (9 JSON, 3 HTML)
- [x] New test files ported (7 new test modules)
- [x] Existing test_iheart_parser.py updated (import + constructor)
- [x] Settings flags added (5 new flags, all False)
- [x] Boundary check passed (no migrations, no UI, no scheduler, no seeds)
- [x] Targeted infrastructure tests: 156 passed
- [x] Full test suite: 492 passed, 2 skipped (+102)
- [x] Ruff: clean
- [x] Mypy: clean
- [x] Static safety scan: clean
- [x] EXTRACT-1 docs created
- [x] No production changes made
