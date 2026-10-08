# Tenga Inventory POS — Implementation State (Current)

**Last Updated:** October 8, 2026  
**Status:** Substantially implemented with PostgreSQL support and API layer

---

## Document Purpose

This document clarifies the current state of the Tenga Inventory POS system as of October 2026, contrasting planned requirements (in original /docs) with actual implementation. It is designed to help developers understand:

1. What has been **actually implemented** (not what was planned)
2. Which original requirements are **implemented vs deferred vs evolved**
3. Which **new decisions** were made during implementation
4. What **critical architectural decisions** are now **enforced** in code

This document should be read **alongside** the original requirements (/docs) to understand the full history of the project.

---

## Historical Context

### Documentation Timeline

**Phase 1 — Requirements & Discovery (Before implementation)**
- Original /docs files: `01-project-charter.md` through `14-requirements-traceability-matrix.md`
- These documents define the **planned MVP** for inventory management
- Written before any service code was implemented (T001-T006)
- Contain unknowns (U001-U010) representing planning-phase questions

**Phase 2 — Implementation (T001-T006)**
- Core service layer built (5 services, 10 domain entities)
- New architectural decisions made: **U006, U007, U008** (POS-specific)
- Note: These are **different** from original U001-U010 unknowns
- Test suite: 36 unit tests + planning for E2E

**Phase 3 — Integration & API (T007-T009)**
- End-to-end integration tests (8 scenarios)
- PostgreSQL persistence layer added
- API layer with FastAPI
- Authentication/authorization module
- Offline capability manager
- Alembic migration system
- Additional test suites (173 total tests)

---

## Current Implementation Architecture

### Technology Stack

| Component | Technology | Version | Status |
|-----------|-----------|---------|--------|
| Runtime | Python | 3.14+ | ✅ Working |
| ORM | SQLAlchemy | 2.1.5 | ✅ Active |
| Database (Dev) | SQLite | 3.x | ✅ Working |
| Database (Prod) | PostgreSQL | 13+ | ✅ Supported |
| Migrations | Alembic | Latest | ✅ Working |
| API Framework | FastAPI | Latest | ✅ Implemented |
| Testing | pytest | 7.4.3+ | ✅ 173 tests |
| Auth | JWT-based | Custom | ✅ Implemented |

### Core Modules

#### 1. **Database Layer** (`src/database/`)
- **Purpose:** Database configuration and session management
- **Status:** ✅ Complete (SQLite + PostgreSQL)
- **Files:**
  - `config.py` - Database engine setup, connection pooling
  - `__init__.py` - Session factory (`get_db()`)
  - `migrations.py` - Alembic integration
- **Features:**
  - Dual-mode: SQLite for dev, PostgreSQL for production
  - Connection pooling with Alembic versioning
  - Prepared for multi-tenant deployments

#### 2. **Models Layer** (`src/models/`)
- **Purpose:** Domain entities and data structures
- **Status:** ✅ Complete (10 core entities)
- **Core Entities:**
  1. **Organization** - Root tenant
  2. **User** - Application users (3 roles: Owner/Admin, Manager, Staff)
  3. **Location** - Inventory locations
  4. **Product** - Saleable items with SKU, cost, category
  5. **Till** - POS registers
  6. **Subscription** - Billing state machine (ACTIVE → GRACE → LIMITED)
  7. **Stock** - Derived cache (computed from movements)
  8. **InventoryMovement** - Immutable append-only ledger
  9. **Sale** - Transaction records
  10. **SaleItem** - Transaction line items
  11. **TillSession** - Till operational context
  12. **CachedSubscriptionState** - Device-side offline cache
- **Design Patterns:**
  - Immutable ledger (InventoryMovement)
  - Derived cache (Stock computed from movements)
  - State machine (Subscription)
  - Organization isolation via FK

