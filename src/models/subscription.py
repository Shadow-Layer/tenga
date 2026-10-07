"""Subscription lifecycle enums and compatibility exports.

The canonical SQLAlchemy subscription table is
``src.models.entities.Subscription``. This module intentionally does not
declare an ORM model so the application has a single subscription table.
"""
from datetime import datetime, timedelta
from enum import Enum

from src.models.entities import Subscription


class SubscriptionState(str, Enum):
    """Authoritative subscription operational states."""

    ACTIVE = "ACTIVE"
    GRACE = "GRACE"
    LIMITED = "LIMITED"


class SubscriptionTerm(str, Enum):
    """Supported subscription billing terms."""

    MONTHLY = "MONTHLY"
    ANNUAL = "ANNUAL"


GRACE_PERIOD_DAYS = {
    SubscriptionTerm.MONTHLY: 7,
    SubscriptionTerm.ANNUAL: 30,
}


def normalize_subscription_term(term: SubscriptionTerm | str) -> SubscriptionTerm:
    """Return a supported subscription term enum from a stored term value."""
    if isinstance(term, SubscriptionTerm):
        return term
    return SubscriptionTerm(str(term).upper())


def normalize_subscription_state(state: SubscriptionState | str) -> SubscriptionState:
    """Return a supported subscription state enum from a stored state value."""
    if isinstance(state, SubscriptionState):
        return state
    return SubscriptionState(str(state).upper())


def grace_duration_for_term(term: SubscriptionTerm | str) -> timedelta:
    """Return the configured grace duration for a billing term."""
    return timedelta(days=GRACE_PERIOD_DAYS[normalize_subscription_term(term)])


__all__ = [
    "Subscription",
    "SubscriptionState",
    "SubscriptionTerm",
    "GRACE_PERIOD_DAYS",
    "normalize_subscription_term",
    "normalize_subscription_state",
    "grace_duration_for_term",
]
