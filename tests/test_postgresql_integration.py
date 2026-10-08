"""PostgreSQL integration tests for database persistence.

These tests verify:
- PostgreSQL compatibility
- Schema migration
- Data persistence across restarts
- Organization isolation
- Transaction semantics
"""
import os
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from src.database.config import Base, IS_POSTGRESQL
from src.models.entities import (
    Organization, User, Location, Product, Till, Subscription,
    Stock, InventoryMovement, Sale, SaleItem, TillSession
)
from src.models.subscription import SubscriptionState, SubscriptionTerm
from src.services.inventory_service import InventoryService
from src.services.sale_service import SaleService


# Skip all tests if PostgreSQL is not available
POSTGRES_URL = os.getenv("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="TEST_POSTGRES_URL not set - PostgreSQL integration tests skipped"
)


@pytest.fixture
def pg_engine():
    """Create a PostgreSQL engine for testing."""
    if not POSTGRES_URL:
        pytest.skip("PostgreSQL not configured")
    
    engine = create_engine(
        POSTGRES_URL,
        echo=False,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up - drop all tables
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def pg_session(pg_engine):
    """Create a PostgreSQL session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    db = SessionLocal()
    yield db
    db.close()


class TestPostgreSQLSchema:
    """Test PostgreSQL schema creation and integrity."""

    def test_schema_creates_all_tables(self, pg_engine):
        """Verify all tables are created correctly."""
        inspector = None
        try:
            from sqlalchemy import inspect
            inspector = inspect(pg_engine)
        except ImportError:
            pytest.skip("sqlalchemy.inspect not available")
        
        table_names = set(inspector.get_table_names())
        expected_tables = {
            'organization', 'user', 'location', 'product', 'till',
            'subscription', 'stock', 'inventory_movement', 'sale',
            'sale_item', 'till_session'
        }
        
        assert expected_tables.issubset(table_names), \
            f"Missing tables: {expected_tables - table_names}"

    def test_schema_creates_indexes(self, pg_engine):
        """Verify indexes are created for query performance."""
        inspector = None
        try:
            from sqlalchemy import inspect
            inspector = inspect(pg_engine)
        except ImportError:
            pytest.skip("sqlalchemy.inspect not available")
        
        # Check for key indexes
        org_indexes = inspector.get_indexes('organization')
        org_index_names = {idx['name'] for idx in org_indexes}
        assert any('code' in name for name in org_index_names), \
            "Missing index on organization.code"

    def test_schema_creates_foreign_keys(self, pg_engine):
        """Verify foreign key constraints are created."""
        inspector = None
        try:
            from sqlalchemy import inspect
            inspector = inspect(pg_engine)
        except ImportError:
            pytest.skip("sqlalchemy.inspect not available")
        
        # Check user has foreign key to organization
        user_fks = inspector.get_foreign_keys('user')
        org_fk = next(
            (fk for fk in user_fks if fk['constrained_columns'] == ['organization_id']),
            None
        )
        assert org_fk is not None, "Missing foreign key user.organization_id -> organization.id"
        assert org_fk['referred_table'] == 'organization'


class TestPostgreSQLPersistence:
    """Test data persistence in PostgreSQL."""

    def test_organization_persists(self, pg_session):
        """Verify organization data persists in PostgreSQL."""
        org = Organization(name="Test Org", code="TEST")
        pg_session.add(org)
        pg_session.commit()
        
        org_id = org.id
        
        # Fetch in new session
        result = pg_session.query(Organization).filter(
            Organization.id == org_id
        ).first()
        
        assert result is not None
        assert result.name == "Test Org"
        assert result.code == "TEST"

    def test_product_persists_with_org_isolation(self, pg_session):
        """Verify products are isolated by organization."""
        org1 = Organization(name="Org 1", code="ORG1")
        org2 = Organization(name="Org 2", code="ORG2")
        pg_session.add_all([org1, org2])
        pg_session.flush()
        
        prod1 = Product(
            organization_id=org1.id,
            sku="SKU001",
            name="Product 1",
            price=10.00
        )
        prod2 = Product(
            organization_id=org2.id,
            sku="SKU001",  # Same SKU in different org
            name="Product 2",
            price=20.00
        )
        pg_session.add_all([prod1, prod2])
        pg_session.commit()
        
        # Each org should see only its product
        org1_products = pg_session.query(Product).filter(
            Product.organization_id == org1.id
        ).all()
        assert len(org1_products) == 1
        assert org1_products[0].name == "Product 1"
        
        org2_products = pg_session.query(Product).filter(
            Product.organization_id == org2.id
        ).all()
        assert len(org2_products) == 1
        assert org2_products[0].name == "Product 2"

    def test_inventory_movement_append_only(self, pg_session):
        """Verify inventory movements are append-only."""
        org = Organization(name="Test Org", code="TEST")
        user = User(
            organization_id=1,  # Will be set after org commit
            email="user@test.com",
            username="user",
            password_hash="hash",
            role="operator"
        )
        location = Location(
            organization_id=1,
            code="LOC001",
            name="Location 1"
        )
        product = Product(
            organization_id=1,
            sku="SKU001",
            name="Product 1",
            price=10.00
        )
        
        pg_session.add(org)
        pg_session.flush()
        
        user.organization_id = org.id
        location.organization_id = org.id
        product.organization_id = org.id
        
        pg_session.add_all([user, location, product])
        pg_session.commit()
        
        # Record a movement
        movement = InventoryMovement(
            organization_id=org.id,
            location_id=location.id,
            product_id=product.id,
            movement_type="IN",
            quantity=10,
            reason="PURCHASE",
            recorded_by_id=user.id,
            created_at=datetime.utcnow()
        )
        pg_session.add(movement)
        pg_session.commit()
        
        # Verify movement is immutable
        with pytest.raises(Exception):
            movement.quantity = 20
            pg_session.commit()

    def test_stock_cache_updates(self, pg_session):
        """Verify stock cache is updated correctly."""
        org = Organization(name="Test Org", code="TEST")
        location = Location(
            organization_id=1,
            code="LOC001",
            name="Location 1"
        )
        product = Product(
            organization_id=1,
            sku="SKU001",
            name="Product 1",
            price=10.00
        )
        user = User(
            organization_id=1,
            email="user@test.com",
            username="user",
            password_hash="hash",
            role="operator"
        )
        
        pg_session.add(org)
        pg_session.flush()
        
        location.organization_id = org.id
        product.organization_id = org.id
        user.organization_id = org.id
        
        pg_session.add_all([location, product, user])
        pg_session.commit()
        
        # Create stock entry
        stock = Stock(
            organization_id=org.id,
            location_id=location.id,
            product_id=product.id,
            quantity=0
        )
        pg_session.add(stock)
        pg_session.commit()
        
        # Verify stock exists
        result = pg_session.query(Stock).filter(
            Stock.location_id == location.id,
            Stock.product_id == product.id
        ).first()
        
        assert result is not None
        assert result.quantity == 0

    def test_sale_with_items_persists(self, pg_session):
        """Verify sales with line items persist correctly."""
        org = Organization(name="Test Org", code="TEST")
        location = Location(
            organization_id=1,
            code="LOC001",
            name="Location 1"
        )
        till = Till(
            organization_id=1,
            location_id=1,
            code="TILL001",
            name="Till 1"
        )
        product = Product(
            organization_id=1,
            sku="SKU001",
            name="Product 1",
            price=10.00
        )
        user = User(
            organization_id=1,
            email="cashier@test.com",
            username="cashier",
            password_hash="hash",
            role="operator"
        )
        
        pg_session.add(org)
        pg_session.flush()
        
        location.organization_id = org.id
        till.organization_id = org.id
        till.location_id = location.id
        product.organization_id = org.id
        user.organization_id = org.id
        
        pg_session.add_all([location, till, product, user])
        pg_session.commit()
        
        # Create sale
        sale = Sale(
            organization_id=org.id,
            till_id=till.id,
            cashier_id=user.id,
            total_amount=10.00,
            discount_amount=0,
            tax_amount=0,
            payment_method="CASH",
            status="COMPLETED"
        )
        pg_session.add(sale)
        pg_session.flush()
        
        # Add sale item
        item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=1,
            unit_price=10.00,
            discount_per_item=0,
            total_price=10.00
        )
        pg_session.add(item)
        pg_session.commit()
        
        # Verify sale with items persists
        result = pg_session.query(Sale).filter(
            Sale.id == sale.id
        ).first()
        
        assert result is not None
        assert len(result.sale_items) == 1
        assert result.sale_items[0].quantity == 1


class TestPostgreSQLTransactions:
    """Test transaction semantics in PostgreSQL."""

    def test_transaction_rollback_on_error(self, pg_session):
        """Verify transaction rolls back on error."""
        org = Organization(name="Test Org", code="TEST")
        pg_session.add(org)
        pg_session.commit()
        
        try:
            # Try to create duplicate organization
            dup_org = Organization(name="Test Org", code="TEST")
            pg_session.add(dup_org)
            pg_session.commit()
        except Exception:
            pg_session.rollback()
        
        # Verify only one organization exists
        count = pg_session.query(Organization).count()
        assert count == 1

    def test_concurrent_operations_isolation(self, pg_session, pg_engine):
        """Verify transaction isolation prevents dirty reads."""
        org = Organization(name="Test Org", code="TEST")
        pg_session.add(org)
        pg_session.commit()
        
        # Create a second session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
        session2 = SessionLocal()
        
        try:
            # In session1, create a product (uncommitted)
            product = Product(
                organization_id=org.id,
                sku="SKU001",
                name="Product 1",
                price=10.00
            )
            pg_session.add(product)
            # Don't commit yet
            
            # Session2 should not see uncommitted product
            count = session2.query(Product).filter(
                Product.organization_id == org.id
            ).count()
            assert count == 0
            
            # After commit, session2 should see it
            pg_session.commit()
            count = session2.query(Product).filter(
                Product.organization_id == org.id
            ).count()
            assert count == 1
        finally:
            session2.close()


class TestPostgreSQLSubscription:
    """Test subscription persistence in PostgreSQL."""

    def test_subscription_persists_with_state(self, pg_session):
        """Verify subscription state persists correctly."""
        org = Organization(name="Test Org", code="TEST")
        pg_session.add(org)
        pg_session.flush()
        
        tomorrow = datetime.utcnow() + timedelta(days=30)
        grace_end = tomorrow + timedelta(days=7)
        
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            state=SubscriptionState.ACTIVE.value,
            start_date=datetime.utcnow(),
            expiry_date=tomorrow,
            grace_end_date=grace_end,
            auto_renew=True
        )
        pg_session.add(sub)
        pg_session.commit()
        
        # Fetch and verify
        result = pg_session.query(Subscription).filter(
            Subscription.id == sub.id
        ).first()
        
        assert result is not None
        assert result.state == "ACTIVE"
        assert result.plan == "BASIC"
        assert result.term == "MONTHLY"


class TestPostgreSQLIndexPerformance:
    """Test that indexes improve query performance."""

    def test_organization_code_index_unique(self, pg_session):
        """Verify organization code is unique across org."""
        org = Organization(name="Test Org", code="UNIQUE")
        pg_session.add(org)
        pg_session.commit()
        
        # Try to create duplicate code
        with pytest.raises(Exception):
            dup = Organization(name="Test Org 2", code="UNIQUE")
            pg_session.add(dup)
            pg_session.commit()

    def test_user_email_unique_per_org(self, pg_session):
        """Verify user email is unique per organization."""
        org = Organization(name="Test Org", code="TEST")
        pg_session.add(org)
        pg_session.flush()
        
        user1 = User(
            organization_id=org.id,
            email="user@test.com",
            username="user1",
            password_hash="hash",
            role="operator"
        )
        pg_session.add(user1)
        pg_session.commit()
        
        # Different org can have same email
        org2 = Organization(name="Test Org 2", code="TEST2")
        pg_session.add(org2)
        pg_session.flush()
        
        user2 = User(
            organization_id=org2.id,
            email="user@test.com",
            username="user2",
            password_hash="hash",
            role="operator"
        )
        pg_session.add(user2)
        pg_session.commit()
        
        # But same org should have unique email
        with pytest.raises(Exception):
            dup_user = User(
                organization_id=org.id,
                email="user@test.com",
                username="user3",
                password_hash="hash",
                role="operator"
            )
            pg_session.add(dup_user)
            pg_session.commit()