#### 3. **Services Layer** (`src/services/`)
- **Purpose:** Stateless business logic
- **Status:** ✅ Complete (5 core services + additional helpers)
- **Core Services:**
  1. **SubscriptionService** - State machine (ACTIVE → GRACE → LIMITED)
  2. **InventoryService** - Ledger management, reconciliation, discrepancy detection
  3. **SaleService** - Online/offline sales, idempotent commitment
  4. **TillService** - Session management, LIMITED mode enforcement
  5. **SyncService** - Batch processing, idempotent sync, state synchronization
- **Key Characteristics:**
  - All stateless (db parameter injected)
  - All testable in isolation
  - Enforce critical decisions (U006, U007, U008)

#### 4. **API Layer** (`src/routers/`)
- **Purpose:** FastAPI REST endpoints
- **Status:** ✅ Implemented (test failures present, see Known Issues)
- **Endpoints Available:**
  - `/organizations` - Organization management
  - `/products` - Product CRUD
  - `/locations` - Location management
  - `/tills` - Till operations
  - `/sales` - Sale creation and commitment
  - `/subscriptions` - Subscription lifecycle
  - `/inventory` - Movement and stock queries
  - `/sync` - Device sync endpoint
- **Features:**
  - JWT authentication
  - Organization isolation in queries
  - Role-based authorization checks

#### 5. **Authentication/Authorization Layer** (`src/`)
- **Purpose:** User authentication and access control
- **Status:** ✅ Implemented (some test issues)
- **Features:**
  - JWT token generation and validation
  - Role-based access control (RBAC)
  - Organization-level data isolation
  - User activation/deactivation

#### 6. **Schemas** (`src/schemas/`)
- **Purpose:** Request/response validation with Pydantic
- **Status:** ✅ Complete
- **Coverage:**
  - Product, Location, Organization, User schemas
  - Sale, Subscription, Till, Inventory schemas
  - Sync protocol schemas

#### 7. **Migration System** (`src/migrations/`)
- **Purpose:** Database schema versioning with Alembic
- **Status:** ✅ Complete
- **Features:**
  - Initial schema: `b143c7e5867b` (all 10 entities)
  - Forward upgrade and downgrade support
  - Version tracking table
  - Idempotent migrations
- **Helper Script:**
  - `scripts/migrate.py` - Command-line tool for migrations

#### 8. **Offline Capability** (`src/`)
- **Purpose:** Offline device state management
- **Status:** ✅ Implemented (OfflineManager class)
- **Features:**
  - CachedSubscriptionState model
  - Pending sale queueing
  - Sync batch processing
  - Conflict detection

---

## Critical Architectural Decisions (U006, U007, U008)

**IMPORTANT NOTE:** These decisions were made **during implementation** and are **different** from the original unknowns (U001-U010) in the requirements phase. These use the same IDs (U006-U008) but refer to **completely different topics**.

### ✅ U006 — Permit & Reconcile Afterward

**Topic:** Offline oversell handling

**Decision:** Sales do not validate stock availability at the point of sale. Tills can oversell (record sales that exceed available stock). Discrepancies are detected during sync via physical inventory reconciliation and adjustment movements.

**Why:** Enables offline-first operation where tills can't query real-time inventory. Conflicts are resolved asynchronously on reconnection.

**Implementation:**
- `SaleService.create_sale()` - No stock validation
- `InventoryService.detect_discrepancy()` - Detects shortage/surplus post-sync
- Sale moves to ledger during sync; if stock insufficient, adjustment recorded

**Tested:** `test_multi_till_offline_conflict_scenario` - Two tills oversell same product, both sales committed, discrepancy detected

**Code Location:** `src/services/sale_service.py`, `src/services/inventory_service.py`

---

### ✅ U007 — Tiered Grace Periods

**Topic:** Subscription operational windows during expiry

