# Compliance and Retention Guardrails

**Date:** 2026-06-05  
**Status:** Policy document — binding on all implementation passes  
**Owner:** Architecture

---

## 1. Governing Principles

1. **No data collected without legal basis.** Every source must have a compliance status
   of `approved` before production enablement. Unknown status = not approved.
2. **Receive, not record.** Radio broadcasts are public signals. Capturing track metadata
   from them is lawful. Storing the audio itself is not permitted without licensing.
3. **Robots.txt is a constraint, not a suggestion.** Any URL used for web scraping must
   have `robots.txt` checked and the result recorded in VALIDATION_REGISTER.md.
4. **Terms of Service bind collection.** If a provider's ToS prohibits automated access,
   programmatic data collection from that provider is blocked regardless of technical
   feasibility.
5. **Source enrichment ≠ source capture.** Spotify and MusicBrainz confirm what a track is;
   they do not confirm that it was played on a specific radio station.
6. **No evasion of any kind.** No IP rotation to avoid rate limits, no User-Agent spoofing
   to bypass restrictions, no session token theft, no login bypass, no JS execution
   to access bot-protected content.

---

## 2. Source Risk Classification

| Source class | Legal basis | Risk level | Compliance action required |
|---|---|---|---|
| Official broadcaster API | Explicit permission or documented public API | Low | ToS review, record approval |
| Public HTML page (raw) | Implicit public access; ToS review required | Medium | Check robots.txt, review ToS, record decision |
| ICY/Shoutcast stream metadata | Receiving public broadcast signal (metadata in-band) | Low | Confirm stream is public; check ToS if applicable |
| HLS/DASH timed metadata | Same as ICY | Low | Same as ICY |
| Audio fingerprinting | Short sample of public broadcast; no storage | Medium-high | API terms review + legal review before deployment |
| Licensed vendor data | Contractual | Low (once licensed) | Contract review; usage limits enforced |
| MusicBrainz | CC0 / ODbL open data | Low | None — enrichment only |
| Spotify | Developer agreement | Low (enrichment-only use) | Existing developer agreement; no streaming/scraping |
| JavaScript-rendered content accessed via headless browser | Browser automation; ToS typically prohibit bots | **High — do not implement** | Block unless explicit API alternative found |
| Authenticated content (login required) | Requires credentials; unauthorized access prohibited | **Very high — block** | Never implement |
| Geo-restricted content accessed via VPN/proxy | Intentional circumvention | **Very high — block** | Never implement |

---

## 3. robots.txt Policy

For every URL used in a Tier 2 (web metadata) source:

1. Fetch `{domain}/robots.txt` before writing any collector.
2. Check for `User-agent: *` or `User-agent: TenXRadar` disallow rules.
3. Record finding in VALIDATION_REGISTER.md under the relevant VAL code.
4. If `Disallow: /` or a specific disallow covers the target path:
   - Mark compliance_status = `BLOCKED`
   - Do not proceed with that source
   - Find an alternative (API, stream metadata, licensed data)
5. If no disallow: proceed, but still review the site's ToS (robots.txt ≠ ToS).

Current robots.txt check status:

| URL | Checked | Finding | Status |
|---|---|---|---|
| heart.co.uk/robots.txt | ❌ Not yet | — | Pending |
| radiowave.com.au/robots.txt | ❌ Not yet | — | Pending |
| radiowavemonitor.com/robots.txt | ❌ Not yet | — | Pending |
| onlineradiobox.com/robots.txt | ❌ Not yet | — | Pending |
| rms.api.bbc.co.uk (API — no robots.txt) | N/A | Official API | ToS only |

---

## 4. Data Retention Policy

### 4a. What may be stored

| Data type | Storage | Max retention | Notes |
|---|---|---|---|
| Play event (artist, title, station, timestamp) | PostgreSQL | Indefinite (business data) | Core product data |
| Source event ID | PostgreSQL | With play event | For dedup only |
| Acoustic fingerprint hash | PostgreSQL / Redis | 30 days | Derived — no audio |
| Raw HTML response | Filesystem / S3 | `RAW_PAYLOAD_RETENTION_DAYS` setting | Before parse; useful for debugging drift |
| Raw JSON response | Filesystem / S3 | Same | Same |
| Collector run metadata | PostgreSQL | Indefinite | Operational |
| NoTrackEvent | PostgreSQL | 90 days | Operational |
| Source health record | PostgreSQL | Rolling 20 runs | Operational |
| HTTP status codes | PostgreSQL | Rolling 20 runs | Operational |
| API request logs | Log files | 7 days | Operational |

### 4b. What must never be stored

| Data type | Reason |
|---|---|
| Audio bytes (any duration) | Copyright; no license to store broadcast audio |
| Audio stream chunks/segments | Same — no partial audio storage |
| Full audio tracks in any format | Copyright |
| Login credentials (any provider) | Security; also prohibited by all ToS |
| Private API tokens (non-operator) | Legal; session theft |
| User PII from scraped pages | GDPR / data protection |
| Personal data from now-playing APIs | Data minimisation |

### 4c. `store_audio` hard enforcement

The `RawPayload` entity must reject any write where:
- `content_type` starts with `audio/`
- `byte_size > 1_048_576` (1 MB) without explicit override for known-large HTML pages

This prevents accidental audio storage from a misconfigured stream reader.

---

## 5. Provider-Specific Compliance Notes

### BBC RMS API (`rms.api.bbc.co.uk`)

- **ToS review required** before any production use (VAL-BBC1-006).
- BBC Developer Terms at bbc.co.uk/developer must be read.
- BBC Sounds' programme schedule is CC-licensed; the RMS track/segment API may have
  separate terms.
