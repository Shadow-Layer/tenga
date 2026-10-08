"""PostgreSQL and Migration Configuration Guide for Tenga Inventory POS.

This document describes how to configure and use the database persistence layer
with PostgreSQL and Alembic migrations.
"""

# PostgreSQL Configuration

## Environment Variables

The database configuration uses environment variables:

- `DATABASE_URL`: Full database connection URL
  - SQLite (default): `sqlite:////path/to/tenga.db`
  - PostgreSQL: `postgresql://user:password@localhost/tenga`
  
  Default: `sqlite:////home/tea/Documents/apps/tenga-inventory/tenga.db`

- `SQL_ECHO`: Enable SQL query logging (true/false)
  Default: false

### PostgreSQL-Specific Variables

- `DB_POOL_SIZE`: Connection pool size (default: 10)
- `DB_MAX_OVERFLOW`: Maximum overflow connections (default: 20)

## Example .env Configuration

```env
# SQLite (development/testing)
DATABASE_URL=sqlite:////path/to/tenga.db

# PostgreSQL (production)
DATABASE_URL=postgresql://tenga:password@localhost:5432/tenga
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
SQL_ECHO=false
```

# Database Migrations

The project uses Alembic for version-controlled database migrations.

## Migration System Structure

```
src/migrations/
  env.py                              # Alembic environment config
  script.py.mako                      # Migration template
  versions/
    b143c7e5867b_initial_schema_...py # Initial schema migration
alembic.ini                           # Alembic configuration
```

## Running Migrations

### Initialize Database (First Run)

```bash
# With Alembic (recommended)
alembic upgrade head

# Or use the legacy init_db helper
python -c "from src.database import init_db; init_db()"
```

### Upgrade to Latest Schema

```bash
alembic upgrade head
```

### Downgrade to Previous Version

```bash
# Go back one migration
alembic downgrade -1

# Go back to base (drop all tables)
alembic downgrade base
```

### Check Current Migration Version

```bash
alembic current
```

### View Migration History

```bash
alembic history
```

## Creating New Migrations

When domain models change:

```bash
# Auto-generate migration based on model changes
alembic revision --autogenerate -m "Add new table or column"

# Edit the migration file in src/migrations/versions/
# Review the upgrade() and downgrade() functions

# Test the migration
alembic upgrade head
alembic downgrade -1
```

## Migration Best Practices

1. **Always review auto-generated migrations** before applying
2. **Test upgrade AND downgrade** locally before production
3. **Include rollback support** (downgrade function)
4. **Keep migrations small and focused** on single logical change
5. **Never modify existing migrations** - create new ones instead
6. **Test with both SQLite and PostgreSQL** if possible

# Schema Overview

## Tables (10 entities)

### Core Organization
- **organization**: Tenant/organization record (single per deployment)

### Users & Roles
- **user**: Application users with roles (operator, manager, admin)

### Inventory Management
- **location**: Physical or logical inventory locations
- **product**: Saleable items
- **stock**: Computed stock quantity cache (from inventory movements)
- **inventory_movement**: Append-only audit trail of all inventory changes

### POS Operations
- **till**: Logical till/register
- **till_session**: Operational context (till opened/closed by operator)
- **sale**: Completed transaction
- **sale_item**: Line items in a sale

### Subscriptions
- **subscription**: Billing state machine

## Key Constraints

### Uniqueness
- organization.code: unique
- organization.name: unique
- product.sku: unique per organization
- user.email: unique per organization
- till.code: unique per organization
- location.code: unique per organization

### Foreign Keys (Organization Isolation)
All entities except Organization have `organization_id` FK to organization table.
This ensures complete data isolation by organization (multi-tenant).

### Immutable Tables
- **inventory_movement**: Append-only, cannot be updated or deleted

### Derived/Cached Tables
- **stock**: Computed from inventory_movement ledger (SUM(IN) - SUM(OUT))

## Indexes

Indexes are created for:
- Foreign key columns
- Commonly searched fields (email, code, etc.)
- Time-based queries (created_at, updated_at)
- Composite indexes for multi-column queries

# Testing Database Connections

## SQLite (Default)

Tests use in-memory SQLite by default:

```bash
pytest tests/
```

All 82 existing tests pass with SQLite.

## PostgreSQL Integration Tests

To run PostgreSQL-specific tests:

```bash
# Start a PostgreSQL container (example using Docker)
docker run -d \
  --name tenga-postgres \
  -e POSTGRES_DB=tenga_test \
  -e POSTGRES_USER=tenga \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:15

# Set test database URL
export TEST_POSTGRES_URL="postgresql://tenga:password@localhost:5432/tenga_test"

# Run PostgreSQL integration tests
pytest tests/test_postgresql_integration.py -v

# Stop container
docker stop tenga-postgres && docker rm tenga-postgres
```

PostgreSQL integration tests verify:
- Schema creation
- Data persistence
- Organization isolation
- Transaction semantics
- Index performance
- Foreign key constraints

## Migration System Tests

```bash
pytest tests/test_migration_system.py -v
```

Tests verify:
- Alembic configuration
- Migration up/down
- Schema version tracking
- Idempotency

# Service Layer & Transactions

The services use database sessions with proper transaction management:

### Atomic Operations
- SaleService.create_sale: Creates sale with items in single transaction
- InventoryService.record_movement: Records movement atomically
- SaleService.commit_pending_sale: Commits with idempotency check

### Transaction Behavior
- Services accept optional `db` session (for dependency injection)
- Sessions auto-commit after each operation
- Rollback prevents duplicate records on retry
- Idempotency checks prevent duplicate inventory movements

### Example: Safe Sale Creation

```python
from src.services.sale_service import SaleService
from src.database import SessionLocal

db = SessionLocal()
try:
    sale = SaleService.create_sale(
        organization_id=1,
        till_id=1,
        cashier_id=1,
        payment_method="CASH",
        items=[
            {"product_id": 1, "quantity": 2, "unit_price": 10.00},
        ],
        db=db
    )
    # Sale persisted, inventory movements recorded
    db.commit()
except Exception as e:
    db.rollback()
    raise
finally:
    db.close()
```

# Production Deployment Checklist

- [ ] Set DATABASE_URL to PostgreSQL connection string
- [ ] Set DB_POOL_SIZE appropriately for expected load
- [ ] Run migrations: `alembic upgrade head`
- [ ] Verify schema: `alembic current`
- [ ] Test database connection: `curl https://localhost:8000/ready`
- [ ] Monitor database: Check connection pool, query performance
- [ ] Backup strategy: Regular PostgreSQL backups
- [ ] Monitoring: Set up alerts on database availability

# Troubleshooting

## Connection Refused

```
Error: Connection refused on postgresql://localhost/tenga
```

Check:
- PostgreSQL is running
- Correct host/port in DATABASE_URL
- Database exists
- User has permissions

## Migration Conflicts

```
Error: Target database is not up to date
```

Check current version and conflicts:
```bash
alembic current
alembic branches
```

## Duplicate Record on Retry

The sales service uses idempotency checks:
```python
# In SaleService._generate_movements_for_sale
existing = db.query(InventoryMovement).filter(
    InventoryMovement.reference_type == "SALE",
    InventoryMovement.reference_id == sale.id,
    InventoryMovement.product_id == sale_item.product_id,
).first()

if existing:
    continue  # Skip if already created
```

This ensures retries don't create duplicate movements.

# Performance Considerations

## Connection Pooling

PostgreSQL uses connection pooling:
- Default pool_size=10
- max_overflow=20 allows temporary overflow
- pool_pre_ping=True verifies connections before use
- pool_recycle=3600 recycles connections after 1 hour

## Query Optimization

Indexes on frequently queried columns:
- organization_id (all tables)
- created_at (time-series queries)
- SKU/code/email (lookups)
- Foreign keys (joins)

## Stock Cache

Stock table is a computed view:
- Updated after each inventory movement
- Provides O(1) stock queries
- Calculated from append-only ledger

# References

- Alembic Documentation: https://alembic.sqlalchemy.org
- SQLAlchemy Documentation: https://docs.sqlalchemy.org
- PostgreSQL Connection Strings: https://www.postgresql.org/docs/current/libpq-connect.html
