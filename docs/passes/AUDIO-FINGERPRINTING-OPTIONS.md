# Audio Fingerprinting Options — Feasibility Assessment

**Date:** 2026-06-05  
**Status:** Research / feasibility — no implementation yet  
**Next step:** FINGERPRINTING-FEASIBILITY-1 (after stream metadata discovery)

---

## 1. Why Audio Fingerprinting

When official APIs and web metadata sources fail, the only remaining programmatic way to
identify what is playing on a radio station without API access is to:

1. Connect to the station's public audio stream
2. Capture a short sample (3–10 seconds)
3. Compute an acoustic fingerprint of the sample
4. Send the fingerprint to a recognition service
5. Receive artist + title identification
6. Immediately discard the audio

This approach is:
- Independent of any station API or website structure
- Resilient to API deprecation and selector drift
- Used commercially by broadcast monitoring firms (BDS, Luminate, Nielsen)
- Legal where clearly authorised by service terms or broadcasting law

**What audio fingerprinting is not:**
- It is not music streaming
- It is not music storage
- It is not music redistribution
- It is not a way to "download" radio content

The audio sample is ephemeral. Only the fingerprint result (artist, title, confidence) is
retained. No audio bytes enter the database.

---

## 2. How It Works in the TenX Radar Architecture

```
Stream URL
    │
    ▼
Connect to stream (ICY/HLS/DASH)
    │
    ▼ (read ≤ 10 seconds of audio bytes)
AudioSampleCapture
    │
    ▼
FingerprintCompute (local hash OR send to API)
    │
    ├──→ Keep: FingerprintResult { artist, title, confidence, provider, fingerprint_hash }
    │
    └──→ Discard: AudioBytes (zero-copy: never written to disk, never logged)
    │
    ▼
CaptureObservation → Capture Resolver → PlayEvent
```

The audio bytes are processed in memory only. The `RawPayload` store MUST NOT receive
audio content. Only the fingerprint hash and recognition result are retained.

---

## 3. Provider Comparison

### 3a. ACRCloud Broadcast Monitoring

**Type:** Commercial SaaS API  
**Website:** acrcloud.com  
**Product:** "Broadcast Monitoring" (radio-specific) and "Music Recognition API"

| Dimension | Assessment |
|---|---|
| Coverage | 10M+ tracks; US, UK, AU commercial radio well covered |
| API type | REST API; send fingerprint bytes (not audio), receive JSON result |
| Sample required | 3–8 seconds of audio |
| Fingerprint method | Proprietary acoustic fingerprint computed client-side or server-side |
| Latency | Sub-second recognition after fingerprint submission |
| Radio-specific features | Yes — Broadcast Monitoring product designed for radio detection |
| Rate limits | Tier-based; typical commercial plans support 24/7 monitoring |
| Cost | Tiered pricing; "Broadcast Monitoring" product has station-level pricing |
| ToS for broadcast monitoring | Designed for this use case; requires account and API keys |
| Self-hosting | No — cloud service |
| Compliance fit | High — purpose-built for radio track identification |

**ACRCloud is the strongest commercial option for broadcast monitoring.** It is used by
major industry players. The API accepts a fingerprint of the audio, not raw audio, reducing
data transmission. Terms must be reviewed before integration.

### 3b. AudD

**Type:** Commercial SaaS API  
**Website:** audd.io  
**Product:** "Music Recognition API" and "Radio Monitoring"

| Dimension | Assessment |
|---|---|
| Coverage | Mainstream commercial music; international |
| API type | REST API; send audio bytes or URL |
| Sample required | ≥3 seconds |
| Radio-specific features | "Radio Monitoring" product available |
| Rate limits | Tiered; free tier available for testing |
| Cost | Lower entry cost than ACRCloud; may have usage caps |
| ToS for broadcast monitoring | Generally permissive; requires API key |
| Self-hosting | No — cloud service |
| Compliance fit | Medium-high — less specialized than ACRCloud for broadcast |

**AudD is a lower-cost alternative.** The free tier allows feasibility testing without
commitment. The radio monitoring product exists but is less battle-hardened than ACRCloud.

### 3c. AcoustID / Chromaprint

**Type:** Open source + community database  
**Website:** acoustid.org, github.com/acoustid/chromaprint  
**Product:** AcoustID fingerprinting library + open lookup API

| Dimension | Assessment |
|---|---|
| Coverage | Music with MusicBrainz mappings; strong for catalogue music |
| API type | Open API; fingerprint computed locally with Chromaprint library |
| Sample required | ≥10 seconds recommended |
| Radio-specific features | None — general music recognition |
| Rate limits | 3 req/s for free API |
| Cost | Free |
| ToS | Open; requires application registration |
| Self-hosting | Fingerprint computation yes; lookup no (external API) |
| Coverage gap | Less comprehensive for recent/new releases; may miss tracks |
| Compliance fit | Medium — not designed for continuous radio monitoring |

