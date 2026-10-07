# Tenga Inventory — Final Assumption Register

This final register lists assumptions, consequences if they are wrong, priority to validate, and validation plan.

---

## A001 — Pilot representativeness (Confirmed)
- Assumption: Arrupe + small groceries represent target market.
- If wrong: Product may overfit and miss larger market needs.
- Validation: Pilot metrics (adoption, retention), surveys.
- Priority: Validate during pilot.

---

## A002 — Weighted average acceptable (Confirmed)
- Assumption: Weighted-average costing is usable for MVP.
- If wrong: Need to implement FIFO/LIFO earlier.
- Validation: Pilot accounting reconciliation and feedback.
- Priority: Validate in first month of pilot operations.

---

## A003 — Cost optional per item (Confirmed)
- Assumption: Some items will have no cost; system must accept that.
- If wrong: Valuation incomplete; consider nudging cost input or making mandatory for some categories.
- Validation: Track % receipts with cost in pilot.
- Priority: Monitor during pilot.

---

## A004 — Three-role RBAC suffices (Confirmed)
- If wrong: May need finer permissions (per-location, per-action).
- Validation: Pilot feedback; incidents where access controls block workflows.
- Priority: Monitor; if >10% of workflows need granular control, consider phase-2.

---

## A005 — Online-first MVP (Proposed)
- Assumption: Online-only is acceptable for pilots.
- If wrong: Some pilot sites may require offline capabilities early.
- Validation: Pilot connectivity questionnaire; early pilot trials.
- Priority: Must validate before broad pilot rollout.

---

## A006 — Location-specific stock (Confirmed)
- Assumption: Product+Location identity is the right model.
- If wrong: Would need allocation/reservation semantics; schema rework costly.
- Validation: Pilot operational fit; ask "Where is it?" during onboarding.
- Priority: High confidence, pilot validation to confirm semantics.

---

## A007 — Atomic transfers (Confirmed)
- If wrong: Accounting/auditors might prefer paired movements; design may need change.
- Validation: Pilot audit feedback.
- Priority: Monitor; low probability of change.

---

## A008 — Costs immutable at receipt (Confirmed)
- If wrong: Provide well-documented correction flow and consider a future cost-correction movement type.
- Validation: Pilot incidents requesting direct edits.
- Priority: Medium.

---

## A009 — Drill-down valuation suffices (Confirmed)
- If wrong: Provide more visibility or alternative valuation methods.
- Validation: Pilot user trust metrics; audit requests.
- Priority: Monitor.

---

## A010 — Manual opening balances acceptable (Proposed)
- If wrong: Implement CSV import prior to larger pilot onboarding.
- Validation: Pilot onboarding durations; site data volume.
- Priority: Validate during pilot scoping.

---

## A011 — Movement history suffices for audits (Proposed)
- If wrong: Provide structured export formats and additional reporting.
- Validation: Pilot audit requests and legal/regulatory checks.
- Priority: Validate for each pilot jurisdiction.

---

## A012 — UX progression supports pilots (Confirmed)
- If wrong: Rebalance default vs advanced controls based on observed user behavior.
- Validation: Usability sessions during pilot onboarding.
- Priority: Ongoing.

---

## Actions
- For Proposed assumptions (A005, A010, A011): prioritize pilot scoping questionnaires before implementation.
- Track assumption validation as part of pilot metrics (create simple validation checklist for each pilot).

