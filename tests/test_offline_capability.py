"""Tests for client-side offline capability."""

import pytest
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.client.offline_manager import OfflineManager
from src.client.storage import LocalStorage
from src.client.sync_manager import SyncManager
from src.client.api_client import APIClient
from src.client.connectivity import ConnectivityManager, ConnectivityStatus


class TestLocalStorage:
    """Tests for local storage."""

    def test_storage_initialization(self):
        """Test storage initializes with database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = LocalStorage(db_path)
            
            assert os.path.exists(db_path)
            storage.get_connection().close()

    def test_set_get_session_state(self):
        """Test storing and retrieving session state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            
            storage.set_session_state("auth_token", "abc123")
            token = storage.get_session_state("auth_token")
            
            assert token == "abc123"

    def test_session_state_with_dict(self):
        """Test storing and retrieving complex session state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            
            state = {"user_id": 1, "email": "test@example.com"}
            storage.set_session_state("user", state)
            retrieved = storage.get_session_state("user")
            
            assert retrieved == state

    def test_save_and_get_org_context(self):
        """Test organization context caching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            
            storage.save_org_context(
                org_id=1,
                org_name="Test Org",
                org_code="TEST",
                location_id=10,
                till_id=100
            )
            
            context = storage.get_org_context(1)
            assert context["org_name"] == "Test Org"
            assert context["location_id"] == 10

    def test_cache_products(self):
        """Test product catalog caching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            
            products = [
                {"id": 1, "sku": "SKU001", "name": "Product 1", "price": 10.0},
                {"id": 2, "sku": "SKU002", "name": "Product 2", "price": 20.0},
            ]
            
            storage.cache_products(1, products)
            cached = storage.get_products(1)
            
            assert len(cached) == 2
            assert cached[0]["name"] == "Product 1"

    def test_cache_and_get_stock(self):
        """Test stock caching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            
            stock_data = [
                {"product_id": 1, "location_id": 10, "quantity": 100},
                {"product_id": 2, "location_id": 10, "quantity": 50},
            ]
            
            storage.cache_stock(1, stock_data)
            stock = storage.get_stock_at_location(1, 10)
            
            assert stock[1] == 100
            assert stock[2] == 50

    def test_create_and_get_pending_sale(self):
        """Test creating and retrieving pending sales."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            
            items = [
                {"product_id": 1, "quantity": 2, "unit_price": 10.0, "total_price": 20.0}
            ]
            
            sale_id = str(uuid4())
            storage.create_pending_sale(
                sale_id=sale_id,
                org_id=1,
                till_id=10,
                cashier_id=5,
                location_id=20,
                total_amount=20.0,
                payment_method="CASH",
                items=items
            )
            
            sales = storage.get_pending_sales(1)
            assert len(sales) == 1
            assert sales[0]["id"] == sale_id
            assert len(sales[0]["items"]) == 1

    def test_mark_sale_synced(self):
        """Test marking sale as synced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            
            sale_id = str(uuid4())
            items = [{"product_id": 1, "quantity": 1, "unit_price": 10.0, "total_price": 10.0}]
            
            storage.create_pending_sale(
                sale_id, 1, 10, 5, 20, 10.0, "CASH", items
            )
            
            storage.mark_sale_synced(sale_id, 999)
            
            sale = storage.get_pending_sale(sale_id)
            assert sale["status"] == "SYNCED"
            assert sale["server_sale_id"] == 999

    def test_sync_queue(self):
        """Test sync event queueing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            
            event_id = str(uuid4())
            event_data = {"product_id": 1, "quantity": 10}
            
            storage.enqueue_sync_event(event_id, 1, "INVENTORY_MOVEMENT", event_data)
            
            events = storage.get_pending_events(1)
            assert len(events) == 1
            assert events[0]["event_type"] == "INVENTORY_MOVEMENT"

    def test_mark_event_synced(self):
        """Test marking event as synced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            
            event_id = str(uuid4())
            storage.enqueue_sync_event(event_id, 1, "TEST", {})
            
            storage.mark_event_synced(event_id, "batch123")
            
            events = storage.get_pending_events(1, limit=100)
            synced = [e for e in events if e["id"] == event_id]
            assert len(synced) == 0  # Should not appear in pending

    def test_connectivity_state(self):
        """Test connectivity tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            
            storage.set_connectivity(True)
            assert storage.is_online() is True
            
            storage.set_connectivity(False)
            assert storage.is_online() is False


class TestConnectivityManager:
    """Tests for connectivity management."""

    def test_connectivity_initialization(self):
        """Test connectivity manager initializes."""
        manager = ConnectivityManager()
        assert manager.status == ConnectivityStatus.ONLINE

    def test_connectivity_callbacks(self):
        """Test connectivity change callbacks."""
        manager = ConnectivityManager()
        called = []
        
        def callback(status):
            called.append(status)
        
        manager.add_callback(callback)
        
        # Mock the is_reachable to return False
        with patch.object(manager, 'is_reachable', return_value=False):
            manager._update_status(False)
            
            assert len(called) == 1
            assert called[0] == ConnectivityStatus.OFFLINE

    def test_is_online(self):
        """Test is_online check."""
        manager = ConnectivityManager()
        
        with patch.object(manager, 'is_reachable', return_value=True):
            manager._update_status(True)
            assert manager.is_online() is True
        
        with patch.object(manager, 'is_reachable', return_value=False):
            manager._update_status(False)
            assert manager.is_online() is False


class TestSyncManager:
    """Tests for sync manager."""

    def test_prepare_sync_batch(self):
        """Test batch preparation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            api_client = Mock()
            
            # Create a pending sale
            sale_id = str(uuid4())
            items = [{"product_id": 1, "quantity": 1, "unit_price": 10.0, "total_price": 10.0}]
            storage.create_pending_sale(sale_id, 1, 10, 5, 20, 10.0, "CASH", items)
            
            manager = SyncManager(storage, api_client, "device1", 1)
            batch_id, batch_items = manager.prepare_sync_batch()
            
            assert len(batch_items) == 1
            assert batch_items[0]["action"] == "SALE_COMMIT"
            assert batch_items[0]["sequence"] == 0

    def test_sync_with_success(self):
        """Test successful synchronization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            api_client = Mock()
            
            # Create pending sale
            sale_id = str(uuid4())
            items = [{"product_id": 1, "quantity": 1, "unit_price": 10.0, "total_price": 10.0}]
            storage.create_pending_sale(sale_id, 1, 10, 5, 20, 10.0, "CASH", items)
            
            # Mock API response
            api_client.submit_sync_batch.return_value = {
                "status": "COMPLETED",
                "processed_items": 1,
                "total_items": 1,
                "errors": []
            }
            
            manager = SyncManager(storage, api_client, "device1", 1)
            success, result = manager.sync()
            
            assert success is True

    def test_sync_with_error(self):
        """Test sync with API error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            api_client = Mock()
            
            # Create a pending sale first
            sale_id = str(uuid4())
            items = [{"product_id": 1, "quantity": 1, "unit_price": 10.0, "total_price": 10.0}]
            storage.create_pending_sale(sale_id, 1, 10, 5, 20, 10.0, "CASH", items)
            
            # Mock API error
            api_client.submit_sync_batch.side_effect = Exception("Network error")
            
            manager = SyncManager(storage, api_client, "device1", 1)
            success, result = manager.sync()
            
            assert success is False
            assert "Network error" in result.get("error", "")

    def test_get_sync_status(self):
        """Test getting sync status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(os.path.join(tmpdir, "test.db"))
            api_client = Mock()
            
            manager = SyncManager(storage, api_client, "device1", 1)
            status = manager.get_sync_status()
            
            assert "sync_status" in status
            assert "pending_sales" in status
            assert status["pending_sales"] == 0


class TestOfflineManager:
    """Tests for main offline manager."""

    def test_offline_manager_initialization(self):
        """Test offline manager initializes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = OfflineManager(device_id="device123", db_path=db_path)
            
            assert manager.device_id == "device123"
            assert manager.org_id is None
            
            manager.shutdown()

    def test_initialize_context(self):
        """Test initializing organization context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OfflineManager(
                device_id="device1",
                db_path=os.path.join(tmpdir, "test.db"),
                api_base_url="http://localhost:8000"
            )
            
            manager.initialize(org_id=1, org_name="Test Org", org_code="TEST",
                             location_id=10, till_id=100)
            
            assert manager.org_id == 1
            context = manager.storage.get_org_context(1)
            assert context["org_name"] == "Test Org"
            
            manager.shutdown()

    def test_create_offline_sale(self):
        """Test creating an offline sale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OfflineManager(
                device_id="device1",
                db_path=os.path.join(tmpdir, "test.db")
            )
            
            manager.initialize(org_id=1, org_name="Test", org_code="TST",
                             location_id=10, till_id=100)
            
            items = [
                {"product_id": 1, "quantity": 2, "unit_price": 10.0},
                {"product_id": 2, "quantity": 1, "unit_price": 20.0},
            ]
            
            sale_id = manager.create_sale(
                till_id=100,
                cashier_id=5,
                payment_method="CASH",
                items=items
            )
            
            assert sale_id is not None
            sales = manager.get_pending_sales()
            assert len(sales) == 1
            assert sales[0]["total_amount"] == 40.0
            
            manager.shutdown()

    def test_create_sale_validation(self):
        """Test sale creation validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OfflineManager(
                device_id="device1",
                db_path=os.path.join(tmpdir, "test.db")
            )
            
            manager.initialize(org_id=1, org_name="Test", org_code="TST",
                             location_id=10, till_id=100)
            
            # Test with empty items
            with pytest.raises(ValueError):
                manager.create_sale(100, 5, "CASH", [])
            
            # Test without initialization
            manager2 = OfflineManager(db_path=os.path.join(tmpdir, "test2.db"))
            with pytest.raises(ValueError):
                manager2.create_sale(100, 5, "CASH", [{"product_id": 1, "quantity": 1, "unit_price": 10}])
            
            manager.shutdown()
            manager2.shutdown()

    def test_get_pending_sync_count(self):
        """Test counting pending items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OfflineManager(
                device_id="device1",
                db_path=os.path.join(tmpdir, "test.db")
            )
            
            manager.initialize(org_id=1, org_name="Test", org_code="TST",
                             location_id=10, till_id=100)
            
            assert manager.get_pending_sync_count() == 0
            
            items = [{"product_id": 1, "quantity": 1, "unit_price": 10.0}]
            manager.create_sale(100, 5, "CASH", items)
            
            assert manager.get_pending_sync_count() >= 1
            
            manager.shutdown()

    def test_sync_with_mock_api(self):
        """Test synchronization with mocked API."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OfflineManager(
                device_id="device1",
                db_path=os.path.join(tmpdir, "test.db")
            )
            
            manager.initialize(org_id=1, org_name="Test", org_code="TST",
                             location_id=10, till_id=100)
            
            # Create sale
            items = [{"product_id": 1, "quantity": 1, "unit_price": 10.0}]
            sale_id = manager.create_sale(100, 5, "CASH", items)
            
            # Mock API
            manager.api_client.submit_sync_batch = Mock(return_value={
                "status": "COMPLETED",
                "processed_items": 1,
                "total_items": 1,
                "errors": []
            })
            
            # Perform sync
            success = manager.sync()
            
            assert success is True
            # Sync may be called multiple times depending on batching strategy
            assert manager.api_client.submit_sync_batch.call_count >= 1
            
            manager.shutdown()

    def test_get_status(self):
        """Test getting offline status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OfflineManager(
                device_id="device1",
                db_path=os.path.join(tmpdir, "test.db")
            )
            
            manager.initialize(org_id=1, org_name="Test", org_code="TST",
                             location_id=10, till_id=100)
            
            status = manager.get_status()
            
            assert status["device_id"] == "device1"
            assert status["organization_id"] == 1
            assert "is_online" in status
            assert "pending_count" in status
            
            manager.shutdown()

    def test_cached_products_and_stock(self):
        """Test cached product and stock access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OfflineManager(
                device_id="device1",
                db_path=os.path.join(tmpdir, "test.db")
            )
            
            manager.initialize(org_id=1, org_name="Test", org_code="TST",
                             location_id=10, till_id=100)
            
            # Cache products
            products = [
                {"id": 1, "sku": "SKU1", "name": "Product 1", "price": 10.0},
            ]
            manager.storage.cache_products(1, products)
            
            cached = manager.get_cached_products()
            assert len(cached) == 1
            
            # Cache stock
            stock = [{"product_id": 1, "location_id": 10, "quantity": 100}]
            manager.storage.cache_stock(1, stock)
            
            cached_stock = manager.get_cached_stock(10)
            assert cached_stock[1] == 100
            
            manager.shutdown()

    def test_event_callbacks(self):
        """Test event callback mechanism."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OfflineManager(
                device_id="device1",
                db_path=os.path.join(tmpdir, "test.db")
            )
            
            events = []
            
            def on_sale_created(sale_id):
                events.append(("sale_created", sale_id))
            
            manager.on("sale_created", on_sale_created)
            manager.initialize(org_id=1, org_name="Test", org_code="TST",
                             location_id=10, till_id=100)
            
            items = [{"product_id": 1, "quantity": 1, "unit_price": 10.0}]
            sale_id = manager.create_sale(100, 5, "CASH", items)
            
            assert len(events) > 0
            assert events[0][0] == "sale_created"
            
            manager.shutdown()


