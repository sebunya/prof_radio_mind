# DATA-VERIFY-1 — Production Station and Source Seed Verification

This document records the verification of production database station and source seeds for Nova, KIIS, and Capital FM UK.

---

## 1. Station Verification
Verified that the database contains the correct stations:
* **Capital FM UK**:
  * call_sign: `CAPITALFM`
  * name: `Capital FM UK`
  * city: `London`
  * country_code: `GB`
  * frequency: `95.8 FM`
* **Nova 96.9**:
  * call_sign: `NOVA969`
  * name: `Nova 96.9`
* **KIIS-FM**:
  * call_sign: `KIISFM`
  * name: `KIIS-FM`

---

## 2. Source Verification
Verified that the database contains the correct sources and config status:
* **Capital FM UK (Online Radio Box)**:
  * URL: `https://onlineradiobox.com/uk/capitalfmuk/`
  * validation_status: `UNVALIDATED`
  * parser_status: `NOT_BUILT`
* **Capital FM UK (Manual CSV Fallback)**:
  * validation_status: `VALIDATED`
  * parser_status: `BUILT`
* **Nova 96.9 (Radiowave)**:
  * validation_status: `VALIDATED`
  * parser_status: `BUILT`
* **KIIS-FM (iHeart)**:
  * validation_status: `VALIDATED`
  * parser_status: `BUILT`

---

## 3. Data Integrity & Safety
* Checked that Nova and KIIS records remain fully intact and unmodified.
* Confirmed that validation_status for the Capital FM UK Online Radio Box candidate source remains conservative (`UNVALIDATED`) until the parser is verified and live collection is explicitly approved.
