---
title: "Phase D: Fiscal Integration (D014)"
status: "Investigation Complete — Awaiting Approval"
date: "October 10, 2026"
---

# Phase D: Fiscal Integration and Compliance Policy (D014)

## Executive Summary

**Decision:** Tenga POS must support ZIMRA-compliant fiscalization for sales. TengaVFD shall handle fiscal integration independently using approved ZIMRA Fiscal Device Gateway procedures. TengaPOS communicates through a defined fiscalization interface; sale completion and fiscal status are separate concerns.

**Authoritative Basis:** 
- ZIMRA official guidance (zimra.co.zw) confirms fiscalization is mandatory for taxpayers including those below VAT registration threshold
- ZIMRA Fiscal Device Gateway API specification supports both online and offline modes
- This decision is scoped to architectural boundaries; specific compliance details must be verified against current ZIMRA regulations and device approval status

**Risk Level:** Medium (requires active integration with external fiscal authority)

---

## Problem Statement

### What Needs Clarification

Sales involve three distinct concepts:
1. **Sale Recording:** Transaction persisted in inventory ledger (inventory effect)
2. **Receipt Printing:** Operational convenience (customer receipt, audit trail)
3. **Fiscal Compliance:** Tax authority requirement (ZIMRA, fiscal numbering, reporting)

These are NOT the same operation. A sale can be recorded without a receipt being printed. A receipt can be printed without fiscal verification. Fiscal verification may happen asynchronously (after sale completion).

**Question:** In Zimbabwe, can a POS sale be considered "final" without fiscal compliance?

### Current Backend State

✅ **Sale Model:**
- Status field: COMPLETED, PENDING, CANCELLED
- Timestamp: Created immediately on sale creation
- Reference: Links to Till, Cashier, Location

❌ **Fiscal Integration:**
- Not yet implemented
- No fiscal device integration
- No FDMS communication
- No receipt numbering (fiscal or otherwise)

---

## ZIMRA Regulatory Requirements

### Official Guidance (Source: zimra.co.zw)

#### 1. Mandatory Fiscalization

**Requirement:** Taxpayers are required to fiscalize under applicable legislation, including taxpayers below the VAT registration threshold.

**Implication:** Fiscalization is NOT optional for Tenga deployments in Zimbabwe. It is a mandatory compliance requirement.

**Who is Affected:**
- All registered POS system users
- Even small shops below VAT threshold
- Both online and offline operations (with caveats)

#### 2. Approved Integration Methods

**Options per ZIMRA Specification:**

**Option A: Virtual Fiscal Devices**
- Cloud-based fiscal verification
- Online communication with ZIMRA FDMS (Fiscal Device Management System)
- Real-time fiscal receipt numbering and reporting

**Option B: Direct POS-to-FDMS Integration**
- POS system integrates directly with ZIMRA FDMS API
- No intermediate fiscal device required
- Real-time or offline submission (per specification)

**Option C: Approved Physical Fiscal Device**
- Hardware fiscal device attached to POS
- Device handles ZIMRA communication
- POS must integrate with device protocol

**Status:** All three approaches are recognized in ZIMRA guidance. Selection depends on deployment context, device approval status, and operational needs.

#### 3. Offline Fiscal Procedures

**Capability:** ZIMRA Fiscal Device Gateway API specification describes both online and offline communication modes.

**Offline Procedure (if device is approved for offline):**
- Fiscal records stored locally on device/POS
- Submitted through files when connectivity becomes available
- Fiscal-day handling: Movements must be grouped by fiscal day
- Submission order: Must maintain chronological order
- Numbering: Fiscal numbers assigned online or using pre-authorized offline numbering scheme

**Prerequisite:** Offline fiscalization is only permitted if the registered device/deployment has explicit approval for offline mode. Not all devices/taxpayers are permitted to fiscalize offline.

**Consequence:** If offline operation is required, must verify whether target deployment is approved for offline fiscalization BEFORE assuming it is available.

#### 4. Outstanding Legal Questions (To Be Verified)

The following questions must be answered against current ZIMRA regulations before finalizing implementation:

1. **Exact Obligations:** What are the precise requirements for each device type (virtual, integrated, physical)?
2. **Taxpayer Circumstances:** Do obligations differ by business type, turnover, VAT status, or location?
3. **Offline Approval:** Which deployments are explicitly approved for offline fiscalization?
4. **Offline Numbering:** What offline fiscal-numbering schemes are approved (pre-authorized ranges, device-local with verification, other)?
5. **Submission Timing:** What are the maximum allowed delays for offline fiscal submission (24 hours, daily, end-of-fiscal-day)?
6. **Sync Failures:** If fiscal submission fails after multiple retries, what is the recovery procedure?
7. **Device Approval:** Where does TengaVFD need to be registered for ZIMRA compliance?

---

## System Architecture: Tenga POS ↔ TengaVFD ↔ ZIMRA FDMS

### System Boundaries

```
┌─────────────────────┐
│   Till (Device)     │ (Android/iOS/Web)
│  Record Sale        │
│  UI: "Sale #001"    │
└──────────┬──────────┘
           │ POST /sales (ordinary POS endpoint)
           ▼
┌──────────────────────────┐
│    TengaPOS             │ (Backend)
│  - Sale persistence     │
│  - Inventory ledger     │
│  - Receipt printing     │
│  - Sync protocol        │
└──────────┬──────────────┘
           │ Fiscalization interface
           │ (defined contract)
           ▼
┌──────────────────────────┐
│    TengaVFD             │ (Fiscal Integration Layer)
│  - ZIMRA communication  │
│  - Fiscal numbering     │
│  - Receipt formatting   │
│  - Offline queuing      │
│  - Compliance rules     │
└──────────┬──────────────┘
           │ ZIMRA FDMS API
           ▼
┌──────────────────────────┐
│   ZIMRA FDMS            │ (Tax Authority)
│  - Fiscal verification  │
│  - Receipt numbering    │
│  - Reporting            │
└──────────────────────────┘
```

### Responsibility Allocation

**TengaPOS (this codebase):**
- ✅ Record sale in inventory ledger
- ✅ Print local receipt (customer receipt for reference)
- ✅ Manage sale status (COMPLETED, PENDING, CANCELLED)
- ✅ Define fiscalization interface / contract
- ⚠️ Call fiscalization interface when appropriate (decision pending)
- ❌ NOT responsible for ZIMRA communication

**TengaVFD (separate system):**
- ✅ Accept fiscalization requests from TengaPOS
- ✅ Format fiscal receipt per ZIMRA requirements
- ✅ Communicate with ZIMRA FDMS (online mode)
- ✅ Queue fiscal records locally (offline mode)
- ✅ Retry failed submissions
- ✅ Handle offline-to-online transition
- ✅ Report fiscal numbering and status back to TengaPOS
- ❌ NOT responsible for inventory ledger

**Deployment/Configuration:**
- ✅ Verify target deployment's ZIMRA device approval status
- ✅ Select appropriate offline procedure (if permitted)
- ✅ Configure retry/timeout behavior per operational needs

---

## Sale State Model with Fiscal Separation

### State Transitions

```
Conceptual Layers:
  1. Sale Recording (Inventory)
  2. Fiscal Status (Tax Compliance)
  3. Receipt Status (Operations)

Sale Lifecycle:
┌─────────────────────────────────────────────────────┐
│ RECORDED (Inventory Ledger)                         │
│ - Sale created, timestamped, saved to ledger       │
│ - Inventory movement applied (or PENDING if offline)│
│ - Status: May be COMPLETED or PENDING              │
└──────────────────────┬──────────────────────────────┘
                       │ (sale can proceed independently
                       │  of fiscal status)
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────┐         ┌──────────────────┐
│ Receipt Printed  │         │ Fiscal Status    │
│ - Local receipt  │         │                  │
│   issued         │         ├──────────────────┤
│ - Customer gets  │         │ PENDING          │
│   copy           │         │ (awaiting VFD)   │
│ - For reference  │         │                  │
│   only           │         │ SUBMITTED        │
└──────────────────┘         │ (VFD received)   │
                             │                  │
                             │ ACKNOWLEDGED     │
                             │ (ZIMRA confirmed)│
                             │                  │
                             │ FAILED           │
                             │ (error, retry)   │
                             └──────────────────┘
```

### Sale Model Proposed Fields

