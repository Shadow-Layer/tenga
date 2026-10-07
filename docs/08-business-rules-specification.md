# Tenga Inventory — Business Rules Specification

## Purpose

Business rules encode the constraints and logic that govern how the system behaves. For each major domain operation, this document specifies what is allowed, what is required, what is validated, and why.

Rules derive from business decisions (D001–D010) and use cases (UC-001–UC-011).

---

## BR-Rules: Product Management

### BR-P001 — Product Creation

**Rule:** A product must have a unique SKU within its organization.

**Derives from:** BR-003, D006

**Validation:**
- `product.sku` is checked against all existing products in the organization.
- If a duplicate SKU exists, creation is rejected with error: "SKU 'X' already exists for product 'Y'."
- SKU is case-sensitive (or case-insensitive by explicit choice; recommend case-insensitive for usability).

**Rationale:** SKU is the primary identifier for the product historically. Uniqueness prevents confusion and ensures movement history can be traced unambiguously.

---

### BR-P002 — Required Product Fields

**Rule:** A product must include: name, SKU, unit of measure, and category.

**Derives from:** BR-003, UC-001

**Validation:**
- All four fields are required on create.
- Fields cannot be empty strings or null after creation.
- Name and SKU minimum length: 1 character; practical maximum: 255 characters.
- Category can be auto-assigned to a default category if omitted (alternative: required).

**Rationale:** These fields enable identification (name, SKU), quantification (unit), and classification (category).

---

### BR-P003 — Optional Product Fields

**Rule:** Product may have optional: barcode, cost per unit, minimum stock level.

**Derives from:** BR-003, BR-007

**Validation:**
- Barcode: optional, can be empty, or null.
- Cost per unit: optional, must be non-negative if provided (can be 0).
- Minimum stock level: optional, must be non-negative integer if provided.

**Rationale:** Different inventory items have different needs. Barcodes are useful but not required for all items. Cost is optional to support institutions that don't track valuation.

---

### BR-P004 — Product Edits

**Rule:** Product fields can be edited after creation, except SKU.

**Derives from:** D006, BR-P001

**Permitted edits:** name, category, barcode, cost per unit, minimum stock level, is_active (archive/unarchive).

**Forbidden edits:** SKU (is the historical identifier).

**Rationale:** SKU is the primary identifier in movement history. Changing it would require rewriting history. All other fields are metadata that can change without breaking history.

---

### BR-P005 — Product Archival

**Rule:** Products can be archived (is_active=false) but not hard-deleted if movements exist.

**Derives from:** BR-P004, BR-M001

**Validation:**
- Admin can archive a product regardless of movement count.
- Hard deletion is not available in MVP; can be deferred to post-MVP or admin tools only.
- Archived products: do not appear in normal product lists; movements and history remain queryable.

**Rationale:** Maintains historical integrity. Movement history must remain traceable; deleting a product would break audit trail.

---

## BR-Rules: Stock Movement and Balance

### BR-M001 — Movement Immutability

**Rule:** Once created, a StockMovement cannot be edited or deleted from the UI.

**Derives from:** BR-005, D005, D009, D018

**Validation:**
- No edit or delete UI is provided for movements.
- API (if exposed) rejects edit/delete requests on existing movements.
- System raises an audit alert if direct database edits are detected (future monitoring).

**Rationale:** Append-only ledger ensures accountability and auditability. Mistakes are corrected via corrective movements (Adjustment or CountCorrection), not by editing the original.

---

### BR-M002 — Movement Type Semantics

**Rule:** Each StockMovement type has specific validation rules and metadata requirements.

**Derives from:** D007, UC-002, UC-003, UC-004, UC-005, UC-008

**Type: OpeningBalance**
- Used only during system initialization or CSV import to establish starting quantities.
- No corresponding real-world event (synthetic entry to bootstrap system).
- Quantity can be positive or negative (though negative opening is unusual).

**Type: Receipt**
- Stock entering a location from external source (supplier, donation, transfer-in).
- Quantity must be positive.
- Cost per unit is optional; if provided, is used for valuation.
- Location is required.
- Reason and reference are optional.

**Type: Issue**
- Stock leaving a location for known reason (sale, damage, loss, usage, disposal).
- Quantity must be positive (stored as negative internally to indicate outflow).
- Reason is required (e.g., "Damage", "Loss", "Expired", "Usage").
- Location is required.
- Reference is optional.

**Type: Transfer**
- Stock moves from source location to destination location.
- Source location and destination location are both required and must be different.
- Quantity must be positive.
- Single movement with both location effects (atomically).
- Reason is optional (e.g., "Replenishment", "Relocation").
- Reference is optional.

**Type: Adjustment**
- Stock quantity changed to correct discrepancies or account for adjustments.
- Quantity change can be positive (+) or negative (-); must be non-zero.
- Reason is required (e.g., "Count correction", "Damage found", "Inventory loss").
- Location is required.
- Reference is optional.

