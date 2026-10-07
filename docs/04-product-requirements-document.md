# Tenga Inventory — Product Requirements Document (PRD)

## Purpose
Translate BRD requirements into product behaviours, UX principles, and an explicit MVP scope. This PRD guides design and implementation while preserving the inventory-first philosophy.

## Product vision statement
Tenga Inventory is the simplest reliable way for organizations and small shops to know what they have, where it is, and what happened to it — without forcing sales or accounting structures. The product reveals complexity only when needed.

## Product principles
- Minimal friction for core loop actions.
- Progressive disclosure: advanced fields/options hidden by default.
- Clear accountability: append-only history and corrective movements.
- Practical valuation: weighted-average for MVP; store receipt costs.

## Core capabilities (MVP)
- Item management (create/edit): required fields (name, SKU, unit, category), optional cost and reorder level.
- Locations: hierarchical or flat locations (store/department/storeroom/shelf) with stock assigned per location.
- Stock movements: receive, issue, transfer, adjust; each movement records user, date, reason, optional cost.
- Stock counts: start count, capture physical qty, compare, reconcile (creates adjustment movements).
- Movement history: searchable timeline per item, location, date range.
- Valuation: average cost, inventory value per item and aggregated.
- Users/roles: Owner/Admin, Manager, Staff with capabilities defined in D005.
- Search & basic reporting: low-stock list, stock by location, recent movements, export options.

## UX and interaction principles
- Primary screen shows quick answers: stock on hand, low-stock indicators, quick actions (receive, move, count).
- Create-item and receive stock are the most prominent entry points for new users.
- Errors are recoverable: corrections are explicit corrective movements with reasons.
- Onboarding offers templates: single-location shop (Owner only) and institutional (departments).

## Acceptance criteria — representative
- Create item flow saves an item and optionally a starting balance.
- Receive flow accepts quantity, location, optional cost, and records a movement.
- Transfer flow reduces source and increases destination and records both sides in a single logical action.
- Count workflow produces a pending count and when applied creates reconciliation movements with reasons.
- Movement history displays who performed actions and is append-only from the UI.

## Non-functional requirements
- Performance: list and movement queries remain responsive with tens of thousands of SKUs and typical movement rates expected in small shops; performance to be validated in feasibility.
- Data integrity: movements and derived balances must be transactional to prevent data races.
- Security: basic authentication and role enforcement as defined in D005.

## MVP scope classification
- MVP: all "Core capabilities" above (per D003).
- Post-MVP / Should: CSV import/export of bulk opening balances, basic offline sync, integration with TengaPOS (decoupled), scheduled low-stock alerts.
- Future / Deferred: FIFO/LIFO costing, lot/serial/expiry tracking, supplier/purchase order management, granular RBAC, complex analytics dashboards.

## Success metrics (pilot-driven)
- Pilot adoption: % of pilot staff completing 10+ movements in first month.
- Task completion: % of attempted counts reconciled successfully.
- Value metric: reported reduction in stockouts or time saved during inventory tasks (qualitative pilot feedback).

## Risks & mitigations (product)
- Scope creep: enforce MVP exclusions in feature planning and sprints.
- Misaligned UX: conduct fast usability sessions during pilot onboarding.

---
Next steps: generate use cases and domain/data requirements from these product requirements (Iteration 2).