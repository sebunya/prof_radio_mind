# Future Design: Proof-of-Play Reporting

**Status:** Design-only. Not scheduled for MVP implementation.  
**MVP Boundary:** No proof-of-play code exists in passes 1–21.  
**Prerequisite passes:** 22+ (DB persistence layer), 25+ (playlist automation baseline)

---

## Overview

Proof-of-Play (PoP) reporting allows RMIAS to generate legally-admissible airplay logs that demonstrate a song was broadcast at a specific time and station. These reports are used for:

- **APRA AMCOS / PPCA royalty processing** — royalty calculation requires timestamped evidence of each broadcast
- **Label reporting** — labels need accurate airplay counts to verify promotional performance
- **Dispute resolution** — broadcasters need audit-quality records to contest incorrect royalty claims

---

## Problem Statement

Radio stations currently rely on manual logs or third-party monitoring services (Radiowave, Nielsen) for proof-of-play. These services are expensive and have coverage gaps. RMIAS already captures `play_events` with timestamps, station, artist, title, and source — this is the raw material for a PoP report. The gap is: (a) legal attestation, (b) tamper-evident storage, and (c) regulatory-compliant export format.

---

## Functional Requirements

### R1 — Tamper-evident play log
Each `PlayEvent` must be stored with a content hash (SHA-256 of artist + title + played_at + station_id). Any modification is detectable. This is already implemented in `RawPayload`; `PlayEvent` needs the same treatment.

### R2 — Station-signed attestation
Each daily PoP report must be digitally signed by the station operator (or RMIAS on their behalf using a key they control). Signature proves the station acknowledges the log.

### R3 — Export format
Exports must be available in:
- **CSV** — for internal use and label submissions
- **DDEX ERN 4.x** — industry standard for music licensing data exchange (future)

### R4 — Regulatory retention
PoP records must be retained for a minimum of 7 years (APRA AMCOS requirement). Storage architecture must support this without operational cost explosion (cold storage tiering).

### R5 — Dispute workflow
Operators can flag individual `PlayEvent` records as disputed. Disputed events are excluded from PoP exports until resolved through the review queue.

### R6 — Confidence threshold
Only `PlayEvent` records with `ConfidenceLevel.HIGH` (≥ 0.85) are included in primary PoP exports by default. Lower-confidence events are included in a separate "provisional" annexure.

---

## Non-Functional Requirements

- Export generation time: < 30 seconds for a 24-hour station log (~200–400 events)
- Storage: cold-tier archival after 90 days (S3 Glacier or equivalent)
- Audit log: all export requests must be logged with operator identity
- Immutability: once a PoP report is generated and signed, it cannot be edited (only superseded with a new version)

---

## Proposed Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                       Proof-of-Play System                          │
│                                                                     │
│  ┌───────────────┐   ┌──────────────────┐   ┌─────────────────┐   │
│  │  PlayEvent    │   │  Confidence      │   │  Dispute        │   │
│  │  Store        │──▶│  Scorer          │──▶│  Filter         │   │
│  └───────────────┘   └──────────────────┘   └────────┬────────┘   │
│                                                       │            │
│                              ┌────────────────────────▼──────────┐ │
│                              │  PoP Report Generator              │ │
│                              │  - Group by station + date         │ │
│                              │  - Compute SHA-256 manifest        │ │
│                              │  - Attach operator signature       │ │
│                              └────────────────────────┬──────────┘ │
│                                                       │            │
│                   ┌───────────────────────────────────▼──────────┐ │
│                   │  PoP Report Store (immutable, versioned)      │ │
│                   │  primary: high-confidence events              │ │
│                   │  provisional: medium/low confidence annexure  │ │
│                   └──────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

### New domain entities required