**Type: CountCorrection**
- Adjustment created as a result of count reconciliation.
- Quantity is the difference (observed - expected); can be +/-.
- Reason is "Physical count" (fixed).
- Reference is the Count ID (e.g., "Count #C-001").
- Location is required.
- Automatically created; not directly entered by users.

**Rationale:** Semantic types make audit trail clear and enable type-specific validation.

---

### BR-M003 — Movement Date

**Rule:** StockMovement.created_at is set to the system time at creation and is immutable.

**Derives from:** BR-005, D009

**Validation:**
- System captures current timestamp automatically on creation.
- Users can set a logical date (e.g., receipt date), but system timestamp is independent.
- Editing date after creation is not permitted (immutability).

**Rationale:** System timestamp provides true ordering of events; logical date reflects business event date.

---

### BR-M004 — Movement User Identity

**Rule:** Every movement records the user who created it.

**Derives from:** BR-008, D005

**Validation:**
- User ID, username, and role are captured at movement creation.
- This information is immutable.

**Rationale:** Accountability. Auditors must know who performed each action.

---

### BR-M005 — Cost Lock on Receipt

**Rule:** Receipt movement cost, once set, cannot be changed.

**Derives from:** BR-007, D009

**Validation:**
- UI does not permit editing the cost on an existing receipt.
- API rejects cost edit requests.
- If cost correction is needed, user creates an Adjustment movement with reason "Cost correction" or similar (post-MVP: could have a Cost Correction type).

**Rationale:** Historical cost is immutable to preserve audit trail and prevent silent revaluation.

---

### BR-M006 — Balance Cache Consistency

**Rule:** StockBalance for (Product, Location) is updated atomically with every movement.

**Derives from:** D006, BR-M001

**Validation:**
- Every movement creation triggers a StockBalance update.
- StockBalance.updated_at is set to movement.created_at.
- StockBalance.last_movement_id is set to the movement ID (for audit).
- Updates are transactional: movement created AND balance updated, or both rolled back.

**Invariant:** StockBalance[P,L].quantity = SUM(movements where product=P, location=L)

**Rationale:** Balance cache enables fast queries. Transactional consistency prevents race conditions.

---

### BR-M007 — Quantity Constraints for Issue

**Rule:** Issue quantity cannot exceed available balance; system warns but may allow override.

**Derives from:** UC-003

**Validation:**
- When user enters issue quantity, system checks: quantity ≤ StockBalance[Product, Location].quantity.
- If quantity > balance:
  - **MVP strict mode:** Reject and show error "Insufficient stock. Available: 150, Requested: 160."
  - **MVP lenient mode:** Show warning "Quantity exceeds balance. Continue?" and allow override if confirmed.
  - (Recommend lenient mode to allow for small discrepancies or adjustments.)

**If override:** Balance can go negative; negative balances are flagged in reports and UI for investigation.

**Rationale:** Prevents accidental over-issues; negative balances indicate a data integrity problem that needs investigation.

---

## BR-Rules: Stock Counting and Reconciliation

### BR-C001 — Count Scope

**Rule:** A count must specify a scope: one location, one product, or full inventory.

**Derives from:** UC-006

**Validation:**
- Scope is required when starting a count.
- Valid scopes: specific location (required), specific product (optional, across all locations), full inventory.
- Count generates line items for all products (if full inventory) or products at the specified location.

**Rationale:** Enables both full and partial counts. Arrupe might count one department; grocery might count one shelf.

---

### BR-C002 — Count Line Item Comparison

**Rule:** For each product in count scope, system compares expected (from system) to observed (from physical count).

**Derives from:** UC-006

**Validation:**
- Expected quantity is the StockBalance[Product, Location] at count start time.
- Observed quantity is what the user entered physically.
- Difference = Observed - Expected (can be +/-, 0).

**Rationale:** The comparison reveals discrepancies. Difference of 0 = no adjustment needed.

---

### BR-C003 — Count Approval

**Rule:** A pending count must be reviewed and approved before reconciliation.

**Derives from:** UC-007

**Validation:**
- Count starts as "Pending".
- Manager or Admin can review and move to "Approved" or "Rejected".
- "Rejected" count is discarded; no adjustments created.
- "Approved" count can proceed to reconciliation.

**Rationale:** Two-person control. Initial counter enters data; manager verifies before adjustments are applied.

---

### BR-C004 — Reconciliation Creates Adjustment Movements

**Rule:** When a count is reconciled, each differing line creates a CountCorrection movement.

**Derives from:** UC-008, D007

**Validation:**
- For each CountLineItem where difference ≠ 0:
  - Create StockMovement with type=CountCorrection.
  - Quantity = difference (Observed - Expected).
  - Reason = "Physical count".
  - Reference = Count ID.
  - Update StockBalance[Product, Location] with quantity change.
