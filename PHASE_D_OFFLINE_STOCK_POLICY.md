---
title: "Phase D: Offline Stock Policy (D010a)"
status: "Investigation Complete — Awaiting Approval"
date: "October 10, 2026"
---

# Phase D: Offline Inventory Mutation and Reconciliation Policy (D010a)

## Executive Summary

**Decision:** Tenga shall support durable offline recording for all core inventory operations (sales, receipts, transfers, adjustments, counts, returns) with operation-specific reconciliation rules and clear restrictions where operations cannot be safely completed offline.

**Rationale:** Multiple tills and managers working offline with intermittent connectivity must be able to record inventory movements durably. The system must distinguish between durable local recording, synchronization, and reconciliation without silently losing transactions or inventing false certainty about shared inventory state.

**Architecture Principle:** Inventory movements are events with identity, timestamp, and audit trail. Device-local balances are provisional; the backend ledger is authoritative.

---

## Problem Statement

### The Multi-Till Offline Scenario

Small grocery shops in Zimbabwe operate with multiple checkout tills that frequently go offline due to intermittent connectivity. Each till may independently sell inventory, receive stock, perform transfers, or record adjustments while disconnected from the server.

**Example:** Last synchronized stock: 5 units
- Till A sells 4 units (offline, local record)
- Till B sells 3 units (offline, local record)  
- Manager checks in 5 units (offline, local record)
- Another till records adjustment -2 (offline, local record)

**Total movements recorded:** Sales -7, Receipt +5, Adjustment -2 = Net -4 units  
**Physical stock before movements:** 5 units  
**Physical stock after all movements:** 1 unit (correct calculation)

**Challenge:** Without a coherent policy, the system may:
- ❌ Silently lose the check-in or adjustment
- ❌ Double-count a movement on sync retry
- ❌ Apply physical count incorrectly against concurrent movements
- ❌ Discard the manager's receipt because "balance went negative"

### Current Backend State

✅ **Infrastructure Already in Place:**
- InventoryMovement: Append-only ledger (no updates/deletes)
- Sale model: Has status field (completed, pending, cancelled)
- SyncService: Batch processing with idempotency support
- CachedSubscriptionState: Device offline state caching
- Tests: `test_can_oversell_in_offline_mode`, `test_multi_till_offline_conflict_scenario`

✅ **Decision U006 Already Implemented:**
- "Permit & Reconcile Afterward"
- No stock validation at point of sale
- Tills can oversell (negative stock allowed)
- Discrepancies detected post-hoc

---

## Proposed Policy: Offline Inventory Mutation and Reconciliation

### Core Principles

**1. Durable First**
Every offline operation must be stored locally with unique ID, actor, timestamp, and reason before the UI reports it as recorded. Do not report "sale recorded" until it has been persisted to the device's local ledger.

**2. No Silent Loss**
Every valid movement retains its identity and audit history through the entire lifecycle (local → sync → reconciliation). A movement is never silently discarded because it conflicts with another movement or the current balance.

**3. Idempotent Synchronization**
Retrying a movement sync must not apply it twice. Each offline movement is assigned a unique device-local ID; the server deduplicates by (device_id, local_movement_id) to prevent double-counting.

**4. Explicit Authority**
The backend ledger is the authoritative inventory state. Device-local balances are provisional while disconnected. The device presents expected balance based on local records; the server is never incorrect.

**5. Conflict-Aware Reconciliation**
Each operation type has specific reconciliation semantics:
- **Sale:** Record both sides; if negative stock results, flag for count/adjustment
- **Stock Receipt:** Record with source; validate against receiving location  
- **Transfer:** Record source decrement and destination increment atomically
- **Physical Count:** Compare against ledger balance; reconcile intervening movements
- **Adjustment:** Apply with reason; validate permissions server-side
- **Return:** Apply restock policy (case-specific, not automatic)

