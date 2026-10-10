"""Tests for Offline Fiscal Queue Management (T4)."""
import pytest
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.services.fiscal_queue import FiscalQueue, FiscalQueueManager
from src.database.config import Base


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestFiscalQueueEnqueue:
    """Test enqueueing fiscal submissions."""
    
    def test_enqueue_creates_entry(self, db_session):
        """Test enqueueing creates new entry."""
        manager = FiscalQueueManager(db_session)
        payload = json.dumps({"sale_id": "SALE-001", "amount": "100.00"})
        
        manager.enqueue("SALE-001", payload)
        
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-001"
        ).first()
        
        assert entry is not None
        assert entry.status == "pending"
        assert entry.request_payload == payload
        assert entry.retry_count == 0
    
    def test_enqueue_idempotent(self, db_session):
        """Test duplicate enqueues are idempotent."""
        manager = FiscalQueueManager(db_session)
        payload = json.dumps({"sale_id": "SALE-001", "amount": "100.00"})
        
        manager.enqueue("SALE-001", payload)
        manager.enqueue("SALE-001", payload)  # Should not create duplicate
        
        count = db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-001"
        ).count()
        
        assert count == 1
    
    def test_enqueue_with_error_message(self, db_session):
        """Test enqueue with error message."""
        manager = FiscalQueueManager(db_session)
        payload = json.dumps({"sale_id": "SALE-001"})
        error = "ZIMRA offline"
        
        manager.enqueue("SALE-001", payload, error)
        
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-001"
        ).first()
        
        assert entry.error_message == error


class TestFiscalQueueDequeue:
    """Test dequeueing fiscal submissions."""
    
    def test_get_pending_items_returns_ready(self, db_session):
        """Test getting pending items returns ready submissions."""
        manager = FiscalQueueManager(db_session)
        
        # Enqueue multiple items
        for i in range(3):
            payload = json.dumps({"sale_id": f"SALE-{i:03d}"})
            manager.enqueue(f"SALE-{i:03d}", payload)
        
        pending = manager.get_pending_items()
        
        assert len(pending) == 3
        assert all(p.status == "pending" for p in pending)
    
    def test_get_pending_items_respects_retry_schedule(self, db_session):
        """Test pending items respects retry schedule."""
        manager = FiscalQueueManager(db_session)
        
        # Enqueue item
        payload1 = json.dumps({"sale_id": "SALE-001"})
        manager.enqueue("SALE-001", payload1)
        
        # Mark as failed with retry scheduled
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-001"
        ).first()
        entry.status = "failed"
        entry.retry_count = 1
        entry.next_retry_at = datetime.utcnow() + timedelta(seconds=10)
        db_session.commit()
        
        # Enqueue another item (ready immediately)
        payload2 = json.dumps({"sale_id": "SALE-002"})
        manager.enqueue("SALE-002", payload2)
        
        pending = manager.get_pending_items()
        
        # Only SALE-002 should be ready
        assert len(pending) == 1
        assert pending[0].sale_id == "SALE-002"
    
    def test_get_pending_items_respects_limit(self, db_session):
        """Test pending items respects limit."""
        manager = FiscalQueueManager(db_session)
        
        for i in range(5):
            payload = json.dumps({"sale_id": f"SALE-{i:03d}"})
            manager.enqueue(f"SALE-{i:03d}", payload)
        
        pending = manager.get_pending_items(limit=2)
        
        assert len(pending) == 2


