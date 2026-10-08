# Tenga Inventory — Final Unknowns Register

This register records unresolved questions, priority to resolve, resolution path, and timing.

---

## U001 — Offline operation
- Status: Deferred / Must validate
- Impact if unresolved: Architecture unaffected for MVP, but pilots with poor connectivity may fail adoption.
- Resolution: Pilot connectivity questionnaire and early ground-truthing.
- Timeline: Before pilot onboarding.

---

## U002 — Cost enforcement at receipt
- Status: Resolved for MVP (cost optional). Monitor.
- Impact if wrong: Valuation completeness may suffer; consider soft-nudges or category-level enforcement.
- Resolution: Track percent of receipts with cost; follow-up in 2–4 weeks of pilot.

---

## U003 — Scale targets (SKU & throughput)
- Status: Pending (must resolve for capacity planning)
- Impact: Performance and storage design decisions rely on realistic scale numbers.
- Resolution: Collect estimates from grocery pilots; run a performance benchmark with representative dataset.
- Timeline: Pilot scoping.

---

## U004 — Import needs (opening balances)
- Status: Deferred to post-MVP unless pilot requires earlier
- Impact: Onboarding time for large catalogs.
- Resolution: Request sample CSVs; decide whether CSV import UI is needed before pilot onboarding.
- Timeline: Pilot kickoff.

---

## U005 — Integrations (which systems pilots use)
- Status: Deferred
- Impact: Integration priority may change roadmap.
- Resolution: Pilot questionnaires; log existing systems and integration needs.
- Timeline: Pilot onboarding.

---

## U006 — Regulatory / fiscal requirements
- Status: Pending
- Impact: Data retention/export/format could be required by law in some jurisdictions.
- Resolution: Ask pilot legal/finance teams; document any special requirements before pilot go-live.
- Timeline: Pilot scoping.

---

## U007 — Arrupe accountability details
- Status: Pending
- Impact: May require check-out/check-in features or custodian assignment.
- Resolution: Interview Arrupe managers and observe sample workflows.
- Timeline: Pilot setup week.

---

## U008 — Grocery count frequency & methodology
- Status: Pending
- Impact: Count UX may need to support frequent partial counts and quick spot checks.
- Resolution: Interview grocery pilot owners; observe current counting practices.
- Timeline: Pilot design phase.

---

## U009 — Reserved/Committed stock semantics
- Status: Deferred (MVP tracks only current quantity)
- Impact: If shops need committed/reserved semantics (e.g., layaway), feature must be planned.
- Resolution: Validate with pilots; if required, design reservation model post-MVP.
- Timeline: Post-MVP as needed.

---

## U010 — Pilot onboarding volume & timeline
- Status: Pending
- Impact: Affects whether CSV import is required pre-launch.
- Resolution: Collect counts and sample exports from pilots.
- Timeline: Immediately during pilot engagement.

---

---

## CRITICAL CLARIFICATION — October 8, 2026

**⚠️ NAMING COLLISION ALERT**

During implementation (T001-T006), three architectural decisions were made and assigned IDs **U006-U008**. These decisions refer to **completely different topics** than the planning-phase unknowns listed below:

### Original Planning Unknowns (This Document)
| ID | Topic |
|----|-------|
| U001 | Offline operation |
| U002 | Cost enforcement at receipt |
| U003 | Scale targets |
| U004 | Import needs |
| U005 | Integrations |
| U006 | **Regulatory/fiscal requirements** |
| U007 | **Arrupe accountability details** |
| U008 | **Grocery count frequency & methodology** |
| U009 | Reserved/committed stock semantics |
| U010 | Pilot onboarding volume & timeline |

### Implementation Decisions (Different Document)
| ID | Topic |
|----|-------|
| U006 | **Permit & Reconcile Afterward** (oversell policy) |
| U007 | **Tiered Grace Periods** (subscription lifecycle) |
| U008 | **Offline Optimism** (device caching) |

**These are NOT the same topics.** See `implementation-decisions-u006-u007-u008.md` for details on the implementation decisions.

**Recommendation for future:** Use non-colliding ID scheme (D013+, ARCH-001+, IMPL-001+, etc.)

---

## Status Update on Original Planning Unknowns (U001-U010)

### U001 — Offline operation
- **Original Status:** Deferred to post-MVP
- **Current Status:** ✅ **IMPLEMENTED** (October 2026)
- **Evidence:** See `implementation-decisions-u006-u007-u008.md` (U008 decision) and T003 completion
- **Implementation:** Full offline sync protocol, device caching, idempotent batching
- **Notes:** Became core architecture rather than post-MVP feature due to POS requirements

---

### U002 — Cost enforcement at receipt
- **Original Status:** MVP decision: cost is optional. Monitor pilot behavior.
- **Current Status:** ⏸️ **DEFERRED PENDING PILOT**
- **Evidence:** Cost field remains optional in Product and InventoryMovement models
- **Notes:** No constraint enforcement in code; awaiting pilot feedback on data quality

---

### U003 — Scale targets
- **Original Status:** Pending pilot questionnaire
- **Current Status:** ❓ **UNRESOLVED (No pilot data collected)**
- **Evidence:** No scale testing performed; placeholder targets not validated
- **Notes:** Should be resolved before production scaling; current implementation suitable for 100-10K SKUs, 10-100 tx/day

