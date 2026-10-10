"""Offline fiscal queue management for handling submissions when ZIMRA is unavailable."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.orm import Session
from src.database.config import Base
from decimal import Decimal

logger = logging.getLogger(__name__)


class FiscalQueue(Base):
    """Queue entry for pending fiscal submissions."""
    __tablename__ = "fiscal_queue"
    
    id = Column(Integer, primary_key=True)
    sale_id = Column(String(36), nullable=False, unique=True)
    request_payload = Column(Text, nullable=False)  # JSON string
    status = Column(String(20), nullable=False, default="pending")  # pending, submitting, submitted, failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


class FiscalQueueManager:
    """Manager for offline fiscal queue operations."""
    
    # Retry backoff schedule: exponential backoff starting at 1 second
    RETRY_BACKOFF_SECONDS = [1, 2, 4, 8, 16, 32]
    BATCH_SIZE = 50
    BATCH_DELAY_SECONDS = 1
    CLEANUP_DAYS = 30
    
    def __init__(self, db: Session):
        """
        Initialize queue manager.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db
    
    def enqueue(
        self,
        sale_id: str,
        request_payload: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Add fiscal submission to queue.
        
        Args:
            sale_id: Sale ID
            request_payload: JSON string of fiscal request
            error_message: Optional error message if enqueueing due to failure
        """
        # Check if already queued (idempotency)
        existing = self.db.query(FiscalQueue).filter(FiscalQueue.sale_id == sale_id).first()
        if existing:
            logger.info(f"Fiscal request for sale {sale_id} already in queue")
            return
        
        entry = FiscalQueue(
            sale_id=sale_id,
            request_payload=request_payload,
            status="pending",
            error_message=error_message
        )
        
        self.db.add(entry)
        self.db.commit()
        
        logger.info(f"Enqueued fiscal submission for sale {sale_id}")
    
    def get_pending_items(self, limit: Optional[int] = None) -> List[FiscalQueue]:
        """
        Get pending items ready for submission.
        
        Items are ready if:
        - Status is 'pending' or 'failed'
        - next_retry_at is None or has passed
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of ready FiscalQueue entries
        """
        now = datetime.utcnow()
        query = self.db.query(FiscalQueue).filter(
            FiscalQueue.status.in_(["pending", "failed"]),
            (FiscalQueue.next_retry_at.is_(None) | (FiscalQueue.next_retry_at <= now))
        ).order_by(FiscalQueue.created_at)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def mark_submitting(self, queue_id: int) -> None:
        """Mark entry as currently submitting."""
        entry = self.db.query(FiscalQueue).filter(FiscalQueue.id == queue_id).first()
        if entry:
            entry.status = "submitting"
            self.db.commit()
    
    def mark_submitted(self, queue_id: int, fiscal_number: str) -> None:
        """
        Mark entry as successfully submitted.
        
        Args:
            queue_id: Queue entry ID
            fiscal_number: ZIMRA-assigned fiscal number
        """
        entry = self.db.query(FiscalQueue).filter(FiscalQueue.id == queue_id).first()
        if entry:
            entry.status = "submitted"
            entry.submitted_at = datetime.utcnow()
            entry.error_message = None
            self.db.commit()
            
            logger.info(f"Marked fiscal submission as submitted: {fiscal_number}")
    
    def mark_failed(
        self,
        queue_id: int,
        error_message: str,
        retry: bool = True
    ) -> None:
        """
        Mark entry as failed and schedule retry if applicable.
        
        Args:
            queue_id: Queue entry ID
            error_message: Error description
            retry: If True, schedule next retry; if False, mark as permanently failed
        """
        entry = self.db.query(FiscalQueue).filter(FiscalQueue.id == queue_id).first()
        if not entry:
            return
        
        entry.status = "failed"
        entry.error_message = error_message
        
        if retry and entry.retry_count < len(self.RETRY_BACKOFF_SECONDS):
            # Schedule next retry using current retry_count as index
            backoff = self.RETRY_BACKOFF_SECONDS[entry.retry_count]
            entry.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff)
            entry.status = "pending"
            entry.retry_count += 1
            logger.info(
                f"Scheduled retry for sale {entry.sale_id} in {backoff}s "
                f"(attempt {entry.retry_count})"
            )
        else:
            # Max retries exceeded
            entry.status = "failed"
            entry.retry_count += 1
            logger.error(
                f"Max retries exceeded for sale {entry.sale_id}. "
                f"Error: {error_message}"
            )
        
        self.db.commit()
    
    def cleanup_old_entries(self, older_than_days: Optional[int] = None) -> int:
        """
        Remove submitted entries older than specified days.
        
        Args:
            older_than_days: Age threshold (defaults to CLEANUP_DAYS)
            
        Returns:
            Number of entries deleted
        """
        if older_than_days is None:
            older_than_days = self.CLEANUP_DAYS
        
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        count = self.db.query(FiscalQueue).filter(
            FiscalQueue.status == "submitted",
            FiscalQueue.submitted_at <= cutoff_date
        ).delete()
        
        self.db.commit()
        
        if count > 0:
            logger.info(f"Cleaned up {count} old fiscal queue entries")
        
        return count
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get queue status summary.
        
        Returns:
            Dictionary with queue metrics
        """
        total = self.db.query(FiscalQueue).count()
        pending = self.db.query(FiscalQueue).filter(FiscalQueue.status == "pending").count()
        submitting = self.db.query(FiscalQueue).filter(FiscalQueue.status == "submitting").count()
        submitted = self.db.query(FiscalQueue).filter(FiscalQueue.status == "submitted").count()
        failed = self.db.query(FiscalQueue).filter(FiscalQueue.status == "failed").count()
        
        # Find oldest pending
        oldest = self.db.query(FiscalQueue).filter(
            FiscalQueue.status.in_(["pending", "failed"])
        ).order_by(FiscalQueue.created_at).first()
        
        oldest_age_seconds = None
        if oldest:
            oldest_age_seconds = (datetime.utcnow() - oldest.created_at).total_seconds()
        
        return {
            "total": total,
            "pending": pending,
            "submitting": submitting,
            "submitted": submitted,
            "failed": failed,
            "oldest_age_seconds": oldest_age_seconds,
            "timestamp": datetime.utcnow().isoformat()
        }
