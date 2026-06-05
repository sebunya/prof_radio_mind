# Station Coverage Matrix

**Date:** 2026-06-05  
**Status:** Current as of production VAL-LIVE-ENDPOINTS run  
**Legend:** ✅ Validated & active | 🔄 Repair candidate | ❌ Blocked/failed | ⏳ Pending discovery | 🔒 Compliance gate | ⬛ Not planned

Each station lists sources by tier. Tier 1 is most authoritative; Tier 5 is most independent.
All sources default to disabled. None may be enabled without passing the enablement gates in
RADIO-COVERAGE-ARCH-1-plan.md §8.

---

## NOVA969 — Nova 96.9 FM Sydney (Australia, 96.9 MHz)

| Tier | Source type | URL / ID | Status | Compliance | Notes |
|---|---|---|---|---|---|
| T2 | Radiowave diary (radiowave.com.au) | `radiowave.com.au/diary?idds=11129` | ⏳ Re-validate | Unknown | **Wrong URL was tested in D5 diagnostic. Actual collector URL never confirmed live.** |
| T3 | ICY stream metadata | TBD — STREAM-METADATA-DISCOVERY-1 | ⏳ Discover | Unknown | `streamtheworld_icy.py` exists; needs stream URL |
| T6 | MusicBrainz enrichment | Enrichment only | ✅ Available | Approved | Not a capture source |
| T6 | Spotify enrichment | Enrichment only | ✅ Available (disabled) | Approved | Not a capture source |
| — | Manual CSV | Operator upload | ✅ Always available | N/A | Last resort only |

**Primary capture path:** T2 Radiowave (pending re-validation with correct URL)  
**Fallback path:** T3 ICY stream (pending discovery)  
**Gap:** Never had a secondary source. Entirely dependent on a single HTML scraper.

---

## KIISFM — KIIS-FM 106.5 FM Sydney (Australia, 106.5 MHz)

| Tier | Source type | URL / ID | Status | Compliance | Notes |
|---|---|---|---|---|---|
| T1 | iHeart v3 live-meta | `api.iheart.com/api/v3/live-meta/stream/2501/currentTrack` | ❌ API gone | Unknown | Station ID 2501 may be correct but the API endpoint itself is invalid |
| T3 | ICY stream metadata | TBD — STREAM-METADATA-DISCOVERY-1 | ⏳ Discover | Unknown | iHeart AU streams carry ICY metadata |
| T6 | MusicBrainz enrichment | Enrichment only | ✅ Available | Approved | Not a capture source |
| T6 | Spotify enrichment | Enrichment only | ✅ Available (disabled) | Approved | Not a capture source |
| — | Manual CSV | Operator upload | ✅ Always available | N/A | Last resort only |

**Primary capture path:** T3 ICY stream (pending discovery — highest-priority path)  
**Gap:** iHeart v3 API is gone. Until ICY is discovered and validated, no automated collection.

---

## CAPITALFM — Capital FM UK (London, 95.8 MHz)

| Tier | Source type | URL / ID | Status | Compliance | Notes |
|---|---|---|---|---|---|
| T2 | Online Radio Box scraper | `onlineradiobox.com/uk/capitalfmuk/` | ⏳ UNVALIDATED | Unknown | VAL-CAPUK-ORB-001 required; parser not built |
| T3 | ICY stream metadata | TBD | ⏳ Discover | Unknown | Global Radio streams; needs URL discovery |
| T6 | MusicBrainz enrichment | Enrichment only | ✅ Available | Approved | Not a capture source |
| T6 | Spotify enrichment | Enrichment only | ✅ Available (disabled) | Approved | Not a capture source |
| — | Manual CSV | Operator upload | ✅ Always available | N/A | Last resort only |

**Primary capture path:** T2 Online Radio Box (unvalidated) or T3 ICY  
**Gap:** No validated source exists. The Online Radio Box parser is not yet built.

---

## BBCRADIO1 — BBC Radio 1 UK (97.6–99.8 MHz)

| Tier | Source type | URL / ID | Status | Compliance | Notes |
|---|---|---|---|---|---|
| T1 | BBC RMS API | `rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest` | 🔒 Endpoint valid | **Pending ToS review** | VAL-BBC1-001 PASS; VAL-BBC1-006 manual required |
| T3 | ICY / AAC stream metadata | BBC publishes stream URLs | ⏳ Discover | Unknown | BBC streams are documented and public |
| T6 | MusicBrainz enrichment | Enrichment only | ✅ Available | Approved | Not a capture source |
| T6 | Spotify enrichment | Enrichment only | ✅ Available (disabled) | Approved | Not a capture source |
| — | Manual CSV | Operator upload | ✅ Always available | N/A | Last resort only |

**Primary capture path:** T1 BBC RMS API (strongest source; needs ToS clearance only)  
**Secondary path:** T3 ICY stream (independent fallback if RMS fails)  
**Gap:** ToS review is the only blocker. BBC is the most immediately enableable station.  
**Note:** BBC publishes official stream URLs at bbc.co.uk/sounds. T3 discovery is low-effort.

---

## HEARTFMUK — Heart FM UK (London, 106.2 MHz)