**Decision:** When a subscription expires, the organization enters a GRACE state for a fixed duration. During GRACE, tills can still operate. After grace expires, system enters LIMITED mode (tills cannot open, read-only). Grace duration is tiered by subscription term:
- **Monthly subscriptions:** 7-day grace
- **Annual subscriptions:** 30-day grace

**Why:** Allows organizations to resolve billing issues without immediately losing access to POS during subscription renewal delays.

**Implementation:**
- `SubscriptionService.compute_current_state()` - Calculates state from expiry_date + grace_duration
- `TillService.assert_open_allowed()` - Checks state; raises if LIMITED
- Grace periods defined in `src/models/subscription.py`

**Tested:**
- `test_monthly_grace_is_7_days` - Monthly grace = 7 days
- `test_annual_grace_is_30_days` - Annual grace = 30 days
- `test_can_open_when_grace` - Till operations allowed during GRACE
- `test_cannot_open_when_limited` - Till operations blocked in LIMITED

**Code Location:** `src/services/subscription_service.py`, `src/models/subscription.py`

---

### ✅ U008 — Offline Optimism

**Topic:** Offline device state validation

**Decision:** Devices (tills) cache the subscription state from the last successful sync. While offline, devices operate optimistically using the cached state. On reconnection, the server provides current state; if changed (e.g., subscription expired), cache updates and next operation is validated against new state.

**Why:** Allows offline tills to remain operational as long as the cached state permits, without requiring server queries. Once reconnected, server enforces current state.

**Implementation:**
- `CachedSubscriptionState` model - Stores last-synced subscription state
- `SyncService.get_subscription_state_sync()` - Returns current state on sync
- `TillService` checks both: server-side (if online) or cached (if offline)
- Cache updates on sync receipt

**Tested:**
- `test_allow_with_cached_active` - Offline till with cached ACTIVE state allows operations
- `test_allow_with_cached_grace` - Offline till with cached GRACE state allows operations
- `test_block_with_cached_limited` - Offline till with cached LIMITED state blocks operations
- `test_offline_device_cache_update_on_sync` - Cache updates when reconnecting

**Code Location:** `src/models/cached_subscription_state.py`, `src/services/sync_service.py`, `src/services/till_service.py`

---

## Relationship Between Original & New Decisions

### **CRITICAL CLARIFICATION:**

The original requirements documents (/docs) contain **unknowns U001-U010** which are **planning questions** from the MVP phase.

This document and implementation artifacts reference **decisions U006-U008** which are **POS-specific architectural decisions** made during implementation.

**These use the same ID numbers but refer to COMPLETELY DIFFERENT CONCEPTS.**

| ID | Original (U001-U010) | Implementation (U006-U008) |
|----|----------------------|--------------------------|
| U006 | Regulatory/fiscal requirements | Permit & Reconcile Afterward |
| U007 | Arrupe accountability model | Tiered Grace Periods |
| U008 | Grocery count methodology | Offline Optimism |

The original unknowns were about **planning questions for the MVP**. The implementation decisions are about **POS-specific technical architecture**.

**To avoid future confusion:**
- Original planning unknowns: U001-U010 (in `/docs/unknowns-register.md`)
- Implementation decisions: U006-U008 (documented in this file and implementation artifacts)
- New naming scheme recommended for future decisions to avoid collision

---

## Implementation vs Planned Requirements

### ✅ IMPLEMENTED (from original MVP scope)

- Core inventory model (products, locations, stock)
- Movement ledger (append-only, immutable)
- Physical inventory counting
- Stock reconciliation
- Multi-tenant organization isolation
- User management with roles
- Audit trail
- Basic reporting

### ⏸️ EVOLVED/EXTENDED (beyond original MVP)

- **POS Integration** - Original scope was inventory-only; now includes sales transactions
- **Subscription Model** - Not in original MVP; added for billing cycles
- **Offline Capability** - Original planned for post-MVP; now core architecture
- **Till Sessions** - Not in original requirements; added for POS
- **Grace Periods** - Not in original requirements; added for SaaS billing
- **API Layer** - Original didn't specify; now RESTful with FastAPI
- **Authentication** - Original didn't specify; now JWT-based with roles
- **PostgreSQL** - Original was SQLite; PostgreSQL now supported via Alembic