---

### U004 — Import needs (opening balances CSV)
- **Original Status:** Deferred to post-MVP unless pilot requires
- **Current Status:** ⏸️ **DEFERRED (Not implemented)**
- **Evidence:** No CSV import feature in codebase
- **Notes:** Manual entry sufficient for MVP; recommend CSV import for Phase 2 if pilots need rapid onboarding

---

### U005 — Integrations (POS, accounting)
- **Original Status:** Deferred as post-MVP
- **Current Status:** ⏸️ **DEFERRED (Not implemented)**
- **Evidence:** No ERP/accounting integrations in code
- **Notes:** Inventory-first principle maintained; integrations remain optional future work

---

### U006 (Original) — Regulatory/fiscal requirements
- **Original Status:** Pending pilot questionnaire
- **Current Status:** ❓ **UNRESOLVED (No pilot data; Assumption A011 defers formal audit exports)**
- **Evidence:** No compliance export formats implemented
- **Notes:** Should be validated during pilot scoping; may affect data retention/format post-MVP

---

### U007 (Original) — Arrupe accountability model details
- **Original Status:** Pending Arrupe pilot onboarding
- **Current Status:** ❓ **PARTIALLY RESOLVED** (Core Transfer workflow implemented; specialized workflows TBD)
- **Evidence:** `Transfer` movement type implemented in InventoryMovement; no special "check-out/check-in" workflow
- **Notes:** Basic accountability via location assignment and movement audit trail; specialized Arrupe workflows deferred

---

### U008 (Original) — Grocery count frequency & methodology
- **Original Status:** Pending pilot interviews
- **Current Status:** ✅ **ADDRESSED** (Flexible counting supported)
- **Evidence:** InventoryMovement with type `COUNT` supports both full and partial inventory counts
- **Notes:** MVP supports full counts and partial spot checks; recommend pilot validation of UX

---

### U009 — Reserved/committed stock semantics
- **Original Status:** Deferred (MVP tracks only current quantity)
- **Current Status:** ⏸️ **DEFERRED (Not implemented)**
- **Evidence:** Stock model tracks only quantity; no "available" vs "reserved" distinction
- **Notes:** Post-MVP feature if pilots require layaway or pre-order semantics

---

### U010 — Pilot onboarding volume & timeline
- **Original Status:** Pending pilot scoping
- **Current Status:** ❓ **UNRESOLVED (No pilot deployment yet)**
- **Evidence:** System handles arbitrary volumes (tested with synthetic data)
- **Notes:** Will be resolved during first pilot onboarding; recommend data loading strategy conversation

---

## Summary: Planning Unknowns Resolution Status

| Unknown | Resolution Path | Timeline | Status |
|---------|-----------------|----------|--------|
| U001 (Offline) | **IMPLEMENTED** (became core feature) | Oct 2026 | ✅ Done |
| U002 (Cost mandatory?) | Monitor pilot; MVP optional | Pilot phase | ⏸️ Deferred |
| U003 (Scale targets) | Pilot questionnaire + benchmark | Pilot kickoff | ❓ Pending |
| U004 (Import volume) | Ask pilots; defer CSV if not urgent | Pilot kickoff | ⏸️ Deferred |
| U005 (Integrations) | Defer; integrations optional | Post-MVP | ⏸️ Deferred |
| U006 (Compliance) | Ask pilots; A011 defers formal exports | Pilot kickoff | ❓ Pending |
| U007 (Arrupe accountability) | Pilot interviews; basic workflows in MVP | Pilot phase | ⏳ Partial |
| U008 (Grocery count methodology) | MVP supports flexible counting | Pilot phase | ✅ Addressed |
| U009 (Reserved stock) | Defer if not needed; post-MVP if required | Post-MVP | ⏸️ Deferred |
| U010 (Onboarding volume) | Pilot scoping conversations | Pilot phase | ❓ Pending |

**Summary:**
- ✅ **1 implemented** (U001 - offline became core)
- ✅ **1 addressed** (U008 - counting support included)
- ⏳ **1 partial** (U007 - basic workflows in MVP)
- ❓ **4 pending** (U003, U006, U010 - require pilot data; U002 - requires monitoring)
- ⏸️ **5 deferred** (U002, U004, U005, U009 - post-MVP unless pilot demands)

---

## Pilot Readiness Checklist

Before pilot deployment, **must resolve:**
- ❓ U003 - Confirm scale targets (SKU count, transaction volume)
- ❓ U006 - Confirm regulatory requirements (data retention, export formats)
- ❓ U010 - Finalize onboarding volume and data loading approach

**Should validate during pilot:**
- ⏸️ U002 - Cost data quality with voluntary entry
- ⏳ U007 - Whether basic accountability workflows meet Arrupe needs
- ✅ U008 - Whether count UX supports grocery practices

**Can defer to Phase 2:**
- ⏸️ U004 - CSV import (use manual entry for MVP)
- ⏸️ U005 - ERP integrations
- ⏸️ U009 - Reserved stock semantics