**AcoustID is appropriate for testing and non-commercial use.** It is a fallback option
for tracks that match MusicBrainz catalogue, but coverage gaps for recent commercial
radio music make it unreliable as a primary fingerprinting solution.

### 3d. Comparison Table

| Dimension | ACRCloud | AudD | AcoustID |
|---|---|---|---|
| Broadcast monitoring product | ✅ Yes | ✅ Yes | ❌ No |
| Coverage for radio music | ✅ High | ✅ High | ⚠️ Variable |
| Sends audio to cloud | ⚠️ Fingerprint only | ⚠️ Audio bytes | ⚠️ Fingerprint |
| Self-hostable | ❌ No | ❌ No | ✅ Partial |
| Free tier for testing | ❌ Contact sales | ✅ Yes | ✅ Yes |
| Cost for 8 stations, 24/7 | High | Medium | Free |
| ToS reviewed | ❌ Not yet | ❌ Not yet | ❌ Not yet |
| Recommended path | First choice | Testing fallback | Open-source supplement |

---

## 4. Technical Design: Fingerprint Collector

The existing `streamtheworld_icy.py` collector connects to ICY streams to read metadata.
An audio fingerprinting collector would connect to the same streams but read a short audio
segment instead.

```
FingerprintCollector:
  stream_url:         str              # Same URL used for ICY metadata
  sample_duration_s:  int = 5         # 5 seconds is sufficient for ACRCloud
  provider:           FingerprintProvider
  api_key:            str              # From settings (never logged)

fetch_raw():
  1. Connect to stream with Range or time-limited read
  2. Read sample_duration_s × bitrate bytes
  3. Return raw audio bytes (transient — never persisted)

compute_and_recognize():
  1. Compute acoustic fingerprint from audio bytes
  2. Send fingerprint to provider API
  3. Return FingerprintResult { artist, title, confidence, provider, mbid? }
  4. Delete audio bytes from memory

store_result():
  1. Persist FingerprintResult as CaptureObservation
  2. Store fingerprint_hash in SourceHealthRecord
  3. Do NOT write audio bytes to RawPayload store
```

**Retention rule:** The `RawPayload` store must have `content_type != audio/*` enforced.
Any payload with an audio content type must be rejected at write time.

---

## 5. Data Retained vs Discarded

| Data type | Retained? | Duration | Storage |
|---|---|---|---|
| Audio bytes (raw stream) | **NEVER** | — | Not written anywhere |
| Acoustic fingerprint hash | Yes | 30 days | `SourceHealthRecord.fingerprint_hash` |
| Artist + title (from API) | Yes | Per play event retention policy | `PlayEvent` table |
| Confidence score | Yes | With play event | `PlayEvent.meta` |
| Provider used | Yes | With play event | `PlayEvent.attribution` |
| API request/response log | Yes | 7 days | Debug log only, no audio |
| Sample size (bytes) | Yes | With collector run | `CollectorRun.meta` |

---

## 6. Legal Considerations

**Capturing a public broadcast to identify the song:** This is broadly accepted in
commercial broadcast monitoring. BDS (Billboard Data Services), Luminate (formerly
MRC Data), and Nielsen all operate on this basis. The broadcast is a public signal
emitted for public reception. Receiving it to identify its content is analogous to
a person listening to the radio and noting what was played.

**Key constraints:**
1. Do not store full audio tracks or extended recordings.
2. Do not store samples beyond the time needed for identification.
3. Do not build a searchable audio archive.
4. Do not redistribute audio in any form.
5. Respect the fingerprinting API's own terms of service.
6. For streams that require authentication or geographic access: do not attempt
   fingerprinting without confirming the stream is public.
7. Comply with applicable copyright law in the jurisdiction of both the stream
   origin and the monitoring server (Germany in our case for Hetzner).

**German law (relevant for Hetzner server):**  
Under German copyright law (UrhG), temporary reproduction for the purpose of reception
of a licensed broadcast is generally permitted. The monitoring service should not build
any archive that could substitute for licensing the music. This should be confirmed with
legal counsel before production deployment of Tier 4.

---

## 7. Recommended Implementation Sequence for Fingerprinting

1. **FINGERPRINTING-FEASIBILITY-1** (now): Review ACRCloud and AudD terms. Get test API keys.
   Test against a single public stream manually. Confirm fingerprint-only transmission.

2. **FINGERPRINTING-PILOT-1** (after feasibility): Implement `FingerprintCollector` behind
   a disabled flag. Test against one station in development only. Confirm no audio stored.

3. **FINGERPRINTING-VAL-1** (after pilot): Validate against live stream for one station.
   Confirm recognition rate, latency, and no audio stored in any log or storage path.

4. **FINGERPRINTING-PROD-1** (after compliance approval): Deploy to production with
   appropriate flag, retention policy, and monitoring.

**Do not deploy to production without legal review.** Fingerprinting is the highest legal
risk tier in the system and must not be fast-tracked.
