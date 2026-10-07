# Tenga Inventory — Discovery Summary (Iteration 1)

## What we established
- Inventory-first is a core product principle: Tenga Inventory must be useful without POS/accounting (D001).
- Primary pilots: Arrupe Jesuit University (institutional) and 2–5 small grocery shops (commercial) to validate contrasting workflows (D002).
- MVP required capability bundle: items, locations, stock quantities, movements, counts, adjustments, basic valuation (weighted average), basic roles, audit trail, search/reporting (D003, D004, D005).

## What we learned
- The minimum useful inventory loop can be extremely simple and still valuable: Create item → place stock → move stock → count → reconcile → understand history.
- Recording movement-level cost while computing valuation via weighted average preserves future options without forcing complexity.
- Simple role model (Owner/Admin, Manager, Staff) gives accountability without excessive permission management.

## What we derived
- Movement history must be append-only from the UI to ensure accountability; mistakes are corrected by corrective movements.
- Cost should be optional per item and recorded at receipt; valuation uses weighted average.
- MVP must prioritize UX for both single-owner shops (easy Owner-only path) and institutions with departmental structures.

## What remains unknown
- Offline requirements and sync strategy (U001).
- Whether cost should be mandatory for commercial receipts (U002).
- Concrete SKU and throughput targets for grocery pilots to validate performance (U003).
- Data import expectations for opening balances (U004).

## What changed
- Clarified exclusions: no POS, no accounting, no supplier/purchase workflows in MVP.
- Confirmed three-role RBAC instead of granular permissions.

## Consequences
- Product, BRD, and PRD will avoid POS/accounting vocabulary and treat integrations as optional/future.
- UX design must create two friendly onboarding paths (single-owner shops vs institutions).
- Movement storage must preserve per-movement cost and user metadata.

## Next steps
1. Review and confirm Iteration 1 documents.
2. Address unknowns with pilot questionnaires (connectivity, SKU counts, import samples).
3. Proceed to Iteration 2 (DERIVE) after confirmation.

---
Files created in session workspace: decision-ledger.md, assumption-register.md, unknowns-register.md, discovery-summary.md, and the four primary documents (01–04).
