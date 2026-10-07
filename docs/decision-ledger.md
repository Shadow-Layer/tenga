# Decision Ledger

## Decision ID: D001
Topic: Inventory-first product principle

Decision: Confirmed — "Inventory-first: Tenga Inventory must be useful without sales, POS, accounting, or ERP"

Reasoning:
- User observation: existing systems force small businesses into broader systems too early.
- Inventory is operationally useful (receiving, counting, moving, adjusting, valuing) without sales.
- Aligns with Tenga philosophy: start with smallest useful capability and reveal complexity later.

Alternatives considered:
- Treat inventory as a subsystem of POS/ERP.
- Hybrid approach that partially exposes POS-related features by default.

Why alternatives were rejected:
- Subsystem approach recreates the problem of forced complexity for users who only need inventory.
- Hybrid approach risks ambiguous UX and scope creep; can be revisited later if concrete needs arise.

Consequences:
- MVP must not require sales/purchases/accounting to operate core inventory workflows.
- Product must support standalone stock operations (products, quantities, locations, movements, counts, adjustments, basic costing) without sales entities.
- Integrations with POS/accounting must be optional and clearly decoupled.
- Documentation, onboarding, and UI should avoid POS/accounting vocabulary by default.

Affected requirements:
- BRD: include explicit requirement that core inventory workflows operate independently.
- PRD: mark sales/purchasing/accounting integrations as Optional or Future.
- Feasibility: evaluate technical implications for decoupling and later integration.

Affected documents:
- Project Charter
- Feasibility Study
- BRD
- PRD

Confidence: High (user explicitly confirmed)

Open questions:
- Which user segments should be prioritized for MVP? (affects exact scope)
- Which inventory capabilities are Required vs Optional in MVP (costing, multi-location, stock valuation)?

Status: Confirmed

---

(Additional decisions will be appended as discovery continues.)

## Decision ID: D006
Topic: Stock is location-specific

Decision: Confirmed — Stock belongs to a location; Product + Location defines a stock balance. There is no primary global pool of stock separate from locations; global totals are derived by summing location balances.

Derived from: BR-004 (Locations), BR-006 (Counts), D002 (pilot needs)

Reasoning:
- Matches Arrupe's accountability model where custody is per department/location.
- Simplifies mental model for staff: stock is where it physically is.
- Avoids allocation/ reservation abstractions for MVP while still allowing aggregated views.

Consequences:
- Inventory queries and counts operate at Product+Location granularity.
- Transfers must move quantity between locations (affecting two balances).
- UI must clearly show per-location balances and derive global totals when needed.

Affected requirements:
- BR-004, BR-006, BR-005, BR-009

Confidence: High (user confirmed)

Open questions:
- None immediate; supports future allocation features if required.

Status: Confirmed

---

## Decision ID: D007
Topic: Semantic movement types

Decision: Confirmed — Movements are typed (Opening Balance, Receipt, Issue, Transfer, Adjustment, CountCorrection). Movements are stored in a single StockMovement entity with a required type field; type governs validation and semantics but not the storage model.

Derived from: BR-005 (Movements & audit), BR-006 (Counts), Decision D006

Reasoning:
- Semantic types improve audit clarity: reviewers can understand "why" a change occurred at a glance.
- Keeps data model simple (single movement table) while enabling type-specific rules and UX.

Consequences:
- Movement records include: type, product, location (single for most types; transfer includes source+destination), quantity (+/-), cost (optional), reason, reference, user, timestamp.
- Validation rules vary by type (e.g., Receipt may require cost input when provided; Opening Balance recorded only during setup/import).

Affected requirements:
- BR-005, BR-006, BR-007, BR-011

Confidence: High (user confirmed)

Status: Confirmed

---

## Decision ID: D008
Topic: Transfers are atomic

Decision: Confirmed — Transfers are recorded as a single atomic StockMovement of type Transfer that affects both source and destination balances in one transactional operation and presents as one event in the UI.

Derived from: D006, D007, BR-005

Reasoning:
- Single-event transfers are easier to audit and match user mental models ("I moved 5 from A to B").
- Avoids the need to later reconcile paired issue/receipt records to find transfers.

