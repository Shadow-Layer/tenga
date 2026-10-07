# Tenga Inventory — MVP Scope Definition

## Purpose

This document applies the **MVP Dependency Test** to every requirement and feature, determining what is included in MVP, what is deferred, and why.

The dependency test: A feature is MVP only if it is:
1. **Foundational** — Required by multiple other features, or
2. **Required by another MVP feature**, or
3. **Necessary for data integrity**, or
4. **Necessary for the core workflow**, or
5. **Required for the product's stated promise** (inventory-first, standalone, auditable).

---

## The MVP Dependency Test

### Core Workflow (Non-negotiable MVP)

The minimum viable product must support the entire core inventory loop without external systems:

```
Create Product
    ↓
Place Stock (Receive)
    ↓
Move Stock (Transfer, Issue, Adjust)
    ↓
Count Stock (Physical Count)
    ↓
Reconcile (Compare & Correct)
    ↓
View History (Audit Trail)
```

Any feature that breaks this chain must be MVP.

Any feature that is useful but not in this chain is deferred unless it's foundational to multiple workflows.

---

## Requirements Scope Assessment

### REQ-001 — Create Product

**Classification:** MUST (MVP)

**Reasoning:** Foundational. No inventory exists without products.

**Dependency:** Required by every other requirement.

**Status:** MVP. Include basic fields (name, SKU, unit, category); optional fields (cost, minimum, barcode) are optional but included for completeness without extra complexity.

---

### REQ-002 — Search and Filter Products

**Classification:** MUST (MVP)

**Reasoning:** Necessary for core workflow. Users must find products quickly to receive/issue/transfer stock.

**Dependency:** Required by REQ-005, REQ-006, REQ-007, REQ-008.

**Status:** MVP. Simple search (name, SKU) and basic filters (category). Advanced filters (custom fields) deferred.

---

### REQ-003 — View Product Details

**Classification:** MUST (MVP)

**Reasoning:** Core workflow. Users must see what they have, where, and history.

**Dependency:** Enables UC-009 (View Product History & Valuation).

**Status:** MVP. Display current stock per location, recent movements, valuation. Drill-down to cost history included (required for trust).

---

### REQ-004 — Define Locations

**Classification:** MUST (MVP)

**Reasoning:** Core architectural requirement. Stock is location-specific (D006). No stock without locations.

**Dependency:** Required by REQ-005, REQ-006, REQ-007, REQ-008.

**Status:** MVP. Simple location creation and management (flat or shallow hierarchy). Bulk location import can be post-MVP.

---

### REQ-005 — Receive Stock

**Classification:** MUST (MVP)

**Reasoning:** Core workflow. Essential for introducing stock into system.

**Dependency:** Required by valuation, movement history, and counting.

**Status:** MVP. Required fields: Product, Location, Quantity. Optional: Cost, Reason, Reference. Date pre-filled.

---

### REQ-006 — Issue Stock

**Classification:** MUST (MVP)

**Reasoning:** Core workflow. Stock leaves the system for various reasons (usage, damage, loss).

**Dependency:** Required for realistic inventory management and loss accounting.

**Status:** MVP. Required fields: Product, Location, Quantity, Reason. Optional: Reference.

---

### REQ-007 — Transfer Stock

**Classification:** MUST (MVP)

**Reasoning:** Core workflow. Needed for both pilots: Arrupe (inter-department), Grocery (shelf replenishment).

**Dependency:** Required to answer "Where did this stock go?"

**Status:** MVP. Atomic transfer between locations (one movement with both effects).

---

### REQ-008 — Adjust Stock Quantity

**Classification:** MUST (MVP)

**Reasoning:** Core workflow. Necessary to correct discrepancies discovered via counts or physical observations.

**Dependency:** Enables count reconciliation and loss accounting.

**Status:** MVP. Required reason field; optional reference.

---

### REQ-009 — Perform Stock Count

**Classification:** MUST (MVP)

**Reasoning:** Core workflow. Essential for comparing physical vs system.

**Dependency:** Required for reconciliation and audit confidence.

**Status:** MVP. Start count, record observations, save as pending.

---

### REQ-010 — Reconcile Stock Count

**Classification:** MUST (MVP)

**Reasoning:** Core workflow. Closes the loop: count → adjust → reconcile.

**Dependency:** Completes the core inventory loop.

**Status:** MVP. Review differences, create CountCorrection movements, update balances.

---

### REQ-011 — View Movement History

