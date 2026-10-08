# Tenga Inventory POS — Critical Architectural Decisions (U006, U007, U008)

**Status:** ✅ All three decisions implemented and verified in production code  
**Last Updated:** October 8, 2026

---

## Document Purpose

This document captures three critical architectural decisions made during the implementation of Tenga Inventory POS (T001-T006). These decisions shape the entire system's behavior for offline operation, subscription management, and inventory reconciliation.

**CRITICAL NOTE:** These decisions use IDs U006, U007, U008 which **collide with the original unknowns registry** in `/docs/unknowns-register.md`. The original U006-U008 refer to planning-phase questions (regulatory requirements, Arrupe workflows, grocery count methodology). These U006-U008 refer to **completely different architectural decisions** made during implementation.

To avoid confusion:
- **Original Unknowns (Planning Phase):** U001-U010 in `unknowns-register.md`
- **Implementation Decisions:** U006-U008 in this document
- **Recommendation:** Future decisions should use different naming scheme (e.g., D011, D012, D013 or ARCH-001, ARCH-002, ARCH-003)

---

## Decision U006 — Permit & Reconcile Afterward

### Summary
Sales transactions **do not validate stock availability** at point of sale. Tills can oversell (record sales exceeding available stock). Discrepancies are detected during device sync via physical inventory reconciliation.

### Decision Context
- **Timeline:** T001-T006 implementation
- **Trigger:** Offline-first architecture requirement
- **Confidence:** High
- **Reversibility:** Expensive (core to inventory model)

### Problem Statement
In offline-first systems, tills cannot query real-time stock levels when disconnected. Two approaches exist:

1. **Validate & Block** - Reject sales that would cause shortage. Requires cached stock predictions or pessimistic assumptions.
2. **Permit & Reconcile** - Allow sales regardless of stock; detect and reconcile discrepancies on sync.

Approach 1 requires sophisticated cache invalidation and predictive logic. Approach 2 is simpler and matches physical retail practices (physical count is source of truth).

### Decision Rationale
- **Operational Reality:** Physical retail reconciles via periodic counts; software counts are derived
- **Offline Architecture:** Cannot reliably predict stock without server queries
- **Conflict Resolution:** Multi-till concurrent sales will always risk oversell; detect post-hoc rather than prevent
- **Simplicity:** Eliminates need for cache coherency protocol between tills

### Implementation

#### No Stock Validation on Sale
```python
# src/services/sale_service.py
@staticmethod
def create_sale(db: Session, till_id: int, items: List[Dict], ...) -> Sale:
    # Does NOT check if quantity available exceeds stock
    # Creates sale with status COMPLETED (online) or PENDING (offline)
    # On sync, PENDING sales are committed
```

#### Discrepancy Detection on Sync
```python
# src/services/inventory_service.py
@staticmethod
def detect_discrepancy(db: Session, product_id: int, location_id: int, 
                      physical_count: int) -> Optional[Dict]:
    # Computes ledger_quantity from sum of all movements
    # Compares against physical_count
    # Returns {"type": "shortage"|"surplus", "quantity": abs(diff)}
    # Caller decides whether to record adjustment movement
```

#### Reconciliation Workflow
1. Till records sale offline (PENDING status)
2. Till reconnects and syncs batch of pending sales
3. Server commits each sale as InventoryMovement
4. Server checks if any movement results in negative stock
5. If shortage detected, caller records ADJUSTMENT movement with reason "PHYSICAL_COUNT_DISCREPANCY"
6. Stock is corrected and discrepancy tracked in ledger

### Tested Scenarios

| Scenario | Test | Result |
|----------|------|--------|
| Single sale below stock | `test_create_sale_within_stock` | ✅ PASS — Sale created, stock decreases |
| Single sale exceeds stock | `test_can_oversell_in_offline_mode` | ✅ PASS — Sale created, negative stock allowed |
| Multi-till simultaneous sales | `test_multi_till_offline_conflict_scenario` | ✅ PASS — Both sales committed, shortage detected |
| Discrepancy detection | `test_detect_discrepancy_shortage` + `test_detect_discrepancy_surplus` | ✅ PASS — Both cases detected |
| Idempotent commitment | `test_idempotent_commitment` | ✅ PASS — Duplicate sync doesn't double-count |

### Consequences

**Positive:**
- ✅ Enables offline-first architecture without complex cache protocols
- ✅ Matches physical retail practices (count is source of truth)
- ✅ Simplifies till-to-server sync (no conditional logic on stock)
- ✅ Multiple tills can operate independently without coordination

**Negative/Trade-offs:**
- ⚠️ Oversold stock is possible (short-term; corrected on reconciliation)
- ⚠️ Requires disciplined physical count process
- ⚠️ Needs audit trail for discrepancy investigation (implemented)

