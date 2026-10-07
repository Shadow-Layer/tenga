# Tenga Inventory — Assumption Register

## A001
Assumption: Pilot sites (Arrupe and small grocery shops) represent meaningful use-cases for broader market.
Why we believe it: Institutional inventory and small retail are common cases where inventory is used independent of POS.
Evidence: User input and domain knowledge; complementary use-cases provide contrast.
Risk if wrong: Product may overfit pilots and not generalize; wasted pilot effort.
How to validate: Run pilots and collect adoption/retention metrics.
Status: Proposed

## A002
Assumption: Weighted average costing is acceptable for MVP valuation.
Why we believe it: Balances simplicity and meaningful valuation for both pilots.
Evidence: User confirmed preference; reduces need for batch/lot tracing.
Risk if wrong: Some businesses may require FIFO or per-batch costing immediately.
How to validate: Pilot feedback and sample accounting reconcilations.
Status: Confirmed

## A003
Assumption: Cost entry can be optional per item and optionally recommended in receipts.
Why we believe it: Institutions may not want or need costing, while shops usually do.
Evidence: User input during discovery.
Risk if wrong: Incomplete valuation or poor reporting for shops that omit costs.
How to validate: Monitor pilot behavior and assess whether cost entry rates suffice.
Status: Confirmed

## A004
Assumption: Simple three-role RBAC suffices for MVP.
Why we believe it: Avoids complexity while providing necessary accountability.
Evidence: User provided role definitions.
Risk if wrong: Institutions may require finer-grained permissions; may complicate adoption.
How to validate: Pilot feedback and incident analysis.
Status: Confirmed

## A005
Assumption: Online-first MVP is acceptable; offline sync deferred.
Why we believe it: Offline sync adds complexity and is not essential to validate core loop.
Evidence: Feasibility preference and resource prioritization.
Risk if wrong: Some pilot environments may have unreliable connectivity.
How to validate: Ask pilots about connectivity; record incidents and consider offline for post-MVP.
Status: Proposed

---

## A006
Assumption: Stock is location-specific, not globally pooled and allocated.
Why we believe it: Matches both pilots' accountability needs; simpler mental model.
Evidence: User confirmed during domain deep-dive. Aligns with Arrupe's departmental custody model and grocery's shelf/storeroom model.
Risk if wrong: May need to rework mental model if pilots expect allocation/reservation semantics.
How to validate: Pilot onboarding; test with "Where is this stock?" questions.
Status: Confirmed

---

## A007
Assumption: Transfers are atomic single movements, not paired issue/receipt.
Why we believe it: Clearer audit trail; matches user mental model.
Evidence: User confirmed during domain deep-dive.
Risk if wrong: Auditors may expect separate issue and receipt records.
How to validate: Pilot audit feedback; test transfer history with auditors.
Status: Confirmed

---

## A008
Assumption: Receipt costs are immutable (locked at creation).
Why we believe it: Prevents silent revaluation; simple audit trail.
Evidence: User confirmed during domain deep-dive.
Risk if wrong: Corrections may be cumbersome; pilots may request cost editing.
How to validate: Pilot feedback on cost correction workflows.
Status: Confirmed

---

## A009
Assumption: Valuation drill-down (current value + cost history) is sufficient for pilot confidence.
Why we believe it: Simple headlines with optional depth balances usability and auditability.
Evidence: User preference stated during domain deep-dive.
Risk if wrong: Pilots may distrust valuations without more transparency.
How to validate: Monitor pilot questions and concerns about valuation.
Status: Confirmed

---

## A010
Assumption: Manual entry of opening balances is acceptable for MVP; CSV import is post-MVP.
Why we believe it: Simpler to implement; pilots can enter via Receive movements.
Evidence: Feasibility estimate; MVP scope prioritizes core loop over import speed.
Risk if wrong: Pilot onboarding may take longer than desired if thousands of SKUs.
How to validate: Ask pilots about opening balance volume (REQ-024 assessment).
Status: Proposed

---

## A011
Assumption: Movement history is sufficient for audit compliance; formal audit reports/exports are post-MVP.
Why we believe it: Core movement history provides audit trail; formal reports can be added later.
Evidence: MVP scope prioritizes core loop; audit compliance varies by jurisdiction/industry.
Risk if wrong: Some pilots may have legal audit requirements that need formal export/reporting.
How to validate: Ask pilots about audit/compliance needs (U006 assessment).
Status: Proposed

---

## A012
Assumption: Three-level UX progression (Basic, Intermediate, Advanced) supports both pilot types.
Why we believe it: Arrupe staff need simple core path; Admin/managers can access deeper features.
Evidence: User feedback during UX design phase.
Risk if wrong: Single level may be too simple or complex for one of the pilot types.
How to validate: Usability testing during pilot onboarding.
Status: Confirmed