**6. Visible Uncertainty**
The UI must clearly distinguish:
- ✅ **Recorded:** Movement stored locally; unique ID assigned; awaiting sync
- ✅ **Sync Pending:** Queued for server submission  
- ✅ **Synchronized:** Server acknowledged; applied to inventory ledger
- ⚠️ **Reconciliation Required:** Server detected conflict (e.g., negative stock) requiring manual action (physical count or adjustment)
- ❌ **Failed:** Sync failed; device may retry

**7. No Invented Certainty**
A device's local balance is provisional. The UI must not claim "stock is now 3 units" with confidence while offline. Phrases like "recorded locally" and "pending confirmation" are more accurate.

---

## Operation-Specific Reconciliation Rules

### 1. Sale (Point-of-Sale Transaction)

**Offline Behavior:**
- Till records sale with unique local ID
- Decrements local stock (allows negative)
- UI shows: "Sale #A1234 recorded locally; pending sync confirmation"

**Sync Behavior:**
- Server receives sale with device_id + local_id
- Deduplicates: if (device_id, local_id) exists, return success without reapplying
- Creates InventoryMovement (SALE, quantity=-sold_qty, reference_id=sale_id)
- Calculates resulting stock balance

**Reconciliation:**
- If resulting balance < 0: Flag discrepancy
- Physical count performed: Adjustment movement records actual count vs. ledger
- Reconciliation complete when physical count and ledger agree

**Test Cases:**
- ✅ Single sale within stock: Stock decrements correctly
- ✅ Multiple offline sales exceeding stock: All recorded; negative balance allowed; detected on sync
- ✅ Duplicate sync: Second attempt returns success without double-applying
- ✅ Device restart while pending: Local ledger persists; sync retried

### 2. Stock Receipt (Inbound Purchase/Transfer)

**Offline Behavior:**
- Manager records receipt with PO/reference, source, quantity, cost
- Increments local stock
- UI shows: "Receipt #R5678 recorded locally; requires sync and location reconciliation"

**Sync Behavior:**
- Server validates reference integrity and source (if required)
- Creates InventoryMovement (RECEIPT, quantity=+received_qty, reference_id=receipt_id)
- Increments stock balance at receiving location

**Reconciliation:**
- Receiving location manager confirms items physically received
- If discrepancy: Adjustment movement records actual vs. ledger
- Auditor can trace: Receipt → Sync → Physical confirmation

**Test Cases:**
- ✅ Receipt without visible reference: Allowed; recorded; sync completes
- ✅ Receipt with invalid PO: Recorded locally; server flags on sync; manager corrects
- ✅ Duplicate receipt: Deduplicates on (device_id, local_id); no double-counting

### 3. Stock Transfer (Between Locations)

**Offline Behavior:**
- Source location records dispatch: quantity decrements, movement type=TRANSFER_OUT
- Destination location records receipt: quantity increments, movement type=TRANSFER_IN
- Both recorded with matching transfer_id
- UI shows: "Transfer #T9012 dispatched; awaiting destination receipt and sync"

**Sync Behavior:**
- Server receives both movements
- Validates they reference same transfer_id
- Applies both atomically (or neither)
- Prevents stock creation/loss if one side fails

**Reconciliation:**
- If destination never records receipt: Source decrement stands; destination manager must reconcile
- Physical count at each location catches missing receipt
- Adjustment movement corrects imbalance

**Test Cases:**
- ✅ Both sides offline: Transfer recorded at both locations; syncs together
- ✅ Only source records offline: Destination receives nothing; can be corrected on destination's next sync
- ✅ Duplicate sync: Atomic reapplication prevented

### 4. Physical Count (Inventory Observation)

**Offline Behavior:**
- Manager counts actual physical units at a location
- Records: Observed quantity, timestamp (when count happened), which ledger version it's based on
- Does NOT automatically adjust balance
- UI shows: "Physical count #C3456 recorded; 23 units observed at timestamp T. Requires reconciliation."

**Sync Behavior:**
- Server receives count observation
- Calculates ledger balance at that timestamp
- Compares: Observed count vs. Ledger balance at count time + intervening movements
- Calculates discrepancy: Ledger - Observed + Intervening movements

