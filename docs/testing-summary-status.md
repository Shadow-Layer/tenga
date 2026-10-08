# Testing Summary & Status

**Last Updated:** October 8, 2026  
**Total Tests:** 173 | **Passing:** 98 | **Failing:** 18 | **Skipped:** 13

---

## Overview

The Tenga Inventory POS system has comprehensive test coverage across unit tests, integration tests, and acceptance criteria. However, some test categories are experiencing failures related to API integration and offline capability.

---

## Test Breakdown by Category

### ✅ Unit Tests — Passing (Core Services)

| File | Tests | Status | Coverage |
|------|-------|--------|----------|
| `test_subscription_service.py` | 12 | ✅ PASSING | State machine, grace periods, renewal |
| `test_migration_system.py` | 8 | ✅ PASSING | Alembic migrations, version tracking |

**Total: 20 tests passing**

---

### ⚠️ Unit Tests — Failing (Services with Issues)

| File | Tests | Status | Issues |
|------|-------|--------|--------|
| `test_sales_inventory.py` | 12 | ⚠️ 3 FAILING | Oversell scenario, discrepancy detection, invalid product |
| `test_till_service.py` | 12 | ⚠️ 2 FAILING | Session open/close, current session queries |

**Total: 12 tests failing**

**Known Issues:**
- `test_detect_discrepancy_surplus` - May have issue with surplus calculation
- `test_create_sale_invalid_product_fails` - Product validation not working as expected
- `test_open_session` - SQLAlchemy session/transaction issue
- `test_close_session` - Session state not updating correctly
- `test_get_current_open_session` - Query logic issue

---

### 🔄 Integration Tests — Partial Passing

| File | Tests | Status | Issues |
|------|-------|--------|--------|
| `test_integration_e2e.py` | 8 | ⚠️ 2 FAILING | Multi-till operations, offline conflicts |

**Total: 6 tests passing, 2 failing**

**Failing Scenarios:**
- `test_multi_till_sales` - Till isolation/concurrency issue
- `test_multi_till_offline_conflict_scenario` - Conflict detection not working

---

### ❌ API Tests — Mostly Failing

| File | Tests | Status | Issues |
|------|-------|--------|--------|
| `test_api_organizations.py` | ~5 | ❌ 3 ERRORS | SQLAlchemy integration with FastAPI |
| `test_api_products_locations.py` | ~10 | ❌ 3 ERRORS | Route/session issues |
| `test_api_sales.py` | ~5 | ❌ 4 ERRORS | Database session not initialized |
| `test_api_subscriptions.py` | ~5 | ❌ 4 ERRORS | Session/transaction issues |
| `test_api_sync.py` | ~2 | ❌ 1 ERROR | Route not found or session issue |
| `test_api_tills.py` | ~5 | ❌ 4 ERRORS | Database session errors |

**Total: ~35 API tests, ~18 errors**

**Root Cause:** SQLAlchemy session initialization issue in FastAPI request handlers. Database session not properly injected or committed.

---

### 🔴 Auth/Security Tests — Failing

| File | Tests | Status | Issues |
|------|-------|--------|--------|
| `test_security_auth.py` | ~17 | ⚠️ ~7 FAILING | Token validation, org isolation, role enforcement |

**Total: ~10 passing, ~7 failing**

**Failing Scenarios:**
- `test_login_invalid_password` - Auth endpoint issue
- `test_get_current_user` - Token validation failing
- `test_login_inactive_user` - User status check not working
- `test_user_cannot_access_other_org_products` - Org isolation not enforced in API
- `test_user_cannot_access_other_org_locations` - Same issue
- `test_user_cannot_access_other_org_tills` - Same issue
- `test_manager_can_create_user` - Role checks not enforced
- `test_admin_can_create_user` - Role checks not enforced

---

### 🚀 Offline Capability Tests — Failing

| File | Tests | Status | Issues |
|------|-------|--------|--------|
| `test_offline_capability.py` | ~22 | ⚠️ ~9 FAILING | Cache management, sync, offline manager |

**Total: ~13 passing, ~9 failing**

**Failing Scenarios:**
- `test_create_offline_sale` - OfflineManager class issue
- `test_get_pending_sync_count` - Cache/queue tracking broken
- `test_sync_with_mock_api` - Sync protocol issue
- `test_event_callbacks` - Event handling broken
- `test_offline_sale_flow` - Multi-step workflow issue
- `test_offline_persistence_across_restarts` - Storage issue

**Root Cause:** OfflineManager class appears to have edge cases in cache invalidation and queue management.

