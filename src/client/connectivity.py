"""Connectivity detection and management for offline operation.

Detects online/offline status and provides callbacks for state changes.
"""

import socket
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional
from enum import Enum


class ConnectivityStatus(str, Enum):
    """Connectivity status values."""
    ONLINE = "online"
    OFFLINE = "offline"
    RECONNECTING = "reconnecting"


class ConnectivityManager:
    """Manages device connectivity state."""

    def __init__(self, check_interval: int = 10, check_host: str = "8.8.8.8", 
                 check_port: int = 53):
        """Initialize connectivity manager.
        
        Args:
            check_interval: Seconds between connectivity checks
            check_host: Host to ping for connectivity (default: Google DNS)
            check_port: Port to check (default: 53 for DNS)
        """
        self.check_interval = check_interval
        self.check_host = check_host
        self.check_port = check_port
        
        self.status = ConnectivityStatus.ONLINE
        self.last_check = datetime.utcnow()
        self.callbacks = []
        self.lock = threading.RLock()
        self.running = False
        self.thread = None

    def add_callback(self, callback: Callable[[ConnectivityStatus], None]) -> None:
        """Register callback for status changes.
        
        Args:
            callback: Function called with new status when connectivity changes
        """
        with self.lock:
            self.callbacks.append(callback)

    def start(self) -> None:
        """Start periodic connectivity checks."""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            self.thread = threading.Thread(target=self._check_loop, daemon=True)
            self.thread.start()

    def stop(self) -> None:
        """Stop connectivity checks."""
        with self.lock:
            self.running = False

    def _check_loop(self) -> None:
        """Periodic connectivity check loop."""
        while self.running:
            try:
                is_online = self.is_reachable()
                self._update_status(is_online)
                threading.Event().wait(self.check_interval)
            except Exception:
                pass

    def is_reachable(self) -> bool:
        """Check if device can reach external service.
        
        Returns:
            True if reachable, False if offline
        """
        try:
            socket.create_connection(
                (self.check_host, self.check_port),
                timeout=3
            ).close()
            return True
        except (socket.error, socket.timeout):
            return False

    def _update_status(self, is_online: bool) -> None:
        """Update connectivity status and notify callbacks."""
        with self.lock:
            new_status = ConnectivityStatus.ONLINE if is_online else ConnectivityStatus.OFFLINE
            
            if new_status != self.status:
                self.status = new_status
                self.last_check = datetime.utcnow()
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(new_status)
                    except Exception:
                        pass

    def is_online(self) -> bool:
        """Check current connectivity status.
        
        Returns:
            True if online, False if offline
        """
        with self.lock:
            return self.status == ConnectivityStatus.ONLINE

    def force_check(self) -> ConnectivityStatus:
        """Force immediate connectivity check.
        
        Returns:
            Current connectivity status
        """
        is_online = self.is_reachable()
        self._update_status(is_online)
        
        with self.lock:
            return self.status

    def wait_for_online(self, timeout: int = None) -> bool:
        """Wait for device to come online.
        
        Args:
            timeout: Maximum seconds to wait (None = indefinite)
        
        Returns:
            True if came online, False if timeout
        """
        start = datetime.utcnow()
        timeout_delta = timedelta(seconds=timeout) if timeout else None
        
        while True:
            if self.is_online():
                return True
            
            if timeout_delta and (datetime.utcnow() - start) > timeout_delta:
                return False
            
            threading.Event().wait(1)
