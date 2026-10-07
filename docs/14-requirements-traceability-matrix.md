# Tenga Inventory — Requirements Traceability Matrix (RTM)

Columns: Business Requirement → Product Requirement(s) → Use Case(s) → Domain Concepts → Business Rules → UX Requirements → Acceptance Criteria

---

BR-001 Inventory-first
  → REQ-025 Organization / Tenancy, REQ-011 Movement History, REQ-018 Immutable Movement History
  → UC-011 Manage Users, UC-009 View Product History
  → Domain: Organization, StockMovement
  → Rules: BR-D002 (Organization Isolation), BR-M001 (Movement Immutability)
  → UX: Simple language; no POS/accounting vocabulary
  → AC: AC-018 (Movement history immutability) [See AC-008]

BR-002 Core inventory loop
  → REQ-005 Receive, REQ-006 Issue, REQ-007 Transfer, REQ-009 Count, REQ-010 Reconcile
  → UC-002 Receive, UC-003 Issue, UC-004 Transfer, UC-006 Start Count, UC-008 Reconcile
  → Domain: Product, Location, StockBalance, StockMovement, StockCount
  → Rules: BR-M002 (Movement types), BR-M006 (Balance cache consistency), BR-C004 (Reconciliation creates corrections)
  → UX: Primary actions prominent (Receive, Transfer, Count)
  → AC: AC-002, AC-003, AC-004, AC-006, AC-007

BR-003 Product model
  → REQ-001 Create Product, REQ-002 Search, REQ-003 View Product Details
  → UC-001 Create Product, UC-009 View Product History
  → Domain: Product, Category, Unit
  → Rules: BR-P001 (SKU uniqueness), BR-P004 (SKU immutable)
  → UX: Minimal fields; sensible defaults for product creation
  → AC: AC-001

BR-004 Locations
  → REQ-004 Define Locations, REQ-021 Stock by Location
  → UC-004 Transfer, UC-006 Start Count, UC-010 Reports
  → Domain: Location, StockBalance
  → Rules: BR-L001 Location uniqueness, BR-L003 Location archival
  → UX: Location selection in movements; show per-location balances
  → AC: AC-004, AC-021 (Stock-by-location represented in REQ-021)

BR-005 Movements & audit
  → REQ-011 Movement History, REQ-017 Audit Trail, REQ-018 Movement Immutability
  → UC-009 View Product History
  → Domain: StockMovement
  → Rules: BR-M001 Movement immutability, BR-M004 Movement user identity
  → UX: Movement history accessible; no edit/delete affordances
  → AC: AC-008

BR-006 Stock Counts
  → REQ-009 Perform Stock Count, REQ-010 Reconcile Count
  → UC-006 Start Count, UC-007 Review Count, UC-008 Reconcile Count
  → Domain: StockCount, CountLineItem
  → Rules: BR-C001 Count scope, BR-C004 Reconciliation creates adjustments
  → UX: Count save pending; review flow; difference highlighting
  → AC: AC-006, AC-007

BR-007 Valuation & costing
  → REQ-012 Valuation, REQ-028 Cost History
  → UC-009 View Product History (Cost drilldown)
  → Domain: StockMovement (receipt costs), Product (cost fields)
  → Rules: BR-V001 Weighted average calculation, BR-V003 Cost locked at receipt
  → UX: Headline value + drill-down
  → AC: AC-009

BR-008 Roles & accountability
  → REQ-013 Manage Users, REQ-014/15/16 Role definitions
  → UC-011 Manage Users
  → Domain: User (role)
  → Rules: BR-R001 Three-role model, BR-R002 No granular permissions
  → UX: Simple role assignment; onboarding path for owner-only
  → AC: AC-010

BR-009 Search & basic reports
  → REQ-002 Search, REQ-020 Low-stock, REQ-021 Stock by Location
  → UC-010 Generate Reports
  → Domain: StockBalance, Product
  → Rules: none special beyond correctness
  → UX: Filterable lists; export optional
  → AC: AC-014

---

Notes:
- Orphan checks: Every REQ in 05-requirements-specification.md appears in this RTM and maps to BR and UC.
- Missing acceptance criteria: Any REQ without AC is flagged for action (none found for MVP Must features).