Consequences:
- Transfer movement stores source location, destination location, product, quantity, user, timestamp, reason.
- System ensures transactional integrity: either both balances update or none do.
- Movement history displays Transfer as a single line with both effects visible.

Affected requirements:
- BR-004, BR-005

Confidence: High (user confirmed)

Status: Confirmed

---

## Decision ID: D009
Topic: Receipt costs are immutable (locked at receipt)

Decision: Confirmed — When a receipt movement includes a cost, that movement's cost is recorded immutably. Corrections to cost require explicit corrective movements or revaluation processes (post-MVP).

Derived from: BR-007, D004

Reasoning:
- Immutable historical costs improve auditability and prevent silent ledger changes.
- Keeps MVP implementation simple and predictable.

Consequences:
- UI and API must disallow editing the cost on existing receipt movements.
- Provide a documented revaluation/correction path (e.g., corrective movement) for exceptions.

Affected requirements:
- BR-005, BR-007

Confidence: High (user confirmed)

Status: Confirmed

---

## Decision ID: D010
Topic: Valuation display with drill-down

Decision: Confirmed — Inventory valuation uses weighted-average in the UI and shows current total value; users can drill down to movement-level cost history to understand the basis of the average.

Derived from: D004, BR-007

Reasoning:
- Simple headline value satisfies quick needs; drill-down provides necessary auditability and trust for pilots.
- Aligns with the "simple by default, depth when demanded" UX principle.

Consequences:
- Valuation workflows compute weighted-average from receipt movement costs; display per-product value and aggregate total; provide link to movement cost history.
- Movement-level costs remain the source of truth for valuation computations.

Affected requirements:
- BR-007, BR-009

Confidence: High (user confirmed)

Status: Confirmed


## Decision ID: D005
Topic: MVP roles and permissions model

Decision: Confirmed — Implement simple role-based access with three roles: Owner/Administrator, Manager, and Staff. Do NOT implement granular per-action permissions in MVP.

Role summaries:
- Owner / Administrator: Full control; manage items, locations, users, system configuration; receive/issue/transfer/adjust stock; perform/review counts; view reports and valuation.
- Manager: Operational control; view inventory; receive/issue/transfer stock; perform counts and adjustments; view movement history and reports; cannot manage users or system settings.
- Staff: Day-to-day operations; view inventory; record permitted stock movements; perform assigned counts; search items; cannot delete records, manage users, or change settings.

Additional rules:
- All meaningful actions must record who + what + when + quantity + location + reason.
- Movement history and audit trail are append-only from the UI; historical records cannot be deleted or silently edited—corrections must be made via corrective movements.

Reasoning:
- Provides accountability and auditability without the complexity of a granular permissions engine.
- Simplifies onboarding for one-person shops while supporting organizational needs for institutions.

Consequences:
- BRD/PRD must specify role capabilities and audit trail requirements.
- UX must make roles understandable at onboarding and allow a one-person shop to operate as Owner only.
- The system must prevent destructive edits to movement history and provide corrective workflows.

Affected documents:
- Project Charter
- Feasibility Study
- BRD
- PRD

Confidence: High (user explicitly specified)

Open questions:
- Should Admin be allowed to hard-delete test/dummy data in a safe sandbox? (likely deferred)

Status: Confirmed

## Decision ID: D004
Topic: MVP cost tracking and valuation

Decision: Confirmed — Record actual movement/receipt costs and use a weighted average cost method for MVP valuation. Cost tracking should be optional per item.

Reasoning:
- Weighted average balances simplicity and useful valuation for both pilot types (grocery and institutional).
- Recording actual movement costs preserves historical data and allows future support for FIFO, batch costing, expiry, and other methods without rearchitecting the movement history.
- Making cost optional avoids forcing valuation on items where it doesn't apply.

Consequences:
- Movement records must include an optional cost field to capture actual receipt/movement cost.
- The valuation UI and reports should compute inventory value using weighted average unless a user opts into a different method in the future.
- Storage and performance considerations: movement history must be stored efficiently, but detailed lot/serial tracking can be deferred to future capabilities.