```python
class Sale(Base):
    # Existing
    id: int
    organization_id: int
    till_id: int
    cashier_id: int
    total_amount: Decimal
    payment_method: str  # cash, card, mobile_money
    status: str  # completed, pending, cancelled (inventory status)
    
    # NEW: Fiscal fields
    fiscal_status: str  # pending, submitted, acknowledged, failed (OPTIONAL)
    fiscal_receipt_number: str  # ZIMRA-assigned fiscal number (OPTIONAL)
    fiscal_submitted_at: DateTime  # When fiscal submission succeeded (OPTIONAL)
    fiscal_error: str  # Error message if fiscal failed (OPTIONAL)
    fiscal_retry_count: int  # How many times VFD retried (OPTIONAL)
    
    # NEW: Tracking
    receipt_printed: bool  # Was customer receipt printed locally?
    print_count: int  # How many times receipt printed (for reprint)
```

### Key Principle

**A sale is RECORDED and INVENTORY-COMPLETE independent of fiscal status.**

- Sale.status = COMPLETED means "inventory has been updated"
- Fiscal_status = PENDING means "awaiting ZIMRA confirmation; submission will retry"
- Both are accurate; neither is "false"

---

## Online vs. Offline Fiscal Procedures

### Online Mode (Connected to ZIMRA FDMS)

```
Sequence:
  1. Till records sale offline (if disconnected) or online (if connected)
  2. Sale syncs to TengaPOS backend; InventoryMovement created
  3. TengaPOS calls TengaVFD: "Fiscalize sale #001"
  4. TengaVFD submits to ZIMRA FDMS in real-time
  5. ZIMRA responds with fiscal_receipt_number
  6. TengaVFD returns fiscal_receipt_number to TengaPOS
  7. TengaPOS updates Sale.fiscal_status = ACKNOWLEDGED
  8. Till prints receipt with fiscal_receipt_number
  9. Customer receives fiscally-compliant receipt

Timing:
  - Total time: ~500ms (network dependent)
  - Blocking: Fiscal submission is synchronous (till waits)
  - Fallback: If ZIMRA unavailable → fiscal_status = FAILED; TengaVFD retries
```

### Offline Mode (Approved Device + Offline Procedure)

**Prerequisite:** Target deployment explicitly approved by ZIMRA for offline fiscalization.

```
Sequence During Offline:
  1. Till records sale while disconnected
  2. Sale queued locally with fiscal_status = PENDING
  3. Receipt printed with placeholder ("Fiscal # pending")
  4. Customer receives preliminary receipt
  5. On reconnection, TengaVFD submits queued fiscal records to ZIMRA
  6. ZIMRA responds with fiscal_receipt_numbers for entire batch
  7. Receipts updated in inventory system (reference only; not reprinted)
  8. Audit trail: "Sale #001 fiscal-acknowledged Oct 10 14:32"

Constraints (per ZIMRA spec):
  - Fiscal records grouped by fiscal-day
  - Submission order maintained (chronological)
  - Numbering: Either pre-authorized offline range or verified by ZIMRA
  - Maximum delay: [TBD per ZIMRA current rules]
  
Fallback if offline for extended period:
  - Sales continue to be recorded (no blocking)
  - Fiscal queue grows
  - When reconnected, batch submitted
  - If still fails: Manual reconciliation required
```

---

## Retry and Error Handling

### Successful Fiscal Submission

```
POST /fiscalize
{
  "sale_id": 123,
  "till_id": 5,
  "amount": 150.00,
  "items": [{"sku": "A001", "qty": 2, "price": 75.00}],
  "timestamp": "2026-10-10T14:30:00Z"
}

Response (200 OK):
{
  "status": "acknowledged",
  "fiscal_receipt_number": "ZIM-1234567890",
  "submitted_at": "2026-10-10T14:30:01Z"
}

Action: Update Sale.fiscal_status = ACKNOWLEDGED, fiscal_receipt_number = ZIM-1234567890
```

### Transient Error (Network Unavailable)

```
POST /fiscalize → Connection timeout

Action by TengaVFD:
  1. fiscal_status = SUBMITTED (not yet confirmed)
  2. Retry queue: Add to batch for later retry
  3. Exponential backoff: 5s, 15s, 60s, 5m, 15m, hourly
  4. Maximum retries: [TBD, recommend 10-12 retries over ~24h]
  5. Alert: "Fiscal submission pending; will retry automatically"

After successful retry:
  fiscal_status = ACKNOWLEDGED, fiscal_receipt_number assigned
```

### Permanent Error (Invalid Data / Permission Denied)