**Classification:** MUST (MVP)

**Reasoning:** Core workflow & audit trail requirement. "What happened?" is central to auditable inventory.

**Dependency:** Required by BR-005, BR-D001 (audit requirements); required to answer "How did we get here?"

**Status:** MVP. Full movement history, immutable, searchable by product/location/date.

---

### REQ-012 — Calculate and Display Stock Valuation

**Classification:** MUST (MVP)

**Reasoning:** Product's stated promise (D004). Weighted-average valuation is a core MVP requirement.

**Dependency:** Required by valuation reports and inventory value metrics.

**Status:** MVP. Weighted-average calculation, display per-product and aggregate, drill-down to cost history.

---

### REQ-013 — Manage Users and Roles

**Classification:** MUST (MVP)

**Reasoning:** Foundational for any multi-user system. Three-role model required (D005).

**Dependency:** Enables REQ-014, REQ-015, REQ-016 (permissions); required for audit trail (who did what).

**Status:** MVP. Create users, assign roles, deactivate users.

---

### REQ-014 — Role: Owner/Admin Permissions

**Classification:** MUST (MVP)

**Reasoning:** Three-role model requires this role (D005).

**Dependency:** Enables system administration.

**Status:** MVP. Full access to all operations.

---

### REQ-015 — Role: Manager Permissions

**Classification:** MUST (MVP)

**Reasoning:** Three-role model requires this role (D005). Needed for institutional pilots (department managers).

**Dependency:** Enables manager-level oversight without full admin access.

**Status:** MVP. Receive/issue/transfer/adjust/count/reconcile; no user/product/location management.

---

### REQ-016 — Role: Staff Permissions

**Classification:** MUST (MVP)

**Reasoning:** Three-role model requires this role (D005). Needed for operational staff (warehouse, departments).

**Dependency:** Enables delegation of work without full system access.

**Status:** MVP. Receive/issue/adjust/count; no transfers (manager approval), no system settings.

---

### REQ-017 — Audit Trail: Record User Identity on Actions

**Classification:** MUST (MVP)

**Reasoning:** Inventory-first principle requires accountability. "Who did what?" is core audit requirement (D005, BR-D001).

**Dependency:** Required for every movement (REQ-005–REQ-010).

**Status:** MVP. Every movement records user, timestamp, action details.

---

### REQ-018 — Audit Trail: Immutable Movement History

**Classification:** MUST (MVP)

**Reasoning:** Append-only ledger is a core product principle (D005, D009). Non-negotiable for audit.

**Dependency:** Required to prevent silent edits and ensure accountability.

**Status:** MVP. Movements cannot be edited/deleted; corrections via explicit corrective movements.

---

### REQ-019 — Search and Filter by Movement Type

**Classification:** SHOULD (Post-MVP)

**Reasoning:** Nice to have. Doesn't break core workflow without it; auditors can manually review history.

**Dependency:** Optional enhancement to movement history view.

**Status:** Post-MVP. Can be added after initial pilot feedback.

---

### REQ-020 — Low-Stock Alerts

**Classification:** MUST (MVP)

**Reasoning:** Necessary for core operational value. Pilots need to know when to replenish.

**Dependency:** Required by both pilot use cases (operational alerting).

**Status:** MVP. Display low-stock items; simple threshold-based alerts. Email/SMS notifications are post-MVP.

---

### REQ-021 — Stock by Location Report

**Classification:** MUST (MVP)

**Reasoning:** Core reporting need. Pilots must answer "What stock is where?"

**Dependency:** Required to provide per-location visibility (especially for Arrupe departments).

**Status:** MVP. Show quantity and value per location, filterable.

---

### REQ-022 — Recent Movements Report

**Classification:** SHOULD (Post-MVP)

**Reasoning:** Useful but not critical. Core history view (REQ-011) provides this; report is convenience.

**Dependency:** Optional; REQ-011 (movement history) serves the same information need.

**Status:** Post-MVP. Can be added after core reporting is validated.

---

### REQ-023 — Export Movement History

**Classification:** SHOULD (Post-MVP)

**Reasoning:** Important for audits and external analysis; not essential for MVP pilots to operate.

**Dependency:** Supports audit use case; not required for daily operation.

**Status:** Post-MVP. Can be added in first iteration post-pilot based on demand.

---

### REQ-024 — Import Opening Balances

**Classification:** SHOULD (Post-MVP)