**Reconciliation:**
- Manager reviews discrepancy explanation
- If ledger calculation is correct: Manager re-counts (items may have moved)
- If count is correct: Adjustment movement explains discrepancy (theft, damage, entry error)
- Audit trail: "Count showed 23, ledger showed 25, adjustment -2 recorded by Manager A"

**Test Cases:**
- ✅ Count without intervening offline movements: Discrepancy straightforward
- ✅ Count with concurrent offline sales: Ledger includes movements; reconciliation shows which movements caused difference
- ✅ Conflicting counts (same location, nearby times): Both recorded; manager addresses discrepancy

### 5. Manual Adjustment (Correction Movement)

**Offline Behavior:**
- Manager records adjustment: quantity change, reason code (DAMAGE, SHRINKAGE, ADJUSTMENT, etc.)
- Records: Who authorized, timestamp, reason
- UI shows: "Adjustment #A7890 recorded: -5 units due to DAMAGE; requires manager approval confirmation on sync"

**Sync Behavior:**
- Server validates:
  - Manager has permission to adjust
  - Reason code is valid canonical value (not custom free text)
  - Quantity change is within reasonable bounds
- Creates InventoryMovement (ADJUSTMENT, quantity=change, reason=code, recorded_by=manager_user_id from JWT)

**Reconciliation:**
- Audit trail is clear: Who, when, reason, timestamp
- Supervisor can review all adjustments over a period
- Does not change policy; documenting the adjustment

**Test Cases:**
- ✅ Adjustment with canonical reason: Syncs successfully
- ✅ Adjustment with invalid reason: Server rejects; manager corrects
- ✅ Adjustment exceeding change limit: Recorded locally; supervisor approval required on sync

### 6. Return (Sale Reversal or Merchandise Return)

**Offline Behavior:**
- Cashier processes return: customer returns items, records refund amount
- Quantity incremented based on return policy (case-specific: resellable, damaged, etc.)
- UI shows: "Return #RT123 recorded; quantities restored based on configured policy; requires sync confirmation"

**Sync Behavior:**
- Server validates:
  - Refund amount not negative/nonsensical
  - Return policy is applied correctly
  - Original sale exists and is in returnable state (not already returned)
- Creates InventoryMovement (RETURN, quantity=+returned_qty, reference_id=sale_id, reason=RETURN)
- Increments stock based on return condition

**Reconciliation:**
- If return quantity > original sale quantity: Flagged as anomaly
- If return happens after physical count: Count is still source of truth; discrepancy reconciled separately

**Test Cases:**
- ✅ Return within policy: Quantity restored; sync succeeds
- ✅ Return exceeding original sale qty: Recorded locally; server flags; manager confirms policy
- ✅ Return of already-returned items: Deduplicates; prevents double-restocking

---

## Synchronization Flow

### Device-Side (Till/Manager Device)

```
Local inventory operation (sale, receipt, count, adjustment, transfer, return):
  1. Persist to device-local SQLite with unique device_local_id
  2. Update local balance (provisional)
  3. UI: "Recorded locally. Sync pending."
  
Periodic sync attempt:
  4. Queue all movements with status=PENDING
  5. Send batch: [device_id, device_local_id, operation_type, details]
  6. On success: Mark as SYNCED; wait for server response
  7. On failure: Retry (exponential backoff); keep as PENDING
  8. On network unavailable: Queue locally; retry when connected
```

### Server-Side (Backend)

```
Receive sync batch from device:
  1. For each movement:
    a. Lookup: (device_id, device_local_id) already applied?
    b. If yes: Return success (idempotent)
    c. If no:
       - Validate movement (permissions, reason codes, references)
       - Create InventoryMovement record
       - Calculate resulting stock balance
       - Check for conflicts (e.g., negative stock)
       - If conflict: Mark for reconciliation; don't reject
       - Commit to database
       - Return status (applied, reconciliation_required, error)

Post-sync:
  2. Detect discrepancies:
     - Negative stock → Flag as shortage
     - Physical count vs. ledger → Calculate diff
  3. Notify device of any reconciliation needed
  4. Append reconciliation instructions to sync response
```