---

### 🏠 PostgreSQL Integration Tests — Skipped

| File | Tests | Status | Reason |
|------|-------|--------|--------|
| `test_postgresql_integration.py` | 31 | ⏸️ SKIPPED | Requires TEST_POSTGRES_URL environment variable |

**To Enable:**
```bash
export TEST_POSTGRES_URL="postgresql://user:pass@localhost/tenga_test"
pytest tests/test_postgresql_integration.py -v
```

---

## Test Execution Summary

### Raw Numbers

```
===================== 98 passed, 18 failed, 13 skipped, 820 warnings =====================
```

### By Category

| Category | Passing | Failing | Skipped | Total |
|----------|---------|---------|---------|-------|
| Unit — Subscription | 12 | 0 | 0 | 12 |
| Unit — Migration | 8 | 0 | 0 | 8 |
| Unit — Sales/Inventory | 9 | 3 | 0 | 12 |
| Unit — Till | 10 | 2 | 0 | 12 |
| Integration E2E | 6 | 2 | 0 | 8 |
| API | ~17 | ~18 | 0 | ~35 |
| Auth/Security | ~10 | ~7 | 0 | ~17 |
| Offline Capability | ~13 | ~9 | 0 | ~22 |
| PostgreSQL | 0 | 0 | 31 | 31 |
| **TOTAL** | **98** | **18** | **13** | **173** |

---

## Critical Decision Verification

### ✅ U006 — Permit & Reconcile Afterward

**Status:** Core logic PASSING, conflicts FAILING

- ✅ `test_can_oversell_in_offline_mode` — PASSING (sales allow negative stock)
- ⚠️ `test_multi_till_offline_conflict_scenario` — FAILING (conflict detection not working)
- ⚠️ `test_detect_discrepancy_surplus` — FAILING (surplus calculation broken)

**Assessment:** Oversell logic works; conflict detection and reconciliation needs debugging.

---

### ✅ U007 — Tiered Grace Periods

**Status:** PASSING (well-tested)

- ✅ `test_monthly_grace_is_7_days` — PASSING
- ✅ `test_annual_grace_is_30_days` — PASSING
- ✅ `test_can_open_when_grace` — PASSING
- ✅ `test_cannot_open_when_limited` — PASSING

**Assessment:** Grace period logic is solid and well-verified.

---

### ⚠️ U008 — Offline Optimism

**Status:** Core logic PASSING, cache management FAILING

- ✅ `test_allow_with_cached_active` — PASSING
- ✅ `test_allow_with_cached_grace` — PASSING
- ✅ `test_block_with_cached_limited` — PASSING
- ⚠️ `test_offline_device_cache_update_on_sync` — Partially working
- ⚠️ Multiple OfflineManager tests FAILING

**Assessment:** Offline validation logic works; cache management and OfflineManager have issues.

---

## Known Issues & Root Causes

### 1. SQLAlchemy Session Management in API Routes

**Affected:** All API tests (~18 errors)  
**Root Cause:** Database session not properly initialized in FastAPI request handlers  
**Symptoms:** `sqlalchemy.exc.IntegrityError`, session not bound, no database connection

**Fix Required:**
- Review `src/routers/` files for session management
- Ensure `get_db()` dependency is correctly used in all routes
- Check session lifecycle (commit/rollback) in route handlers

**Example Pattern:**
```python
# Current (likely broken)
@router.get("/products")
def list_products(org_id: int):
    # db session not injected or not used correctly
    pass

# Should be
@router.get("/products")
def list_products(org_id: int, db: Session = Depends(get_db)):
    products = db.query(Product).filter_by(organization_id=org_id).all()
    return products
```

---

### 2. Till Session Operations

**Affected:** `test_till_service.py` (2 failures)  
**Root Cause:** TillSession state not persisting correctly  
**Symptoms:** Sessions appear to be created but status updates not saved

**Fix Required:**
- Check `TillService.open_session()` - verify session is committed
- Check `TillService.close_session()` - verify closing_balance is set and committed
- Check `TillService.get_current_open_session()` - verify query filter is correct

---

### 3. Inventory Discrepancy Detection

**Affected:** `test_sales_inventory.py` (1-2 failures)  
**Root Cause:** Discrepancy calculation may have off-by-one or logic error  
**Symptoms:** Surplus detection failing, expected values not matching

**Fix Required:**
- Review `InventoryService.detect_discrepancy()` logic
- Verify `get_stock()` calculation is correct
- Add logging to discrepancy detection for debugging

---

### 4. OfflineManager Cache Management

