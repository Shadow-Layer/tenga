# Tenga Inventory — System Model (Plain Language)

## Purpose
A succinct, non-technical model describing inputs, state, operations, history, outputs, boundaries, and integrations.

---

## Inputs (what people put into Tenga)
- Product definitions: name, SKU, unit, category, optional barcode, optional cost, optional minimum level.
- Locations: physical places where stock is held (store, storeroom, department, shelf).
- Stock movements: Receipts, Issues, Transfers, Adjustments, CountCorrections (each with product, location(s), quantity, date, user, reason, optional cost).
- Counts: observed quantities captured in a Count session.
- Users & roles: Owner/Admin, Manager, Staff.

---

## State (what Tenga knows)
- Products (metadata per org).
- Locations (hierarchy/flat list per org).
- StockBalance per (Product, Location): current quantity (derived but cached).
- StockMovement ledger: immutable chronological list of all movements.
- Counts: recorded count sessions and their status.
- Users and roles.
- Organization context (tenant scope).

---

## Operations (what users can do)
- Create products and locations.
- Receive stock (create Receipt movement).
- Issue stock (create Issue movement).
- Transfer stock (atomic Transfer movement affecting two locations).
- Adjust stock (Adjustment movement with reason).
- Start and record Counts; reconcile counts (creates CountCorrection movements).
- View movement history and product details (stock per location, valuation).
- Manage users and assign roles (Owner/Admin only).

---

## How State Changes (the ledger model)
- Every operation that affects stock creates a StockMovement record.
- StockBalance for a (product,location) is updated atomically when a movement is created.
- Movement records are append-only and immutable in UI; corrections are new movements.
- Valuation is computed from receipts with cost; cost is immutable per receipted movement.

---

## History (how Tenga explains past changes)
- Movement ledger answers: who did what, when, where, why, and how much.
- Users can drill down from product to movement list and receipt cost lines to reproduce valuation calculations.

---

## Outputs (what users learn)
- Current stock per location, global totals derived by summation.
- Recent movement list and full history per product or location.
- Low-stock lists based on minimum levels.
- Inventory valuation (weighted average) and drill-down into costs.
- Exportable movement history for audits.

---

## Boundaries (what Tenga does not own)
- Sales: POS is external; Inventory remains independent and receives sales as Issue movements if integrated.
- Accounting: Inventory provides data exports; accounting systems own financial ledgers.
- Procurement: Purchase orders, suppliers; Inventory records receipts but does not manage purchasing workflows in MVP.
- Offline sync and multi-device reconciliation: Deferred to post-MVP unless pilots require earlier.

---

## Integration Surface (future-proofing)
- Stable identifiers (organization_id, product_id, SKU) for mappings.
- Movement ingestion API for external event producers (POS) with idempotency keys.
- CSV import/export for onboarding and audits.
- Read-only endpoints or export services for analytics and accounting.

---

## Domain Invariants (what must always hold)
- StockBalance(P,L) = SUM(StockMovement.quantity WHERE product=P AND location=L).
- Movements are immutable; corrections are new movements.
- Receipt cost, if present, is immutable and used for valuation.
- Transfers are atomic across source and destination.

---

## Risks to Explain to Stakeholders
- Offline needs significantly affect architecture and must be validated early.
- Large-scale datasets require careful performance design.
- Changing core entity semantics (e.g., making stock global-first) later is expensive.

---

## One-paragraph summary
Tenga Inventory records every stock change as an immutable movement tied to a product and location; current balances are derived by summing movements (cached for performance). Users receive, move, count, and reconcile stock; the system is inventory-first and remains usable without sales or accounting. Integrations (POS, accounting) are optional and treated as event producers/consumers rather than owners of inventory state.