```
POST /fiscalize → 400 Bad Request
{
  "error": "Invalid payment_method 'crypto' not recognized"
}

Action by TengaVFD:
  1. fiscal_status = FAILED
  2. fiscal_error = "Invalid payment_method"
  3. Do NOT retry (data is wrong, retrying won't fix it)
  4. Alert: "Fiscal submission failed; requires manual intervention"
  5. TengaPOS: Present error to manager
  6. Manager: Corrects sale data or records manual adjustment
  7. Resubmit with corrected data
```

### Uncertain Outcome (Request Sent, Response Lost)

```
POST /fiscalize → Request succeeded, but response lost (timeout)

TengaVFD Strategy (Idempotent):
  1. fiscal_status = SUBMITTED (conservative)
  2. Retry: Use same sale_id + timestamp
  3. ZIMRA behavior: Recognizes duplicate submission
     - If already processed: Returns existing fiscal_receipt_number
     - If not yet processed: Processes now, returns number
  4. Result: Always converges to correct fiscal_receipt_number
  
Idempotency Key:
  POST /fiscalize
  {
    "idempotency_key": "device_A_sale_001_timestamp_1633876200",
    ...
  }
```

### Sale Recorded But Fiscal Cannot Complete

```
Scenario: Till goes offline after recording sale but before fiscal succeeds

Handling:
  1. Sale.status = COMPLETED (inventory is correct)
  2. fiscal_status = PENDING (awaiting ZIMRA)
  3. Receipt printed: "Fiscal number pending — receipt valid"
  4. On reconnection: Fiscal retry queue processes
  5. Once fiscal succeeds: fiscal_status = ACKNOWLEDGED
  6. Audit trail: Sale and fiscal status both visible

Duration:
  - Short (minutes): Customer may return for receipt reprint with fiscal number
  - Long (hours): Manager reviews queue; may contact ZIMRA if persistent failure
  - Extreme (days): Offline approval procedure applies (if permitted)
```

---

## Acceptance Test Scenarios

### Test 1: Successful Online Fiscalization

```
Setup: Till online, ZIMRA reachable

Action:
  1. Till records sale: $150, 2 items
  2. TengaPOS receives sale, calls fiscalize
  3. TengaVFD submits to ZIMRA
  4. ZIMRA responds: fiscal_receipt_number = ZIM-1234567890
  5. Receipt printed with fiscal number

Assertions:
  ✅ Sale.fiscal_status = ACKNOWLEDGED
  ✅ Sale.fiscal_receipt_number = ZIM-1234567890
  ✅ Timestamp recorded
  ✅ Receipt includes fiscal number
  ✅ No retry attempts made (first try succeeded)
```

### Test 2: Offline Fiscal Queue

```
Setup: Till offline, no internet connection

Action:
  1. Till records sale: $100
  2. TengaVFD queues fiscal: fiscal_status = PENDING
  3. Receipt printed: "Fiscal # pending"
  4. Device remains offline for 1 hour
  5. Device reconnects
  6. TengaVFD submits queued fiscal records
  7. ZIMRA responds with numbers

Assertions:
  ✅ Sale recorded and inventory updated (while offline)
  ✅ Fiscal submission queued (not lost)
  ✅ On reconnection, automatic submission
  ✅ After submission succeeds: fiscal_status = ACKNOWLEDGED
  ✅ Audit trail shows: recorded time, submitted time, acknowledged time
```

### Test 3: Fiscal Submission Failure with Retry

```
Setup: Till online, but ZIMRA temporarily unavailable

Action:
  1. Till records sale: $75
  2. TengaPOS calls fiscalize
  3. TengaVFD submission → timeout (ZIMRA down)
  4. fiscal_status = SUBMITTED; retry queued
  5. 15 seconds later: TengaVFD retries
  6. Still failing (ZIMRA still down)
  7. 60 seconds later: Retry again
  8. ZIMRA comes back online; submission succeeds
  9. fiscal_status = ACKNOWLEDGED

Assertions:
  ✅ Sale not rejected during ZIMRA outage
  ✅ Automatic retry occurred
  ✅ Exponential backoff applied (5s, 15s, 60s pattern)
  ✅ Once ZIMRA online: submission succeeds
  ✅ Retry count: ≥ 2 (at least 2 retries before success)
```

### Test 4: Idempotent Retry