class TestOfflineIntegration:
    """Integration tests for offline workflow."""

    def test_offline_sale_flow(self):
        """Test complete offline sale workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            manager = OfflineManager(
                device_id="pos_device_1",
                db_path=os.path.join(tmpdir, "pos.db")
            )
            
            manager.initialize(
                org_id=1,
                org_name="Test Shop",
                org_code="SHOP",
                location_id=10,
                till_id=100
            )
            
            # Create multiple sales
            for i in range(3):
                items = [
                    {"product_id": 1, "quantity": i+1, "unit_price": 10.0},
                    {"product_id": 2, "quantity": i+1, "unit_price": 20.0},
                ]
                sale_id = manager.create_sale(
                    till_id=100,
                    cashier_id=5,
                    payment_method="CASH",
                    items=items
                )
                assert sale_id is not None
            
            # Verify sales persisted
            pending = manager.get_pending_sales()
            assert len(pending) == 3
            
            # Mock API and sync
            manager.api_client.submit_sync_batch = Mock(return_value={
                "status": "COMPLETED",
                "processed_items": 3,
                "total_items": 3,
                "errors": []
            })
            
            success = manager.sync()
            assert success is True
            
            manager.shutdown()

    def test_offline_persistence_across_restarts(self):
        """Test that offline state persists across restarts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "persistent.db")
            
            # First session
            manager1 = OfflineManager(device_id="device1", db_path=db_path)
            manager1.initialize(org_id=1, org_name="Test", org_code="TST",
                              location_id=10, till_id=100)
            
            items = [{"product_id": 1, "quantity": 1, "unit_price": 10.0}]
            sale_id = manager1.create_sale(100, 5, "CASH", items)
            
            manager1.shutdown()
            
            # Second session - should see persisted sale
            manager2 = OfflineManager(device_id="device1", db_path=db_path)
            manager2.initialize(org_id=1, org_name="Test", org_code="TST",
                              location_id=10, till_id=100)
            
            pending = manager2.get_pending_sales()
            assert len(pending) == 1
            
            manager2.shutdown()

    def test_connectivity_and_auto_sync(self):
        """Test connectivity detection triggers auto-sync."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OfflineManager(
                device_id="device1",
                db_path=os.path.join(tmpdir, "test.db")
            )
            
            events = []
            manager.on("online", lambda: events.append("online"))
            manager.on("offline", lambda: events.append("offline"))
            
            manager.initialize(org_id=1, org_name="Test", org_code="TST",
                             location_id=10, till_id=100)
            
            # Simulate going offline
            manager.connectivity._update_status(False)
            
            assert "offline" in events
            
            manager.shutdown()
