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

## Actionable Summary
- Immediate: run pilot questionnaires for U001, U003, U004, U006, U007, U008, U010 before pilot onboarding.
- Deferred: U005 and U009 addressed post-MVP based on demand.

