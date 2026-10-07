# Tenga Inventory — Final Decision Ledger

This ledger consolidates all decisions (Iteration 1–3), marks confidence, consequences, and whether the decision is expensive to reverse.

---

## D001 — Inventory-first
- Decision: Inventory-first; no POS/accounting required for core workflows.
- Derived from: Project charter; user input.
- Confidence: High
- Consequences: Avoid POS/accounting features in MVP; integration as optional future work.
- Reversibility: Reversible; integration can be added later with effort.

---

## D002 — Pilot Targets
- Decision: Two pilot segments: institutional (Arrupe) and small grocery shops.
- Confidence: High
- Consequences: Product must satisfy both accountability and high-SKU operations.
- Reversibility: Reversible but affects UX decisions.

---

## D003 — MVP Capability Bundle
- Decision: Items, Locations, Movements, Counts, History, Valuation (weighted-average), Users (3 roles), Basic reports.
- Confidence: High
- Consequences: Scope locked for MVP; many features deferred.
- Reversibility: Partial; adding features later is possible but may require data model extensions.

---

## D004 — Weighted-average valuation
- Decision: Record per-receipt cost; compute weighted average for valuation in MVP.
- Confidence: High
- Consequences: Movement records require optional cost; valuation code must be deterministic.
- Reversibility: Reversible (support FIFO/LIFO later), but migration path must be planned.

---

## D005 — Three-role RBAC
- Decision: Owner/Admin, Manager, Staff; no granular permissions in MVP.
- Confidence: High
- Consequences: Simpler UX; possible under-support for complex institutions.
- Reversibility: Reversible with increased complexity (post-MVP).

---

## D006 — Stock is location-specific
- Decision: Stock identity is Product + Location; global totals derived by summation.
- Confidence: High
- Consequences: Locations are first-class; all balances stored per (product,location).
- Reversibility: Expensive to reverse if implemented differently; foundational.

---

## D007 — Semantic movement types
- Decision: Movements are typed (OpeningBalance, Receipt, Issue, Transfer, Adjustment, CountCorrection).
- Confidence: High
- Consequences: Movement semantics guide validation and UX; single StockMovement model is used.
- Reversibility: Moderate; changes possible but will affect audit and UI flows.

---

## D008 — Transfers are atomic
- Decision: Transfer is one atomic event affecting source and destination.
- Confidence: High
- Consequences: Simplifies audit trail and user mental model.
- Reversibility: Expensive in data model change; keep.

---

## D009 — Receipt cost locked
- Decision: Cost at receipt is immutable; corrections via new movements.
- Confidence: High
- Consequences: Auditable costs; need mechanism for cost correction (post-MVP).
- Reversibility: Moderate; changing may break audits.

---

## D010 — Valuation drill-down
- Decision: Show headline valuation (weighted average) and allow movement-level drill-down.
- Confidence: High
- Consequences: Users trust numbers while having access to the underlying receipts.
- Reversibility: Easy; UI change.

---

## Derived decisions during validation
- D011 (Validation): MVP is online-first; offline deferred pending pilot validation.
  - Confidence: Medium
  - Consequence: Offline sync not designed in MVP; impacts users with poor connectivity.
  - Action: Validate with pilot onboarding.

- D012 (Validation): CSV import for opening balances deferred to post-MVP unless pilot requires it.
  - Confidence: Medium
  - Consequence: Onboarding may take longer for large catalogs.
  - Action: Collect pilot data sample.

---

## Decision Confidence Guide
- High: Strong user input or vital to product principle.
- Medium: Reasonable but requires pilot validation.
- Low: Speculative or future-looking; avoid implementing until validated.

---

## Expensive-to-reverse decisions
- Stock-is-location-specific (D006)
- Transfers-atomic (D008)
- Movement immutability approach (D007, D009)

These should be considered architectural anchors; change only with strong evidence.

---

## Next Review
- Revisit decisions D011, D012 after pilot scoping and initial onboarding.

