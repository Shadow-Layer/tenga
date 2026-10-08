"""Client-side offline capability for Tenga Inventory POS.

This module provides offline-first functionality for POS devices:
- Local state persistence (org, location, till, products, stock)
- Offline sales creation and queueing
- Pending event synchronization with server
- Connectivity detection and handling
- Idempotent retry and conflict resolution
"""

from src.client.offline_manager import OfflineManager
from src.client.sync_manager import SyncManager
from src.client.connectivity import ConnectivityManager

__all__ = [
    "OfflineManager",
    "SyncManager", 
    "ConnectivityManager",
]