### Validation Proof
- **Code:** `src/services/sale_service.py::create_sale()` - no stock check
- **Code:** `src/services/inventory_service.py::detect_discrepancy()` - detects post-sync
- **Test:** `tests/test_sales_inventory.py::TestOversell::test_can_oversell_in_offline_mode`
- **Test:** `tests/test_integration_e2e.py::TestMultiTillOfflineConflict::test_multi_till_offline_conflict_scenario`
- **Test:** `tests/test_sales_inventory.py::TestDiscrepancy::test_detect_discrepancy_shortage`

### Future Considerations
- Monitor pilot usage to validate that physical count discipline holds
- If overselling becomes problematic, consider per-till inventory caching (post-MVP)
- Archive discrepancies for pattern analysis (which products, which locations oversell most)

### Decision Status
**ENFORCED IN CODE** — Not a configuration option. All sales use this logic.

---

## Decision U007 — Tiered Grace Periods

### Summary
When a subscription expires, the organization transitions through **ACTIVE** → **GRACE** → **LIMITED** states. The grace period duration depends on subscription billing term:
- **Monthly** subscriptions: 7-day grace
- **Annual** subscriptions: 30-day grace

During GRACE, tills can operate normally. Once grace expires, system enters LIMITED mode (tills cannot open new operations).

### Decision Context
- **Timeline:** T002 (Subscription State Machine)
- **Trigger:** SaaS billing model (subscription expiry handling)
- **Confidence:** High
- **Reversibility:** Moderate (affects subscription model; grace duration is configurable)

### Problem Statement
Subscription-based businesses face grace period decisions:

1. **Hard Cutoff** - Subscription expires → immediate LIMITED mode. Affects user experience if renewal is delayed.
2. **Flexible Grace** - Subscription expires → organization has N days to renew before access limited. Balances user flexibility with revenue protection.

Grace period duration question: Should it be uniform or vary by subscription term? Different subscription terms have different renewal cycles:
- Monthly subscribers may need quick grace (they renew frequently)
- Annual subscribers may need longer grace (renewal delay more disruptive to annual customers)

### Decision Rationale
- **User Experience:** Grace periods reduce friction during renewal delays
- **SaaS Pattern:** Industry standard for billing systems
- **Tiered Duration:** Matches customer value (annual customers get more grace)
- **Monthly 7 days:** Approximately 1 week; aligns with typical payment processing delays
- **Annual 30 days:** Approximately 1 month; aligns with annual billing cycle cadence

### Implementation

#### State Machine
```
        ACTIVE
          ↓ (expiry_date reached)
        GRACE (7 or 30 days)
          ↓ (grace_end_date reached)
        LIMITED (read-only)
          ↓ (on renewal)
        ACTIVE (new grace period starts)
```

#### Computed State
```python
# src/services/subscription_service.py
@staticmethod
def compute_current_state(subscription: Subscription) -> SubscriptionState:
    if not subscription.expiry_date:
        return SubscriptionState.ACTIVE
    
    now = datetime.utcnow()
    expiry = subscription.expiry_date
    
    # Not yet expired
    if now < expiry:
        return SubscriptionState.ACTIVE
    
    # Calculate grace end date
    grace_duration = grace_duration_for_term(subscription.term)
    grace_end = expiry + timedelta(days=grace_duration)
    
    # Still in grace
    if now < grace_end:
        return SubscriptionState.GRACE
    
    # Grace expired
    return SubscriptionState.LIMITED
```

#### Grace Duration Configuration
```python
# src/models/subscription.py
GRACE_DURATIONS = {
    SubscriptionTerm.MONTHLY: 7,   # days
    SubscriptionTerm.ANNUAL: 30,   # days
}
```

#### Till Operations Enforcement
```python
# src/services/till_service.py
@staticmethod
def assert_open_allowed(subscription: Subscription, db: Session) -> bool:
    state = SubscriptionService.compute_current_state(subscription)
    
    if state == SubscriptionState.LIMITED:
        raise SubscriptionLimitedError(
            f"Subscription in LIMITED mode; till operations blocked. "
            f"Renew subscription to restore access."
        )
    
    return True  # ACTIVE or GRACE allows operations
```

### Tested Scenarios

| Scenario | Test | Result |
|----------|------|--------|
| Subscription ACTIVE | `test_operational_checks` | ✅ PASS — is_operational() returns True |
| Subscription in GRACE (within 7d for monthly) | `test_can_open_when_grace` | ✅ PASS — Till can open |
| Subscription in LIMITED (after grace expires) | `test_cannot_open_when_limited` | ✅ PASS — Till cannot open |
| Monthly grace period is 7 days | `test_monthly_grace_is_7_days` | ✅ PASS — Delta equals 7 days |
| Annual grace period is 30 days | `test_annual_grace_is_30_days` | ✅ PASS — Delta equals 30 days |
| Renewal resets state to ACTIVE | `test_renewal_resets_to_active` | ✅ PASS — New grace period starts |