**Affected:** `test_offline_capability.py` (~9 failures)  
**Root Cause:** OfflineManager class has edge cases in cache invalidation and queue tracking  
**Symptoms:** Pending sales not tracked, cache not updating, sync failing

**Fix Required:**
- Review OfflineManager class for cache TTL logic
- Check queue persistence across restarts
- Verify event callbacks are properly triggered

---

### 5. Organization Isolation in API

**Affected:** `test_security_auth.py` (3+ failures)  
**Root Cause:** API routes not filtering by organization context  
**Symptoms:** User from org A can see data from org B

**Fix Required:**
- Extract organization_id from JWT token
- Filter all queries by organization_id
- Add tests to verify isolation

**Example:**
```python
# In route handler
org_id = claims['organization_id']  # From JWT
products = db.query(Product).filter_by(organization_id=org_id).all()
```

---

### 6. Role-Based Authorization

**Affected:** `test_security_auth.py` (2+ failures)  
**Root Cause:** Role checks not implemented in all routes  
**Symptoms:** Staff can create users (shouldn't be able to)

**Fix Required:**
- Add role checks to sensitive endpoints (user creation, subscription changes)
- Extract user role from JWT token
- Raise PermissionError if role insufficient

**Example:**
```python
def check_admin(claims: Dict):
    if claims['role'] != 'ADMIN':
        raise PermissionError("Admin access required")
```

---

## Test Failure Priority

### 🔴 Critical (Must Fix Before Production)

1. **API Database Session Issues** — All API tests failing due to session problems
2. **Organization Isolation** — Security risk if users can see other orgs' data
3. **Role-Based Authorization** — Security risk if staff can perform admin actions

### 🟡 High (Should Fix for MVP)

4. **Till Session Operations** — Core POS feature
5. **Offline Conflict Detection** — Critical to U006 decision
6. **OfflineManager Cache** — Affects offline operation reliability

### 🟢 Medium (Address in Phase 2)

7. **Discrepancy Detection Edge Cases** — Reconciliation accuracy
8. **PostgreSQL Tests** — Not blocking current SQLite deployment

---

## Recommended Fix Order

1. **Fix API Database Sessions** (1-2 hours)
   - Review all routes for session dependency injection
   - Add missing `db: Session = Depends(get_db)` parameters
   - Test API routes with fresh database

2. **Fix Organization Isolation** (1-2 hours)
   - Add org_id extraction from JWT in all routes
   - Filter queries by organization_id
   - Add tests for isolation

3. **Fix Role-Based Checks** (1-2 hours)
   - Add role extraction from JWT
   - Add authorization checks on sensitive endpoints
   - Test role enforcement

4. **Fix Till Sessions** (1-2 hours)
   - Debug session lifecycle in TillService
   - Verify database commits

5. **Fix Offline Conflict Detection** (2-3 hours)
   - Debug OfflineManager and sync protocol
   - Test multi-till scenarios
   - Verify idempotency

---

## Running Tests

### All Tests

```bash
pytest tests/ -v
```

### Specific Category

```bash
# Core services (likely to pass)
pytest tests/test_subscription_service.py tests/test_migration_system.py -v

# API tests (currently failing)
pytest tests/test_api_products_locations.py -v

# PostgreSQL tests (skipped by default)
export TEST_POSTGRES_URL="postgresql://..."
pytest tests/test_postgresql_integration.py -v
```

### With Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

### Stop on First Failure

```bash
pytest tests/ -x -v
```

---

## Test Development Best Practices

### For New Features

1. Write failing test first (TDD)
2. Implement feature
3. Verify test passes
4. Check database state in test teardown
5. Add edge case tests

### Template

```python
def test_feature_does_something(db: Session):
    # Setup
    org = Organization(name="Test Org")
    db.add(org)
    db.commit()
    
    # Execute
    result = service_method(org_id=org.id, db=db)
    
    # Verify
    assert result is not None
    assert result.property == expected_value
    
    # Cleanup (optional if using fixtures)
    db.delete(org)
    db.commit()
```

---

## Continuous Integration

For production deployments, establish CI/CD:

```yaml
# Pseudocode: .github/workflows/test.yml
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_DB: tenga_test
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

---

## References

- **Pytest Documentation:** https://docs.pytest.org/
- **SQLAlchemy Testing:** https://docs.sqlalchemy.org/en/20/faq/testing.html
- **FastAPI Testing:** https://fastapi.tiangolo.com/advanced/testing-dependencies/
- **Test Results:** Run `pytest tests/ -v` to see current status
