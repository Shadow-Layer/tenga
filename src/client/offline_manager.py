"""Main offline manager orchestrating all offline capabilities.

Coordinates:
- Local storage
- Connectivity detection
- Offline sales operations
- Synchronization
- State reconciliation
"""

import uuid
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from uuid import uuid4

from src.client.storage import LocalStorage
from src.client.api_client import APIClient
from src.client.sync_manager import SyncManager
from src.client.connectivity import ConnectivityManager, ConnectivityStatus


class OfflineManager:
    """Main orchestrator for offline POS operations."""

    def __init__(self, device_id: str = None, db_path: str = None, 
                 api_base_url: str = None, auth_token: str = None):
        """Initialize offline manager.
        
        Args:
            device_id: Unique device ID (auto-generated if None)
            db_path: Path to local SQLite database
            api_base_url: Base URL for API server
            auth_token: JWT authentication token
        """
        self.device_id = device_id or str(uuid4())
        
        # Initialize components
        self.storage = LocalStorage(db_path)
        self.api_client = APIClient(api_base_url or "http://localhost:8000", auth_token)
        self.connectivity = ConnectivityManager()
        
        self.org_id = None
        self.sync_manager = None
        self.auto_sync_thread = None
        self.auto_sync_running = False
        
        self.lock = threading.RLock()
        self.callbacks = {}  # Event name -> list of callbacks
        
        # Start connectivity monitoring
        self.connectivity.add_callback(self._on_connectivity_changed)
        self.connectivity.start()

    def _emit_event(self, event_name: str, *args, **kwargs) -> None:
        """Emit event to registered callbacks."""
        if event_name not in self.callbacks:
            return
        
        for callback in self.callbacks[event_name]:
            try:
                callback(*args, **kwargs)
            except Exception:
                pass

    def on(self, event_name: str, callback: Callable) -> None:
        """Register callback for event.
        
        Args:
            event_name: Event name (e.g., 'offline', 'online', 'sale_created', 'sync_complete')
            callback: Function to call when event occurs
        """
        if event_name not in self.callbacks:
            self.callbacks[event_name] = []
        self.callbacks[event_name].append(callback)

    def _on_connectivity_changed(self, status: ConnectivityStatus) -> None:
        """Handle connectivity status change."""
        self.storage.set_connectivity(status == ConnectivityStatus.ONLINE)
        
        if status == ConnectivityStatus.ONLINE:
            self._emit_event("online")
            # Auto-sync when reconnecting
            if self.sync_manager and self.org_id:
                self._perform_auto_sync()
        else:
            self._emit_event("offline")

    def initialize(self, org_id: int, org_name: str, org_code: str,
                  location_id: int = None, till_id: int = None) -> None:
        """Initialize offline manager with organization context.
        
        Args:
            org_id: Organization ID
            org_name: Organization name
            org_code: Organization code
            location_id: Location ID
            till_id: Till ID
        """
        with self.lock:
            self.org_id = org_id
            
            # Save context
            self.storage.save_org_context(
                org_id, org_name, org_code, location_id, till_id, self.device_id
            )
            
            # Create sync manager
            self.sync_manager = SyncManager(
                self.storage, self.api_client, self.device_id, org_id
            )
            
            self._emit_event("initialized")

    def sync_context(self) -> bool:
        """Synchronize organization context from server.
        
        Fetches and caches:
        - Organization details
        - Locations
        - Product catalog
        - Stock information
        - Subscription state
        
        Returns:
            True if successful
        """
        if not self.org_id:
            raise ValueError("Manager not initialized")
        
        try:
            # Get organization
            org = self.api_client.get_organization(self.org_id)
            
            # Get locations
            locations = self.api_client.get_locations(self.org_id)
            
            # Get products
            products = self.api_client.get_products(self.org_id)
            self.storage.cache_products(self.org_id, products)
            
            # Get stock for primary location if available
            context = self.storage.get_org_context(self.org_id)
            if context and context.get("location_id"):
                stock = self.api_client.get_stock(self.org_id, context["location_id"])
                self.storage.cache_stock(self.org_id, stock)
            
            # Get and cache subscription state
            if self.sync_manager:
                self.sync_manager.update_subscription_cache()
            
            self._emit_event("context_synced")
            return True
        
        except Exception as e:
            self._emit_event("context_sync_failed", str(e))
            return False

    def create_sale(self, till_id: int, cashier_id: int, payment_method: str,
                   items: List[Dict], notes: str = None) -> str:
        """Create an offline sale.
        
        Args:
            till_id: Till ID
            cashier_id: Cashier user ID
            payment_method: Payment method (CASH, CARD, etc.)
            items: List of sale items with product_id, quantity, unit_price
            notes: Optional notes
        
        Returns:
            Sale ID for reference
        
        Raises:
            ValueError: If organization not initialized or invalid input
        """
        if not self.org_id:
            raise ValueError("Manager not initialized")
        
        # Validate items
        if not items:
            raise ValueError("Sale must have at least one item")
        
        total_amount = 0
        items_with_total = []
        for item in items:
            if not item.get("product_id") or not item.get("quantity") or not item.get("unit_price"):
                raise ValueError(f"Invalid item: {item}")
            total_price = item["quantity"] * item["unit_price"]
            total_amount += total_price
            items_with_total.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "total_price": total_price
            })
        
        # Get location from context
        context = self.storage.get_org_context(self.org_id)
        location_id = context.get("location_id") if context else None
        if not location_id:
            raise ValueError("Location not set in context")
        
        # Create local sale
        sale_id = str(uuid4())
        
        self.storage.create_pending_sale(
            sale_id, self.org_id, till_id, cashier_id, location_id,
            total_amount, payment_method, items_with_total,
            metadata={"created_offline": True, "notes": notes}
        )
        
        # Add to sync queue
        self.storage.enqueue_sync_event(
            f"sale_{sale_id}",
            self.org_id,
            "SALE_COMMIT",
            {
                "sale_id": sale_id,
                "user_id": cashier_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        
        self._emit_event("sale_created", sale_id)
        
        # Auto-sync if online
        if self.connectivity.is_online() and self.sync_manager:
            self._perform_auto_sync()
        
        return sale_id

    def get_pending_sales(self) -> List[Dict]:
        """Get all pending sales awaiting sync.
        
        Returns:
            List of pending sales
        """
        if not self.org_id:
            return []
        
        return self.storage.get_pending_sales(self.org_id)

    def get_pending_sync_count(self) -> int:
        """Get number of pending events awaiting sync.
        
        Returns:
            Count of pending events
        """
        if not self.org_id:
            return 0
        
        pending_sales = self.storage.get_pending_sales(self.org_id)
        pending_events = self.storage.get_pending_events(self.org_id)
        
        return len(pending_sales) + len(pending_events)

    def sync(self) -> bool:
        """Manually trigger synchronization.
        
        Returns:
            True if sync successful
        """
        if not self.sync_manager or not self.org_id:
            return False
        
        success, result = self.sync_manager.sync()
        self._emit_event("sync_complete", success, result)
        
        return success

    def _perform_auto_sync(self) -> None:
        """Perform automatic synchronization in background."""
        if self.auto_sync_running:
            return
        
        def sync_thread():
            try:
                self.auto_sync_running = True
                self.sync()
            finally:
                self.auto_sync_running = False
        
        thread = threading.Thread(target=sync_thread, daemon=True)
        thread.start()

    def start_auto_sync(self, interval_seconds: int = 30) -> None:
        """Start automatic synchronization.
        
        Args:
            interval_seconds: Seconds between sync attempts
        """
        if self.auto_sync_thread and self.auto_sync_thread.is_alive():
            return
        
        def auto_sync_loop():
            while self.auto_sync_running:
                if self.connectivity.is_online() and self.get_pending_sync_count() > 0:
                    self.sync()
                
                threading.Event().wait(interval_seconds)
        
        self.auto_sync_running = True
        self.auto_sync_thread = threading.Thread(target=auto_sync_loop, daemon=True)
        self.auto_sync_thread.start()

    def stop_auto_sync(self) -> None:
        """Stop automatic synchronization."""
        self.auto_sync_running = False

    def get_status(self) -> Dict[str, Any]:
        """Get current offline operation status.
        
        Returns:
            Status dictionary with:
            - device_id
            - organization_id
            - is_online
            - pending_sales
            - pending_events
            - last_sync
            - sync_status
        """
        context = self.storage.get_org_context(self.org_id) if self.org_id else None
        sync_status = self.sync_manager.get_sync_status() if self.sync_manager else {}
        
        return {
            "device_id": self.device_id,
            "organization_id": self.org_id,
            "is_online": self.connectivity.is_online(),
            "connectivity_status": self.connectivity.status.value,
            "context": context,
            "pending_sales": self.get_pending_sales(),
            "pending_count": self.get_pending_sync_count(),
            "sync_status": sync_status,
        }

    def get_cached_products(self) -> List[Dict]:
        """Get cached product catalog.
        
        Returns:
            List of products
        """
        if not self.org_id:
            return []
        
        return self.storage.get_products(self.org_id)

    def get_cached_stock(self, location_id: int = None) -> Dict[int, int]:
        """Get cached stock quantities.
        
        Args:
            location_id: Location ID (uses org context if not provided)
        
        Returns:
            Dict of product_id -> quantity
        """
        if not self.org_id:
            return {}
        
        if not location_id:
            context = self.storage.get_org_context(self.org_id)
            location_id = context.get("location_id") if context else None
        
        if not location_id:
            return {}
        
        return self.storage.get_stock_at_location(self.org_id, location_id)

    def shutdown(self) -> None:
        """Shutdown offline manager and cleanup resources."""
        self.stop_auto_sync()
        self.connectivity.stop()
        self.api_client.close()
