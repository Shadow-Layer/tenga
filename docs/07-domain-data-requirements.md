# Tenga Inventory — Domain & Data Requirements

## Purpose

This document defines the conceptual entities and data structures required to support Tenga Inventory. It describes what information the system must know, how entities relate, and what must remain historically true or be allowed to change.

Note: This is NOT a database schema. It's a conceptual data model. Technical schema design is deferred to technical architecture phase.

---

## Core Question: Stock Identity

**Derived from:** D006

**Answer:** Stock is located. The fundamental identity is **(Product, Location)**.

A "stock balance" is:
- How many units of Product X exist at Location Y right now.
- Not a property of the product alone.
- Not a property of the location alone.
- The intersection of both.

**Consequence:** The system must track quantity at this (Product, Location) granularity. Global totals are derived.

---

## Domain Entities

### 1. Organization

**What it represents:** A tenant / business unit. Multi-organization support allows separate Tenga instances or SaaS tenants.

**Why it exists:** Isolation between organizations; SKU uniqueness is per-organization.

**Information required:**
- `organization_id` (UUID)
- `name` (string, required)
- `created_at` (timestamp)

**Related entities:** owns Products, Locations, Users, StockMovements

**What must remain historically true:** Organization name and creation date are immutable (in practice).

**What can change:** Organization configuration (future: time zone, currency, fiscal year).

---

### 2. Product

**What it represents:** An inventory item (also called SKU, line item, good).

**Why it exists:** Core unit of inventory. Everything tracks quantity of products.

**Information required:**
- `product_id` (UUID)
- `organization_id` (FK to Organization)
- `name` (string, required, e.g., "Coca-Cola 500ml")
- `sku` (string, required, unique within organization)
- `barcode` (string, optional)
- `unit_of_measure` (string, required, e.g., "bottle", "box", "unit")
- `category_id` (FK to Category, optional)
- `cost_per_unit` (decimal, optional, in base currency)
- `minimum_stock_level` (integer, optional)
- `is_active` (boolean, default true; allows soft deletion)
- `created_at` (timestamp)
- `created_by_user_id` (FK to User, for audit)
- `updated_at` (timestamp)

**Related entities:**
- Category (many-to-one)
- StockBalance (one-to-many, one for each location)
- StockMovement (one-to-many, all movements for this product)
- StockCount (one-to-many, all counts involving this product)

