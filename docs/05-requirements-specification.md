# Tenga Inventory — Requirements Specification

## Purpose

This document catalogs all functional requirements for Tenga Inventory MVP, derived from Iteration 1 decisions and Iteration 2 domain analysis. Every requirement traces to a business requirement, user need, or system consequence established in earlier phases.

## Requirement Format

Each requirement includes:

- **Requirement ID** — Unique identifier (REQ-XXX)
- **Category** — Functional area
- **Description** — What the system must do
- **Derived From** — Which business/domain decision(s)
- **Priority** — Must / Should / Could / Deferred
- **User** — Who needs this
- **Expected Behaviour** — What the system does
- **Related Requirements** — Dependencies and related items
- **Acceptance Criteria** — How to verify completion

---

## REQ-001 — Create Product

**Category:** Product Management

**Description:** Users can create a product with required fields (name, SKU, unit of measure, category) and optional fields (barcode, cost per unit, minimum/reorder level).

**Derived From:** BR-003, D003

**Priority:** Must

**User:** Owner/Admin, Manager

**Expected Behaviour:**
- Create Product form accepts: name (required), SKU (required, unique per organization), unit (required), category (required), barcode (optional), cost (optional), minimum stock level (optional).
- System validates SKU uniqueness within the organization.
- On save, product exists and is ready to receive stock.

**Related Requirements:** REQ-002, REQ-014

**Acceptance Criteria:**
- Product can be created with only name, SKU, unit, category.
- SKU uniqueness is enforced.
- Optional fields can be omitted without error.
- Product persists and appears in inventory.

---

## REQ-002 — Search and Filter Products

**Category:** Product Management

**Description:** Users can search and filter the product list by name, SKU, category, or other attributes.

**Derived From:** BR-009

**Priority:** Must

**User:** All roles

**Expected Behaviour:**
- Search box accepts partial SKU or product name.
- Filters available by category, unit, minimum stock level status.
- Results update live or on submit.

**Related Requirements:** REQ-001, REQ-009, REQ-010

**Acceptance Criteria:**
- Search by SKU finds product by partial match.
- Search by name finds product.
- Filter by category works.
- Results are usable for further actions (receive, transfer, adjust).

---

## REQ-003 — View Product Details

**Category:** Product Management

**Description:** Users can view all product information, including current stock per location, cost history, and recent movements.

**Derived From:** BR-003, BR-005

**Priority:** Must

**User:** All roles

**Expected Behaviour:**
- Product detail screen shows: name, SKU, unit, category, cost, minimum level, current stock per location, valuation, cost history, recent 20 movements.
- Locations and movements are linked and navigable.

**Related Requirements:** REQ-001, REQ-011, REQ-012, REQ-028

**Acceptance Criteria:**
- Current stock per location is displayed correctly.
- Movements list shows type, quantity, location, user, date, reason.
- Cost history is accessible.

---

## REQ-004 — Define Locations

**Category:** Locations

**Description:** Users can define locations (store, department, storeroom, shelf) where stock is held. Locations can be organized hierarchically or flat.

**Derived From:** BR-004, D006

**Priority:** Must

**User:** Owner/Admin

**Expected Behaviour:**
- Admin can create locations with a name and optional description.
- Locations can be organized as a simple list or shallow hierarchy (e.g., Store > Floor > Shelf).
- Stock is always assigned to a specific location.

**Related Requirements:** REQ-005, REQ-008, REQ-017

**Acceptance Criteria:**
- Location can be created.
- Location can be used in stock movement workflows.
- Multiple products can have stock at the same location.

---

## REQ-005 — Receive Stock

**Category:** Stock Movements

**Description:** Users can record stock receipt—new stock entering a location—with optional cost.

**Derived From:** BR-002, BR-005, BR-007, D007, D009

**Priority:** Must

**User:** Owner/Admin, Manager, Staff

**Expected Behaviour:**
- Receive form: Product (required), Location (required), Quantity (required, positive), Cost (optional, per unit or total), Reason (optional, e.g., "Supplier delivery"), Reference (optional, e.g., "Invoice #123"), Date (pre-filled, editable).
- On submit, creates StockMovement of type Receipt.
- Stock balance at that location increases.
- Cost is recorded immutably on the movement.

**Related Requirements:** REQ-008, REQ-011, REQ-015, REQ-022

**Acceptance Criteria:**
- Receipt is recorded without cost; system does not invent a cost.
- Receipt is recorded with cost; average cost is updated.
- Stock balance reflects receipt.
- Movement appears in product history.

---

## REQ-006 — Issue Stock

**Category:** Stock Movements

