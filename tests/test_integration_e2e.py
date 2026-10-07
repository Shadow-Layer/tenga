"""
End-to-End Integration Tests for T007

Comprehensive testing of:
1. Basic POS flow (org → subscription → till → sales)
2. Multi-till scenarios
3. Offline scenarios (single and multi-till with conflicts)
4. Inventory adjustments
5. Subscription expiry and grace periods
6. Offline subscription expiry
7. Idempotency guarantees
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.database import SessionLocal, init_db, drop_db
from src.models.entities import (
    Organization, User, Location, Product, Till,
    Subscription, TillSession, Sale, SaleItem, 
    InventoryMovement, Stock
)
from src.models.subscription import SubscriptionState, SubscriptionTerm
from src.models.cached_subscription_state import CachedSubscriptionState
from src.services.subscription_service import SubscriptionService
from src.services.inventory_service import InventoryService
from src.services.sale_service import SaleService
from src.services.till_service import TillService
from src.services.sync_service import SyncService


@pytest.fixture(scope="function")
def db():
    """Fresh database for each test."""
    drop_db()
    init_db()
    db = SessionLocal()
    yield db
    db.close()


class TestBasicPOSFlow:
    """E2E Scenario 1: Basic POS Flow"""
    
    def test_complete_pos_flow(self, db):
        """
        User creates organization, subscription, location, tills, products.
        User logs into till, opens session, records sales, closes session.
        Verify: sales in inventory, stock correct, session closed.
        """
        # 1. Create organization
        org = Organization(name="Coffee Shop", code="COFFEE")
        db.add(org)
        db.commit()
        
        # 2. Create subscription (ACTIVE)
        sub = Subscription(
            organization_id=org.id,
            plan="PRO",
            term=SubscriptionTerm.MONTHLY.value,
            expiry_date=datetime.utcnow() + timedelta(days=30),
        )
        db.add(sub)
        db.commit()
        
        # 3. Create location and products
        location = Location(
            organization_id=org.id,
            code="MAIN",
            name="Main Store",
        )
        db.add(location)
        db.commit()
        
        product_coffee = Product(
            organization_id=org.id,
            sku="COFFEE1",
            name="Espresso",
            price=3.50,
        )
        product_tea = Product(
            organization_id=org.id,
            sku="TEA1",
            name="Green Tea",
            price=2.50,
        )
        db.add_all([product_coffee, product_tea])
        db.commit()
        
        # 4. Create till
        till = Till(
            organization_id=org.id,
            location_id=location.id,
            code="TILL1",
            name="Front Counter",
        )
        db.add(till)
        db.commit()
        
        # 5. Create cashier
        cashier = User(
            organization_id=org.id,
            email="cashier@coffee.com",
            username="cashier",
            full_name="Alice Barista",
            password_hash="hash",
        )
        db.add(cashier)
        db.commit()
        
        # 6. Open till session
        session = TillService.open_session(
            organization_id=org.id,
            till_id=till.id,
            operator_id=cashier.id,
            opening_balance=100.00,
            db=db,
        )
        assert session.status == "OPEN"
        
        # 7. Record sales
        sale1 = SaleService.create_sale(
            organization_id=org.id,
            till_id=till.id,
            cashier_id=cashier.id,
            payment_method="CASH",
            items=[
                {"product_id": product_coffee.id, "quantity": 2, "unit_price": 3.50},
                {"product_id": product_tea.id, "quantity": 1, "unit_price": 2.50},
            ],
            db=db,
        )
        assert sale1.status == "COMPLETED"
        assert sale1.total_amount == 9.50
        
        # 8. Close session
        session_closed = TillService.close_session(
            session.id,
            closing_balance=109.50,
            db=db,
        )
        assert session_closed.status == "CLOSED"
        
        # 9. Verify: stock reflects sales
        coffee_stock = InventoryService.compute_stock_at_location(
            org.id, product_coffee.id, location.id, db
        )
        tea_stock = InventoryService.compute_stock_at_location(
            org.id, product_tea.id, location.id, db
        )
        assert coffee_stock == -2  # 0 - 2 sold
        assert tea_stock == -1     # 0 - 1 sold


class TestMultiTillScenario:
    """E2E Scenario 2: Multi-Till Simultaneous Operation"""
    
    def test_multi_till_sales(self, db):
        """Two users, two tills, same location. Sales correctly attributed."""
        org = Organization(name="Bakery", code="BAKERY")
        db.add(org)
        db.commit()
        
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            expiry_date=datetime.utcnow() + timedelta(days=30),
        )
        db.add(sub)
        db.commit()
        
        location = Location(organization_id=org.id, code="LOC1", name="Main")
        db.add(location)
        db.commit()
        
        product = Product(
            organization_id=org.id,
            sku="BREAD",
            name="Sourdough",
            price=5.00,
        )
        db.add(product)
        db.commit()
        
        # Create two tills
        till_a = Till(
            organization_id=org.id,
            location_id=location.id,
            code="TILL_A",
            name="Till A",
        )
        till_b = Till(
            organization_id=org.id,
            location_id=location.id,
            code="TILL_B",
            name="Till B",
        )
        db.add_all([till_a, till_b])
        db.commit()
        
        # Create two cashiers
        cashier_a = User(
            organization_id=org.id,
            email="cashier_a@bakery.com",
            username="cashier_a",
            full_name="Alice",
            password_hash="hash",
        )
        cashier_b = User(
            organization_id=org.id,
            email="cashier_b@bakery.com",
            username="cashier_b",
            full_name="Bob",
            password_hash="hash",
        )
        db.add_all([cashier_a, cashier_b])
        db.commit()
        
        # Open sessions on both tills
        session_a = TillService.open_session(
            org.id, till_a.id, cashier_a.id, db=db
        )
        session_b = TillService.open_session(
            org.id, till_b.id, cashier_b.id, db=db
        )
        
        # Both create sales
        sale_a = SaleService.create_sale(
            org.id, till_a.id, cashier_a.id, "CASH",
            [{"product_id": product.id, "quantity": 3, "unit_price": 5.00}],
            db=db,
        )
        sale_b = SaleService.create_sale(
            org.id, till_b.id, cashier_b.id, "CARD",
            [{"product_id": product.id, "quantity": 2, "unit_price": 5.00}],
            db=db,
        )
        
        # Both sales completed
        assert sale_a.status == "COMPLETED"
        assert sale_b.status == "COMPLETED"
        assert sale_a.till_id == till_a.id
        assert sale_b.till_id == till_b.id
        
        # Total stock should reflect both
        stock = InventoryService.compute_stock_at_location(
            org.id, product.id, location.id, db
        )
        assert stock == -5  # -3 from till_a, -2 from till_b


class TestOfflineSingleTill:
    """E2E Scenario 3: Offline Operation - Single Till"""
    
    def test_single_till_offline_sync(self, db):
        """
        Till goes offline, records sales, syncs.
        Verify: sales committed to ledger, stock correct.
        """
        org = Organization(name="Retail", code="RETAIL")
        db.add(org)
        db.commit()
        
        sub = Subscription(
            organization_id=org.id,
            plan="PRO",
            term=SubscriptionTerm.MONTHLY.value,
            expiry_date=datetime.utcnow() + timedelta(days=30),
        )
        db.add(sub)
        db.commit()
        
        location = Location(organization_id=org.id, code="LOC1", name="Store")
        db.add(location)
        db.commit()
        
        product = Product(
            organization_id=org.id,
            sku="WIDGET",
            name="Widget",
            price=10.00,
        )
        db.add(product)
        db.commit()
        
        till = Till(
            organization_id=org.id,
            location_id=location.id,
            code="TILL1",
            name="Till 1",
        )
        db.add(till)
        db.commit()
        
        cashier = User(
            organization_id=org.id,
            email="cashier@retail.com",
            username="cashier",
            full_name="Cashier",
            password_hash="hash",
        )
        db.add(cashier)
        db.commit()
        
        device_id = "DEVICE_123"
        
        # Till goes offline and records sales
        offline_sale1 = SaleService.create_sale(
            org.id, till.id, cashier.id, "CASH",
            [{"product_id": product.id, "quantity": 5, "unit_price": 10.00}],
            offline_device_id=device_id,
            db=db,
        )
        offline_sale2 = SaleService.create_sale(
            org.id, till.id, cashier.id, "CASH",
            [{"product_id": product.id, "quantity": 3, "unit_price": 10.00}],
            offline_device_id=device_id,
            db=db,
        )
        
        assert offline_sale1.status == "PENDING"
        assert offline_sale2.status == "PENDING"
        
        # Till syncs - both sales committed
        SaleService.commit_pending_sale(offline_sale1.id, cashier.id, db)
        SaleService.commit_pending_sale(offline_sale2.id, cashier.id, db)
        
        db.refresh(offline_sale1)
        db.refresh(offline_sale2)
        assert offline_sale1.status == "COMPLETED"
        assert offline_sale2.status == "COMPLETED"
        
        # Stock reflects total sale
        stock = InventoryService.compute_stock_at_location(
            org.id, product.id, location.id, db
        )
        assert stock == -8  # -5 - 3


class TestMultiTillOfflineConflict:
    """E2E Scenario 4: Multi-Till Offline with Conflict Detection (U006)"""
    
    def test_multi_till_offline_conflict_scenario(self, db):
        """
        Setup: 8 units in stock.
        Till A and B cache state, both go offline.
        Till A sells 5 (cache: 3 left).
        Till B sells 5 (cache: 3 left).
        Till A syncs first (server: 3 units ok).
        Till B syncs (server: -2 units, shortage detected).
        Verify: both sales committed, discrepancy recorded.
        """
        org = Organization(name="Retail", code="RETAIL")
        db.add(org)
        db.commit()
        
        sub = Subscription(
            organization_id=org.id,
            plan="PRO",
            term=SubscriptionTerm.MONTHLY.value,
            expiry_date=datetime.utcnow() + timedelta(days=30),
        )
        db.add(sub)
        db.commit()
        
        location = Location(organization_id=org.id, code="LOC1", name="Store")
        db.add(location)
        db.commit()
        
        product = Product(
            organization_id=org.id,
            sku="LIMITED",
            name="Limited Item",
            price=10.00,
        )
        db.add(product)
        db.commit()
        
        # Create admin user for inventory operations
        admin = User(
            organization_id=org.id,
            email="admin@retail.com",
            username="admin",
            full_name="Admin",
            password_hash="hash",
        )
        db.add(admin)
        db.commit()
        
        # Seed initial stock of 8 units
        InventoryService.record_movement(
            org.id, product.id, location.id, 8, "PURCHASE",
            admin.id, db=db
        )
        
        till_a = Till(
            organization_id=org.id,
            location_id=location.id,
            code="TILL_A",
            name="Till A",
        )
        till_b = Till(
            organization_id=org.id,
            location_id=location.id,
            code="TILL_B",
            name="Till B",
        )
        db.add_all([till_a, till_b])
        db.commit()
        
        cashier_a = User(
            organization_id=org.id,
            email="cashier_a@retail.com",
            username="cashier_a",
            full_name="Cashier A",
            password_hash="hash",
        )
        cashier_b = User(
            organization_id=org.id,
            email="cashier_b@retail.com",
            username="cashier_b",
            full_name="Cashier B",
            password_hash="hash",
        )
        db.add_all([cashier_a, cashier_b])
        db.commit()
        
        # Both tills go offline and record sales
        device_a = "DEVICE_A"
        device_b = "DEVICE_B"
        
        sale_a = SaleService.create_sale(
            org.id, till_a.id, cashier_a.id, "CASH",
            [{"product_id": product.id, "quantity": 5, "unit_price": 10.00}],
            offline_device_id=device_a,
            db=db,
        )
        
        sale_b = SaleService.create_sale(
            org.id, till_b.id, cashier_b.id, "CASH",
            [{"product_id": product.id, "quantity": 5, "unit_price": 10.00}],
            offline_device_id=device_b,
            db=db,
        )
        
        # Both sync (Till A first, then Till B)
        SaleService.commit_pending_sale(sale_a.id, cashier_a.id, db)
        SaleService.commit_pending_sale(sale_b.id, cashier_b.id, db)
        
        # Both sales should be COMMITTED despite shortage
        db.refresh(sale_a)
        db.refresh(sale_b)
        assert sale_a.status == "COMPLETED"
        assert sale_b.status == "COMPLETED"
        
        # Stock should be negative (shortage detected)
        stock = InventoryService.compute_stock_at_location(
            org.id, product.id, location.id, db
        )
        assert stock == -2  # 8 - 5 - 5 = -2 (shortage)
        
        # Physical count triggers discrepancy detection
        # (In real flow: inventory reconciliation would happen)
        discrepancy = InventoryService.detect_discrepancy(
            org.id, product.id, location.id, 0, db  # Physical count shows 0
        )
        assert discrepancy == 2  # 0 - (-2) = 2 (surplus of 2 from ledger perspective)


class TestInventoryAdjustment:
    """E2E Scenario 5: Inventory Adjustment & Reconciliation"""
    
    def test_inventory_adjustment_workflow(self, db):
        """
        Ledger says 8, physical count is 5 (shortage).
        Record ADJUSTMENT movement.
        Verify: stock corrected, adjustment tracked.
        """
        org = Organization(name="Retail", code="RETAIL")
        db.add(org)
        db.commit()
        
        location = Location(organization_id=org.id, code="LOC1", name="Store")
        db.add(location)
        db.commit()
        
        product = Product(
            organization_id=org.id,
            sku="ITEM",
            name="Item",
            price=1.00,
        )
        db.add(product)
        db.commit()
        
        admin = User(
            organization_id=org.id,
            email="admin@retail.com",
            username="admin",
            full_name="Admin",
            password_hash="hash",
        )
        db.add(admin)
        db.commit()
        
        # Create 8 units in ledger
        InventoryService.record_movement(
            org.id, product.id, location.id, 8, "PURCHASE",
            admin.id, db=db
        )
        
        stock_before = InventoryService.compute_stock_at_location(
            org.id, product.id, location.id, db
        )
        assert stock_before == 8
        
        # Physical count shows 5 (shortage of 3)
        InventoryService.record_movement(
            org.id, product.id, location.id, -3, "ADJUSTMENT",
            admin.id, db=db
        )
        
        stock_after = InventoryService.compute_stock_at_location(
            org.id, product.id, location.id, db
        )
        assert stock_after == 5
        
        # Verify adjustment recorded
        movements = db.query(InventoryMovement).filter(
            InventoryMovement.organization_id == org.id,
            InventoryMovement.product_id == product.id,
            InventoryMovement.reason == "ADJUSTMENT",
        ).all()
        
        assert len(movements) == 1
        assert movements[0].quantity == -3


class TestSubscriptionGracePeriod:
    """E2E Scenario 6: Subscription Expiry & Grace Period Transition"""
    
    def test_subscription_grace_period_transition(self, db):
        """
        Subscription ACTIVE expires.
        Transitions to GRACE (7 days for monthly).
        Can open till in GRACE.
        After grace expires, transitions to LIMITED.
        Cannot open till in LIMITED.
        """
        org = Organization(name="Coffee", code="COFFEE")
        db.add(org)
        db.commit()
        
        # Create ACTIVE subscription
        expiry_date = datetime.utcnow() - timedelta(days=1)  # Expired yesterday
        grace_end = datetime.utcnow() + timedelta(days=6)    # Grace ends in 6 days
        
        sub = Subscription(
            organization_id=org.id,
            plan="PRO",
            term=SubscriptionTerm.MONTHLY.value,
            expiry_date=expiry_date,
            grace_end_date=grace_end,
        )
        db.add(sub)
        db.commit()
        
        # Verify subscription is in GRACE
        state = SubscriptionService.compute_current_state(sub)
        assert state == SubscriptionState.GRACE
        assert SubscriptionService.is_operational(sub)
        
        location = Location(organization_id=org.id, code="LOC1", name="Store")
        db.add(location)
        db.commit()
        
        till = Till(
            organization_id=org.id,
            location_id=location.id,
            code="TILL1",
            name="Till",
        )
        db.add(till)
        db.commit()
        
        user = User(
            organization_id=org.id,
            email="user@coffee.com",
            username="user",
            full_name="User",
            password_hash="hash",
        )
        db.add(user)
        db.commit()
        
        # Should be able to open till in GRACE
        TillService.assert_open_allowed(org.id, db)  # No exception
        
        session = TillService.open_session(
            org.id, till.id, user.id, db=db
        )
        assert session.status == "OPEN"
        
        # Now simulate LIMITED state (grace expired)
        sub.grace_end_date = datetime.utcnow() - timedelta(days=1)
        db.commit()
        
        state = SubscriptionService.compute_current_state(sub)
        assert state == SubscriptionState.LIMITED
        assert not SubscriptionService.is_operational(sub)
        
        # Cannot open new till in LIMITED
        with pytest.raises(ValueError):
            TillService.assert_open_allowed(org.id, db)


class TestOfflineSubscriptionExpiry:
    """E2E Scenario 7: Offline Subscription Expiry (U008)"""
    
    def test_offline_device_cache_update_on_sync(self, db):
        """
        Device online, syncs state, goes offline.
        Subscription expires while device is offline.
        Device operates normally (cache shows ACTIVE).
        Device comes online, receives LIMITED state from server.
        Cache updates, next operation blocked.
        """
        org = Organization(name="Coffee", code="COFFEE")
        db.add(org)
        db.commit()
        
        # Subscription ACTIVE
        sub = Subscription(
            organization_id=org.id,
            plan="PRO",
            term=SubscriptionTerm.MONTHLY.value,
            expiry_date=datetime.utcnow() + timedelta(days=30),
        )
        db.add(sub)
        db.commit()
        
        location = Location(organization_id=org.id, code="LOC1", name="Store")
        db.add(location)
        db.commit()
        
        till = Till(
            organization_id=org.id,
            location_id=location.id,
            code="TILL1",
            name="Till",
        )
        db.add(till)
        db.commit()
        
        user = User(
            organization_id=org.id,
            email="user@coffee.com",
            username="user",
            full_name="User",
            password_hash="hash",
        )
        db.add(user)
        db.commit()
        
        device_id = "DEVICE_OFFLINE"
        
        # Device syncs: caches ACTIVE state
        state_snapshot = SyncService.get_subscription_state_sync(org.id, db)
        
        cache = CachedSubscriptionState(
            device_id=device_id,
            organization_id=org.id,
            state=state_snapshot["state"],
            state_snapshot=state_snapshot,
            last_sync_at=datetime.utcnow(),
        )
        db.add(cache)
        db.commit()
        
        # Device goes offline and operates
        assert cache.state == SubscriptionState.ACTIVE.value
        TillService.assert_offline_cached_allowed(cache.state)  # No exception
        
        # Server subscription expires -> LIMITED
        sub.expiry_date = datetime.utcnow() - timedelta(days=10)
        sub.grace_end_date = datetime.utcnow() - timedelta(days=2)
        db.commit()
        
        # Device comes back online, gets new state
        new_state_snapshot = SyncService.get_subscription_state_sync(org.id, db)
        
        # Device updates cache
        cache.state = new_state_snapshot["state"]
        cache.state_snapshot = new_state_snapshot
        cache.last_sync_at = datetime.utcnow()
        db.commit()
        
        # Next offline operation should be blocked
        assert cache.state == SubscriptionState.LIMITED.value
        with pytest.raises(ValueError):
            TillService.assert_offline_cached_allowed(cache.state)


class TestIdempotencyOnSync:
    """E2E Scenario 8: Offline Transaction Idempotency"""
    
    def test_duplicate_sync_not_double_processed(self, db):
        """
        Till records sales offline.
        Till syncs (sales committed).
        Till goes offline again immediately.
        Till syncs again with same batch.
        Verify: server detects duplicate, no double-processing.
        """
        org = Organization(name="Retail", code="RETAIL")
        db.add(org)
        db.commit()
        
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            expiry_date=datetime.utcnow() + timedelta(days=30),
        )
        db.add(sub)
        db.commit()
        
        location = Location(organization_id=org.id, code="LOC1", name="Store")
        db.add(location)
        db.commit()
        
        product = Product(
            organization_id=org.id,
            sku="ITEM",
            name="Item",
            price=10.00,
        )
        db.add(product)
        db.commit()
        
        till = Till(
            organization_id=org.id,
            location_id=location.id,
            code="TILL1",
            name="Till",
        )
        db.add(till)
        db.commit()
        
        cashier = User(
            organization_id=org.id,
            email="cashier@retail.com",
            username="cashier",
            full_name="Cashier",
            password_hash="hash",
        )
        db.add(cashier)
        db.commit()
        
        device_id = "DEVICE_SYNC"
        
        # Record offline sale
        offline_sale = SaleService.create_sale(
            org.id, till.id, cashier.id, "CASH",
            [{"product_id": product.id, "quantity": 5, "unit_price": 10.00}],
            offline_device_id=device_id,
            db=db,
        )
        assert offline_sale.status == "PENDING"
        sale_id = offline_sale.id
        
        # First sync: commit the sale
        SaleService.commit_pending_sale(sale_id, cashier.id, db)
        
        db.refresh(offline_sale)
        assert offline_sale.status == "COMPLETED"
        
        # Count movements after first commit
        movements_after_first = db.query(InventoryMovement).filter(
            InventoryMovement.reference_id == sale_id,
            InventoryMovement.reference_type == "SALE",
        ).all()
        
        initial_movement_count = len(movements_after_first)
        assert initial_movement_count > 0
        
        # Second sync attempt with same sale (idempotent)
        # Should not create duplicate movements
        SaleService.commit_pending_sale(sale_id, cashier.id, db)
        
        movements_after_second = db.query(InventoryMovement).filter(
            InventoryMovement.reference_id == sale_id,
            InventoryMovement.reference_type == "SALE",
        ).all()
        
        # Should still have same count (no duplicates)
        assert len(movements_after_second) == initial_movement_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