**Reasoning:** Useful for onboarding; manual entry is slower but sufficient for MVP. Pilots can enter opening balances via Receive movements.

**Dependency:** Optional enhancement to reduce setup time.

**Status:** Post-MVP. Manual entry works for MVP; CSV import post-pilot for faster scale.

---

### REQ-025 — Organization / Tenancy

**Classification:** MUST (MVP)

**Reasoning:** Foundational for multi-organization support. SKU uniqueness per-organization requires this.

**Dependency:** Required by every other requirement (all data scoped to organization).

**Status:** MVP. Single organization per instance or SaaS multi-tenancy support. Required for data isolation.

---

### REQ-026 — Dashboard / Quick Status

**Classification:** COULD (MVP if time; deferred acceptable)

**Reasoning:** Nice to have. Doesn't block any core workflow; useful for engagement.

**Dependency:** Optional; view individual reports separately.

**Status:** Deferred. Post-MVP if time; initial pilots can use reports individually.

---

### REQ-027 — Backup and Data Durability

**Classification:** MUST (MVP)

**Reasoning:** Essential for any production system. Pilots must trust data is safe.

**Dependency:** Non-negotiable for pilot confidence and data protection.

**Status:** MVP. Automated daily backups, documented recovery process.

---

### REQ-028 — Cost History for Product

**Classification:** SHOULD (MVP, but could be post-MVP)

**Reasoning:** Important for valuation trust; drill-down in REQ-012 provides this information. Separate detailed view is enhancement.

**Dependency:** Supports REQ-012 (valuation); included as drill-down by default.

**Status:** MVP (as drill-down detail in product view). Detailed cost history timeline view is post-MVP enhancement.

---

### REQ-029 — Barcode Scanning

**Classification:** DEFERRED (Future)

**Reasoning:** Speed enhancement; not necessary for MVP. Manual product selection works.

**Dependency:** Optional; doesn't affect core workflow.

**Status:** Post-MVP. Phase 2 if pilots request speed improvements.

---

### REQ-030 — Batch/Lot Tracking

**Classification:** DEFERRED (Future)

**Reasoning:** Adds complexity (expiry, FIFO/LIFO). Weighted average with per-unit cost is sufficient for MVP.

**Dependency:** Optional; would require significant data model changes.

**Status:** Post-MVP. Can be added if pilots (especially food/pharma) require it.

---

## Features by Classification

### MVP (Included in First Release)

| Feature | Requirements |
|---------|--------------|
| **Product Management** | REQ-001, REQ-002, REQ-003 |
| **Location Management** | REQ-004 |
| **Stock Movements** | REQ-005, REQ-006, REQ-007, REQ-008 |
| **Stock Counting** | REQ-009, REQ-010 |
| **Movement History** | REQ-011 |
| **Valuation** | REQ-012, REQ-028 (as drill-down) |
| **User Management** | REQ-013, REQ-014, REQ-015, REQ-016 |
| **Audit Trail** | REQ-017, REQ-018 |
| **Reporting** | REQ-020, REQ-021 |
| **Organization/Tenancy** | REQ-025 |
| **Data Protection** | REQ-027 |

**Total MVP Requirements:** 22 Must + 0 Should = 22 features

---

### Post-MVP (Phase 2, if time/demand)

| Feature | Requirements | Reason |
|---------|--------------|--------|
| Movement type filters | REQ-019 | Nice to have; manual filtering suffices |
| Recent movements report | REQ-022 | Convenience; history view covers need |
| CSV export | REQ-023 | Important for audits; manual export suffices initially |
| CSV import (opening balances) | REQ-024 | Speeds onboarding; manual entry works for MVP |
| Dashboard | REQ-026 | Engagement; individual reports sufficient |
| Cost history detail view | REQ-028 | Drill-down provides this; detail view is enhancement |

**Total Post-MVP Requirements:** 6 Should

---

### Deferred (Future, No Priority)

| Feature | Requirements | Reason |
|---------|--------------|--------|
| Barcode scanning | REQ-029 | Speed enhancement; manual entry works |
| Batch/lot tracking | REQ-030 | Complex; only needed if pilots require expiry/FIFO |

**Total Deferred Requirements:** 2 Future

---

## MVP Dependency Test: Summary

### Core Workflow Coverage

✓ **Create Product** (REQ-001) — MVP ✓
  ↓
✓ **Place Stock** (REQ-005, Receive) — MVP ✓
  ↓
✓ **Move Stock** (REQ-006, REQ-007, REQ-008, Issue/Transfer/Adjust) — MVP ✓
  ↓