```
Setup: Till sent fiscal request; response lost

Action:
  1. Till records sale: $200, ID = "sale_042"
  2. TengaPOS calls fiscalize with idempotency_key
  3. TengaVFD submits; ZIMRA responds: ZIM-9876543210
  4. Response lost (timeout)
  5. TengaVFD retries same request (same idempotency key)
  6. ZIMRA recognizes duplicate; returns same fiscal number

Assertions:
  ✅ First attempt: fiscal_receipt_number = ZIM-9876543210 (generated)
  ✅ Retry attempt: fiscal_receipt_number = ZIM-9876543210 (same number)
  ✅ No second fiscal number issued
  ✅ Sale correctly fiscalized exactly once
```

### Test 5: Invalid Sale Data

```
Setup: Till records sale with invalid data

Action:
  1. Till records sale: payment_method = "cryptocurrency" (invalid)
  2. TengaPOS calls fiscalize
  3. ZIMRA rejects: 400 Bad Request, "Invalid payment method"
  4. fiscal_status = FAILED
  5. fiscal_error = "Invalid payment method"
  6. TengaVFD does NOT retry (data is wrong)

Assertions:
  ✅ fiscal_status = FAILED (not SUBMITTED)
  ✅ Error message captured
  ✅ No automatic retries (won't fix wrong data)
  ✅ Alert to manager: manual correction needed
  ✅ Sale remains recorded (inventory OK)
  ✅ Manager corrects payment_method → cash
  ✅ Resubmit fiscalization
  ✅ Second attempt succeeds
```

### Test 6: Uncertain Outcome

```
Setup: Network flaky; request succeeds but response unclear

Action:
  1. Till records sale: $180, ID = "sale_088"
  2. TengaPOS calls fiscalize (idempotency_key = "dev_A_088")
  3. TengaVFD submits; ZIMRA processes (fiscal number generated: ZIM-5555555555)
  4. Response packet lost (network hiccup)
  5. TengaVFD timeout; retries with same idempotency_key
  6. ZIMRA recognizes key; returns: ZIM-5555555555 (same number)

Assertions:
  ✅ First attempt recorded: sale_status = SUBMITTED, no number yet
  ✅ Retry succeeds: sale_status = ACKNOWLEDGED, fiscal_receipt_number = ZIM-5555555555
  ✅ No duplicate fiscal receipt issued
  ✅ Idempotent behavior guaranteed
```

### Test 7: Prolonged Offline (Device Restart)

```
Setup: Till offline for extended period; device power cycles

Action:
  1. Till records sale: $120 (offline, status = PENDING)
  2. Device battery dies / power loss
  3. Device rebooted; sale still in queue (persisted locally)
  4. Device reconnects to network
  5. TengaVFD submits queued fiscal
  6. ZIMRA processes; fiscal number assigned

Assertions:
  ✅ Sale not lost after restart
  ✅ Fiscal queue persisted
  ✅ On reconnection: submission automatic
  ✅ fiscal_status = ACKNOWLEDGED after submission
  ✅ Audit trail complete
```

---

## Implementation Consequences for Slice B (Checkout)

### 1. Sale Completion Flow

**Current (No Fiscal):**
```
Till records sale → Inventory updated → Receipt printed → Done
Timing: ~100ms
```

**With Fiscal Integration:**
```
Till records sale → Inventory updated → Call fiscalize → Wait for fiscal response
                                                               ↓
                                                    (success) → Receipt printed → Done
                                                               ↓
                                                    (failure/timeout) → Queue retry → "Fiscal pending" receipt
```

**Impact:**
- Sale is ALWAYS recorded immediately (inventory-complete)
- Fiscal submission may be async (if offline or if TengaVFD handles it async)
- Receipt printing may happen before fiscal confirmation (interim receipt valid)
- Final receipt with fiscal number becomes available after confirmation

### 2. Checkout UI Changes

**During Sale Recording:**
```
✅ Till button: "Complete Sale" → Sale recorded instantly
   UI: "Sale #001 recorded" (immediate feedback)

⏳ After recording:
   - If fiscal succeeds: UI: "Fiscal # ZIM-1234567890 ✓"
   - If fiscal pending: UI: "Fiscal verification in progress..."
   - If fiscal fails: UI: "Fiscal error; will retry. Receipt valid for now."
```