### ❓ NOT YET IMPLEMENTED (deferred from original scope)

- CSV import for opening balances (U004 in original unknowns)
- Advanced integrations with ERP/accounting systems (U005)
- Complex permission models beyond 3 roles
- Formal audit export for compliance (U006 in original unknowns)
- Advanced barcode/RFID tracking
- Multi-organization federation (prepared in code but not tested)

---

## Test Coverage Summary

### Current Status
- **Total Tests:** 173
- **Passing:** 98
- **Failing:** 18
- **Skipped:** 13

### Test Categories

| Category | File | Count | Status |
|----------|------|-------|--------|
| Unit Tests — Subscription | `test_subscription_service.py` | 12 | ✅ Passing |
| Unit Tests — Sales/Inventory | `test_sales_inventory.py` | 12 | ⚠️ Some failing |
| Unit Tests — Till | `test_till_service.py` | 12 | ⚠️ Some failing |
| E2E Integration | `test_integration_e2e.py` | 8 | ⚠️ Some failing |
| PostgreSQL Integration | `test_postgresql_integration.py` | 31 | ⏸️ Skipped by default |
| Migration System | `test_migration_system.py` | 8 | ✅ Passing |
| API Tests | `test_api_*.py` | ~35 | ⚠️ Multiple errors |
| Auth/Security | `test_security_auth.py` | ~17 | ⚠️ Some failing |
| Offline Capability | `test_offline_capability.py` | ~22 | ⚠️ Some failing |

### Known Test Issues
- API layer tests have SQLAlchemy integration errors
- Some offline tests failing (offline manager edge cases)
- Auth tests have integration issues (route not found)
- Note: See Known Issues section below

---

## Known Limitations

### By Design
1. **Single Database Connection** - Services get single db session; prepared for connection pooling
2. **Organization Isolation** - Assumes single org per deployment; multi-org uses shared FK, not row-level security
3. **No Cascade Deletes** - Entities can't be deleted if referenced; by design for audit trail
4. **Subscription State Computed** - Not stored; computed on-the-fly from dates
5. **SQLite for Dev, PostgreSQL for Prod** - Development uses SQLite; production should use PostgreSQL

### Not Yet Implemented
1. **Connection Pooling** - Prepared in config but not exposed
2. **Advanced RBAC** - Only 3 roles; granular permissions deferred
3. **Formal Audit Export** - No compliance export formats
4. **Multi-Org Federation** - Code prepared but untested
5. **Payment Processing** - Out of scope (external system)

### Test Failures (To Be Investigated)
1. API route errors in several test files (likely FastAPI integration issue)
2. Some offline manager tests failing (edge case in cache invalidation)
3. Auth tests failing (route configuration issue)

---

## Database Schema

### 11 Core Tables (plus Alembic version)

```
organization                    (root tenant)
├── user                        (members, 3 roles)
├── location                    (inventory locations)
├── product                     (items, SKU unique)
│   ├── stock                   (derived: qty per location)
│   └── inventory_movement      (append-only ledger)
├── till                        (POS registers)
│   └── till_session            (operational context)
├── subscription                (billing state machine)
│   └── sale                    (transactions)
│       └── sale_item           (line items)
└── cached_subscription_state   (offline device cache)

Key Constraints:
- organization_id FK required on all entities except Organization
- SKU unique per organization
- Email unique per organization
- Stock is derived cache (recalculated on each movement)
- InventoryMovement is immutable (no UPDATE/DELETE)
```

---

## Migration Guide

### For Development (SQLite)

```bash
# Initialize new database
python scripts/migrate.py init

# Apply latest migrations
python scripts/migrate.py upgrade head

# Check current version
python scripts/migrate.py current

# Show history
python scripts/migrate.py history
```

