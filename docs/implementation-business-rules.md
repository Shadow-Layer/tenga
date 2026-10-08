# Tenga Inventory POS — Implementation-Specific Business Rules

**Status:** ✅ Enforced in production code  
**Last Updated:** October 8, 2026

---

## Document Purpose

This document captures business rules that were **decided and implemented** during development (T001-T006, T007, T009), beyond what was documented in the original requirements. These rules are **actively enforced by the service layer** and should be understood before extending the system.

---

## Subscription Lifecycle Rules

### Rule S001: Subscription State Transition

**Rule:** Subscription state is computed from expiry_date and grace period, not stored.

```
ACTIVE (if now < expiry_date)
    ↓ [on expiry_date]
GRACE (if now >= expiry_date AND now < grace_end_date)
    ↓ [after grace period]
LIMITED (if now >= grace_end_date)
    ↓ [on renewal via renew_subscription()]
ACTIVE (new grace period starts)
```

**Enforcement:** `SubscriptionService.compute_current_state()`  
**Code:** `src/services/subscription_service.py`

**Implementation Detail:** State is **never stored** in the Subscription table. Always compute on-the-fly from dates. This means:
- Subscription table only has: `expiry_date`, `renewal_date`, `term` (monthly/annual)
- Grace duration derived from `term`
- State computation is deterministic and replay-safe

---

### Rule S002: Grace Period Duration by Term

**Rule:** Grace period duration depends on subscription billing term:

| Term | Duration | Rationale |
|------|----------|-----------|
| MONTHLY | 7 days | Weekly cadence aligns with payment processing |
| ANNUAL | 30 days | Monthly cadence aligns with annual renewal cycle |

**Enforcement:** `grace_duration_for_term()` in subscription model  
**Code:** `src/models/subscription.py`

**Configuration:** Hardcoded; should be moved to config for production

```python
GRACE_DURATIONS = {
    SubscriptionTerm.MONTHLY: 7,
    SubscriptionTerm.ANNUAL: 30,
}
```

---

### Rule S003: Limited Mode Blocks Till Operations

**Rule:** When subscription enters LIMITED state, tills cannot open new sessions.

| Operation | ACTIVE | GRACE | LIMITED |
|-----------|--------|-------|---------|
| Open till | ✅ Allowed | ✅ Allowed | ❌ Blocked |
| Close till | ✅ Allowed | ✅ Allowed | ✅ Allowed (historical) |
| Create sale | ✅ Allowed | ✅ Allowed | ❌ Blocked |
| View stock | ✅ Allowed | ✅ Allowed | ✅ Allowed (read-only) |

**Enforcement:** `TillService.assert_open_allowed(subscription, db)`  
**Code:** `src/services/till_service.py`

**Consequence:** If till is already open when subscription enters LIMITED mode, till can be closed but cannot be reopened. Till sessions are immutable once closed.

---

### Rule S004: Renewal Resets Grace Period

**Rule:** When subscription is renewed, state resets to ACTIVE and a new grace period is calculated.

**Current Behavior:** Renewal is manual via `SubscriptionService.renew_subscription()`. Sets new `expiry_date` based on renewal frequency (monthly/annual from current date).

**Code:** `src/services/subscription_service.py`

**Future:** Should integrate with payment system to auto-trigger renewal.

---

## Inventory & Stock Rules

### Rule I001: Immutable Inventory Movement Ledger

**Rule:** Once recorded, InventoryMovement rows **cannot be updated or deleted**. This is enforced at the database layer.

**Enforcement:** SQLAlchemy event listeners prevent UPDATE and DELETE operations

```python
# src/models/entities.py
@event.listens_for(InventoryMovement, 'before_update')
def prevent_inventory_movement_update(mapper, connection, target):
    raise IntegrityError("Cannot update inventory movement", ...)

@event.listens_for(InventoryMovement, 'before_delete')
def prevent_inventory_movement_delete(mapper, connection, target):
    raise IntegrityError("Cannot delete inventory movement", ...)
```

**Consequence:**
- Corrections require NEW movement record (e.g., ADJUSTMENT type)
- Audit trail is immutable and auditable
- Historical data is trustworthy

**API Impact:** No HTTP DELETE or PATCH for inventory movements.

---

### Rule I002: Stock is Derived Cache

**Rule:** Stock quantity is **computed from InventoryMovement ledger**, not stored as primary data. Stock table is a derived cache for performance.

**Computation:**
```sql
SELECT 
    product_id, 
    location_id,
    SUM(quantity) as quantity
FROM inventory_movement
WHERE product_id = ? AND location_id = ?
GROUP BY product_id, location_id
```

**Enforcement:** `InventoryService.get_stock()` always computes; updates Stock table on each movement

**Consequence:**
- Stock queries can be expensive (O(n) where n = movements)
- Stock table provides O(1) performance for common queries
- Stock is always accurate (derived from truth)
- No stock reconciliation needed (only inventory counting)

**Staleness:** Stock cache is updated synchronously on movement; no lag.

---

### Rule I003: No Stock Validation on Sale (Decision U006)