**Description:** Users can record stock leaving a location (usage, sale, disposal, etc.).

**Derived From:** BR-002, BR-005, D007

**Priority:** Must

**User:** Owner/Admin, Manager, Staff

**Expected Behaviour:**
- Issue form: Product (required), Location (required), Quantity (required, positive), Reason (required, e.g., "Damaged", "Loss", "Usage"), Reference (optional), Date (pre-filled, editable).
- On submit, creates StockMovement of type Issue.
- Stock balance at location decreases.
- Quantity cannot exceed available stock at location (or system warns and allows override with reason).

**Related Requirements:** REQ-008, REQ-011, REQ-015, REQ-022

**Acceptance Criteria:**
- Issue is recorded with reason.
- Stock balance decreases.
- User cannot issue more than available (or accepts override).

---

## REQ-007 — Transfer Stock

**Category:** Stock Movements

**Description:** Users can transfer stock from one location to another in a single atomic operation.

**Derived From:** BR-004, BR-005, D006, D008

**Priority:** Must

**User:** Owner/Admin, Manager

**Expected Behaviour:**
- Transfer form: Product (required), Source Location (required), Destination Location (required, distinct from source), Quantity (required, positive), Reason (optional), Date (pre-filled, editable).
- On submit, creates single StockMovement of type Transfer.
- Source location balance decreases, destination balance increases, in one transactional operation.
- Both effects appear as a single line in movement history.

**Related Requirements:** REQ-008, REQ-011, REQ-015, REQ-022

**Acceptance Criteria:**
- Transfer creates a single movement record.
- Source and destination balances update correctly.
- Movement history shows transfer as one event with both locations.

---

## REQ-008 — Adjust Stock Quantity

**Category:** Stock Movements

**Description:** Users can adjust stock quantity to correct for discrepancies or account for known changes (damage, loss, count corrections, etc.).

**Derived From:** BR-002, BR-005, D007

**Priority:** Must

**User:** Owner/Admin, Manager

**Expected Behaviour:**
- Adjust form: Product (required), Location (required), Quantity Change (required, +/-, e.g., +5 or -3), Reason (required, e.g., "Count correction", "Damage found"), Reference (optional), Date (pre-filled, editable).
- On submit, creates StockMovement of type Adjustment.
- Stock balance at location changes by the specified amount.
- Reason is recorded immutably.

**Related Requirements:** REQ-005, REQ-006, REQ-011, REQ-015, REQ-022

**Acceptance Criteria:**
- Adjustment is recorded with reason.
- Stock balance changes by the specified amount.
- Reason is visible in movement history.

---

## REQ-009 — Perform Stock Count

**Category:** Stock Counting

**Description:** Users can initiate a stock count, record physical quantities observed, and create a pending count for review and reconciliation.

**Derived From:** BR-006, D007

**Priority:** Must

**User:** Owner/Admin, Manager, Staff

**Expected Behaviour:**
- Start Count: User selects location (required) or product scope (required) and starts a count session.
- Record Count: For each product/location, user enters physical quantity observed.
- Save Count: Count is saved as a pending Count record with timestamp, user, location, and line items (product, location, counted quantity, expected quantity from system).
- Count can be reviewed before reconciliation or discarded.

**Related Requirements:** REQ-010, REQ-011, REQ-015, REQ-022

**Acceptance Criteria:**
- Count can be started and items recorded.
- Count compares physical vs system quantities.
- Count status is visible (pending/reconciled).

---

## REQ-010 — Reconcile Stock Count

**Category:** Stock Counting

**Description:** Users can review a pending count and reconcile differences by creating adjustment movements.

**Derived From:** BR-006, D007

**Priority:** Must

**User:** Owner/Admin, Manager

**Expected Behaviour:**
- Reconcile view shows pending count with differences highlighted (expected vs physical).
- User can approve each difference or make line-item adjustments.
- On reconciliation, for each differing line item, a StockMovement of type CountCorrection is created with the difference and a reference to the count.
- Count status changes to Reconciled.

**Related Requirements:** REQ-009, REQ-011, REQ-015, REQ-022

**Acceptance Criteria:**
- Reconciliation creates one CountCorrection movement per differing line.
- Stock balances reflect the count.
- Count status is updated to Reconciled.

---

## REQ-011 — View Movement History

**Category:** Movement History

**Description:** Users can view the complete append-only movement history for a product, location, or date range.

**Derived From:** BR-005, D005, D007, D009

**Priority:** Must

**User:** All roles

