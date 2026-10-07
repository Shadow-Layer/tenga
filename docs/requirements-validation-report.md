# Tenga Inventory — Requirements Validation Report

## Purpose
This report documents the adversarial review outcome (Iteration 3): what survived, what changed, what remains uncertain, major risks, architectural implications, and recommended next steps prior to technical design.

---

## Executive Summary
- Iteration 1+2 created a coherent inventory-first model: location-specific stock, append-only movement ledger, atomic transfers, weighted-average valuation, three-role RBAC, online-first MVP.
- Challenging the model produced no fatal contradictions. Key architectural anchors (stock=product+location; movement immutability; transfer atomicy) remain sound and defensible for both pilots.
- Main remaining unknowns: offline needs (U001), scale targets (U003), import volume (U004), and pilot-specific workflows (Arrupe accountability U007, grocery counting U008).
- Recommendation: Validate unknowns with pilot scoping immediately. Proceed to architecture after that.

---

## What Survived Unchanged
1. Inventory-first principle (D001)
2. Product + Location identity for stock (D006)
3. Movement ledger with typed movements (D007)
4. Atomic Transfer model (D008)
5. Receipt costs immutable; weighted-average valuation with drill-down (D009,D010)
6. Three-role RBAC (D005)

These are foundational; design and documentation assume and preserve them.

---

## What Changed or Was Strengthened by Validation
- Online-first vs offline: made explicit as a validated assumption (A005) to be rechecked with pilots (previously ambiguous).
- CSV import: deferred but added clear acceptance path for urgent pilot needs (A010/U004).
- Non-functional requirements: added explicit atomicity/consistency and backup requirements (NFRs added).

---

## Problems Found (Gaps & Risks)
1. **Offline risk (High impact)** — If pilots need offline, architecture must change significantly. Classification: Must resolve before wide roll-out.
2. **Scale undefined (Medium-High impact)** — Performance design needs SKU and transaction volume; collect pilot estimates before implementation.
3. **Onboarding friction (Medium)** — Manual opening balances could be onerous for large catalogs; CSV import may need prioritization for some pilots.
4. **Permission nuance (Low-Medium)** — Three roles may be insufficient for complex institutions; monitor pilot feedback.
5. **Error/conflict UX unspecified (Medium)** — Concurrency and partial-failure UX needs explicit design (alerts, retry semantics).
6. **Cost correction path (Low)** — While costs are immutable, a formal revaluation/adjustment flow needs documenting for auditors.

---

## Test Scenarios & Findings (select highlights)
- Inventory-without-sales: Tenga remains useful. Movements, counts, reconciliation, and valuation operate independently of sales. No functional dependency on POS found.
- Future POS activation: Inventory can accept POS events as Issue movements; Inventory remains owner of stock state. Integration design constraints added.
- Failure modes (partial success, crash, concurrency): Requirements require atomicity and rollback. NFRs specify transactional integrity, but implementation must ensure DB-level transactions and conflict handling.

---

## Architectural Implications
- Use a transactional datastore with ACID guarantees for movements and balances.
- Maintain a StockMovement ledger (append-only) and a StockBalance cache updated transactionally.
- Provide import/export endpoints and idempotency keys for external integrations.
- Keep offline sync as an explicit future feature—avoid design choices that make future sync impossible (e.g., soft-rewrites of movement history).

---

## Major Risks
1. Offline requirement appears late (Risk priority: High). Mitigation: pilot connectivity survey; if any pilot requires offline, promote offline support to high-priority pre-MVP work.
2. Performance at scale (Risk priority: Medium). Mitigation: early benchmarking with representative datasets.
3. Compliance/regulatory needs in some jurisdictions (Risk priority: Medium). Mitigation: ask pilots about legal retention requirements.

---

## Recommended Next Steps (Immediate)
1. Run pilot scoping questionnaires covering U001, U003, U004, U006, U007, U008, U010.
2. Draft technical architecture focusing on ACID datastore, transaction model for movements, and API design for integration with idempotency.
3. Define detailed error and concurrency UX flows (conflict resolution, negative balance handling, partial failure recovery).
4. Prepare CSV import utility spec if pilot data volumes warrant.
5. Codify cost correction policy (document required actions and reporting for corrections).

---

## Final Readiness Assessment
- Condition to proceed to Iteration 3 (architecture): **Yes**, provided pilot scoping answers the listed unknowns (particularly offline & scale). If scoping uncovers offline necessity, pause and re-evaluate scope/cost.

---

Prepared by: Tenga Inventory DERIVE + CHALLENGE agent
Date: 2026-08-20

