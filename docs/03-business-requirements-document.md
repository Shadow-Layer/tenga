# Tenga Inventory — Business Requirements Document (BRD)

## Overview
Derived from Iteration 1 decisions (D001–D005). The BRD describes what the business needs Tenga Inventory to accomplish and why.

## Priority legend
- Must — required for MVP
- Should — important but can be post-MVP
- Could — optional
- Deferred — future

## BR-001 — Inventory-first (Must)
Category: Product philosophy
Description: The system must provide core inventory capabilities without requiring sales, invoices, suppliers, or accounting.
Origin: Decision D001
User: Institutional managers, shop owners, staff
Expected behaviour: Users can perform all core inventory workflows independently of POS/accounting.
Acceptance: Pilots complete core workflows without enabling/using POS or accounting features.

## BR-002 — Core inventory loop (Must)
Category: Inventory management
Description: Support the create → place → move → count → reconcile → history loop as primary workflows.
Origin: Decision D003
User: Stock keepers, managers, staff
Expected behaviour: Users can create items, receive stock, issue/transfer stock, start and apply counts, and view movement history.
Acceptance: The core loop runs end-to-end in pilot sites.

## BR-003 — Product model (Must)
Category: Product management
Description: Items must include name, SKU/code, optional barcode, unit of measure, category, optional cost, and minimum/reorder level.
Origin: User input
User: Item managers
Expected behaviour: Items can be created/edited; cost is optional; SKU uniqueness enforced per org.
Acceptance: Items created in pilots contain required fields and allow optional cost.

## BR-004 — Locations (Must)
Category: Locations
Description: Locations hierarchy (store, department, storeroom, shelf) must be supported. Stock belongs to a specific location.
Origin: Decision D003
User: Inventory staff, managers
Expected behaviour: Users assign stock to locations; transfers move stock between locations with history recorded.
Acceptance: Transfers and location-level stock queries work in pilots.

## BR-005 — Movements & audit (Must)
Category: Movement history
Description: All stock changes must be recorded as movements with reason/reference, date, and user. Movements are append-only from UI; corrections are recorded as corrective movements.
Origin: Decision D003, D005
User: Auditors, admins, staff
Expected behaviour: History shows who did what and when; no silent edits to past movements.
Acceptance: Pilot users can see movement history and perform corrective movements.

## BR-006 — Stock counts (Must)
Category: Stock counting
Description: Allow starting a stock count, recording physical quantities, comparing expected vs actual, and applying reconciliations as movements.
Origin: Decision D003
User: Stock counters, managers
Expected behaviour: Counts can be saved as pending, reviewed, and reconciled into movements.
Acceptance: Pilots perform at least one reconciliation cycle with recorded movements.

## BR-007 — Valuation & costing (Must)
Category: Inventory valuation
Description: Record movement costs; compute item average unit cost (weighted average) for inventory valuation. Cost is optional per item.
Origin: Decision D004
User: Managers, owners
Expected behaviour: Receipts accept optional cost; UI shows average cost and inventory value (qty × avg cost).
Acceptance: Pilots can view valuation and understand cost basis.

## BR-008 — Roles & accountability (Must)
Category: User management
Description: Implement Owner/Admin, Manager, and Staff roles. Actions record user identity and required metadata.
Origin: Decision D005
User: Admins, managers, staff
Expected behaviour: Role restrictions enforce capabilities; every movement includes who/when/reason.
Acceptance: Role-based flows function in pilots; audit trail includes user info.

## BR-009 — Search & basic reports (Must)
Category: Reporting
Description: Basic queries: search/filter items, stock by location, low-stock list, recent movements, inventory value.
Origin: User input
User: Managers, owners
Expected behaviour: Users can discover items and see actionable lists (e.g., low-stock).
Acceptance: Pilots use reports to perform replenishment or accountability tasks.

## BR-010 — Exclusions (Must)
Category: Scope
Description: The following are explicitly not required in MVP: POS, customers, invoices, supplier/purchase workflows, accounting integrations, granular RBAC, complex dashboards.
Origin: Decision D003
User: Product and engineering
Expected behaviour: MVP does not implement these features; any references in UI/documentation are absent.
Acceptance: Feature list and product builds do not include excluded areas.

## BR-011 — Data import/export (Should)
Category: Operational
Description: Support CSV import of opening balances and export of movement history for audits.
Origin: Operational needs
User: Admins, adopters migrating from spreadsheets
Expected behaviour: Admins can import initial items and balances via CSV; export movement history.
Acceptance: Pilot sites can import an initial sample dataset.

## Dependencies & notes
- BR-007 depends on movement records storing optional cost.
- BR-005 and BR-006 depend on immutable movement history semantics.

---
Next: derive use cases and acceptance tests from these business requirements.
