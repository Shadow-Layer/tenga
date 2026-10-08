# Tenga Inventory — Final Decision Ledger

This ledger consolidates all decisions (Iteration 1–3), marks confidence, consequences, and whether the decision is expensive to reverse.

---

## D001 — Inventory-first
- Decision: Inventory-first; no POS/accounting required for core workflows.
- Derived from: Project charter; user input.
- Confidence: High
- Consequences: Avoid POS/accounting features in MVP; integration as optional future work.
- Reversibility: Reversible; integration can be added later with effort.

---

## D002 — Pilot Targets
- Decision: Two pilot segments: institutional (Arrupe) and small grocery shops.
- Confidence: High
- Consequences: Product must satisfy both accountability and high-SKU operations.
- Reversibility: Reversible but affects UX decisions.

---

## D003 — MVP Capability Bundle
- Decision: Items, Locations, Movements, Counts, History, Valuation (weighted-average), Users (3 roles), Basic reports.
- Confidence: High
- Consequences: Scope locked for MVP; many features deferred.
- Reversibility: Partial; adding features later is possible but may require data model extensions.

---

## D004 — Weighted-average valuation
- Decision: Record per-receipt cost; compute weighted average for valuation in MVP.
- Confidence: High
- Consequences: Movement records require optional cost; valuation code must be deterministic.
- Reversibility: Reversible (support FIFO/LIFO later), but migration path must be planned.

---

## D005 — Three-role RBAC
- Decision: Owner/Admin, Manager, Staff; no granular permissions in MVP.
- Confidence: High
- Consequences: Simpler UX; possible under-support for complex institutions.
- Reversibility: Reversible with increased complexity (post-MVP).

---

## D006 — Stock is location-specific
- Decision: Stock identity is Product + Location; global totals derived by summation.
- Confidence: High
- Consequences: Locations are first-class; all balances stored per (product,location).
- Reversibility: Expensive to reverse if implemented differently; foundational.

---

## D007 — Semantic movement types
- Decision: Movements are typed (OpeningBalance, Receipt, Issue, Transfer, Adjustment, CountCorrection).
- Confidence: High
- Consequences: Movement semantics guide validation and UX; single StockMovement model is used.
- Reversibility: Moderate; changes possible but will affect audit and UI flows.

---

## D008 — Transfers are atomic
- Decision: Transfer is one atomic event affecting source and destination.
- Confidence: High
- Consequences: Simplifies audit trail and user mental model.
- Reversibility: Expensive in data model change; keep.

---

## D009 — Receipt cost locked
- Decision: Cost at receipt is immutable; corrections via new movements.
- Confidence: High
- Consequences: Auditable costs; need mechanism for cost correction (post-MVP).
- Reversibility: Moderate; changing may break audits.

---

## D010 — Valuation drill-down
- Decision: Show headline valuation (weighted average) and allow movement-level drill-down.
- Confidence: High
- Consequences: Users trust numbers while having access to the underlying receipts.
- Reversibility: Easy; UI change.

---

## Derived decisions during validation
- D011 (Validation): MVP is online-first; offline deferred pending pilot validation.
  - Confidence: Medium
  - Consequence: Offline sync not designed in MVP; impacts users with poor connectivity.
  - Action: Validate with pilot onboarding.

- D012 (Validation): CSV import for opening balances deferred to post-MVP unless pilot requires it.
  - Confidence: Medium
  - Consequence: Onboarding may take longer for large catalogs.
  - Action: Collect pilot data sample.

---

## Decision Confidence Guide
- High: Strong user input or vital to product principle.
- Medium: Reasonable but requires pilot validation.
- Low: Speculative or future-looking; avoid implementing until validated.

---

## Expensive-to-reverse decisions
- Stock-is-location-specific (D006)
- Transfers-atomic (D008)
- Movement immutability approach (D007, D009)

These should be considered architectural anchors; change only with strong evidence.

---

---

## IMPLEMENTATION PHASE DECISIONS (October 2026)

**Note:** The decisions below were made during implementation (T001-T006) and use IDs U006-U008. These are **completely different from the original planning unknowns** that also use U006-U008. See `implementation-decisions-u006-u007-u008.md` for full details.

### U006 (Implementation) — Permit & Reconcile Afterward

**Topic:** Offline sales and stock reconciliation