| Tier | Source type | URL / ID | Status | Compliance | Notes |
|---|---|---|---|---|---|
| T2 | Heart FM last-played HTML | `heart.co.uk/radio/last-played-songs/` | 🔄 Selector drift — repair candidate | Unknown | Old selectors broken. New classes in raw HTML: `last_played_songs`, `song_wrapper`, `song__text-content` |
| T3 | ICY stream metadata | TBD | ⏳ Discover | Unknown | Global Radio streams; needs URL discovery |
| T6 | MusicBrainz enrichment | Enrichment only | ✅ Available | Approved | Not a capture source |
| T6 | Spotify enrichment | Enrichment only | ✅ Available (disabled) | Approved | Not a capture source |
| — | Manual CSV | Operator upload | ✅ Always available | N/A | Last resort only |

**Primary capture path:** T2 Heart FM HTML (after HEART-HTML-PARSER-FIX-1)  
**Secondary path:** T3 ICY stream (independent fallback)  
**Gap:** One repair pass needed. New selector set must be confirmed from a live response  
capture, not guessed. ToS status of heart.co.uk scraping must also be recorded.

---

## WHTZ (Z100) — Z100 New York (100.3 MHz, call sign WHTZ)

| Tier | Source type | URL / ID | Status | Compliance | Notes |
|---|---|---|---|---|---|
| T1 | iHeart v3 live-meta | `stream/614/currentTrack` (assumed — v2 search shows id 1469) | ❌ API gone | Unknown | Correct iHeart ID may be 1469, not 614; but API endpoint is invalid regardless |
| T3 | ICY stream metadata | TBD | ⏳ Discover | Unknown | iHeart US streams carry ICY; needs URL discovery |
| T6 | MusicBrainz enrichment | Enrichment only | ✅ Available | Approved | Not a capture source |
| T6 | Spotify enrichment | Enrichment only | ✅ Available (disabled) | Approved | Not a capture source |
| — | Manual CSV | Operator upload | ✅ Always available | N/A | Last resort only |

**Primary capture path:** T3 ICY stream (iHeart API unavailable; stream metadata is the path)  
**Gap:** No validated source. Station ID correction alone insufficient; API path must also work.

---

## WKSC — WKSC 103.5 FM Chicago (103.5 MHz)

| Tier | Source type | URL / ID | Status | Compliance | Notes |
|---|---|---|---|---|---|
| T1 | iHeart v3 live-meta | `stream/821/currentTrack` (v2 search shows id 849) | ❌ API gone | Unknown | Same API failure as Z100 |
| T3 | ICY stream metadata | TBD | ⏳ Discover | Unknown | iHeart US streams carry ICY |
| T6 | MusicBrainz enrichment | Enrichment only | ✅ Available | Approved | Not a capture source |
| T6 | Spotify enrichment | Enrichment only | ✅ Available (disabled) | Approved | Not a capture source |
| — | Manual CSV | Operator upload | ✅ Always available | N/A | Last resort only |

**Primary capture path:** T3 ICY stream  
**Gap:** No validated source. Mirror of Z100 situation.

---

## KIIS1027 — KIIS-FM 102.7 FM Los Angeles (102.7 MHz)

| Tier | Source type | URL / ID | Status | Compliance | Notes |
|---|---|---|---|---|---|
| T2 | Radiowave Monitor diary | `radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080` | ❌ 0 rows across all dates | Unknown | IDDS=5080 unverified; may be wrong ID or US stations not tracked |
| T1 | iHeart v3 live-meta | API unavailable (same as Z100/WKSC) | ❌ API gone | Unknown | — |
| T3 | ICY stream metadata | TBD | ⏳ Discover | Unknown | iHeart US streams |
| T6 | MusicBrainz enrichment | Enrichment only | ✅ Available | Approved | Not a capture source |
| T6 | Spotify enrichment | Enrichment only | ✅ Available (disabled) | Approved | Not a capture source |
| — | Manual CSV | Operator upload | ✅ Always available | N/A | Last resort only |

**Primary capture path:** No validated source. T3 ICY is the only viable path pending discovery.  
**Gap:** All programmatic sources blocked. This station has no automated collection path currently.

---

## Coverage Gap Summary

| Station | Automated sources (validated) | Automated sources (pending) | Immediate next action |
|---|---|---|---|
| NOVA969 | 0 | 1 (Radiowave re-validate) | RADIOWAVE-REVALIDATION-1 |
| KIISFM | 0 | 1 (ICY stream discovery) | STREAM-METADATA-DISCOVERY-1 |
| CAPITALFM | 0 | 2 (ORB parser + ICY) | VAL-CAPUK-ORB-001 or ICY discovery |
| BBCRADIO1 | 0 | 1 (BBC RMS — ToS gate only) | BBC-TOS-REVIEW-1 (human) |
| HEARTFMUK | 0 | 2 (parser repair + ICY) | HEART-HTML-PARSER-FIX-1 |
| WHTZ / Z100 | 0 | 1 (ICY stream) | STREAM-METADATA-DISCOVERY-1 |
| WKSC | 0 | 1 (ICY stream) | STREAM-METADATA-DISCOVERY-1 |
| KIIS1027 | 0 | 1 (ICY stream) | STREAM-METADATA-DISCOVERY-1 |

**8 stations tracked. 0 automated sources currently validated and operational.**  
Manual CSV fallback is always available but requires operator data uploads.  
Stream metadata discovery is the highest-leverage next pass — it covers all 8 stations.