class TestFiscalQueueStatusTransitions:
    """Test queue status transitions."""
    
    def test_mark_submitting(self, db_session):
        """Test marking entry as submitting."""
        manager = FiscalQueueManager(db_session)
        payload = json.dumps({"sale_id": "SALE-001"})
        manager.enqueue("SALE-001", payload)
        
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-001"
        ).first()
        
        manager.mark_submitting(entry.id)
        
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.id == entry.id
        ).first()
        
        assert entry.status == "submitting"
    
    def test_mark_submitted(self, db_session):
        """Test marking entry as submitted."""
        manager = FiscalQueueManager(db_session)
        payload = json.dumps({"sale_id": "SALE-001"})
        manager.enqueue("SALE-001", payload)
        
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-001"
        ).first()
        
        before = datetime.utcnow()
        manager.mark_submitted(entry.id, "ZWE-12345678")
        after = datetime.utcnow()
        
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.id == entry.id
        ).first()
        
        assert entry.status == "submitted"
        assert entry.submitted_at is not None
        assert before <= entry.submitted_at <= after
        assert entry.error_message is None
    
    def test_mark_failed_with_retry(self, db_session):
        """Test marking entry as failed with retry scheduled."""
        manager = FiscalQueueManager(db_session)
        payload = json.dumps({"sale_id": "SALE-001"})
        manager.enqueue("SALE-001", payload)
        
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-001"
        ).first()
        
        before = datetime.utcnow()
        manager.mark_failed(entry.id, "Connection timeout", retry=True)
        after = datetime.utcnow()
        
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.id == entry.id
        ).first()
        
        assert entry.status == "pending"  # Resets to pending for retry
        assert entry.retry_count == 1
        assert entry.error_message == "Connection timeout"
        assert entry.next_retry_at is not None
        # Backoff should be 1 second (first retry)
        expected_retry = before + timedelta(seconds=1)
        assert abs((entry.next_retry_at - expected_retry).total_seconds()) < 1
    
    def test_mark_failed_exponential_backoff(self, db_session):
        """Test exponential backoff schedule."""
        manager = FiscalQueueManager(db_session)
        
        # Enqueue item
        payload = json.dumps({"sale_id": "SALE-001"})
        manager.enqueue("SALE-001", payload)
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-001"
        ).first()
        
        # Fail it multiple times and check backoff
        expected_backoffs = [1, 2, 4, 8, 16, 32]
        
        for expected_backoff in expected_backoffs:
            before = datetime.utcnow()
            manager.mark_failed(entry.id, "Error", retry=True)
            after = datetime.utcnow()
            
            entry = db_session.query(FiscalQueue).filter(
                FiscalQueue.id == entry.id
            ).first()
            
            expected_retry = before + timedelta(seconds=expected_backoff)
            assert abs((entry.next_retry_at - expected_retry).total_seconds()) < 1
    
    def test_mark_failed_max_retries_exceeded(self, db_session):
        """Test marking entry as permanently failed after max retries."""
        manager = FiscalQueueManager(db_session)
        payload = json.dumps({"sale_id": "SALE-001"})
        manager.enqueue("SALE-001", payload)
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-001"
        ).first()
        
        # Exhaust retries (6 retries scheduled, then 1 final failure)
        num_backoff_slots = len(manager.RETRY_BACKOFF_SECONDS)
        for i in range(num_backoff_slots + 1):
            manager.mark_failed(entry.id, "Error", retry=True)
            entry = db_session.query(FiscalQueue).filter(
                FiscalQueue.id == entry.id
            ).first()
        
        # Should be permanently failed now with retry_count = num_backoff_slots + 1
        assert entry.status == "failed"
        assert entry.retry_count == num_backoff_slots + 1


class TestFiscalQueueCleanup:
    """Test queue cleanup operations."""
    
    def test_cleanup_old_submitted_entries(self, db_session):
        """Test cleanup removes old submitted entries."""
        manager = FiscalQueueManager(db_session)
        
        # Create submitted entry (old)
        old_entry = FiscalQueue(
            sale_id="SALE-OLD",
            request_payload=json.dumps({"amount": "100.00"}),
            status="submitted",
            submitted_at=datetime.utcnow() - timedelta(days=31)
        )
        db_session.add(old_entry)
        
        # Create recent submitted entry
        recent_entry = FiscalQueue(
            sale_id="SALE-RECENT",
            request_payload=json.dumps({"amount": "100.00"}),
            status="submitted",
            submitted_at=datetime.utcnow() - timedelta(days=1)
        )
        db_session.add(recent_entry)
        db_session.commit()
        
        deleted = manager.cleanup_old_entries(older_than_days=30)
        
        assert deleted == 1
        
        # Old entry deleted
        assert db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-OLD"
        ).count() == 0
        
        # Recent entry remains
        assert db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-RECENT"
        ).count() == 1
    
    def test_cleanup_preserves_pending_entries(self, db_session):
        """Test cleanup doesn't delete pending entries."""
        manager = FiscalQueueManager(db_session)
        
        # Create old pending entry
        old_pending = FiscalQueue(
            sale_id="SALE-PENDING",
            request_payload=json.dumps({"amount": "100.00"}),
            status="pending",
            created_at=datetime.utcnow() - timedelta(days=31)
        )
        db_session.add(old_pending)
        db_session.commit()
        
        deleted = manager.cleanup_old_entries(older_than_days=30)
        
        assert deleted == 0
        
        # Pending entry preserved
        assert db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id == "SALE-PENDING"
        ).count() == 1


class TestFiscalQueueStatus:
    """Test queue status reporting."""
    
    def test_get_queue_status(self, db_session):
        """Test getting queue status summary."""
        manager = FiscalQueueManager(db_session)
        
        # Add various entries
        for i in range(3):
            payload = json.dumps({"sale_id": f"SALE-{i:03d}"})
            manager.enqueue(f"SALE-{i:03d}", payload)
        
        # Mark one as submitted
        entry = db_session.query(FiscalQueue).first()
        manager.mark_submitted(entry.id, "ZWE-12345")
        
        # Mark one as failed with retry (which resets to pending)
        entry = db_session.query(FiscalQueue).filter(
            FiscalQueue.sale_id != "SALE-000"
        ).first()
        manager.mark_failed(entry.id, "Error", retry=True)
        
        status = manager.get_queue_status()
        
        assert status['total'] == 3
        assert status['pending'] >= 1  # At least 1 pending (requeued from failure)
        assert status['submitted'] == 1
        assert status['failed'] == 0  # Failed with retry is reset to pending
        assert status['timestamp'] is not None
