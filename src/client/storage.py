"""Local SQLite storage for client-side offline state.

Provides a lightweight embedded database for storing:
- Session/authentication state
- Organization, location, till, and user context
- Product catalog for local reference
- Stock information (last known state)
- Pending sales events
- Sync metadata and status
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading


class LocalStorage:
    """Thread-safe SQLite storage for offline state."""

    def __init__(self, db_path: str = None):
        """Initialize local storage.
        
        Args:
            db_path: Path to SQLite database. Defaults to ~/.tenga_inventory/local.db
        """
        if db_path is None:
            db_dir = Path.home() / ".tenga_inventory"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "local.db")
        
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Session state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Organization context
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_org_context (
                    org_id INTEGER PRIMARY KEY,
                    org_name TEXT NOT NULL,
                    org_code TEXT NOT NULL,
                    location_id INTEGER,
                    till_id INTEGER,
                    device_id TEXT,
                    cached_at TEXT NOT NULL,
                    expires_at TEXT
                )
            """)
            
            # Product catalog
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_products (
                    product_id INTEGER PRIMARY KEY,
                    org_id INTEGER NOT NULL,
                    sku TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    price REAL NOT NULL,
                    cost REAL,
                    is_active INTEGER DEFAULT 1,
                    cached_at TEXT NOT NULL,
                    UNIQUE(org_id, sku)
                )
            """)
            
            # Stock cache (last known quantities)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    location_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    last_synced_at TEXT,
                    cached_at TEXT NOT NULL,
                    UNIQUE(org_id, product_id, location_id)
                )
            """)
            
            # Pending sales (created offline, awaiting sync)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_sales (
                    id TEXT PRIMARY KEY,
                    org_id INTEGER NOT NULL,
                    till_id INTEGER NOT NULL,
                    cashier_id INTEGER NOT NULL,
                    location_id INTEGER NOT NULL,
                    total_amount REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TEXT NOT NULL,
                    synced_at TEXT,
                    server_sale_id INTEGER,
                    sync_error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            # Pending sale items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_sale_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id TEXT NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    total_price REAL NOT NULL,
                    FOREIGN KEY(sale_id) REFERENCES pending_sales(id)
                )
            """)
            
            # Sync queue (events awaiting synchronization)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id TEXT PRIMARY KEY,
                    org_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TEXT NOT NULL,
                    synced_at TEXT,
                    sync_batch_id TEXT,
                    sync_error TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            
            # Sync metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    org_id INTEGER PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    last_sync_at TEXT,
                    last_batch_id TEXT,
                    subscription_state TEXT,
                    subscription_expires_at TEXT,
                    pending_count INTEGER DEFAULT 0
                )
            """)
            
            # Connectivity state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectivity_state (
                    key TEXT PRIMARY KEY,
                    is_online INTEGER NOT NULL,
                    last_checked_at TEXT NOT NULL,
                    last_changed_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def set_session_state(self, key: str, value: Any) -> None:
        """Store session state."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO session_state (key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value) if not isinstance(value, str) else value, 
                 datetime.utcnow().isoformat())
            )
            conn.commit()
            conn.close()

    def get_session_state(self, key: str) -> Optional[Any]:
        """Retrieve session state."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM session_state WHERE key = ?", (key,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                try:
                    return json.loads(row["value"])
                except (json.JSONDecodeError, TypeError):
                    return row["value"]
            return None

    def save_org_context(self, org_id: int, org_name: str, org_code: str, 
                        location_id: int = None, till_id: int = None, 
                        device_id: str = None, expires_at: str = None) -> None:
        """Cache organization context."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO local_org_context 
                (org_id, org_name, org_code, location_id, till_id, device_id, cached_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (org_id, org_name, org_code, location_id, till_id, device_id,
                  datetime.utcnow().isoformat(), expires_at))
            conn.commit()
            conn.close()

    def get_org_context(self, org_id: int) -> Optional[Dict]:
        """Retrieve cached organization context."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM local_org_context WHERE org_id = ?", (org_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None

    def cache_products(self, org_id: int, products: List[Dict]) -> None:
        """Cache product catalog."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            for product in products:
                cursor.execute("""
                    INSERT OR REPLACE INTO local_products 
                    (product_id, org_id, sku, name, description, price, cost, is_active, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (product.get("id"), org_id, product.get("sku"), product.get("name"),
                      product.get("description"), product.get("price"), product.get("cost"),
                      1 if product.get("is_active", True) else 0, now))
            
            conn.commit()
            conn.close()

    def get_products(self, org_id: int) -> List[Dict]:
        """Get cached products for organization."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM local_products WHERE org_id = ? AND is_active = 1 ORDER BY name",
                (org_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]

    def cache_stock(self, org_id: int, stock_data: List[Dict]) -> None:
        """Cache stock quantities."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            for item in stock_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO local_stock 
                    (org_id, product_id, location_id, quantity, cached_at, last_synced_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (org_id, item.get("product_id"), item.get("location_id"), 
                      item.get("quantity", 0), now, item.get("last_synced_at")))
            
            conn.commit()
            conn.close()

    def get_stock_at_location(self, org_id: int, location_id: int) -> Dict[int, int]:
        """Get stock for all products at location."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT product_id, quantity FROM local_stock 
                WHERE org_id = ? AND location_id = ?
            """, (org_id, location_id))
            rows = cursor.fetchall()
            conn.close()
            
            return {row["product_id"]: row["quantity"] for row in rows}

    def create_pending_sale(self, sale_id: str, org_id: int, till_id: int, cashier_id: int,
                           location_id: int, total_amount: float, payment_method: str,
                           items: List[Dict], metadata: Dict = None) -> None:
        """Create a pending (offline) sale."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT INTO pending_sales 
                (id, org_id, till_id, cashier_id, location_id, total_amount, payment_method, status, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sale_id, org_id, till_id, cashier_id, location_id, total_amount, payment_method,
                  "PENDING", now, json.dumps(metadata) if metadata else None))
            
            for item in items:
                cursor.execute("""
                    INSERT INTO pending_sale_items 
                    (sale_id, product_id, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                """, (sale_id, item["product_id"], item["quantity"], 
                      item["unit_price"], item["total_price"]))
            
            conn.commit()
            conn.close()

    def get_pending_sales(self, org_id: int, status: str = "PENDING") -> List[Dict]:
        """Get pending sales awaiting sync."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pending_sales 
                WHERE org_id = ? AND status = ?
                ORDER BY created_at ASC
            """, (org_id, status))
            rows = cursor.fetchall()
            conn.close()
            
            result = []
            for row in rows:
                sale_dict = dict(row)
                # Get items
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM pending_sale_items WHERE sale_id = ?",
                    (sale_dict["id"],)
                )
                items = [dict(item_row) for item_row in cursor.fetchall()]
                conn.close()
                
                sale_dict["items"] = items
                result.append(sale_dict)
            
            return result

    def get_pending_sale(self, sale_id: str) -> Optional[Dict]:
        """Get a specific pending sale."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pending_sales WHERE id = ?", (sale_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            sale_dict = dict(row)
            cursor.execute(
                "SELECT * FROM pending_sale_items WHERE sale_id = ?",
                (sale_id,)
            )
            items = [dict(item_row) for item_row in cursor.fetchall()]
            conn.close()
            
            sale_dict["items"] = items
            return sale_dict

    def mark_sale_synced(self, sale_id: str, server_sale_id: int) -> None:
        """Mark a pending sale as synced."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pending_sales 
                SET status = 'SYNCED', synced_at = ?, server_sale_id = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), server_sale_id, sale_id))
            conn.commit()
            conn.close()

    def mark_sale_sync_failed(self, sale_id: str, error: str) -> None:
        """Mark a pending sale sync as failed."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pending_sales 
                SET sync_error = ?, retry_count = retry_count + 1
                WHERE id = ?
            """, (error, sale_id))
            conn.commit()
            conn.close()

    def enqueue_sync_event(self, event_id: str, org_id: int, event_type: str,
                          event_data: Dict) -> None:
        """Add event to sync queue."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_queue 
                (id, org_id, event_type, event_data, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (event_id, org_id, event_type, json.dumps(event_data), "PENDING",
                  datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()

    def get_pending_events(self, org_id: int, limit: int = 100) -> List[Dict]:
        """Get events awaiting synchronization."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sync_queue 
                WHERE org_id = ? AND status = 'PENDING'
                ORDER BY created_at ASC
                LIMIT ?
            """, (org_id, limit))
            rows = cursor.fetchall()
            conn.close()
            
            result = []
            for row in rows:
                event_dict = dict(row)
                event_dict["event_data"] = json.loads(event_dict["event_data"])
                result.append(event_dict)
            
            return result

    def mark_event_synced(self, event_id: str, batch_id: str) -> None:
        """Mark an event as synced."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_queue 
                SET status = 'SYNCED', synced_at = ?, sync_batch_id = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), batch_id, event_id))
            conn.commit()
            conn.close()

    def mark_event_sync_failed(self, event_id: str, error: str) -> None:
        """Mark an event sync as failed."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_queue 
                SET sync_error = ?, retry_count = retry_count + 1
                WHERE id = ?
            """, (error, event_id))
            conn.commit()
            conn.close()

    def update_sync_metadata(self, org_id: int, device_id: str = None, 
                            last_sync_at: str = None, last_batch_id: str = None,
                            subscription_state: str = None, 
                            subscription_expires_at: str = None) -> None:
        """Update sync metadata for organization."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO sync_metadata 
                (org_id, device_id, last_sync_at, last_batch_id, subscription_state, subscription_expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (org_id, device_id, last_sync_at, last_batch_id, 
                  subscription_state, subscription_expires_at))
            
            conn.commit()
            conn.close()

    def get_sync_metadata(self, org_id: int) -> Optional[Dict]:
        """Get sync metadata for organization."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sync_metadata WHERE org_id = ?", (org_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None

    def set_connectivity(self, is_online: bool) -> None:
        """Update connectivity state."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO connectivity_state 
                (key, is_online, last_checked_at, last_changed_at)
                VALUES (?, ?, ?, ?)
            """, ("connectivity", 1 if is_online else 0, now, now))
            
            conn.commit()
            conn.close()

    def is_online(self) -> bool:
        """Check if device is online."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT is_online FROM connectivity_state WHERE key = ?", ("connectivity",))
            row = cursor.fetchone()
            conn.close()
            
            return row["is_online"] == 1 if row else True  # Default to online