Affected requirements:
- BRD: include movement cost field and optional costing per item; define valuation as weighted average for MVP.
- PRD: specify UX for optional cost input on receipts and clear display of average cost and inventory value.
- Feasibility: verify storage and performance implications for movement history at expected SKU/transaction volumes.

Affected documents:
- Project Charter
- Feasibility Study
- BRD
- PRD

Confidence: High (user explicitly selected this approach)

Open questions:
- Should cost be mandatory at receipt entry for commercial pilots, or merely recommended? (affects UX and enforcement)

Status: Confirmed

## Decision ID: D003
Topic: MVP Required capability bundle

Decision: Confirmed — The MVP must implement the following core capabilities:

- Items / Products: name, SKU/code, optional barcode, unit of measure, category, cost, minimum/reorder level
- Locations: store, department, storeroom, shelf/location; stock belongs to a specific location
- Stock quantities: current quantity, available quantity, minimum level, simple low-stock indication
- Stock movements: receive, issue, transfer, adjust; movement history with reason/reference, date and user
- Stock counts: start a count, record physical quantity, compare expected vs actual, apply/reconcile differences
- Basic item history: current stock, movement timeline, previous counts, cost history
- Basic users & accountability: who performed movement/count/adjustment; basic roles/permissions; audit trail
- Basic search & reporting: search/filter inventory, stock by location, low-stock items, recent movements
- Basic stock valuation: simple valuation at a basic level

Decision exclusions (explicitly NOT required in MVP):
- No POS, no customers, no invoices
- No accounting integration
- No supplier management or purchasing workflow
- No complex dashboards or AI features

Reasoning:
- Directly satisfies both pilot needs: institutional accountability and grocery operational volume without forcing POS/ERP concepts.
- Keeps scope focused on the core inventory loop: Create item → put stock somewhere → move stock → count stock → reconcile → understand history.

Consequences:
- BRD and PRD must define the MVP around these capabilities and treat excluded areas as Optional/Future.
- UX design must prioritize a simple core loop and avoid POS/accounting vocabulary by default.
- Technical feasibility should ensure performant handling of many SKUs and an audit trail for movements.

Affected documents:
- Project Charter
- Feasibility Study
- BRD
- PRD

Confidence: High (user explicitly defined required bundle)

Open questions:
- Depth of "basic roles/permissions" for MVP (which actions require authentication/authorization?)
- Granularity of "cost history" (should we store per-receipt cost, average cost, or simple last-cost?)

Status: Confirmed

## Decision ID: D002
Topic: Primary MVP pilot targets

Decision: Confirmed — Prioritize two complementary pilot segments: 1) Institutional inventory (Arrupe Jesuit University) and 2) Small grocery shops (2–5 commercial pilots)

Reasoning:
- These two segments contrast use-cases: accountability-focused institutional inventory and availability-focused commercial inventory.
- Both validate the hypothesis that inventory is useful without sales and demand different UX and workflow emphases.
- Running both pilots provides diverse, high-value feedback about the minimum useful inventory feature set.

Alternatives considered:
- Target only one segment for MVP (institutional or commercial).
- Broader "all small businesses" target.

Why alternatives were rejected:
- Single-segment targeting risks overfitting the product to one workflow and missing cross-cutting requirements.
- Broad targeting increases scope and slows discovery; pilots allow focused validation.

Consequences:
- MVP must support workflows for receiving, issuing/transferring, counting, adjustments, and accountability (who/which department) for institutional use.
- MVP must support high SKU volumes, fast replenishment checks, simple stocktaking, and loss/damage adjustments for grocery use.
- Onboarding and terminology may need small-mode and institutional-mode defaults.

Affected requirements:
- BRD: identify requirements specific to institutional accountability (department ownership, assignment) and grocery operations (fast counts, SKU bulk actions).
- PRD: define MVP capabilities that satisfy both pilots; mark specialized features as Optional or Future.

Affected documents:
- Project Charter
- Feasibility Study
- BRD
- PRD

Confidence: High (user strongly recommends these pilots)

Open questions:
- Which specific workflows for institutional accountability are required (e.g., check-out/check-in to departments, custodian assignment)?
- For grocery pilots, what scale of SKUs and transaction frequency should MVP handle?

Status: Confirmed
