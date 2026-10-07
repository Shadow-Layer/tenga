"""Subscription lifecycle state machine and grace period logic.

Manages subscription states (ACTIVE, GRACE, LIMITED) and transitions based on
expiry dates and grace period durations per subscription term.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from src.models.entities import Subscription
from src.models.subscription import (
    SubscriptionState,
    SubscriptionTerm,
    grace_duration_for_term,
    normalize_subscription_state,
    normalize_subscription_term,
)


class SubscriptionStateError(Exception):
    """Raised when subscription state machine encounters invalid transitions."""
    pass


class SubscriptionService:
    """Manages subscription lifecycle and state transitions."""

    @staticmethod
    def compute_current_state(subscription: Subscription) -> SubscriptionState:
        """Determine current subscription state based on expiry and grace periods.

        Args:
            subscription: Subscription record

        Returns:
            Current state (ACTIVE, GRACE, or LIMITED)

        Raises:
            SubscriptionStateError: If subscription term is unknown
        """
        if not subscription.expiry_date:
            return SubscriptionState.ACTIVE

        now = datetime.utcnow()
        expiry = subscription.expiry_date

        # Not yet expired
        if now < expiry:
            return SubscriptionState.ACTIVE

        # Expired but in grace period
        if subscription.grace_end_date and now < subscription.grace_end_date:
            return SubscriptionState.GRACE

        # Grace period expired
        return SubscriptionState.LIMITED

    @staticmethod
    def compute_grace_end_date(
        expiry_date: datetime,
        term: SubscriptionTerm | str,
    ) -> datetime:
        """Compute grace period end date based on subscription term.

        Args:
            expiry_date: Subscription expiry date
            term: Subscription billing term (MONTHLY or ANNUAL)

        Returns:
            Grace period end date

        Raises:
            SubscriptionStateError: If term is invalid
        """
        try:
            term_enum = normalize_subscription_term(term)
            grace_delta = grace_duration_for_term(term_enum)
            return expiry_date + grace_delta
        except ValueError as e:
            raise SubscriptionStateError(f"Invalid subscription term: {term}") from e

    @staticmethod
    def transition_to_grace_if_expired(
        subscription: Subscription,
        db: Session,
    ) -> bool:
        """Check if subscription has expired and transition to GRACE if needed.

        Returns:
            True if transitioned to GRACE, False otherwise

        Raises:
            SubscriptionStateError: If grace_end_date was not set on expiry
        """
        now = datetime.utcnow()

        # Already in GRACE or LIMITED
        if subscription.state in [SubscriptionState.GRACE, SubscriptionState.LIMITED]:
            return False

        # Not yet expired
        if now < subscription.expiry_date:
            return False

        # Expired: transition to GRACE
        if not subscription.grace_end_date:
            raise SubscriptionStateError(
                "grace_end_date must be set before subscription expiry"
            )

        subscription.state = SubscriptionState.GRACE.value
        subscription.updated_at = now
        db.commit()
        return True

    @staticmethod
    def transition_to_limited_if_grace_expired(
        subscription: Subscription,
        db: Session,
    ) -> bool:
        """Check if grace period has expired and transition to LIMITED if needed.

        Returns:
            True if transitioned to LIMITED, False otherwise
        """
        now = datetime.utcnow()

        # Not in GRACE
        if subscription.state != SubscriptionState.GRACE.value:
            return False

        # Grace period not yet expired
        if not subscription.grace_end_date or now < subscription.grace_end_date:
            return False

        # Grace expired: transition to LIMITED
        subscription.state = SubscriptionState.LIMITED.value
        subscription.updated_at = now
        db.commit()
        return True

    @staticmethod
    def is_operational(subscription: Subscription) -> bool:
        """Check if subscription allows normal operations (ACTIVE or GRACE).

        Args:
            subscription: Subscription record

        Returns:
            True if ACTIVE or GRACE, False if LIMITED
        """
        state = SubscriptionService.compute_current_state(subscription)
        return state in [SubscriptionState.ACTIVE, SubscriptionState.GRACE]

    @staticmethod
    def is_limited(subscription: Subscription) -> bool:
        """Check if subscription is in LIMITED mode (no operations allowed).

        Args:
            subscription: Subscription record

        Returns:
            True if LIMITED, False otherwise
        """
        state = SubscriptionService.compute_current_state(subscription)
        return state == SubscriptionState.LIMITED

    @staticmethod
    def is_expired(subscription: Subscription) -> bool:
        """Check if subscription has expired (no longer ACTIVE).

        Args:
            subscription: Subscription record

        Returns:
            True if expired (in GRACE or LIMITED), False if ACTIVE
        """
        state = SubscriptionService.compute_current_state(subscription)
        return state != SubscriptionState.ACTIVE

    @staticmethod
    def days_remaining_in_grace(subscription: Subscription) -> Optional[int]:
        """Compute days remaining in grace period.

        Args:
            subscription: Subscription record

        Returns:
            Days remaining, or None if not in GRACE
        """
        state = SubscriptionService.compute_current_state(subscription)
        if state != SubscriptionState.GRACE:
            return None

        if not subscription.grace_end_date:
            return None

        now = datetime.utcnow()
        remaining = subscription.grace_end_date - now
        return max(0, remaining.days)

    @staticmethod
    def renew_subscription(
        subscription: Subscription,
        new_expiry_date: datetime,
        db: Session,
    ) -> None:
        """Renew subscription, computing new grace period and transitioning to ACTIVE.

        Args:
            subscription: Subscription record
            new_expiry_date: New expiry date
            db: Database session

        Raises:
            SubscriptionStateError: If subscription term is invalid
        """
        subscription.expiry_date = new_expiry_date
        subscription.grace_end_date = SubscriptionService.compute_grace_end_date(
            new_expiry_date,
            subscription.term,
        )
        subscription.state = SubscriptionState.ACTIVE.value
        subscription.updated_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def get_subscription_by_org(
        organization_id: int,
        db: Session,
    ) -> Optional[Subscription]:
        """Fetch subscription for an organization.

        Args:
            organization_id: Organization ID
            db: Database session

        Returns:
            Subscription record, or None if not found
        """
        return db.query(Subscription).filter(
            Subscription.organization_id == organization_id
        ).first()
