"""Synchronization manager for offline-to-online sync operations.

Handles:
- Batch preparation and transmission
- Idempotency and retry logic
- Conflict detection and resolution
- Acknowledgment tracking
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import threading
import time

from src.client.storage import LocalStorage
from src.client.api_client import APIClient


class SyncStatus(str, Enum):
    """Status of sync operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class EventType(str, Enum):
    """Types of events that can be synced."""
    SALE_COMMIT = "SALE_COMMIT"
    SALE_CREATION = "SALE_CREATION"
    INVENTORY_MOVEMENT = "INVENTORY_MOVEMENT"


class SyncManager:
    """Manages synchronization of offline events with server."""

    def __init__(self, storage: LocalStorage, api_client: APIClient, 
                 device_id: str, org_id: int, max_retries: int = 3):
        """Initialize sync manager.
        
        Args:
            storage: Local storage instance
            api_client: API client instance
            device_id: Device ID
            org_id: Organization ID
            max_retries: Maximum retry attempts per event
        """
        self.storage = storage
        self.api_client = api_client
        self.device_id = device_id
        self.org_id = org_id
        self.max_retries = max_retries
        
        self.last_sync_at = None
        self.sync_status = SyncStatus.PENDING
        self.lock = threading.RLock()

    def prepare_sync_batch(self, pending_sales: List[Dict] = None,
                          pending_events: List[Dict] = None,
                          max_batch_size: int = 100) -> Tuple[str, List[Dict]]:
        """Prepare a batch of pending events for sync.
        
        Args:
            pending_sales: Pending sales to include (None = fetch from storage)
            pending_events: Pending events to include (None = fetch from storage)
            max_batch_size: Maximum items in batch
        
        Returns:
            Tuple of (batch_id, batch_items)
        """
        batch_id = str(uuid.uuid4())
        batch_items = []
        sequence = 0
        
        # Add pending sales
        if pending_sales is None:
            pending_sales = self.storage.get_pending_sales(self.org_id)
        
        for sale in pending_sales[:max_batch_size]:
            if sequence >= max_batch_size:
                break
            
            item = {
                "batch_id": batch_id,
                "sequence": sequence,
                "action": "SALE_COMMIT",
                "payload": {
                    "sale_id": sale["id"],
                    "user_id": sale["cashier_id"],
                    "transaction_id": f"sale_{sale['id']}",
                    "timestamp": sale["created_at"],
                }
            }
            batch_items.append(item)
            sequence += 1
        
        # Add pending events if space available
        if pending_events is None:
            pending_events = self.storage.get_pending_events(self.org_id)
        
        for event in pending_events:
            if sequence >= max_batch_size:
                break
            
            item = {
                "batch_id": batch_id,
                "sequence": sequence,
                "action": event["event_type"],
                "payload": event["event_data"]
            }
            batch_items.append(item)
            sequence += 1
        
        return batch_id, batch_items

    def sync(self) -> Tuple[bool, Dict[str, Any]]:
        """Perform synchronization with server.
        
        Returns:
            Tuple of (success, result_dict)
                - success: True if all events synced
                - result_dict: Detailed sync results
        """
        with self.lock:
            self.sync_status = SyncStatus.IN_PROGRESS
        
        try:
            # Prepare batch
            batch_id, batch_items = self.prepare_sync_batch()
            
            if not batch_items:
                # Nothing to sync
                with self.lock:
                    self.sync_status = SyncStatus.SUCCESS
                    self.last_sync_at = datetime.utcnow()
                
                return True, {"batch_id": batch_id, "items_synced": 0, "errors": []}
            
            # Submit batch
            response = self.api_client.submit_sync_batch(
                self.device_id,
                self.org_id,
                batch_items
            )
            
            # Process results
            success = self._process_sync_response(batch_id, batch_items, response)
            
            # Update metadata
            self.storage.update_sync_metadata(
                self.org_id,
                device_id=self.device_id,
                last_sync_at=datetime.utcnow().isoformat(),
                last_batch_id=batch_id,
            )
            
            with self.lock:
                self.sync_status = SyncStatus.SUCCESS if success else SyncStatus.PARTIAL_FAILURE
                self.last_sync_at = datetime.utcnow()
            
            return success, response
        
        except Exception as e:
            with self.lock:
                self.sync_status = SyncStatus.FAILED
            
            return False, {"error": str(e), "batch_id": batch_id if 'batch_id' in locals() else None}

    def _process_sync_response(self, batch_id: str, batch_items: List[Dict],
                               response: Dict) -> bool:
        """Process sync response and update local state.
        
        Args:
            batch_id: Batch ID
            batch_items: Original batch items
            response: Server response
        
        Returns:
            True if all items processed successfully
        """
        errors = response.get("errors", [])
        all_success = len(errors) == 0
        
        # Map sequence to item ID
        seq_to_item = {item["sequence"]: item for item in batch_items}
        
        for item in batch_items:
            seq = item["sequence"]
            action = item["action"]
            payload = item["payload"]
            
            # Check if this item had an error
            item_error = next((e for e in errors if e.get("sequence") == seq), None)
            
            if action == "SALE_COMMIT":
                sale_id = payload["sale_id"]
                if item_error:
                    # Handle retry
                    self._handle_sale_sync_failure(sale_id, item_error.get("error"))
                else:
                    self.storage.mark_sale_synced(sale_id, seq)
            else:
                # Handle other event types
                event_id = payload.get("transaction_id", f"{action}_{seq}")
                if item_error:
                    self.storage.mark_event_sync_failed(event_id, item_error.get("error"))
                else:
                    self.storage.mark_event_synced(event_id, batch_id)
        
        return all_success

    def _handle_sale_sync_failure(self, sale_id: str, error: str) -> None:
        """Handle failed sale sync with retry logic.
        
        Args:
            sale_id: Sale ID
            error: Error message
        """
        # Check retry count
        sale = self.storage.get_pending_sale(sale_id)
        if sale and sale["retry_count"] < self.max_retries:
            self.storage.mark_sale_sync_failed(sale_id, error)
        else:
            # Max retries exceeded - mark as permanently failed
            self.storage.mark_sale_sync_failed(sale_id, f"Permanent failure: {error}")

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status.
        
        Returns:
            Status information
        """
        with self.lock:
            metadata = self.storage.get_sync_metadata(self.org_id) or {}
            pending_sales = self.storage.get_pending_sales(self.org_id)
            pending_events = self.storage.get_pending_events(self.org_id)
            
            return {
                "sync_status": self.sync_status.value,
                "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
                "last_batch_id": metadata.get("last_batch_id"),
                "pending_sales": len(pending_sales),
                "pending_events": len(pending_events),
                "subscription_state": metadata.get("subscription_state"),
            }

    def retry_failed_events(self, max_attempts: int = None) -> Tuple[bool, Dict]:
        """Retry previously failed sync attempts.
        
        Args:
            max_attempts: Maximum failed events to retry
        
        Returns:
            Tuple of (success, results)
        """
        # Get failed sales
        failed_sales = self.storage.get_pending_sales(self.org_id, status="SYNCED")
        
        if max_attempts:
            failed_sales = failed_sales[:max_attempts]
        
        if not failed_sales:
            return True, {"retried": 0}
        
        return self.sync()

    def update_subscription_cache(self) -> None:
        """Fetch and cache subscription state from server."""
        try:
            state = self.api_client.get_subscription_state(self.org_id)
            
            self.api_client.cache_subscription_state(
                self.device_id,
                self.org_id,
                state
            )
            
            self.storage.update_sync_metadata(
                self.org_id,
                subscription_state=state.get("state"),
                subscription_expires_at=state.get("expiry_date"),
            )
        except Exception as e:
            # Log but don't fail
            pass

    def clear_synced_events(self, days_old: int = 7) -> int:
        """Clear synced events older than specified days.
        
        Args:
            days_old: Days to keep synced events
        
        Returns:
            Number of events cleared
        """
        # This would require additional storage methods to implement
        # For now, just track synced at timestamp
        return 0