**Expected Behaviour:**
- Movement History view (product-scoped or org-wide) shows: Movement type, Product, Location(s), Quantity, Cost (if present), Reason, Reference, User, Timestamp.
- Movements are displayed in reverse chronological order.
- Movements are immutable from the UI (no edits, deletions).
- Corrections appear as separate Adjustment/CountCorrection movements with explicit reason.

**Related Requirements:** REQ-003, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010

**Acceptance Criteria:**
- Movement history is complete and accurate.
- Movements cannot be edited or deleted.
- Corrections create separate movements.

---

## REQ-012 — Calculate and Display Stock Valuation

**Category:** Inventory Valuation

**Description:** System computes inventory valuation using weighted-average cost and displays current value per product and in aggregate.

**Derived From:** BR-007, D004, D009, D010

**Priority:** Must

**User:** Owner/Admin, Manager

**Expected Behaviour:**
- Valuation Calculation: For each product, compute average cost = sum(receipt quantities × receipt cost) / total received quantity.
- Valuation Display: Show per-product current value = quantity × average cost. Show aggregate inventory value.
- Cost History: Allow drill-down to see receipt-by-receipt cost history and how average was computed.
- Cost is optional; products without cost show quantity only, no valuation.

**Related Requirements:** REQ-005, REQ-001, REQ-003

**Acceptance Criteria:**
- Weighted average is correctly computed.
- Display shows current value and aggregate value.
- Drill-down shows cost history.

---

## REQ-013 — Manage Users and Roles

**Category:** User Management

**Description:** Admin users can create and manage user accounts with role assignments (Owner/Admin, Manager, Staff).

**Derived From:** BR-008, D005

**Priority:** Must

**User:** Owner/Admin

**Expected Behaviour:**
- User Management view allows: Create user (email/username, assign role), Edit user (change role), Deactivate user, View user activity log.
- Three roles available: Owner/Admin (full control), Manager (operational control), Staff (day-to-day operations).
- User roles determine action permissions (see REQ-014–REQ-019).

**Related Requirements:** REQ-014, REQ-015, REQ-016, REQ-017, REQ-018, REQ-019

**Acceptance Criteria:**
- User can be created with role.
- Role-based permissions are enforced.
- User activity is logged.

---

## REQ-014 — Role: Owner/Admin Permissions

**Category:** User Management

**Description:** Owner/Admin role has unrestricted access to all system functions.

**Derived From:** BR-008, D005

**Priority:** Must

**User:** Owner/Admin

**Expected Behaviour:**
- Owner/Admin can: create/edit/delete products, create/manage locations, create/manage users, receive/issue/transfer/adjust stock, perform/reconcile counts, view all reports and valuation, access audit trail, configure system settings (future).

**Related Requirements:** REQ-013, REQ-015, REQ-016, REQ-017

**Acceptance Criteria:**
- Owner/Admin can perform all actions without restriction.

---

## REQ-015 — Role: Manager Permissions

**Category:** User Management

**Description:** Manager role has operational control: manage stock but not system configuration or users.

**Derived From:** BR-008, D005

**Priority:** Must

**User:** Manager

**Expected Behaviour:**
- Manager can: view inventory, receive/issue/transfer/adjust stock, perform/reconcile counts, view movement history and reports, view valuation.
- Manager cannot: create products or locations (Owner/Admin only), create or manage users, access system settings.

**Related Requirements:** REQ-013, REQ-014, REQ-016

**Acceptance Criteria:**
- Manager can perform stock operations.
- Manager cannot access user management or system settings.

---

## REQ-016 — Role: Staff Permissions

**Category:** User Management

**Description:** Staff role has day-to-day operational access: record permitted movements and view inventory.

**Derived From:** BR-008, D005

**Priority:** Must

**User:** Staff

**Expected Behaviour:**
- Staff can: view inventory, record assigned stock movements (receive/issue/adjust based on scope), search products, perform assigned counts.
- Staff cannot: create products or locations, delete any records, manage users or settings, edit movement history.

**Related Requirements:** REQ-013, REQ-014, REQ-015

**Acceptance Criteria:**
- Staff can record movements within their scope.
- Staff cannot access restricted functions.

---

## REQ-017 — Audit Trail: Record User Identity on Actions

**Category:** Audit Trail

**Description:** Every meaningful inventory action records the user who performed it, timestamp, and details of the action.

**Derived From:** BR-005, BR-008, D005

**Priority:** Must

**User:** Auditors, Admins, Managers

**Expected Behaviour:**
- Every movement (receipt, issue, transfer, adjust, count correction) records: user ID, username, role, timestamp, action details (product, location, quantity, reason).
- User activity log shows all actions performed by each user, searchable by date/action type.

**Related Requirements:** REQ-011, REQ-013