### Consequences

**Positive:**
- ✅ Reduces friction during renewal delays
- ✅ Balances user experience with revenue protection
- ✅ Matches SaaS industry best practices
- ✅ Tiered grace reflects customer value (annual more grace)

**Negative/Trade-offs:**
- ⚠️ Grace periods create "dead time" for revenue (organization can't pay but still operates)
- ⚠️ Requires renewal process to be implemented and communicated
- ⚠️ Assumes organizations will renew within grace period (monitoring needed)

### Validation Proof
- **Code:** `src/services/subscription_service.py::compute_current_state()`
- **Code:** `src/services/subscription_service.py::is_operational()`
- **Code:** `src/models/subscription.py::grace_duration_for_term()`
- **Test:** `tests/test_subscription_service.py::TestStateTransitions::test_monthly_grace_is_7_days`
- **Test:** `tests/test_subscription_service.py::TestStateTransitions::test_annual_grace_is_30_days`
- **Test:** `tests/test_till_service.py::TestLimitedModeEnforcement::test_can_open_when_grace`
- **Test:** `tests/test_integration_e2e.py::TestGracePeriod::test_subscription_grace_period_transition`

### Configuration

Grace durations are defined in code and should be externalized for production:

```python
# Future: move to config/environment
GRACE_PERIODS = {
    "MONTHLY": 7,   # days
    "ANNUAL": 30,   # days
}
```

### Future Considerations
- Monitor grace period behavior in production pilots
- Collect data on renewal success rate during grace vs after LIMITED
- Consider dynamic grace periods based on customer tier
- Implement renewal reminders (email, in-app notification)

### Decision Status
**ENFORCED IN CODE** — Grace durations are hardcoded; environment-based config recommended for future

---

## Decision U008 — Offline Optimism

### Summary
Devices (tills) cache subscription state from the last successful sync. While offline, devices operate optimistically based on cached state. On reconnection, the server provides current state; if changed, cache updates and next operation validates against new state.

### Decision Context
- **Timeline:** T003 (Offline Sync Protocol)
- **Trigger:** Offline-first architecture requirement
- **Confidence:** High
- **Reversibility:** Expensive (core sync protocol)

### Problem Statement
Offline tills need to validate subscription state (ACTIVE/GRACE/LIMITED) to enforce business rules (e.g., don't open till in LIMITED mode). Two approaches:

1. **Pessimistic** - Assume LIMITED offline; disable all operations until server confirmation
2. **Optimistic** - Assume last-known state; operate normally until told otherwise

Pessimistic approach kills offline usability. Optimistic approach requires careful cache management and reconciliation on reconnection.

### Decision Rationale
- **Operational Continuity:** Tills must operate offline; pessimistic blocks business
- **Eventual Consistency:** Mobile/POS systems are inherently eventually consistent
- **Explicit Invalidation:** Cache updates only on explicit server message during sync
- **Clear Boundary:** Cache is responsibility of device layer; server is source of truth

### Implementation

#### Device-Side Cache
```python
# src/models/cached_subscription_state.py
class CachedSubscriptionState(Base):
    """Stores subscription state cached on device from last sync."""
    
    id = Column(Integer, primary_key=True)
    till_id = Column(Integer, ForeignKey("till.id"), unique=True)
    state = Column(String, nullable=False)  # ACTIVE, GRACE, LIMITED
    cached_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Optional: TTL
```

#### Sync Protocol Returns State
```python
# src/services/sync_service.py
@staticmethod
def get_subscription_state_sync(db: Session, till_id: int) -> Dict:
    """Return current subscription state for device cache update."""
    till = db.query(Till).filter_by(id=till_id).first()
    subscription = till.location.organization.subscription
    state = SubscriptionService.compute_current_state(subscription)
    
    return {
        "state": state,
        "expires_at": subscription.expiry_date,
        "cached_at": datetime.utcnow(),
    }
```

#### Till Validates Against Cache
```python
# src/services/till_service.py
@staticmethod
def assert_open_allowed(till_id: int, db: Session) -> bool:
    till = db.query(Till).filter_by(id=till_id).first()
    
    # If online: check server state
    if is_connected():
        subscription = till.location.organization.subscription
        state = SubscriptionService.compute_current_state(subscription)
        if state == SubscriptionState.LIMITED:
            raise SubscriptionLimitedError(...)
    
    # If offline: check cached state
    else:
        cache = db.query(CachedSubscriptionState).filter_by(till_id=till_id).first()
        if cache and cache.state == SubscriptionState.LIMITED:
            raise SubscriptionLimitedError(...)
    
    return True
```

#### On Sync, Update Cache
```python
# Device sync handler
def handle_sync_response(sync_result):
    subscription_state = sync_result.get("subscription_state")
    if subscription_state:
        update_local_cache(subscription_state)
```

### Tested Scenarios

| Scenario | Test | Result |
|----------|------|--------|
| Offline with cached ACTIVE | `test_allow_with_cached_active` | ✅ PASS — Operations allowed |
| Offline with cached GRACE | `test_allow_with_cached_grace` | ✅ PASS — Operations allowed |
| Offline with cached LIMITED | `test_block_with_cached_limited` | ✅ PASS — Operations blocked |
| Cache updates on sync | `test_offline_device_cache_update_on_sync` | ✅ PASS — Cache reflects server state |
| Subscription expires while offline | `test_offline_subscription_expiry` | ✅ PASS — Device operates normally; sync reveals change |

### Consequences

**Positive:**
- ✅ Enables offline operation without server queries
- ✅ Matches real-world retail (devices operate optimistically)
- ✅ Simplifies till-to-server sync protocol
- ✅ Provides good user experience during connectivity issues

**Negative/Trade-offs:**
- ⚠️ Offline tills may operate beyond their actual permission window (until sync)
- ⚠️ Requires disciplined cache invalidation
- ⚠️ Reconciliation needed on reconnection (handled via sync response)
- ⚠️ Time-based cache expiry optional but recommended for safety

### Validation Proof
- **Code:** `src/models/cached_subscription_state.py`
- **Code:** `src/services/sync_service.py::get_subscription_state_sync()`
- **Code:** `src/services/till_service.py::assert_open_allowed()`
- **Test:** `tests/test_till_service.py::TestCachedSubscriptionState::test_allow_with_cached_active`
- **Test:** `tests/test_till_service.py::TestCachedSubscriptionState::test_block_with_cached_limited`
- **Test:** `tests/test_integration_e2e.py::TestOfflineScenarios::test_offline_device_cache_update_on_sync`

### Cache Safety Considerations

**Current Implementation:**
- Cache updates only on explicit sync (no TTL)
- No automatic cache expiration

**Recommendations for Production:**
1. **Add TTL (Time-To-Live):**
   ```python
   cache.expires_at = now + timedelta(hours=24)  # Cache valid 24h
   ```

2. **On Sync Failure:** Keep using cached state (optimistic)

3. **On Sync Success:** Always update cache with server state

4. **On Device Startup:** Check cache age; warn if older than TTL

5. **Manual Refresh:** Admin button to force cache sync

### Future Considerations
- Implement cache TTL with age-based warnings
- Add dashboard showing cache age across fleet of tills
- Monitor "stale cache" incidents (till operating with expired subscription)
- Implement push notifications for cache invalidation

### Decision Status
**ENFORCED IN CODE** — Cache model exists and sync protocol includes state response

---

## Summary Table

| Decision | Topic | Status | Impact | Reversibility |
|----------|-------|--------|--------|---------------|
| **U006** | Permit & Reconcile Afterward | ✅ Enforced | High (core to inventory) | Expensive |
| **U007** | Tiered Grace Periods | ✅ Enforced | High (core to billing) | Moderate |
| **U008** | Offline Optimism | ✅ Enforced | High (core to offline) | Expensive |

All three decisions are **implemented in production code**, **tested**, and **actively enforced** via service methods.

---

## Naming Collision Alert

**IMPORTANT:** These decisions (U006-U008) use the **same IDs** as original unknowns in `unknowns-register.md`. They are **completely different topics**:

| ID | Original (Planning) | Implementation |
|----|----------------------|----------------|
| U006 | Regulatory/fiscal | Permit & Reconcile |
| U007 | Arrupe accountability | Tiered Grace |
| U008 | Grocery count methodology | Offline Optimism |

**Recommendation for Future:** Use non-colliding IDs like D011-D013 or ARCH-001-ARCH-003.

---

## References

- **Code:** `src/services/` - Service layer implementing decisions
- **Tests:** `tests/test_subscription_service.py`, `tests/test_sales_inventory.py`, `tests/test_till_service.py`, `tests/test_integration_e2e.py`
- **Models:** `src/models/` - Domain entities enforcing decisions
- **Original Requirements:** `/docs/` - Pre-implementation planning
- **Implementation Summary:** `IMPLEMENTATION_SUMMARY.md`, `STATUS.md`