### For Production (PostgreSQL)

```bash
# Set PostgreSQL connection string
export DATABASE_URL=postgresql://user:pass@localhost/tenga

# Apply migrations
python scripts/migrate.py upgrade head

# Verify
python scripts/migrate.py current
```

### Creating New Migrations

```bash
# Auto-detect changes in models
python scripts/migrate.py revision --autogenerate -m "Add new_column to products"

# Review migration file in src/migrations/versions/
# Then apply
python scripts/migrate.py upgrade head
```

---

## API Summary

### Authentication
- POST `/auth/login` - Get JWT token
- POST `/auth/refresh` - Refresh token
- GET `/auth/me` - Current user

### Organizations
- GET `/organizations` - List (auth required)
- POST `/organizations` - Create (owner only)
- GET `/organizations/{id}` - Details

### Products
- GET `/products` - List per org
- POST `/products` - Create
- GET `/products/{id}` - Details
- PUT `/products/{id}` - Update

### Locations
- GET `/locations` - List per org
- POST `/locations` - Create
- GET `/locations/{id}` - Details

### Sales
- POST `/sales` - Create sale
- GET `/sales/{id}` - Get sale details
- POST `/sales/{id}/commit` - Commit pending sale

### Subscriptions
- POST `/subscriptions` - Create subscription
- GET `/subscriptions/{id}` - Get state
- POST `/subscriptions/{id}/renew` - Renew subscription

### Inventory
- POST `/inventory/movements` - Record movement
- GET `/inventory/stock` - Query stock per location
- POST `/inventory/discrepancy` - Check discrepancy

### Sync
- POST `/sync/batch` - Submit batch of sales/movements
- GET `/sync/state` - Get subscription state

---

## Quick Start

### Install

```bash
pip install -r requirements.txt
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# Only passing tests (skip known failures)
pytest tests/test_subscription_service.py tests/test_migration_system.py -v

# PostgreSQL tests (requires TEST_POSTGRES_URL)
export TEST_POSTGRES_URL=postgresql://...
pytest tests/test_postgresql_integration.py -v
```

### Initialize Database

```bash
python -c "from src.database import init_db; init_db()"
```

### Use Services

```python
from src.services import SubscriptionService, SaleService, TillService
from src.database import get_db

db = next(get_db())

# Check subscription state
sub = db.query(Subscription).first()
state = SubscriptionService.compute_current_state(sub)  # ACTIVE, GRACE, LIMITED

# Create sale
sale = SaleService.create_sale(
    till_id=1,
    items=[{"product_id": 1, "quantity": 5}],
    db=db
)
```

---

## Next Steps for Continued Development

### Immediate (Phase 2 work)
1. **Fix API Tests** - Debug SQLAlchemy integration in API routes
2. **Resolve Auth Integration** - Ensure JWT token validation works in all endpoints
3. **Complete Offline Manager** - Finalize OfflineManager edge cases

### Short-term (T010+)
1. **DevOps/Deployment** - Docker, Kubernetes, production PostgreSQL setup
2. **Monitoring** - Metrics, logs, dashboards
3. **Performance Tuning** - Query optimization, caching
4. **User Interface** - Web/mobile UI consuming API

### Medium-term (Roadmap)
1. **Advanced RBAC** - Granular permission model
2. **Payment Integration** - Subscription billing
3. **ERP Integrations** - Accounting, purchasing systems
4. **Multi-org Support** - Federation, data sharing

---

## References

For more details, see:
- `STATUS.md` - Architecture and deployment
- `FINAL_COMPLETION_REPORT.md` - Comprehensive handoff
- `QUICK_START.md` - Getting started
- `DATABASE_CONFIGURATION.md` - Database setup
- `/docs/` - Original requirements
- Implementation tickets: T001-T006, T007, T009