**Acceptance Criteria:**
- Movement history includes user information.
- User activity log exists and is searchable.

---

## REQ-018 — Audit Trail: Immutable Movement History

**Category:** Audit Trail

**Description:** Movement history is append-only; historical movements cannot be edited or deleted from the UI.

**Derived From:** BR-005, D005, D009

**Priority:** Must

**User:** Auditors, Admins

**Expected Behaviour:**
- UI does not provide edit or delete functions for movements.
- Corrections to errors must be made via explicit corrective movements (Adjustment or CountCorrection type) with documented reason.
- System documentation and UI messaging clarifies this immutability.

**Related Requirements:** REQ-011, REQ-008

**Acceptance Criteria:**
- No edit/delete UI for movements.
- Corrections create new movements.

---

## REQ-019 — Search and Filter by Movement Type

**Category:** Movement History

**Description:** Users can filter movement history by type (Receipt, Issue, Transfer, Adjustment, CountCorrection) to understand specific categories of change.

**Derived From:** BR-005, D007

**Priority:** Should

**User:** Managers, Auditors

**Expected Behaviour:**
- Movement History view includes filter for movement type.
- Filtering shows only movements of selected type(s).

**Related Requirements:** REQ-011

**Acceptance Criteria:**
- Filter by type works.

---

## REQ-020 — Low-Stock Alerts

**Category:** Reporting

**Description:** System identifies and displays items below their minimum stock level.

**Derived From:** BR-009, D003

**Priority:** Must

**User:** Owner/Admin, Manager

**Expected Behaviour:**
- Low-Stock report lists: Product, Current Quantity per Location, Minimum Level, Status (in-stock, low, critical).
- Report can be filtered by location or category.
- List is sortable and exportable.

**Related Requirements:** REQ-001, REQ-003

**Acceptance Criteria:**
- Low-stock report is accurate.
- Items below minimum are flagged.

---

## REQ-021 — Stock by Location Report

**Category:** Reporting

**Description:** Users can view current stock grouped by location.

**Derived From:** BR-009, D006

**Priority:** Must

**User:** All roles (Manager and above for detailed analysis)

**Expected Behaviour:**
- Stock by Location report shows: Location, Products at Location (with quantities), Total Location Value (sum of product values at location).
- Report is filterable by location, category, or product.
- Report shows both quantities and valuation.

**Related Requirements:** REQ-004, REQ-012

**Acceptance Criteria:**
- Report accurately shows stock per location.
- Totals are correct.

---

## REQ-022 — Recent Movements Report

**Category:** Reporting

**Description:** Users can view recent stock movements (last 50–100, configurable) to understand recent activity.

**Derived From:** BR-009

**Priority:** Should

**User:** All roles

**Expected Behaviour:**
- Recent Movements report shows last N movements with: Type, Product, Location(s), Quantity, Reason, User, Timestamp.
- Filterable by product, location, movement type, date range.
- Accessible from product detail or main reports.

**Related Requirements:** REQ-011, REQ-019

**Acceptance Criteria:**
- Recent movements list is accurate and sortable.

---

## REQ-023 — Export Movement History

**Category:** Data Export

**Description:** Users can export movement history to CSV for audit, analysis, or external reporting.

**Derived From:** BR-011

**Priority:** Should

**User:** Owner/Admin, Manager

**Expected Behaviour:**
- Export Movement History function: Select date range, location scope, or product scope. Export as CSV with: Movement ID, Type, Product, Location(s), Quantity, Cost, Reason, Reference, User, Timestamp.
- File is downloadable.

**Related Requirements:** REQ-011, REQ-019

**Acceptance Criteria:**
- Export works and includes all necessary fields.
- File is valid CSV.

---

## REQ-024 — Import Opening Balances

**Category:** Data Import

**Description:** Users can import initial product and stock balance data via CSV to seed the system.

**Derived From:** BR-011, U004

**Priority:** Should

**User:** Owner/Admin

**Expected Behaviour:**
- Import Balances function accepts CSV with: Product Name, SKU, Unit, Category, Location, Quantity, Cost (optional).
- System validates each row and reports errors/warnings.
- On confirmation, creates products and opening-balance movements.
- Opening balance movements are recorded with type OpeningBalance and associated with an import batch reference.

**Related Requirements:** REQ-001, REQ-004, REQ-005

**Acceptance Criteria:**
- CSV is parsed correctly.
- Opening balances are created as movements.
- Errors are reported clearly.

---

## REQ-025 — Organization / Tenancy

**Category:** Multi-Organization

**Description:** System supports multiple organizations (one per installation instance or SaaS tenant). Each organization has independent products, locations, users, and movements.