- **Decision:** Sales do not validate stock availability at point of sale. Tills can oversell (record sales exceeding available stock). Discrepancies are detected during sync via physical inventory reconciliation.
- **Status:** ✅ Implemented and enforced
- **Confidence:** High
- **Reasoning:** Enables offline-first operation without complex cache coherency. Matches physical retail practices where physical count is authoritative.
- **Implementation:** 
  - `SaleService.create_sale()` — No stock validation
  - `InventoryService.detect_discrepancy()` — Detects shortage/surplus post-sync
- **Reversibility:** Expensive (core to inventory/sales model)
- **Tested:** `test_multi_till_offline_conflict_scenario`, `test_can_oversell_in_offline_mode`
- **Code Location:** `src/services/sale_service.py`, `src/services/inventory_service.py`

### U007 (Implementation) — Tiered Grace Periods

**Topic:** Subscription operational windows during expiry

- **Decision:** Subscriptions transition ACTIVE → GRACE → LIMITED. Grace period duration depends on subscription term:
  - Monthly: 7 days
  - Annual: 30 days
- **Status:** ✅ Implemented and enforced
- **Confidence:** High
- **Reasoning:** Reduces friction during renewal delays while protecting revenue. Tiered grace matches customer value (annual customers get more grace).
- **Implementation:**
  - `SubscriptionService.compute_current_state()` — Calculates state from expiry_date + grace_duration
  - `TillService.assert_open_allowed()` — Blocks operations in LIMITED mode
  - `src/models/subscription.py` — Grace duration configuration
- **Reversibility:** Moderate (affects subscription model; grace durations are configurable)
- **Tested:** `test_monthly_grace_is_7_days`, `test_annual_grace_is_30_days`, `test_can_open_when_grace`, `test_cannot_open_when_limited`
- **Code Location:** `src/services/subscription_service.py`, `src/models/subscription.py`, `src/services/till_service.py`

### U008 (Implementation) — Offline Optimism

**Topic:** Offline device state validation

- **Decision:** Devices cache subscription state from last sync. While offline, operate optimistically based on cached state. On reconnection, server provides current state; if changed, cache updates.
- **Status:** ✅ Implemented and enforced
- **Confidence:** High
- **Reasoning:** Enables offline operation without server queries. Matches mobile/POS industry patterns (eventual consistency). Cache updates only on explicit sync.
- **Implementation:**
  - `CachedSubscriptionState` model — Device-side cache
  - `SyncService.get_subscription_state_sync()` — Returns current state on sync
  - `TillService` — Checks server state (if online) or cached state (if offline)
- **Reversibility:** Expensive (core to sync protocol)
- **Tested:** `test_allow_with_cached_active`, `test_allow_with_cached_grace`, `test_block_with_cached_limited`, `test_offline_device_cache_update_on_sync`
- **Code Location:** `src/models/cached_subscription_state.py`, `src/services/sync_service.py`, `src/services/till_service.py`

---

## Decision Summary by Phase

### Original Planning Decisions (D001-D012)
- Focused on MVP scope, architecture, and business model
- Resolved during requirements and design phase
- All recorded in this ledger (D001-D010)
- Derived decisions D011-D012 deferred pending pilot validation

### Implementation Decisions (U006-U008, October 2026)
- Made during service layer development (T001-T006)
- Address POS-specific architecture (subscription lifecycle, offline operation, sales reconciliation)
- All **implemented and tested** in production code
- See `implementation-decisions-u006-u007-u008.md` for detailed analysis

---

## Naming Collision Alert ⚠️

The implementation phase uses IDs **U006-U008** which collide with the original planning-phase unknowns. The topics are completely different:

| ID | Original (Planning Phase) | Implementation Phase |
|----|---------------------------|----------------------|
| U006 | Regulatory/fiscal requirements | Permit & Reconcile Afterward |
| U007 | Arrupe accountability model | Tiered Grace Periods |
| U008 | Grocery count methodology | Offline Optimism |

**Recommendation:** Future decision IDs should use non-colliding scheme (D013+, ARCH-001+, etc.)

---

## Next Review
- Revisit decisions D011, D012 after pilot scoping and initial onboarding.
- Monitor implementation of U006-U008 in pilot deployments.
- Consider formalizing cache TTL policy for U008 (Offline Optimism).