✓ **Count Stock** (REQ-009) — MVP ✓
  ↓
✓ **Reconcile** (REQ-010) — MVP ✓
  ↓
✓ **View History** (REQ-011) — MVP ✓

**Result: Core workflow is complete in MVP.** ✓

---

### Foundational Features (Required by Multiple)

✓ **Search Products** (REQ-002) — Required by Receive, Issue, Transfer, Adjust, Count
  → MVP ✓

✓ **Product Details** (REQ-003) — Required for users to understand current state
  → MVP ✓

✓ **Locations** (REQ-004) — Required by all stock movements
  → MVP ✓

✓ **Valuation** (REQ-012) — Required for inventory value reporting and pilot confidence
  → MVP ✓

✓ **User Management** (REQ-013-016) — Required for multi-user and audit trail
  → MVP ✓

✓ **Audit Trail** (REQ-017-018) — Required for accountability promise
  → MVP ✓

---

### Nice-to-Have (Not Required for Core Workflow)

✗ **Movement Type Filters** (REQ-019) — Manual filtering works
  → Post-MVP

✗ **Recent Movements Report** (REQ-022) — History view provides info
  → Post-MVP

✗ **CSV Export** (REQ-023) — Important for audits but not blocking
  → Post-MVP

✗ **CSV Import** (REQ-024) — Manual entry slower but works
  → Post-MVP

✗ **Dashboard** (REQ-026) — Engagement; reports sufficient
  → Deferred/Nice-to-Have

✗ **Barcode Scanning** (REQ-029) — Speed enhancement
  → Deferred

✗ **Batch/Lot Tracking** (REQ-030) — Complexity; only if needed
  → Deferred

---

## MVP Feature List (Final)

### Core Capabilities

1. **Products:** Create, search, view details, optional edit
2. **Locations:** Create, manage, view stock per location
3. **Stock Movements:** Receive, Issue, Transfer, Adjust (all with user/timestamp/reason)
4. **Stock Counts:** Start, record, reconcile (creates CountCorrection movements)
5. **Movement History:** Full append-only ledger, immutable, searchable by product/location/date
6. **Valuation:** Weighted-average cost display, drill-down to cost history
7. **Users & Roles:** Three-role model (Owner/Admin, Manager, Staff) with permission enforcement
8. **Audit Trail:** User identity on all actions, immutable history
9. **Reports:** Low-stock list, stock by location, inventory value summary
10. **Organization:** Multi-organization support with data isolation
11. **Data Protection:** Automated backups, recovery process

### MVP Non-Functional Requirements

- **Performance:** Lists and queries remain responsive with thousands of products
- **Data Integrity:** Movements and balances transactionally consistent
- **Security:** Authentication, role-based access control, data isolation
- **Reliability:** Data backup and recovery; graceful error handling

---

## Scope Boundaries (What's NOT MVP)

### Explicitly Out of Scope

✗ POS or sales workflows
✗ Customers or invoicing
✗ Supplier or purchase orders
✗ Accounting integrations
✗ Fiscal/tax reporting
✗ Granular RBAC (per-location, per-product permissions)
✗ Complex dashboards or analytics
✗ Barcode scanning (hardware integration)
✗ Batch/lot tracking or expiry dates
✗ Multiple costing methods (FIFO, LIFO, ABC)
✗ Offline sync (online-first)
✗ Mobile app (web-first, responsive)
✗ API or third-party integrations
✗ Email/SMS notifications
✗ Scheduled alerts

These are documented as Future/Deferred to avoid scope creep and keep focus.

---

## MVP Success Criteria

Iteration 2 is complete when:

✓ All 22 MVP requirements are fully specified.
✓ Each requirement traces to a business problem and user need.
✓ Core inventory loop is complete and defensible (Create → Place → Move → Count → Reconcile → History).
✓ Deferred features are documented with clear reasoning.
✓ Both pilots (Arrupe, grocery) can operate with MVP scope.
✓ No deferred feature is essential to pilot operation.

---

## Handoff to Iteration 3

MVP Scope Definition is the input to Technical Architecture:

- Requirements spec → User stories & acceptance tests
- Use cases → Screen design & flows
- Domain model → Database schema & API design
- Business rules → Validation logic & constraints
- UX requirements → Visual design & interaction patterns
- MVP scope → Sprint planning & feature prioritization

Next phase: Architecture & Design (Iteration 3).