```python
@dataclass(frozen=True)
class ProofOfPlayReport:
    id: uuid.UUID
    station_id: uuid.UUID
    report_date: date
    generated_at: datetime
    generated_by: str
    event_count: int              # primary (high-confidence) events
    provisional_count: int        # medium/low confidence events
    manifest_sha256: str          # SHA-256 of concatenated event hashes
    operator_signature: str | None  # base64 ECDSA signature
    storage_path: str             # path to archived CSV/DDEX file
    version: int                  # supersedes previous versions
```

### New API endpoints required

| Method | Path | Description |
|---|---|---|
| GET | `/pop-reports/{station_id}` | List PoP reports for a station |
| POST | `/pop-reports/{station_id}/generate` | Generate PoP report for a date range |
| GET | `/pop-reports/{report_id}/download` | Download signed CSV export |
| POST | `/play-events/{event_id}/dispute` | Flag event as disputed |
| DELETE | `/play-events/{event_id}/dispute` | Resolve dispute |

---

## Signing mechanism (sketch)

RMIAS uses ECDSA-P256 for report signing:

1. Station operator generates a key pair (once, at station setup)
2. Public key stored in RMIAS database against the station
3. Private key held securely by the station operator (hardware token recommended)
4. At report generation: RMIAS computes manifest hash → station operator signs it → signature appended to report
5. Verifiers can check signature against the stored public key

In the MVP-adjacent implementation, RMIAS can sign on behalf of the station using a system key (lower legal weight, but sufficient for internal use and label submissions).

---

## Schema additions (Phase E)

```sql
CREATE TABLE pop_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_id UUID REFERENCES stations(id),
    report_date DATE NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    generated_by VARCHAR(255) NOT NULL,
    event_count INTEGER NOT NULL,
    provisional_count INTEGER NOT NULL DEFAULT 0,
    manifest_sha256 CHAR(64) NOT NULL,
    operator_signature TEXT,
    storage_path TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    superseded_by UUID REFERENCES pop_reports(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (station_id, report_date, version)
);

ALTER TABLE play_events
    ADD COLUMN event_hash CHAR(64),
    ADD COLUMN dispute_reason TEXT,
    ADD COLUMN disputed_at TIMESTAMPTZ,
    ADD COLUMN disputed_by VARCHAR(255);
```

---

## Regulatory context

| Body | Requirement | RMIAS approach |
|---|---|---|
| APRA AMCOS | Airplay logs with timestamp, station, artist, title | `play_events` table meets this |
| PPCA | Phonogram broadcast logs (same as APRA for sound recordings) | Same as above |
| ACMA | Broadcast licence conditions (incidental — no specific log format) | PoP report as evidence |
| ARIA | Chart eligibility verification | PoP report + confidence filter |

> **Legal note:** RMIAS PoP reports are NOT a substitute for legal advice. The station operator is responsible for ensuring their royalty reporting meets all applicable obligations. Consult a broadcast licensing lawyer before relying on RMIAS PoP reports for regulatory compliance.

---

## Implementation roadmap (post-MVP)

| Pass | Deliverable |
|---|---|
| 28 | SHA-256 event hash on `PlayEvent` persistence |
| 29 | Dispute flagging workflow (API + review queue integration) |
| 30 | PoP CSV export (primary + provisional annexure) |
| 31 | Manifest signing with system key (ECDSA-P256) |
| 32 | Cold storage archival job (S3/GCS after 90 days) |
| 33 | DDEX ERN 4.x export adapter (if label requirement emerges) |

---

## Open questions

1. **Legal weight:** What legal standard must RMIAS PoP reports meet for APRA dispute purposes? Do we need a third-party witness or just a chain-of-custody log?
2. **Key custody:** Who holds the signing private key? Station GM? Head of music? A hardware HSM?
3. **Retroactive application:** Can we retroactively apply PoP signing to historical `play_events` already in the database?
4. **DDEX priority:** Are label partners requiring DDEX now, or is CSV sufficient for the first 12 months?
5. **Confidence threshold:** Is 0.85 (HIGH) the right PoP inclusion threshold, or should operators be able to configure per-station?