- Key question: Is programmatic polling at 5-minute intervals for radio track metadata
  permitted under BBC Developer Terms?
- **Block enablement** until VAL-BBC1-006 is manually recorded as PASS.

### iHeart API

- The v3 live-meta API is an undocumented internal API, not a public developer API.
- iHeart does not publish developer documentation for `/api/v3/live-meta/stream/`.
- Using undocumented internal APIs may violate iHeart's ToS.
- **Current status:** API is also unavailable (404), making this moot for now.
- **Path forward:** iHeart stream ICY metadata is the preferred alternative.
- If a documented iHeart developer API is found, review its terms before integration.

### Heart FM (heart.co.uk / Global Radio)

- heart.co.uk is a consumer-facing website.
- **robots.txt must be checked** before the parser repair proceeds.
- If Global Radio has a developer API (some broadcasters do), prefer that over scraping.
- The `last-played-songs` page is a public page. ToS must be reviewed for programmatic
  access frequency constraints.

### Radiowave (radiowave.com.au and radiowavemonitor.com)

- **Both domains** must have robots.txt checked.
- Radiowave is a specialist radio monitoring service; their data may have specific terms.
- The diary endpoint appears to be a public chart — confirm this is publicly intended
  and not a subscriber-only feature.

### ICY / Stream Metadata

- Public radio streams are broadcast for public reception.
- Connecting to a public HTTP stream to read its embedded metadata is equivalent to
  tuning a radio and reading the RDS display.
- No special permission required for public streams.
- Rate constraint: one connection per station; disconnect after metadata read.
- Confirm stream is actually public (no auth header required, no geo-blocking via terms).

### ACRCloud / AudD (audio fingerprinting)

- **Terms of service must be reviewed before integration.**
- ACRCloud's "Broadcast Monitoring" product is specifically designed for this use case;
  the terms likely permit it.
- AudD terms must be checked for broadcast monitoring use case.
- The key question for both: Is this permitted for continuous 24/7 radio monitoring?
- **Do not integrate either service until terms are confirmed approved.**

### Spotify

- **Enrichment only.** The Spotify Developer Agreement prohibits:
  - Using Spotify data to "imply editorial endorsement" by Spotify
  - Using Spotify as a data source for radio charts
  - Streaming or downloading content
  - Storing Spotify content beyond cache limits
- Permitted: Track metadata lookup, artwork display, Spotify track IDs, popularity scores
- The TenX Radar Spotify integration is used after a play event is confirmed from a radio
  source. Spotify confirms metadata about the track. It does not confirm the track was
  broadcast.

### MusicBrainz

- MusicBrainz data is CC0 (public domain) for data and ODbL for database.
- Rate limit: 1 request/second (already implemented in settings).
- Usage is broadly permitted. No ToS concerns for enrichment use.
- Must not be represented as evidence of radio broadcast (it is a music catalog, not a
  radio monitoring service).

---

## 6. Compliance Review Process

For each new source:

1. **Create a VAL-* entry** in `docs/VALIDATION_REGISTER.md` with:
   - Source URL
   - Initial compliance_status = UNKNOWN
   - robots.txt finding
   - ToS review date and outcome
   - Responsible reviewer

2. **Complete the compliance checklist:**
   - [ ] robots.txt checked (for web sources)
   - [ ] Terms of Service read and summarised
   - [ ] Programmatic access explicitly prohibited? → BLOCKED
   - [ ] Rate limits identified and respected
   - [ ] Data fields collected documented
   - [ ] No PII collected without basis
   - [ ] No audio stored
   - [ ] Retention policy recorded
   - [ ] VAL code updated to APPROVED or BLOCKED

3. **Record the decision** with date and reviewer in VALIDATION_REGISTER.md.

4. **Set compliance_status** in source seeds / source capability record.

5. **No enablement** until compliance_status = `approved`.

---

## 7. Anti-Patterns That Are Explicitly Blocked

The following approaches are permanently blocked regardless of technical feasibility:

| Anti-pattern | Reason blocked |
|---|---|
| Rotating IPs / proxies to avoid rate limits | Intentional circumvention; ToS violation |
| Spoofing User-Agent to impersonate browsers | Deceptive; ToS violation |
| Using headless browser (Playwright/Puppeteer) to render JS-only pages | Bot automation; ToS typically prohibit; classification as `js_rendered_content` → `source_not_supported` unless official API found |
| Accessing API endpoints not listed in any public or developer documentation | Undocumented APIs may be ToS violations; also fragile |
| Downloading or storing audio streams beyond fingerprint computation | Copyright violation |
| Accessing geo-restricted content via VPN on the collection server | Intentional circumvention |
| Credential stuffing, credential sharing, or shared login | Prohibited by all platforms |
| Bypassing CAPTCHA or bot detection | Intentional circumvention |
| Scraping data behind a login | Unauthorized access |
| Building a music download or redistribution path | Copyright violation |

These are not open for re-evaluation unless the underlying legal or ToS basis changes
and that change is reviewed and approved by the operator.

---

## 8. Retention Defaults

Until explicit retention policies are set per source, the defaults are:

| Data class | Default retention |
|---|---|
| Raw payloads (HTML/JSON) | `RAW_PAYLOAD_RETENTION_DAYS` setting (0 = forever) |
| Play events | Indefinite |
| Collector run records | Indefinite |
| No-track events | 90 days |
| Source health records | Rolling 20 runs |
| Audio | Never stored |

**Recommendation:** Set `RAW_PAYLOAD_RETENTION_DAYS=90` in production once validators
confirm parsers are stable. Retaining raw HTML/JSON payloads indefinitely consumes disk
and creates no operational value once collection is proven.