### Idempotency Guarantee

```
Table: device_applied_movements
  Columns: device_id, device_local_id, server_movement_id, timestamp

On second sync of same batch:
  - Server looks up (device_id, device_local_id)
  - If found: Return {"status": "already_applied", "server_movement_id": X}
  - Device receives success; does not re-apply locally
  - No double-counting
```

---

## UI State Indicators

The device UI must display movement status clearly:

### Per-Movement Status
```
✅ "Sale recorded" (device has persisted locally, unique ID assigned)
🔄 "Syncing..." (device sending to server)
📡 "Synchronized" (server confirmed receipt)
⚠️ "Reconciliation pending" (server flagged conflict; physical action required)
❌ "Sync failed" (network error; device will retry)
```

### Inventory Balance Indicator
```
Online Mode:
  "Current Stock: 23 units" (from server ledger)
  
Offline Mode:
  "Expected Stock: 18 units*" (based on local movements)
  "*Local balance pending sync confirmation"
  
During Sync:
  "Updating inventory..." (display locked)
  
After Sync with Reconciliation:
  "Expected Stock: 18 units
   Physical count required: Last count showed 20 units
   Discrepancy: +2 units (adjustment or miscount?)"
```

---

## Test Scenarios (Acceptance Tests)

### Scenario 1: Multi-Till Oversell (5-Unit Example)
```
Setup: Stock = 5 units, Till A and Till B go offline

Action:
  Till A: Sell 4 units (local: stock = 1)
  Till B: Sell 3 units (local: stock = 2 at Till B, but shared stock)
  
Sync:
  Till A syncs first: Sale -4 applied; stock = 1 ✓
  Till B syncs second: Sale -3 applied; stock = -2 ✓ (allowed)
  
Reconciliation:
  Server detects: Ledger = -2 units
  Manager performs count: Actual = 0 units (items already moved)
  Adjustment: -2 due to COUNT_CORRECTION reconciles ledger
  
Result:
  ✅ Both sales preserved (no silent loss)
  ✅ Discrepancy detected and flagged
  ✅ Reconciliation process clears inconsistency
```

### Scenario 2: Concurrent Offline Receipt and Sale
```
Setup: Stock = 10 units; Manager and Till both offline

Action:
  Manager records receipt: +5 units (local: stock = 15)
  Till records sale: -8 units (local: stock = 2)
  
Sync Order 1 - Receipt first:
  Receipt syncs: +5 applied; stock = 15 ✓
  Sale syncs: -8 applied; stock = 7 ✓
  
Sync Order 2 - Sale first:
  Sale syncs: -8 applied; stock = 2 ✓
  Receipt syncs: +5 applied; stock = 7 ✓
  
Result:
  ✅ Order-independent (both movements preserved)
  ✅ Final balance is correct regardless of sync order
```

### Scenario 3: Device Restart While Pending
```
Setup: Till has PENDING sales (not yet synced)

Action:
  Till A: Sell 3 units (status = PENDING, local_id = "sale_001")
  Device loses power (restart required)
  Device reboots
  
Recovery:
  Local ledger still has "sale_001" with PENDING status
  User resumes; queue shows "Sale A001 ready to sync"
  Sync: Server deduplicates by (device_id, local_id = "sale_001")
  
Result:
  ✅ No re-entry by user
  ✅ Sync is idempotent
  ✅ Sale is atomic: either fully synced or not sent at all
```

### Scenario 4: Duplicate Sync Attempt
```
Setup: Till A has synced "sale_002" (stock decreased 2 units)

Action:
  Till A: Sync batch includes "sale_002" again (retry)
  
Reconciliation:
  Server lookup: (device_id_A, local_id="sale_002") exists
  Server: Return {"status": "already_applied", "movement_id": 456}
  Till A: Receives success; does not re-apply
  
Result:
  ✅ No double-count
  ✅ Idempotency guaranteed
```