**Rule:** When creating a sale, **inventory availability is not checked**. Sales can exceed available stock.

**Enforcement:** `SaleService.create_sale()` does not call `InventoryService.get_stock()`

**Consequence:**
- Offline tills can sell regardless of cached stock
- Multiple tills can oversell same product independently
- Oversold stock results in negative stock in ledger (allowed)
- Discrepancies are detected during reconciliation (post-sync)

**Code:** `src/services/sale_service.py`

---

### Rule I004: Discrepancy Detection on Reconciliation

**Rule:** Physical inventory reconciliation detects shortage (physical < ledger) and surplus (physical > ledger).

**Process:**
1. Count physical stock at location
2. Call `InventoryService.detect_discrepancy(product_id, location_id, physical_count)`
3. If discrepancy found, record ADJUSTMENT movement with reason "PHYSICAL_COUNT_DISCREPANCY"
4. Adjustment movement corrects stock to match physical count

**Enforcement:** `InventoryService.detect_discrepancy()`  
**Code:** `src/services/inventory_service.py`

**Example:**
```python
ledger_qty = 10  # From sum of movements
physical_qty = 7  # From count
discrepancy = detect_discrepancy(product_id=1, location_id=1, physical_count=7)
# Returns: {"type": "shortage", "quantity": 3}

# Record adjustment
InventoryService.record_movement(
    product_id=1,
    location_id=1,
    quantity=-3,  # Negative to reduce stock
    reason="PHYSICAL_COUNT_DISCREPANCY",
    recorded_by_id=user.id,
    db=db
)
# Stock is now 7 (matches physical)
```

---

### Rule I005: Movement Types

**Rule:** InventoryMovement records include a `type` field indicating the semantic meaning of the movement.

| Type | Meaning | Typical Quantity | Can Be Negative? | Used In |
|------|---------|------------------|-----------------|---------|
| SALE | POS transaction | Negative | No | SaleService |
| ADJUSTMENT | Manual correction | Either | Yes | Reconciliation |
| TRANSFER | Inter-location move | Negative (source), Positive (dest) | No | Staff workflow |
| RECEIPT | Goods received | Positive | No | Procurement |
| COUNT | Physical inventory count | Either | Yes | Counting workflow |
| OPENING_BALANCE | Initial setup | Positive | No | Onboarding |

**Enforcement:** Movement type is required when recording  
**Code:** `src/services/inventory_service.py`

**Consequence:** Audit trail is semantically rich (reviewers can see "why" a quantity changed).

---

## Sale & POS Rules

### Rule P001: Sale Status Lifecycle

**Rule:** Sales progress through states based on creation mode and sync status.

```
Online Mode:
  create_sale() → COMPLETED (immediately committed)

Offline Mode:
  create_sale() → PENDING (queued for sync)
  [on reconnect and sync]
  sync_pending_sales() → COMPLETED (committed to ledger)
```

**Enforcement:** `SaleService.create_sale(online=True/False)`  
**Code:** `src/services/sale_service.py`

**Consequence:**
- Online sales create inventory movements immediately
- Offline sales queue until sync
- Status is immutable once COMPLETED

---

### Rule P002: Idempotent Sale Commitment

**Rule:** Committing the same pending sale multiple times produces no duplicate inventory movements.

**Mechanism:** Idempotency key is `(device_id, batch_id, sequence)`. Duplicate keys are ignored.

**Enforcement:** `SyncService.process_batch()` checks for duplicates before committing

**Code:** `src/services/sync_service.py`

**Consequence:**
- Device can safely retry sync if unsure about success
- No double-counting of sales

---

### Rule P003: Till Sessions Prevent Concurrent Operations

**Rule:** Only one TillSession can be OPEN per till at any time.

**Enforcement:** `TillService.open_session()` checks for existing open session

```python
existing = db.query(TillSession).filter_by(till_id=till_id, status='OPEN').first()
if existing:
    raise TillSessionError(f"Till {till_id} already has open session")
```

**Code:** `src/services/till_service.py`

**Consequence:**
- Till cannot be opened twice
- Cashier must close till before another cashier can open it
- TillSession acts as lock/mutex for till

---

### Rule P004: Till Sessions Track Balance

**Rule:** TillSession records opening and closing cash balance for audit.

**Fields:**
- `opened_at` - Timestamp when opened
- `closed_at` - Timestamp when closed
- `opening_balance` - Starting cash
- `closing_balance` - Ending cash (only when closed)
- `status` - OPEN or CLOSED

**Enforcement:** `TillService.close_session()` requires closing_balance

**Code:** `src/services/till_service.py`

**Consequence:**
- Auditable cash reconciliation
- Till operations are traceable to specific sessions

---

## Organization & User Rules

### Rule O001: Organization Isolation

**Rule:** All entities (users, products, locations, etc.) are isolated by organization via `organization_id` foreign key.

**Enforcement:** Every table except Organization has NOT NULL organization_id FK

**Consequence:**
- Multi-tenant support (though typically single-org per deployment)
- User queries implicitly filtered by organization
- Data from different organizations never mixed

