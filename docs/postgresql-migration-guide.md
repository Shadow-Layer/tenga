# PostgreSQL Migration Guide & Database Configuration

**Status:** ✅ PostgreSQL support implemented with Alembic migrations  
**Last Updated:** October 8, 2026  
**Related:** T009 completion report, `DATABASE_CONFIGURATION.md`

---

## Overview

The Tenga Inventory POS system supports both SQLite (development) and PostgreSQL (production) databases through an Alembic-based migration system. This guide covers setup, usage, and best practices.

---

## Quick Start

### For Development (SQLite)

```bash
# Initialize database
python scripts/migrate.py init

# Apply all migrations
python scripts/migrate.py upgrade head

# Check current version
python scripts/migrate.py current
```

### For Production (PostgreSQL)

```bash
# Set connection string
export DATABASE_URL="postgresql://user:password@hostname:5432/tenga"

# Create database if needed
createdb tenga

# Apply migrations
python scripts/migrate.py upgrade head

# Verify
python scripts/migrate.py current
```

---

## Migration System Overview

### Components

1. **Alembic** - Database version control framework
2. **alembic.ini** - Alembic configuration file
3. **src/migrations/env.py** - Environment configuration
4. **src/migrations/versions/** - Migration scripts
5. **scripts/migrate.py** - CLI tool for running migrations

### Architecture

```
Database
    ↓
alembic_version table (version tracking)
    ↓
src/migrations/versions/ (migration scripts)
    ↓
alembic.ini (configuration)
    ↓
scripts/migrate.py (CLI interface)
```

---

## Database Configuration

### Environment Variables

```bash
# SQLite (default)
DATABASE_URL="sqlite:///tenga.db"

# PostgreSQL
DATABASE_URL="postgresql://user:password@localhost:5432/tenga"

# PostgreSQL with psycopg binary driver
DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/tenga"
```

### Configuration File

See `DATABASE_CONFIGURATION.md` for detailed setup.

### Connection Pooling (Production)

Production deployments should use connection pooling:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)
```

Currently not enabled by default; add to `src/database/config.py` for production.

---

## Schema Overview

### Current Version

- **Revision:** `b143c7e5867b`
- **Date:** October 8, 2026
- **Tables:** 11 (including alembic_version)

### Entities

```
organization                    (root tenant)
    ├── user                    (1..many members)
    ├── location                (1..many locations)
    ├── product                 (1..many products)
    │   ├── stock               (derived: qty per location)
    │   └── inventory_movement  (append-only audit trail)
    ├── till                    (1..many registers)
    │   └── till_session        (1..many sessions)
    ├── subscription            (billing state machine)
    │   └── sale                (1..many transactions)
    │       └── sale_item       (1..many line items)
    └── cached_subscription_state (device-side cache)
```

### Key Constraints

| Constraint | Purpose |
|-----------|---------|
| `organization_id` FK (all tables) | Multi-tenant isolation |
| `sku` UNIQUE per org | Product identity |
| `email` UNIQUE per org | User identity |
| `till_code` UNIQUE per org | Till identity |
| `location_code` UNIQUE per org | Location identity |
| InventoryMovement IMMUTABLE | Append-only audit trail |

### Indexes

31 indexes created for performance:

- **Foreign Keys:** All organization_id, foreign key columns
- **Uniqueness:** SKU, email, codes
- **Time-series:** created_at, updated_at
- **Composite:** organization_id + created_at (common queries)

---

## Migration Commands

### Using scripts/migrate.py (Recommended)

```bash
# Show current version
python scripts/migrate.py current

# Show migration history
python scripts/migrate.py history

# Upgrade to latest
python scripts/migrate.py upgrade head

# Upgrade one step
python scripts/migrate.py upgrade +1

# Downgrade one step
python scripts/migrate.py downgrade

# Downgrade to base (dangerous!)
python scripts/migrate.py downgrade base

# Create new migration (auto-detect changes)
python scripts/migrate.py revision --autogenerate -m "Add new_column to products"

# Initialize fresh (reset to base, then upgrade)
python scripts/migrate.py init

# Show SQL for migration (without running)
python scripts/migrate.py upgrade head --sql
```

### Using Alembic Directly

```bash
# Upgrade to latest
alembic upgrade head

# Downgrade one step
alembic downgrade -1

# Show current
alembic current

# Show history
alembic history

# Create migration with auto-detection
alembic revision --autogenerate -m "Description"
```

---

## Creating New Migrations

### When to Create

Create a migration when you:
- Add new tables
- Add/remove columns
- Change column types
- Add/remove indexes
- Add/remove constraints

### Automatic Detection

```bash
# Alembic auto-detects changes in src/models/
python scripts/migrate.py revision --autogenerate -m "Add order_id to sales"
```

This creates a migration file in `src/migrations/versions/` with changes automatically detected.

### Manual Migration

For complex changes, manually create migration:

```bash
python scripts/migrate.py revision -m "Add computed column"
```

Then edit the generated file:

```python
# src/migrations/versions/REVISION_message.py

def upgrade():
    op.add_column('product', sa.Column('computed_field', sa.String))
    op.create_index('ix_product_computed', 'product', ['computed_field'])

def downgrade():
    op.drop_index('ix_product_computed')
    op.drop_column('product', 'computed_field')
```

### Testing Migration

```bash
# Test upgrade
python scripts/migrate.py upgrade head

# Test downgrade
python scripts/migrate.py downgrade -1

# Test upgrade again
python scripts/migrate.py upgrade head
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Test migrations locally with PostgreSQL
- [ ] Backup production database
- [ ] Review migration SQL: `alembic upgrade head --sql`
- [ ] Plan downtime (if needed) or test migration on replica
- [ ] Have rollback plan

### Deployment Steps

```bash
# 1. Connect to production database
export DATABASE_URL="postgresql://prod_user:pass@prod_host:5432/tenga"

# 2. Check current version
python scripts/migrate.py current
# Expected: b143c7e5867b (or latest)

# 3. Dry-run (show SQL without executing)
python scripts/migrate.py upgrade head --sql

# 4. Execute migration
python scripts/migrate.py upgrade head

# 5. Verify
python scripts/migrate.py current
python scripts/migrate.py history
```

### Rollback Procedure

If migration fails:

```bash
# Downgrade to previous version
python scripts/migrate.py downgrade -1

# Verify
python scripts/migrate.py current

# Check application still works
pytest tests/ -v
```

---

## Multi-Environment Setup

### Development

```bash
# .env.dev
DATABASE_URL="sqlite:///dev.db"
```

### Staging

```bash
# .env.staging
DATABASE_URL="postgresql://staging_user:pass@staging_host/tenga_staging"
```

### Production

```bash
# .env.prod (never committed!)
DATABASE_URL="postgresql://prod_user:pass@prod_host/tenga_prod"
```

### Using Environments

```bash
# Load environment
source .env.prod

# Run migrations
python scripts/migrate.py upgrade head
```

---

## Troubleshooting

### Issue: "alembic_version table not found"

**Cause:** Database exists but migrations never run

**Solution:**
```bash
python scripts/migrate.py init  # Creates alembic_version table
python scripts/migrate.py upgrade head  # Applies migrations
```

### Issue: "Migration conflict" or "head is not a linear history"

**Cause:** Multiple migration branches (rare)

**Solution:**
```bash
# Show branches
alembic branches

# Merge branches (manual process)
# Edit migration files to resolve conflicts
# Test thoroughly before deploying
```

### Issue: "Upgrade fails with SQL error"

**Cause:** Schema mismatch or database incompatibility

**Solution:**
```bash
# Check what went wrong
python scripts/migrate.py upgrade head --sql  # Review SQL

# Downgrade and investigate
python scripts/migrate.py downgrade -1

# Fix models/migration
# Test locally with PostgreSQL
# Retry upgrade
```

### Issue: Performance issues after upgrade

**Cause:** Missing indexes or inefficient queries

**Solution:**
```bash
# Check indexes exist
\d+ table_name  -- PostgreSQL

# Add indexes if missing (in new migration)
python scripts/migrate.py revision --autogenerate -m "Add missing indexes"

# Profile queries
EXPLAIN ANALYZE SELECT ...;
```

---

## Schema Modifications

### Adding a Column

```python
# 1. Update model
# src/models/entities.py
class Product(BaseEntity):
    cost = Column(Float, nullable=True)  # Add this

# 2. Create migration
python scripts/migrate.py revision --autogenerate -m "Add cost to product"

# 3. Review generated migration
# src/migrations/versions/REVISION_add_cost_to_product.py

# 4. Test
python scripts/migrate.py upgrade head
python scripts/migrate.py downgrade -1
python scripts/migrate.py upgrade head

# 5. Deploy
# (follow production deployment steps)
```

### Renaming a Column

```python
# Migration file
def upgrade():
    op.alter_column('product', 'old_name', new_column_name='new_name')

def downgrade():
    op.alter_column('product', 'new_name', new_column_name='old_name')
```

### Removing a Column

**Warning:** Destructive change. Backup first.

```python
def upgrade():
    op.drop_column('product', 'deprecated_field')

def downgrade():
    op.add_column('product', 
        sa.Column('deprecated_field', sa.String, nullable=True))
```

---

## Version Control

### Committing Migrations

```bash
# After creating migration, commit both model and migration
git add src/models/entities.py
git add src/migrations/versions/REVISION_message.py
git commit -m "Add feature: [description]"
```

### Tracking Schema Version

In production, track which version is deployed:

```bash
python scripts/migrate.py current
# Output: b143c7e5867b
```

Store this in a notes file or CI/CD system.

---

## Testing Migrations

### Unit Test (SQLite)

```bash
# Migrations tested automatically on every test run
pytest tests/test_migration_system.py -v
```

### Integration Test (PostgreSQL)

```bash
# Requires TEST_POSTGRES_URL set
export TEST_POSTGRES_URL="postgresql://test:pass@localhost/tenga_test"
pytest tests/test_postgresql_integration.py -v
```

### Full Test Cycle

```bash
# 1. Fresh database
dropdb tenga_dev
createdb tenga_dev

# 2. Migrate
export DATABASE_URL="postgresql://dev:pass@localhost/tenga_dev"
python scripts/migrate.py init
python scripts/migrate.py upgrade head

# 3. Run application tests
pytest tests/ -v

# 4. Downgrade and upgrade again (test idempotency)
python scripts/migrate.py downgrade -1
python scripts/migrate.py upgrade +1

# 5. Tests should still pass
pytest tests/ -v
```

---

## Performance Tuning

### Index Strategy

Current indexes cover:

- **Uniqueness:** SKU, email, codes (prevents duplicates)
- **Foreign Keys:** All FK columns (join performance)
- **Time-series:** created_at (time-range queries)
- **Composite:** organization_id + created_at (common WHERE clauses)

For large deployments (>1M rows):
- Add index on `inventory_movement.product_id, location_id` for stock queries
- Add index on `sale.till_id, created_at` for till reports
- Consider partitioning inventory_movement by date

### Query Optimization

Stock computation is expensive (O(n) where n = movements):

```python
# Instead of computing every time
stock = db.query(func.sum(InventoryMovement.quantity)).filter(
    InventoryMovement.product_id == product_id,
    InventoryMovement.location_id == location_id
).scalar()

# Use cached Stock table
cached_stock = db.query(Stock).filter_by(
    product_id=product_id,
    location_id=location_id
).scalar().quantity
```

Stock cache is updated synchronously on each movement (see `InventoryService.record_movement()`).

---

## Security Considerations

### Database Credentials

- **Never commit .env files with real credentials**
- **Use environment variables for production**
- **Use strong passwords** (20+ characters, mixed case, symbols)
- **Limit database user permissions** to specific tables/operations
- **Use SSL/TLS** for remote PostgreSQL connections

### Access Control

```bash
# Production PostgreSQL user should have limited permissions

CREATE USER tenga_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE tenga TO tenga_user;
GRANT USAGE ON SCHEMA public TO tenga_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO tenga_user;
-- Note: Intentionally exclude DELETE to prevent accidents
```

### Audit Trail

All modifications tracked via:
- `created_at` / `updated_at` timestamps
- `recorded_by_id` in InventoryMovement (who made the change)
- Immutable InventoryMovement (no updates/deletes)

---

## References

- **Alembic Documentation:** https://alembic.sqlalchemy.org/
- **SQLAlchemy Documentation:** https://docs.sqlalchemy.org/
- **PostgreSQL Documentation:** https://www.postgresql.org/docs/
- **Database Configuration:** `DATABASE_CONFIGURATION.md`
- **Implementation Status:** `00-implementation-state-current.md`
- **T009 Completion:** `T009_COMPLETION_REPORT.md`