### Scenario 5: Physical Count During Offline Mutations
```
Setup: Stock = 10 units; Multiple tills offline

Action:
  Till A: Sell 2 units (offline, pending)
  Manager: Record count 9 units (offline, pending) - thinks stock is 10
  Till B: Sell 1 unit (offline, pending)
  
Sync (all three movements):
  Sale -2: Stock = 8
  Count: Observed 9, Ledger (at count time) = 10, Intervening = -1 (Till B), Net discrepancy = -2
  Sale -1: Stock = 7
  
Reconciliation:
  Expected: 10 - 2 - 1 = 7 units
  Observed (count): 9 units
  Discrepancy: Expected 7, observed 9 = +2 units unaccounted for
  Explanation: Count was taken before Till A's sale synced; or count error
  Manager reviews and corrects via adjustment
  
Result:
  ✅ Count is associated with its reference timestamp
  ✅ Intervening movements are accounted for
  ✅ Discrepancy is visible and reconcilable
```

---

## Implementation Consequences

### For Slice B (Checkout)

1. **Sale Recording:**
   - Sale created with status PENDING (offline) or COMPLETED (online)
   - Unique device_local_id assigned immediately
   - No stock validation at sale time
   - No warning "stock low" — only post-sync reconciliation

2. **UI States During Checkout:**
   - "Sale #001 recorded locally" (device persisted)
   - "Sale #001 synced" (server confirmed)
   - "Reconciliation needed: Physical count required" (if discrepancy detected)

3. **Receipt Printing:**
   - Receipt can be printed immediately (does not wait for sync or fiscal completion)
   - Receipt version 1: Local receipt (till#, sale#, timestamp, items, total)
   - Receipt version 2 (fiscal): Fiscal number + FDMS confirmation (separate from sale completion)

### For Backend APIs

1. **POST /sales**
   - Does not validate stock
   - Returns 201 CREATED immediately
   - Sale.status = PENDING (if sync pending) or COMPLETED (if confirmed)

2. **POST /sync/batch**
   - Accepts list of offline movements
   - Deduplicates by (device_id, local_id)
   - Returns status for each movement (applied, already_applied, conflict)
   - Does not reject negative stock

3. **GET /inventory/{product_id}/{location_id}/discrepancies**
   - Returns all detected discrepancies (negative stock, count mismatches)
   - Awaiting reconciliation (manager action required)

### For Data Model

1. **InventoryMovement:**
   - Add: device_id (source of movement), device_local_id (unique on device), sync_status
   - Indexes: (device_id, device_local_id) for deduplication

2. **Sale:**
   - Add: device_local_id (if created offline), sync_status (PENDING, SYNCED)
   - Existing: status (COMPLETED, PENDING, CANCELLED) sufficient

3. **Reconciliation Log:**
   - New table: Detected discrepancies, manager-performed adjustments, audit trail
   - Links movements to reconciliation actions

---

## Decision Approval Gate

### Questions for Product Owner

1. ✅ **Supported Offline Operations**
   Approve: Sales, Stock Receipts, Transfers, Physical Counts, Adjustments, Returns all recorded offline with operation-specific reconciliation rules?
   
2. ✅ **Negative Stock Tolerance**
   Approve: Negative stock allowed short-term (detected on sync); requires physical count + adjustment to reconcile?
   
3. ✅ **Reconciliation Authority**
   Approve: Backend ledger is authoritative; device balance is provisional; UI clearly distinguishes uncertainty?
   
4. ✅ **Conflict Resolution**
   Approve: Each operation type has specific reconciliation semantics (not "reject all conflicts")?

---

## References

- **Related Decisions:** U006 (Permit & Reconcile Afterward), U007 (Tiered Grace), U008 (Offline Optimism)
- **Related Artifacts:** PHASE_1_BASELINE.md (D010a section), implementation-decisions-u006-u007-u008.md
- **Related Code:** 
  - src/models/entities.py (InventoryMovement, Sale, SyncBatchTransaction)
  - src/services/sync_service.py (SyncService.process_sync_batch)
  - src/services/inventory_service.py (InventoryService.detect_discrepancy)
