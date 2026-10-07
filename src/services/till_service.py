"""Till session lifecycle and limited mode enforcement service.

Manages till sessions (open/close) and enforces subscription state restrictions.
"""
from datetime import datetime
from typing import Optional, List, Callable
from sqlalchemy.orm import Session

from src.models.entities import (
    TillSession,
    Till,
    User,
    Organization,
    Sale,
)
from src.models.subscription import SubscriptionState
from src.services.subscription_service import SubscriptionService


class TillService:
    """Manages till sessions and operational restrictions."""

    @staticmethod
    def open_session(
        organization_id: int,
        till_id: int,
        operator_id: int,
        opening_balance: float = 0,
        db: Optional[Session] = None,
    ) -> TillSession:
        """Open a new till session.

        Args:
            organization_id: Organization ID
            till_id: Till ID
            operator_id: Operator user ID
            opening_balance: Opening cash balance
            db: Database session

        Returns:
            Created TillSession

        Raises:
            ValueError: If entities don't exist or till already has open session
        """
        if db is None:
            from src.database import get_db
            db = next(get_db())

        # Validate entities
        org = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        if not org:
            raise ValueError(f"Organization {organization_id} not found")

        till = db.query(Till).filter(
            Till.id == till_id,
            Till.organization_id == organization_id,
        ).first()
        if not till:
            raise ValueError(f"Till {till_id} not found in org {organization_id}")

        operator = db.query(User).filter(
            User.id == operator_id,
            User.organization_id == organization_id,
        ).first()
        if not operator:
            raise ValueError(
                f"Operator {operator_id} not found in org {organization_id}"
            )

        # Check for overlapping open session
        existing_open = db.query(TillSession).filter(
            TillSession.till_id == till_id,
            TillSession.status == "OPEN",
        ).first()
        if existing_open:
            raise ValueError(f"Till {till_id} already has an open session")

        # Create session
        session_number = f"{till_id}-{int(datetime.utcnow().timestamp())}"
        till_session = TillSession(
            organization_id=organization_id,
            till_id=till_id,
            operator_id=operator_id,
            session_number=session_number,
            opening_balance=opening_balance,
            status="OPEN",
            opened_at=datetime.utcnow(),
        )

        db.add(till_session)
        db.commit()
        return till_session

    @staticmethod
    def close_session(
        till_session_id: int,
        closing_balance: float,
        notes: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> TillSession:
        """Close a till session.

        Args:
            till_session_id: Till session ID
            closing_balance: Closing cash balance
            notes: Optional reconciliation notes
            db: Database session

        Returns:
            Updated TillSession

        Raises:
            ValueError: If session not found or already closed
        """
        if db is None:
            from src.database import get_db
            db = next(get_db())

        till_session = db.query(TillSession).filter(
            TillSession.id == till_session_id
        ).first()
        if not till_session:
            raise ValueError(f"Till session {till_session_id} not found")

        if till_session.status != "OPEN":
            raise ValueError(
                f"Till session {till_session_id} is not open (status={till_session.status})"
            )

        till_session.closing_balance = closing_balance
        till_session.status = "CLOSED"
        till_session.closed_at = datetime.utcnow()
        till_session.notes = notes
        till_session.updated_at = datetime.utcnow()

        db.commit()
        return till_session

    @staticmethod
    def get_current_open_session(
        till_id: int,
        db: Session,
    ) -> Optional[TillSession]:
        """Get the currently open session for a till.

        Args:
            till_id: Till ID
            db: Database session

        Returns:
            Open TillSession, or None if no open session
        """
        return db.query(TillSession).filter(
            TillSession.till_id == till_id,
            TillSession.status == "OPEN",
        ).first()

    @staticmethod
    def get_sessions_for_till(
        till_id: int,
        limit: int = 100,
        db: Optional[Session] = None,
    ) -> List[TillSession]:
        """Fetch recent sessions for a till.

        Args:
            till_id: Till ID
            limit: Maximum records to return
            db: Database session

        Returns:
            List of TillSession records, newest first
        """
        if db is None:
            from src.database import get_db
            db = next(get_db())

        return db.query(TillSession).filter(
            TillSession.till_id == till_id
        ).order_by(TillSession.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_sales_in_session(
        till_session_id: int,
        db: Session,
    ) -> List[Sale]:
        """Fetch all sales in a till session.

        Args:
            till_session_id: Till session ID
            db: Database session

        Returns:
            List of Sale records
        """
        return db.query(Sale).filter(
            Sale.till_session_id == till_session_id
        ).order_by(Sale.created_at).all()

    @staticmethod
    def check_limited_mode(
        subscription_or_state: str,
    ) -> bool:
        """Check if subscription is in LIMITED mode.

        Args:
            subscription_or_state: Subscription state string or SubscriptionState enum

        Returns:
            True if LIMITED, False otherwise
        """
        if isinstance(subscription_or_state, str):
            return subscription_or_state == SubscriptionState.LIMITED.value
        return subscription_or_state == SubscriptionState.LIMITED

    @staticmethod
    def get_limited_mode_guard(
        organization_id: int,
        db: Session,
    ) -> Callable[[], bool]:
        """Get a callable that checks if operations are allowed (subscription not LIMITED).

        Returns a function that can be used to guard sale creation, inventory operations, etc.

        Args:
            organization_id: Organization ID
            db: Database session

        Returns:
            Callable that returns True if operations allowed, False if LIMITED
        """
        def guard() -> bool:
            subscription = SubscriptionService.get_subscription_by_org(
                organization_id,
                db,
            )
            if not subscription:
                return True  # No subscription = no restriction

            return not SubscriptionService.is_limited(subscription)

        return guard

    @staticmethod
    def assert_open_allowed(
        organization_id: int,
        db: Session,
    ) -> None:
        """Assert that opening a new till session is allowed (subscription not LIMITED).

        Args:
            organization_id: Organization ID
            db: Database session

        Raises:
            ValueError: If subscription is LIMITED
        """
        subscription = SubscriptionService.get_subscription_by_org(
            organization_id,
            db,
        )
        if subscription and SubscriptionService.is_limited(subscription):
            raise ValueError(
                "Cannot open till session: subscription is in LIMITED mode"
            )

    @staticmethod
    def assert_offline_cached_allowed(
        cached_state: str,
    ) -> None:
        """Assert that operation is allowed based on offline cached state.

        Per U008: if cached state is LIMITED, block locally.
        If cached state is ACTIVE/GRACE, allow.

        Args:
            cached_state: Subscription state from device cache

        Raises:
            ValueError: If cached state is LIMITED
        """
        if cached_state == SubscriptionState.LIMITED.value:
            raise ValueError(
                "Cannot perform operation: cached subscription state is LIMITED"
            )