**Derived From:** BR-003

**Priority:** Must

**User:** System Admin

**Expected Behaviour:**
- On first login, user selects or creates organization.
- All data (products, locations, movements, users) is scoped to organization.
- SKU uniqueness is per-organization, not global.
- Users belong to an organization.

**Related Requirements:** REQ-001, REQ-004, REQ-013

**Acceptance Criteria:**
- Organizations are isolated.
- SKU uniqueness is per-organization.

---

## REQ-026 — Dashboard / Quick Status

**Category:** Reporting

**Description:** Users see a quick overview of inventory status on first login (MVP: simple, post-MVP: customizable).

**Derived From:** PRD, BR-009

**Priority:** Could

**User:** All roles

**Expected Behaviour:**
- Dashboard shows (MVP): Total inventory value, Count of products, Low-stock items count, Recent movements (5–10).
- Dashboard is read-only and updates periodically or on refresh.

**Related Requirements:** REQ-020, REQ-021, REQ-022, REQ-012

**Acceptance Criteria:**
- Dashboard loads and displays key metrics.

---

## REQ-027 — Backup and Data Durability

**Category:** Data Management

**Description:** System provides reliable backup and recovery mechanisms to ensure data is not lost.

**Derived From:** Feasibility Study, BR-005

**Priority:** Must

**User:** System Admin, Owner/Admin

**Expected Behaviour:**
- Automated daily backups of all data (products, movements, users, counts).
- Backup retention and recovery process documented.
- Admin can manually trigger backup/export.

**Related Requirements:** REQ-023

**Acceptance Criteria:**
- Backup is performed automatically.
- Backup can be tested/verified.

---

## REQ-028 — Cost History for Product

**Category:** Inventory Valuation

**Description:** Users can view the cost history for a specific product, showing how average cost has changed over time as new receipts were recorded.

**Derived From:** BR-007, D010

**Priority:** Should

**User:** Owner/Admin, Manager

**Expected Behaviour:**
- Product detail shows: Current Average Cost, List of receipts with cost and date, Computation of weighted average shown step-by-step or graphically.

**Related Requirements:** REQ-012, REQ-003

**Acceptance Criteria:**
- Cost history is accurate.
- Weighted average computation is clear.

---

## REQ-029 — Barcode Scanning (Future)

**Category:** Stock Movements

**Description:** Users can scan product barcodes to speed up data entry for receipts, issues, and counts.

**Derived From:** BR-003

**Priority:** Deferred

**User:** Staff, Manager

**Expected Behaviour:**
- Barcode input field in movement forms accepts barcode scan via barcode reader.
- Barcode lookup returns product; quantity and location are then required.

**Related Requirements:** REQ-005, REQ-006, REQ-007, REQ-008, REQ-009

**Acceptance Criteria:**
- Deferred to post-MVP.

---

## REQ-030 — Batch/Lot Tracking (Future)

**Category:** Inventory Valuation

**Description:** System tracks individual batches or lots of stock separately, enabling FIFO/LIFO costing and expiry tracking.

**Derived From:** D004

**Priority:** Deferred

**User:** Owner/Admin, Manager

**Expected Behaviour:**
- Deferred; MVP uses weighted average only.

**Related Requirements:** REQ-012

**Acceptance Criteria:**
- Deferred to post-MVP when pilots demand batch/expiry tracking.

---

## Summary: Requirements by Priority

### Must (MVP)
REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014, REQ-015, REQ-016, REQ-017, REQ-018, REQ-020, REQ-021, REQ-025, REQ-027

### Should (Post-MVP / If Time)
REQ-019, REQ-022, REQ-023, REQ-024, REQ-028

### Could
REQ-026

### Deferred (Future)
REQ-029, REQ-030

---

## Requirement Dependency Graph

```
Create Product (REQ-001)
  ↓
Receive Stock (REQ-005)
  ↓
View Movement History (REQ-011)
  ↓
Calculate Valuation (REQ-012)

Define Locations (REQ-004)
  ↓
Transfer Stock (REQ-007)
  ↓
View Stock by Location (REQ-021)

Perform Count (REQ-009)
  ↓
Reconcile Count (REQ-010)
  ↓
Adjust Stock (REQ-008)
  ↓
Movement History (REQ-011)

Manage Users (REQ-013)
  ↓
Role-based Permissions (REQ-014, REQ-015, REQ-016)
  ↓
Audit Trail (REQ-017, REQ-018)
```

---

## Next Steps

1. Use these requirements to derive detailed use cases.
2. Develop business rules for each operation.
3. Define UX progression and onboarding.
4. Apply the MVP dependency test to confirm scope.
