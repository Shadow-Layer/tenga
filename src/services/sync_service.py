"""Offline sync protocol and device state reconciliation service.

Handles batch sync of offline sales and state reconciliation.
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from sqlalchemy.orm import Session

from src.models.sync import (
    SyncLog,
    SyncBatchTransaction,
    SyncStatus,
    TransactionType,
    TransactionStatus,
)
from src.models.entities import Organization
from src.services.sale_service import SaleService
from src.services.subscription_service import SubscriptionService


class SyncService:
    """Manages offline-to-online sync operations."""

    @staticmethod
    def process_sync_batch(
        device_id: str,
        organization_id: int,
        transactions: List[dict],
        db: Session,
    ) -> Tuple[SyncLog, List[dict]]:
        """Process a batch of offline transactions from a device.

        Transactions must include:
        - transaction_type: "sale" or "movement"
        - transaction_data: dict with transaction details

        Args:
            device_id: Device ID sending the batch
            organization_id: Organization ID
            transactions: List of transaction dicts
            db: Database session

        Returns:
            Tuple of (SyncLog, list of results for each transaction)

        Raises:
            ValueError: If organization not found
        """
        org = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        if not org:
            raise ValueError(f"Organization {organization_id} not found")

        # Create sync log
        batch_id = str(uuid4())
        sync_log = SyncLog(
            id=str(uuid4()),
            device_id=device_id,
            batch_id=batch_id,
            batch_size=len(transactions),
            status=SyncStatus.SUCCESS,
            timestamp=datetime.utcnow(),
            organization_id=organization_id,
            sync_duration_ms=0,
        )

        results = []
        start_time = datetime.utcnow()

        # Process each transaction
        for idx, transaction in enumerate(transactions):
            batch_transaction = SyncBatchTransaction(
                id=str(uuid4()),
                sync_log_id=sync_log.id,
                transaction_sequence=idx,
                transaction_type=transaction.get("transaction_type"),
                status=TransactionStatus.PENDING,
                transaction_data=transaction.get("transaction_data", {}),
            )

            try:
                # Route by transaction type
                tx_type = transaction.get("transaction_type")
                if tx_type == TransactionType.SALE.value:
                    SyncService._apply_sale_transaction(
                        transaction.get("transaction_data", {}),
                        organization_id,
                        db,
                    )
                    batch_transaction.status = TransactionStatus.APPLIED
                    batch_transaction.applied_at = datetime.utcnow()
                else:
                    raise ValueError(f"Unknown transaction type: {tx_type}")

                results.append({
                    "transaction_sequence": idx,
                    "status": "applied",
                })

            except Exception as e:
                batch_transaction.status = TransactionStatus.FAILED
                batch_transaction.failure_reason = str(e)
                sync_log.status = SyncStatus.PARTIAL_FAILURE
                results.append({
                    "transaction_sequence": idx,
                    "status": "failed",
                    "error": str(e),
                })

            db.add(batch_transaction)

        # Record sync timing
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        sync_log.sync_duration_ms = int(duration)

        db.add(sync_log)
        db.commit()

        return sync_log, results

    @staticmethod
    def _apply_sale_transaction(
        transaction_data: dict,
        organization_id: int,
        db: Session,
    ) -> None:
        """Apply a SALE transaction from sync batch.

        Transaction data must include:
        - sale_id: ID of pending sale
        - user_id: User ID performing sync/commit

        Args:
            transaction_data: Transaction payload
            organization_id: Organization ID
            db: Database session

        Raises:
            ValueError: If sale not found or already applied
        """
        sale_id = transaction_data.get("sale_id")
        user_id = transaction_data.get("user_id")

        if not sale_id or not user_id:
            raise ValueError("Missing sale_id or user_id in transaction data")

        # Commit the pending sale
        SaleService.commit_pending_sale(
            sale_id=sale_id,
            recorded_by_id=user_id,
            db=db,
        )

    @staticmethod
    def get_subscription_state_sync(
        organization_id: int,
        db: Session,
    ) -> Dict[str, any]:
        """Get current subscription state for device cache sync.

        Returns state and grace period info for device to cache.

        Args:
            organization_id: Organization ID
            db: Database session

        Returns:
            Dict with keys:
            - state: ACTIVE, GRACE, or LIMITED
            - expiry_date: ISO datetime
            - grace_end_date: ISO datetime (if in GRACE)
            - days_remaining_in_grace: int (if in GRACE, None otherwise)
            - is_operational: bool
        """
        subscription = SubscriptionService.get_subscription_by_org(
            organization_id,
            db,
        )

        if not subscription:
            return {
                "state": "ACTIVE",
                "is_operational": True,
            }

        state = SubscriptionService.compute_current_state(subscription)
        days_in_grace = SubscriptionService.days_remaining_in_grace(subscription)

        return {
            "state": state.value,
            "expiry_date": subscription.expiry_date.isoformat() if subscription.expiry_date else None,
            "grace_end_date": subscription.grace_end_date.isoformat() if subscription.grace_end_date else None,
            "days_remaining_in_grace": days_in_grace,
            "is_operational": SubscriptionService.is_operational(subscription),
        }

    @staticmethod
    def get_sync_history(
        organization_id: int,
        device_id: Optional[str] = None,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> List[SyncLog]:
        """Fetch sync history for audit trail.

        Args:
            organization_id: Organization ID
            device_id: Optional filter by device
            limit: Maximum records to return
            db: Database session

        Returns:
            List of SyncLog records, newest first
        """
        if db is None:
            from src.database import get_db
            db = next(get_db())

        query = db.query(SyncLog).filter(
            SyncLog.organization_id == organization_id
        )

        if device_id:
            query = query.filter(SyncLog.device_id == device_id)

        return query.order_by(SyncLog.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_idempotency_check(
        device_id: str,
        batch_id: str,
        db: Session,
    ) -> Optional[SyncLog]:
        """Check if batch was already synced (for idempotency).

        Args:
            device_id: Device ID
            batch_id: Batch ID
            db: Database session

        Returns:
            SyncLog if found, None otherwise
        """
        return db.query(SyncLog).filter(
            SyncLog.device_id == device_id,
            SyncLog.batch_id == batch_id,
        ).first()