- All reconciliation movements are created atomically (all or none).

**Rationale:** Count reconciliation is an adjustment operation. Recording as CountCorrection movements ensures full audit trail and distinguishes count-driven changes from manual adjustments.

---

### BR-C005 — Count Status Workflow

**Rule:** Count status follows a defined workflow: Pending → Approved → Reconciled (or Rejected at any point before Approved).

**Derives from:** UC-006, UC-007, UC-008

**Validation:**
- Pending: User can edit line items or save as pending.
- Approved: Count moves to "ready for reconciliation". Cannot be edited, only reconciled or rejected.
- Reconciled: Adjustments created; count is closed.
- Rejected: Count is abandoned; no adjustments created.

**Rationale:** Workflow enforces the intended sequence: count → review → reconcile.

---

## BR-Rules: Transfers

### BR-T001 — Transfer Atomicity

**Rule:** A transfer is a single atomic operation affecting two locations.

**Derives from:** D008, UC-004

**Validation:**
- Transfer movement creates one record with source_location_id and destination_location_id.
- Both StockBalance updates (source -, destination +) happen in one transaction.
- If either update fails, entire transfer is rolled back.

**Rationale:** Atomic transfers are clearer for audit and prevent partial transfers.

---

### BR-T002 — Transfer Location Difference

**Rule:** Source and destination locations must be different.

**Derives from:** UC-004

**Validation:**
- If source_location_id == destination_location_id, system rejects with error "Source and destination must be different."

**Rationale:** A transfer to the same location is a no-op; not a meaningful operation.

---

### BR-T003 — Transfer Quantity Constraints

**Rule:** Transfer quantity must be positive and ≤ source balance.

**Derives from:** UC-004

**Validation:**
- Quantity > 0.
- Quantity ≤ StockBalance[Product, Source Location].
- If violated, system shows error or allows override (similar to BR-M007).

**Rationale:** Ensures source has sufficient stock; allows override if needed to correct an imbalance.

---

## BR-Rules: Locations

### BR-L001 — Location Uniqueness

**Rule:** Location name is unique within organization.

**Derives from:** BR-004

**Validation:**
- Location.name is checked against all locations in the organization.
- If duplicate, creation is rejected with error "Location 'Shop Floor' already exists."

**Rationale:** Prevents confusion. Locations are identified by name in UI.

---

### BR-L002 — Location Hierarchy (Optional)

**Rule:** Locations can have a parent-child relationship (optional), enabling simple hierarchy.

**Derives from:** BR-004

**Validation:**
- Location.parent_location_id is optional.
- If set, must reference an existing location in the same organization.
- Circular references are prevented (a location cannot be its own ancestor).

**Rationale:** Supports organizational structures (Store > Department > Shelf) while remaining optional.

---

### BR-L003 — Location Archival

**Rule:** Locations can be archived but not deleted if movements reference them.

**Derives from:** BR-L001

**Validation:**
- Admin can archive a location (is_active=false).
- Hard deletion not available if movements exist (enforced at DB or app layer).
- Archived locations: do not appear in normal location lists; movements and history remain queryable.

**Rationale:** Historical integrity. Movements reference locations; deleting would break audit trail.

---

## BR-Rules: Valuation

### BR-V001 — Weighted Average Cost Calculation

**Rule:** Inventory value per product is calculated as: (SUM of receipt quantities × receipt costs) / SUM of all receipt quantities.

**Derives from:** BR-007, D004, D010

**Formula:**

```
Average Cost = SUM(Receipt.quantity * Receipt.cost_per_unit) / SUM(Receipt.quantity)
              where Receipt.cost_per_unit is not null
```

**Inventory Value = StockBalance[Product].quantity * Average Cost**

**Validation:**
- Only Receipt movements with cost_per_unit are included.
- If no receipts with cost exist, Average Cost is undefined; value shown as "N/A" or "0" (by choice).
- Divisor (SUM receipt quantity) must be > 0 to compute average (safe check).

**Rationale:** Weighted average is simple, standard, and fair across variable-cost receipts.

---

### BR-V002 — Cost is Optional Per Item

**Rule:** Products can be tracked by quantity without cost. Valuation is optional.

**Derives from:** BR-007, A003

**Validation:**
- If a product has no receipt movements with cost, it has no average cost.
- System shows: "Quantity: 100 units. Cost: Not recorded."
- Such items do not contribute to aggregate inventory value (or contribute 0).

**Rationale:** Institutions may not need valuation for all items. Cost should not be forced.

---

### BR-V003 — Cost Locked at Receipt

**Rule:** Receipt cost, once recorded, is immutable and used for all future valuations.

**Derives from:** BR-007, D009, BR-M005