**What must remain historically true:**
- `sku` cannot change after creation (it's the unique identifier for the product historically).
- Once stock movements exist for a product, the product should not be deleted (archived instead).

**What can change:**
- `name`, `barcode`, `cost_per_unit`, `minimum_stock_level`, `category_id`
- `is_active` (to archive/hide from normal operations)

**Future considerations (not MVP):**
- Batch / lot tracking
- Expiry date
- Serial number
- Images / photos
- Supplier / purchase link

---

### 3. Category

**What it represents:** A classification for products (e.g., "Beverages", "Electronics", "Office Supplies").

**Why it exists:** Allows grouping and filtering; used in reports.

**Information required:**
- `category_id` (UUID)
- `organization_id` (FK to Organization)
- `name` (string, required, unique within organization)
- `description` (string, optional)
- `created_at` (timestamp)

**Related entities:** Products (one-to-many)

**What must remain historically true:** Category name should ideally not change (but can, since it's not a primary identifier).

**What can change:** Description.

---

### 4. Unit

**What it represents:** A unit of measure (e.g., "bottle", "box", "kg", "unit").

**Why it exists:** Clarifies what quantity means (10 bottles vs 10 boxes are different).

**Information required:**
- `unit_id` (UUID)
- `organization_id` (FK to Organization)
- `name` (string, required, unique within organization, e.g., "bottle")
- `abbreviation` (string, optional, e.g., "bott")

**Related entities:** Products (many-to-many via Product.unit_of_measure)

**What must remain historically true:** Unit should not be deleted if products reference it.

**What can change:** Abbreviation (name should ideally not change for historical clarity).

---

### 5. Location

**What it represents:** A physical place where stock is held (e.g., "Shop Floor", "Storeroom", "Finance Department").

**Why it exists:** Stock is location-specific (D006). System must know where things are.

**Information required:**
- `location_id` (UUID)
- `organization_id` (FK to Organization)
- `name` (string, required, unique within organization)
- `description` (string, optional, e.g., "Main retail floor")
- `parent_location_id` (FK to Location, optional; for hierarchy support)
- `is_active` (boolean, default true)
- `created_at` (timestamp)

**Related entities:**
- Parent Location (optional, one-to-one self-reference for hierarchy)
- StockBalance (one-to-many, one for each product)
- StockMovement (one-to-many, all movements from/to this location)
- StockCount (one-to-many, all counts at this location)

**What must remain historically true:** Location structure (name, hierarchy) should not change if movements reference it. Archived locations should be retained for historical accuracy.

**What can change:** Description; `is_active` (can be archived).

**Future considerations:**
- Location capacity / limits
- Location-specific rules (e.g., climate controlled)

---

### 6. StockBalance

**What it represents:** The current quantity of a product at a location.

**Why it exists:** Answers "How much stock do we have?" and "Where is it?" Derived from movements; also maintained as a balance cache for performance.

**Information required:**
- `stock_balance_id` (UUID)
- `product_id` (FK to Product, required)
- `location_id` (FK to Location, required)
- `quantity` (integer, can be 0 or negative)
- `updated_at` (timestamp, when balance was last changed)
- `last_movement_id` (FK to StockMovement, for audit trail and transactional integrity)

**Related entities:** Product, Location, StockMovement

**Source of truth:** Derived from StockMovement history. Current quantity = sum of all movement quantities for (Product, Location).

**Cached for performance:** StockBalance is maintained to answer "current quantity?" quickly. Movements are the true ledger; balance is the cache.

**What must remain historically true:** Movement history is immutable; balance is mutable (always recalculates from movements).

**What can change:** `quantity` (changes with every movement); `updated_at` (changes with every movement).

**Invariant:** StockBalance.quantity = sum(StockMovement.quantity WHERE product_id=X AND location_id=Y).

---

### 7. StockMovement

**What it represents:** A change to stock (receipt, issue, transfer, adjustment, count correction, opening balance).

**Why it exists:** Audit trail. Core ledger. All stock changes are recorded here. Immutable from UI.

**Information required (core):**
- `movement_id` (UUID)
- `organization_id` (FK to Organization)
- `product_id` (FK to Product, required)
- `location_id` (FK to Location, required; for non-transfer types)
- `type` (enum: OpeningBalance, Receipt, Issue, Transfer, Adjustment, CountCorrection)
- `quantity` (integer, signed: positive for in, negative for out, or sign-by-type for transfers)
- `cost_per_unit` (decimal, optional; present for Receipt, optional for others)
- `reason` (string, optional; e.g., "Supplier delivery", "Damage", "Inventory loss")
- `reference` (string, optional; e.g., "Invoice #INV-123", "Count ID #C-001")
- `user_id` (FK to User, required; who performed the action)
- `created_at` (timestamp, required)
- `updated_at` (timestamp, immutable from UI, set on creation)

**Information required (transfer-specific):**
- `source_location_id` (FK to Location, for type=Transfer)
- `destination_location_id` (FK to Location, for type=Transfer)

**Information required (count-specific):**
- `count_id` (FK to StockCount, for type=CountCorrection)

**Related entities:** Product, Location, User, Organization, StockCount

**What must remain historically true:**
- Movement record cannot be edited or deleted after creation (append-only ledger).
- Corrections are made via new Adjustment or CountCorrection movements, not by editing the original.

**What can change:** Nothing (immutable). All fields are set at creation and never modified.

**Historical integrity:**
- Movement captures cost at time of receipt (cost_per_unit at receipt date, not later cost).
- Movement captures user at time of action.
- Movement timestamp is immutable.

**Invariant for Transfers:**
- `quantity` on a Transfer movement affects source location as negative, destination as positive.
- Both location_id updates are atomic (transactionally).

---

### 8. StockCount

**What it represents:** A physical inventory count session (taking physical quantities and comparing to system).

**Why it exists:** Answers "Are our system quantities correct?" and drives reconciliation.

**Information required:**
- `count_id` (UUID)
- `organization_id` (FK to Organization)
- `location_id` (FK to Location, required; which location is being counted)
- `counted_at` (timestamp, when the physical count occurred)
- `created_by_user_id` (FK to User, who initiated the count)
- `status` (enum: Pending, Approved, Reconciled, Rejected)
- `created_at` (timestamp)
- `updated_at` (timestamp)

**Related entities:**
- CountLineItem (one-to-many, the items counted)
- StockMovement (one-to-many, CountCorrection movements created from reconciliation)

**What must remain historically true:** Count record should be retained for audit (even if reconciled).

**What can change:** `status` (from Pending → Approved → Reconciled, or Pending → Rejected).

---

### 9. CountLineItem

**What it represents:** One line in a count (one product at one location, expected vs observed).

**Why it exists:** Details of a count; what was counted and what the discrepancies were.

**Information required:**
- `line_item_id` (UUID)
- `count_id` (FK to StockCount)
- `product_id` (FK to Product)
- `location_id` (FK to Location)
- `expected_quantity` (integer, from StockBalance at time of count start)
- `observed_quantity` (integer, what was physically counted; null if not counted)
- `difference` (integer, calculated: observed - expected)
- `status` (enum: Pending, Approved, Rejected)

**Related entities:** StockCount, Product, Location

**What must remain historically true:** Expected quantity should not change after count creation.

**What can change:** `observed_quantity` (before count is finalized), `status` (Pending → Approved or Rejected).

---

### 10. User

**What it represents:** A person using Tenga Inventory.

**Why it exists:** Authentication, authorization, audit trail.

**Information required:**
- `user_id` (UUID)
- `organization_id` (FK to Organization)
- `email` (string, required, unique within organization)
- `username` (string, optional)
- `full_name` (string, optional)
- `role` (enum: Owner, Admin, Manager, Staff)
- `password_hash` (string, hashed password)
- `is_active` (boolean)
- `created_at` (timestamp)
- `last_login_at` (timestamp, nullable)

**Related entities:** StockMovement (one-to-many, all movements created by this user)

**What must remain historically true:** Email should not change (or if changed, audit why).

**What can change:** Full name, role, is_active.

---

### 11. Organization Settings (Future)

**What it represents:** Configuration specific to an organization (time zone, currency, fiscal year, etc.).

**Why it exists:** MVP doesn't require; deferred for future.

**Anticipated information:**
- `setting_id` (UUID)
- `organization_id` (FK to Organization)
- `timezone` (string, e.g., "UTC", "America/New_York")
- `currency` (string, e.g., "USD", "EUR")
- `fiscal_year_start` (date, e.g., "01-01")

**Status:** Deferred to post-MVP.

---

## Data Relationships

### Cardinality Summary

| Entity | Relationship | Cardinality |
|--------|--------------|-------------|
| Organization | → Products | 1:N |
| Organization | → Locations | 1:N |
| Organization | → Users | 1:N |
| Product | → Category | N:1 (optional) |
| Product | → StockBalance | 1:N (one per location) |
| Location | → StockBalance | 1:N (one per product) |
| (Product, Location) | → StockBalance | 1:1 |
| StockBalance | → StockMovements | 1:N |
| Product | → StockMovements | 1:N |
| Location | → StockMovements | 1:N |
| User | → StockMovements | 1:N |
| Location | → StockCounts | 1:N |
| StockCount | → CountLineItems | 1:N |
| StockMovement | → CountLineItem (for type=CountCorrection) | N:1 (optional) |

---

## Source of Truth Exercise

For each major piece of information, identify the source of truth:

### "How many units of Product X are at Location Y right now?"

**Source of Truth:** StockBalance table (cached).

**Derivable From:** Sum of all StockMovement quantities for (Product X, Location Y).

**Why cached:** Performance. Computing from movements on every query would be slow at scale.

**Transactional Guarantee:** Every movement atomically updates the corresponding StockBalance.

---

### "What is the average cost per unit for Product X?"

**Source of Truth:** All Receipt movements with cost_per_unit for Product X.

**Computed As:** (Sum of Receipt.quantity × Receipt.cost_per_unit) / Sum of all Receipt.quantity

**Updated On:** Every Receipt movement that includes cost.

**Historical accuracy:** Cost reflects the point-in-time cost at receipt date; immutable after.

---

### "Who did what, when, and why?"

**Source of Truth:** StockMovement table (created_by_user_id, created_at, type, reason, reference).

**Immutable:** Yes. Movement records cannot be edited or deleted.

**Corrections:** Made via new movements of type Adjustment or CountCorrection, not by editing the original.

---

### "Is stock below minimum level?"

**Source of Truth:** StockBalance.quantity vs Product.minimum_stock_level.

**Computed On Demand:** In reports and alerts.

---

### "What's the total inventory value?"

**Source of Truth:** All (StockBalance.quantity × weighted_average_cost) for all (Product, Location) pairs.

**Weighted Average Cost:** Derived from Receipt movements with cost.

**Immutable After Receipt:** Cost locked at receipt; no retroactive revaluation in MVP.

---

## Key Data Invariants

### Invariant 1: StockBalance Consistency

```
StockBalance[Product=X, Location=Y].quantity 
  == SUM(StockMovement.quantity 
         WHERE product_id=X AND location_id=Y AND type IN (Receipt, Issue, Transfer, Adjustment, CountCorrection))
```

**Enforcement:** Database constraint or application-layer validation before every movement.

---

### Invariant 2: Movement Immutability

```
StockMovement records cannot be edited or deleted after creation.
Corrections are made via new movements.
```

**Enforcement:** Application layer (no UI for edit/delete). Database constraints (if available).

---

### Invariant 3: Transfer Atomicity

```
Transfer movement affects exactly two locations:
  source_location_id.balance decreases by quantity
  destination_location_id.balance increases by quantity
Atomically in one transaction.
```

**Enforcement:** Database transaction (begin → update both balances → commit).

---

### Invariant 4: Cost Lock

```
Receipt movement.cost_per_unit, once set, cannot be changed.
Corrections require new Adjustment movement.
```

**Enforcement:** Application layer (UI does not allow edit). Database constraint (if desired).

---

### Invariant 5: Organization Isolation

```
Data from Organization A cannot be accessed by Organization B.
All queries include WHERE organization_id = <current_org>.
```

**Enforcement:** Application layer (middleware, repository layer).

---

## MVP Data Model (Simplified ER)

```
Organization
  |
  +---> Product
  |       |
  |       +---> Category
  |       |
  |       +---> StockBalance
  |               |
  |               +---> Location
  |
  +---> Location
  |       |
  |       +---> StockBalance
  |
  +---> User
  +---> StockMovement
  |       |
  |       +---> Product
  |       +---> Location (source/dest)
  |       +---> User
  |       +---> StockCount (for CountCorrection type)
  |
  +---> StockCount
          |
          +---> CountLineItem
                  |
                  +---> Product
                  +---> Location
```

---

## Future Entities (Post-MVP, Not Required)

- **Supplier** — vendor information for POS/purchasing integration
- **PurchaseOrder** — order from supplier
- **Receipt.Batch** or **Lot** — batch/lot tracking, expiry
- **InventoryAdjustmentReason** — dropdown/reference table for adjustment reasons
- **AuditLog** — detailed action log (if not embedded in movements)
- **Backup** — metadata about backups taken
- **Alert** / **Notification** — low-stock notifications, audit alerts

---

## Data Lifecycle

### Product Lifecycle

1. **Created** — New product added (REQ-001).
2. **Active** — Receives stock, movements occur.
3. **Archived** — Product marked inactive; no new stock received, but historical movements remain.
4. **Deleted** — Hard deletion deferred; archived products are soft-deleted (is_active=false).

### StockMovement Lifecycle

1. **Created** — Movement recorded (immutable from this point forward).
2. **Audited** — Available in movement history, searchable.
3. **Never edited** — If mistake, user creates corrective movement.
4. **Retained forever** — For historical accountability.

### StockCount Lifecycle

1. **Started (Pending)** — User initiates count, enters observations.
2. **Reviewed (Approved/Rejected)** — Manager reviews pending count.
3. **Reconciled** — Differences converted to CountCorrection movements; stock updated.
4. **Closed** — Count record retained for audit; no further changes.

---

## Summary: What the System Knows

At any point, the system can answer:

- **Current State:** "How much stock do we have, where?"
- **History:** "What happened to product X, when, who did it, why?"
- **Cost:** "What's the average cost and inventory value?"
- **Audit:** "Who did what, when? Is history accurate and immutable?"
- **Comparison:** "What's physical vs system? Do they match?"

All of this is derivable from the entities and relationships defined above.