**API Impact:** API endpoints should validate organization context before querying

---

### Rule O002: SKU Uniqueness per Organization

**Rule:** Product SKU is unique within an organization, but same SKU can exist in different organizations.

**Enforcement:** Unique constraint: `(organization_id, sku)`

**Code:** `src/models/entities.py` - Product table

**Consequence:**
- SKU is identifier within org context
- Multi-org systems can have overlapping SKUs

---

### Rule O003: User Roles

**Rule:** Users have one of three roles within organization:

| Role | Capabilities |
|------|--------------|
| OWNER | Create organization, all features |
| ADMIN | Manage users, products, locations, subscriptions |
| STAFF | Create sales, record movements, counts |

**Enforcement:** Role is required when creating user. API endpoints check role via JWT token.

**Code:** `src/models/entities.py` - User table, JWT handler

**Note:** Original MVP specified 3 roles; implementation may not fully enforce role-based restrictions in all endpoints (test failures indicate issues).

---

## Offline & Sync Rules

### Rule OFF001: Cached Subscription State

**Rule:** Till caches subscription state from last sync. Offline, till uses cache. On reconnect, server provides new state and cache updates.

**Cache Model:**
```python
class CachedSubscriptionState:
    till_id: int  # Unique per till
    state: str   # ACTIVE, GRACE, LIMITED
    cached_at: datetime
    expires_at: datetime  # Optional TTL
```

**Enforcement:** `SyncService.get_subscription_state_sync()` returns state for cache update

**Code:** `src/models/cached_subscription_state.py`, `src/services/sync_service.py`

**Consequence:**
- Offline till operates with last-known state (optimistic)
- Cache can become stale if subscription changes while offline
- Risk: Till operates beyond permission window until next sync
- Mitigation: Recommended to add TTL (24-48 hours) in production

---

### Rule OFF002: Batch Sync Processing

**Rule:** Device submits batch of transactions (sales, movements) for sync. Server processes each with status tracking.

**Batch Structure:**
```python
{
    "device_id": str,
    "batch_id": str,  # Idempotency key
    "transactions": [
        {
            "sequence": int,
            "type": "SALE" | "MOVEMENT",
            "data": {...}
        }
    ]
}
```

**Processing:**
1. Validate batch_id not already processed (idempotency)
2. For each transaction:
   - Commit to database
   - Track success/failure per transaction
3. Return status for each transaction
4. Update device cache with current state

**Enforcement:** `SyncService.process_batch()`  
**Code:** `src/services/sync_service.py`

**Consequence:**
- Partial batch success allowed (some tx fail, others succeed)
- Device can retry failed transactions next sync
- No all-or-nothing batch semantics (allows loose coupling)

---

### Rule OFF003: Offline Device Validation

**Rule:** When till is offline, only cached subscription state is used for validation. Server state is ignored.

**Enforcement:** Logic in `TillService` checks connection status:

```python
if is_connected():
    # Check server state
    state = SubscriptionService.compute_current_state(subscription)
else:
    # Check cached state
    cache = CachedSubscriptionState.for_till(till_id)
    state = cache.state if cache else None
```

**Code:** `src/services/till_service.py`

**Consequence:**
- Offline till is autonomous and can't be blocked remotely
- Optimistic operation improves UX during connectivity issues

---

## Data Model Rules

### Rule D001: Timestamps on All Entities

**Rule:** Every entity has `created_at` and `updated_at` timestamps.

**Enforcement:** BaseEntity has these columns with defaults

```python
class BaseEntity(Base):
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Code:** `src/models/entities.py`

**Consequence:**
- Auditable creation and modification times
- Enables time-series queries
- Requires UTC timezone handling

---

### Rule D002: Soft Deletes Not Used

**Rule:** Entities do **not** use soft delete pattern (deleted_at flag). Physical deletes are blocked by foreign key constraints.

**Consequence:**
- Once created, entities persist (immutable)
- Deletion would break audit trail
- Data is permanent for compliance

---

## Recommendations for Future Development

1. **Move Grace Duration to Config** - Currently hardcoded in `src/models/subscription.py`. Should be environment variable.

2. **Add Cache TTL** - CachedSubscriptionState should have TTL (24-48 hours). Implement check on offline operations.

3. **Add Cache Expiry Warnings** - If cache age > TTL, warn user that offline state may be stale.

4. **Role-Based API Enforcement** - Some endpoints need stricter role checks (current implementation may have gaps).

5. **Batch Size Limits** - SyncService should enforce maximum batch size to prevent DOS.

6. **Payment Integration** - Subscription renewal should integrate with payment system (currently manual).

7. **Audit Log Exports** - Implement formal audit export for compliance (U006 in original unknowns).

---

## References

- **Code:** `src/services/` - Business logic
- **Models:** `src/models/` - Data definitions
- **Tests:** `tests/` - Behavior verification
- **Decisions:** `implementation-decisions-u006-u007-u008.md`
- **Architecture:** `00-implementation-state-current.md`
