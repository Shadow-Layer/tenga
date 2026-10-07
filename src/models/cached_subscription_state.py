"""Cached subscription state model for offline device support (T002, U008)."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON

from src.database import Base


class CachedSubscriptionState(Base):
    """Device-side cached subscription state for offline operations (U008).

    Devices cache the last-known subscription state to make decisions offline.
    On reconnect, the server's authoritative state is fetched and cache is updated.
    """

    __tablename__ = "cached_subscription_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(100), nullable=False, unique=True, index=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False, index=True)

    # Subscription state snapshot
    state = Column(String(20), nullable=False)  # ACTIVE, GRACE, LIMITED
    state_snapshot = Column(JSON, nullable=False)  # Full state data

    # Last sync timestamp
    last_sync_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")

    __table_args__ = (
        {"extend_existing": True},
    )