**Validation:**
- Receipt movement cost cannot be edited after creation.
- If cost needs to be corrected, a new Adjustment movement is created (post-MVP feature).

**Rationale:** Preserves historical cost basis for auditability.

---

## BR-Rules: Roles and Permissions

### BR-R001 — Three-Role Model

**Rule:** System implements three roles: Owner/Admin, Manager, Staff.

**Derives from:** BR-008, D005

**Role Capabilities:**

| Action | Owner/Admin | Manager | Staff |
|--------|------------|---------|-------|
| Create/Edit Product | ✓ | ✗ | ✗ |
| Create/Edit Location | ✓ | ✗ | ✗ |
| Manage Users | ✓ | ✗ | ✗ |
| Receive Stock | ✓ | ✓ | ✓ |
| Issue Stock | ✓ | ✓ | ✓ |
| Transfer Stock | ✓ | ✓ | ✗ |
| Adjust Stock | ✓ | ✓ | ✓ |
| Perform Count | ✓ | ✓ | ✓ |
| Reconcile Count | ✓ | ✓ | ✗ |
| View Reports | ✓ | ✓ | ✓ (limited) |
| Export Data | ✓ | ✓ | ✗ |

**Rationale:** Simple enough for single-owner shops (Owner only); complex enough for institutions (Admin/Manager/Staff).

---

### BR-R002 — No Granular Permissions

**Rule:** MVP does not implement per-action or per-resource granular permissions (RBAC).

**Derives from:** BR-008, D005

**Validation:**
- Role is the only access control mechanism.
- Features like "Staff can only see assigned locations" are deferred to post-MVP.

**Rationale:** Simplifies implementation and avoids configuration complexity for MVP.

---

## BR-Rules: Data Integrity and Audit

### BR-D001 — Audit Trail Completeness

**Rule:** Every meaningful inventory action is recorded in StockMovement with user, timestamp, type, and reason.

**Derives from:** BR-005, BR-008

**Validation:**
- Receipt, Issue, Transfer, Adjustment, CountCorrection movements all record: user, timestamp, type, reason (where applicable).
- Movement history is searchable by user, product, location, date, type.

**Rationale:** Enables audits and accountability.

---

### BR-D002 — Organization Isolation

**Rule:** All data is scoped to organization. Users cannot access data from other organizations.

**Derives from:** BR-025

**Validation:**
- Every query includes WHERE organization_id = <current_org>.
- Users are assigned to exactly one organization (MVP; future: cross-org access by role).
- Authentication includes organization context.

**Rationale:** Multi-tenancy security.

---

### BR-D003 — Data Backup and Recovery

**Rule:** System maintains regular backups and can recover to a known state.

**Derives from:** BR-027

**Validation:**
- Automated daily backups are performed.
- Backup procedure is tested regularly.
- Recovery procedure is documented.

**Rationale:** Data durability and loss prevention.

---

## BR-Rules: Practical Constraints

### BR-X001 — Quantity Representation

**Rule:** Stock quantities are integers. Fractional quantities are not supported in MVP.

**Derives from:** D006

**Validation:**
- quantity fields are integers.
- If a product naturally has fractional units (e.g., bulk flour by kg), it should be represented with a larger unit (e.g., grams) to remain an integer.

**Rationale:** Simplifies implementation and avoids floating-point precision issues.

---

### BR-X002 — Currency and Decimal Precision

**Rule:** Cost and valuation values are stored with 2-decimal precision (cents).

**Derives from:** BR-007, D004

**Validation:**
- cost_per_unit field is DECIMAL(10, 2) or equivalent.
- Valuation calculations round to 2 decimals.

**Rationale:** Standard financial practice for currency.

---

### BR-X003 — Negative Balances

**Rule:** Stock balance can become negative if issue is approved over-balance. Negative balances are flagged as anomalies.

**Derives from:** BR-M007

**Validation:**
- Negative balances are allowed (not rejected).
- Negative balances trigger a warning or flag in UI and reports: "Negative balance detected; review required."
- Over-issue requires explicit user confirmation.

**Rationale:** Allows for small discrepancies and missing data corrections. Flags for investigation.

---

## Summary: Business Rules by Domain

| Domain | Rules |
|--------|-------|
| Product | BR-P001–BR-P005 |
| Movement & Balance | BR-M001–BR-M007 |
| Counting & Reconciliation | BR-C001–BR-C005 |
| Transfers | BR-T001–BR-T003 |
| Locations | BR-L001–BR-L003 |
| Valuation | BR-V001–BR-V003 |
| Roles & Permissions | BR-R001–BR-R002 |
| Data Integrity & Audit | BR-D001–BR-D003 |
| Practical Constraints | BR-X001–BR-X003 |

These rules are the foundation for implementation. Every feature and code decision should trace back to a rule.
