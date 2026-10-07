# Tenga Inventory — Unknowns Register

## U001 — Offline operation
Unknown: Should the MVP support offline operation and sync?
Why it matters: Affects architecture, complexity, and pilot viability in low-connectivity contexts.
What depends on it: Data model, conflict resolution, UX for offline mode.
What information would resolve it: Pilot sites' connectivity characteristics and tolerance for online-only workflows.
Can it be deferred? Yes — can be deferred to post-MVP with mitigation (clear online requirement documented). Assumption A005 defers this.
Status: Deferred to post-MVP. Validate with pilots during onboarding.

---

## U002 — Cost enforcement at receipt
Unknown: Should cost be mandatory for receipts in commercial pilots?
Why it matters: Affects valuation completeness and data collection.
What depends on it: UX, field validation, and reporting accuracy.
What information would resolve it: Pilot feedback and shop owners' workflows.
Can it be deferred? Yes — start optional and recommend costs. Monitor in pilots.
Status: MVP decision: cost is optional. Validate pilot behavior and adjust recommendation/nudge in post-MVP.

---

## U003 — Scale targets
Unknown: Exact SKU and movement throughput targets for grocery pilots.
Why it matters: Impacts performance and storage design.
What depends on it: Query optimization, batching, pagination.
What information would resolve it: Pilot inventory size estimates and daily transactions per site.
Can it be deferred? Partially — must validate early in feasibility. Performance targets should be confirmed before implementation begins.
Status: Pending pilot questionnaire. Document expected scale: 100–10K SKUs, 10–100 transactions/day.

---

## U004 — Import needs
Unknown: Volume and format of data that pilots can provide for opening balances.
Why it matters: Affects import feature scope and data mapping.
What depends on it: CSV schema, import validation, mapping UI.
What information would resolve it: Request sample exports from pilot sites.
Can it be deferred? Yes — CSV import can be post-MVP should pilots require it. Assumption A010 defers this.
Status: Deferred. Manual entry sufficient for MVP; ask pilots about opening balance volume post-pilot-launch if CSV import becomes urgent.

---

## U005 — Integrations
Unknown: Which external systems (POS, accounting) pilot sites already use and if they require integration.
Why it matters: Could change roadmap priority for integrations.
What information would resolve it: Pilot questionnaires and interviews.
Can it be deferred? Yes — integrations are post-MVP unless a pilot demands otherwise.
Status: Deferred. Inventory-first principle (D001) means Tenga stands alone; integrations are optional future work.

---

## U006 — Regulatory/fiscal requirements
Unknown: Any local legal requirements (e.g., fiscalisation) affecting inventory records.
Why it matters: Affects retention, audit, and data export formats.
What information would resolve it: Jurisdictional research and pilot legal constraints. Assumption A011 defers formal audit exports.
Can it be deferred? Likely yes for initial pilots; escalate if a pilot requires compliance.
Status: Pending pilot questionnaire. Assumption A011 documents that formal audit exports are post-MVP; validate with pilots.

---

## U007 — Arrupe's accountability model details
Unknown: Exact workflows for departmental accountability (e.g., check-out/check-in to departments, custodian assignment).
Why it matters: Affects whether basic Transfer workflow is sufficient or if more structured workflows are needed.
What depends on it: Transfer UX, permission model, reporting on "who has what."
What information would resolve it: Deep-dive interviews with Arrupe managers about current workflows.
Can it be deferred? Partially. Core Transfer workflow should work; specialized workflows (e.g., formal check-out) can be post-MVP.
Status: Pending Arrupe pilot onboarding. Validate transfer workflow covers their needs; escalate specialized workflows to Phase 2.

---

## U008 — Grocery pilots' count frequency and methodology
Unknown: How often do grocery shops count, how much of inventory they count (full vs spot checks), and level of detail needed.
Why it matters: Affects count feature design and reporting emphasis.
What depends on it: Count UX (simple vs detailed), reconciliation workflow, partial count support.
What information would resolve it: Interviews with shop owners about counting practices.
Can it be deferred? No — count is core workflow. Design for full counts + optional partial counts; MVP supports both.
Status: Pending pilot interviews. MVP Count feature should be flexible enough for both full and partial counts.

---

## U009 — Definition of "available stock" vs "committed" or "reserved"
Unknown: Should the system track only current quantity, or also reserved/committed stock?
Why it matters: Affects whether balance field is simple "quantity" or complex "available/reserved/total."
What depends on it: Stock Balance entity design, Transfer logic, Issue validation.
What information would resolve it: Pilot usage patterns (do they reserve stock for pending orders? only Arrupe's formal assignment).
Can it be deferred? Yes. MVP tracks only current quantity; reserved/committed stock is post-MVP if needed.
Status: Deferred. MVP assumes no reservation semantics; Location-specific stock model (A006) is sufficient.

---

## U010 — Pilot onboarding volume and timeline
Unknown: How many products, how much historical data, and timeline for going live for each pilot.
Why it matters: Affects whether manual entry, CSV import, or other data loading methods are appropriate.
What depends on it: Import feature scope, implementation timeline, pilot onboarding support.
What information would resolve it: Pilot questionnaires and project kickoff.
Can it be deferred? Partially. Manual entry works; CSV import can be post-MVP if pilots need speed.
Status: Pending pilot scoping. Document: Arrupe (expect 500–2K items, full 5-year history?), Grocery (expect 200–1K items, clean start).

---

## Summary: Unknowns by Resolution Path

| Unknown | Resolution | Timeline |
|---------|-----------|----------|
| U001 (Offline) | Assumption A005: Defer; ask pilots about connectivity | Pilot kickoff |
| U002 (Cost mandatory?) | Monitor pilot behavior; MVP: optional | Pilot operation |
| U003 (Scale targets) | Pilot questionnaire | Pilot kickoff |
| U004 (Import volume) | Ask pilots; defer CSV if not urgent | Pilot kickoff or post-launch |
| U005 (Integrations) | Defer; integrations are optional/future | Post-MVP |
| U006 (Compliance) | Ask pilots; assumption A011 defers formal exports | Pilot kickoff |
| U007 (Arrupe accountability) | Pilot interviews; escalate specialized workflows | Pilot design phase |
| U008 (Grocery count methodology) | Pilot interviews; MVP supports full and partial | Pilot design phase |
| U009 (Reserved stock) | Defer; MVP doesn't track reservations | Post-MVP if needed |
| U010 (Onboarding volume) | Pilot scoping conversations | Project kickoff |

All unknowns are resolvable without blocking MVP implementation.