**Till Receipt:**
```
Scenario 1 (Online): Receipt printed immediately with fiscal number
  Invoice #001
  Fiscal #ZIM-1234567890
  [items, total]
  "Fiscally compliant receipt"

Scenario 2 (Offline pending): Receipt printed before fiscal number ready
  Invoice #001
  Fiscal #PENDING
  [items, total]
  "Fiscal verification in progress"
  [manager can reprint after fiscal confirmed]

Scenario 3 (Offline, fiscal failed): Receipt still valid
  Invoice #001
  Fiscal #ERROR — Retrying
  [items, total]
  "Contact till manager if issue persists"
```

### 3. API Endpoints

**New/Modified Endpoints:**

```
POST /sales
  - Creates Sale
  - Calls /fiscalize (if online)
  - Returns: Sale with fiscal_status
  - Does NOT block on fiscal response (async)

POST /fiscalize (or called internally by /sales)
  - Request: sale_id, details
  - Response: fiscal_receipt_number, fiscal_status
  - Handles: Retry, offline queue, idempotency

GET /sales/{id}/fiscal-status
  - Returns: Current fiscal_status (PENDING, ACKNOWLEDGED, FAILED)
  - Useful for checking if fiscal confirmed

POST /sales/{id}/receipt/reprint
  - Reprints receipt with latest fiscal number (if available)
  - Handles: Multiple prints, fiscal number changes
```

### 4. Configuration & Deployment

**Environment Variables (New):**
```
FISCAL_ENABLED=true|false
FISCAL_PROVIDER=tenga_vfd|external|mock
FISCAL_RETRY_MAX_ATTEMPTS=12
FISCAL_RETRY_BACKOFF_SECONDS=5,15,60,300,900
FISCAL_OFFLINE_MODE=allowed|required_online  # based on device approval
```

### 5. Error Handling

**Scenarios Checkout Must Handle:**

| Scenario | Sale Status | Fiscal Status | Receipt | Till Behavior |
|----------|-------------|---------------|---------|---------------|
| Success | COMPLETED | ACKNOWLEDGED | Print with fiscal # | Green light |
| Offline (async fiscal) | COMPLETED | SUBMITTED | Print preliminary | Proceed; fiscal in background |
| ZIMRA timeout | COMPLETED | SUBMITTED | Print preliminary | Proceed; manager monitors queue |
| ZIMRA rejected | COMPLETED | FAILED | Print with error | Alert manager; may need correction |
| Network down | COMPLETED | PENDING | Print with "pending" | Proceed; queue for later |

---

## Decision Approval Gate

### Questions for Product Owner

1. ✅ **Mandatory Fiscalization**
   Approve: Tenga POS must support ZIMRA-compliant fiscalization for all sales in Zimbabwe deployments (not optional)?

2. ✅ **System Boundaries**
   Approve: TengaVFD handles fiscal integration independently; TengaPOS calls through defined interface; sale and fiscal status are separate?

3. ✅ **Offline Fiscal Capability**
   Approve: If target deployment is approved by ZIMRA for offline fiscal, use ZIMRA-specified offline procedure (queue + submit on reconnection)?

4. ✅ **Non-Blocking Sale**
   Approve: Sale is recorded and inventory-complete immediately; fiscal confirmation happens async (may be delayed or may be pending)?

5. ✅ **Error Resilience**
   Approve: If ZIMRA unavailable, sales still complete (fiscal retries automatically); till manager notified of fiscal queue status?

---

## Outstanding Questions (To Be Verified)

Before final implementation, clarify with ZIMRA:

- [ ] Device approval process for TengaVFD
- [ ] Offline fiscalization approval status for target deployments
- [ ] Offline numbering scheme (pre-authorized range vs. other)
- [ ] Maximum delay allowed for offline fiscal submission
- [ ] Submission order and fiscal-day grouping requirements
- [ ] Recovery procedures if fiscal submission fails after N retries
- [ ] Audit trail requirements (what must be logged for compliance)
- [ ] Annual reconciliation procedures

---

## References

- **ZIMRA Official Guidance:** zimra.co.zw (Virtual Fiscal Devices, Fiscal Device Gateway API, POS Integration)
- **Related Decisions:** D001 (Inventory-first), U006 (Permit & Reconcile Afterward)
- **Related Artifacts:** PHASE_1_BASELINE.md (D014 section)
- **Related Code:** TengaVFD (separate system; fiscal integration layer)
