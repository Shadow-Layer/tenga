"""Subscription Management API router.

This module provides endpoints for managing organization subscriptions.
Operations include:
- Query subscription details
- Retrieve subscription state (ACTIVE, GRACE, LIMITED)
- Renew subscriptions
- Cache subscription state for offline devices

Subscription states:
- ACTIVE: Subscription is valid
- GRACE: Subscription has expired but within grace period
- LIMITED: Subscription expired and grace period ended (limited functionality)

Grace period handling allows organizations to continue operations
briefly after expiry before reverting to limited mode.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database.config import get_db
from src.models.entities import Subscription, Organization
from src.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    RenewalRequest,
    SubscriptionStateResponse,
)
from src.services.subscription_service import SubscriptionService
from src.models.subscription import SubscriptionState

router = APIRouter()


@router.post(
    "/{org_id}",
    status_code=201,
    response_model=SubscriptionResponse,
    summary="Create subscription",
    description="Create a new subscription for an organization",
)
def create_subscription(
    org_id: int,
    request: SubscriptionCreate,
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Create a new subscription for an organization.
    
    Args:
        org_id: Organization ID
        request: Subscription creation request
        db: Database session
        
    Returns:
        Created subscription object
        
    Raises:
        404: If organization not found
        409: If subscription already exists for org
    """
    # Check if organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=404,
            detail=f"Organization {org_id} not found",
        )
    
    # Check if subscription already exists
    existing = SubscriptionService.get_subscription_by_org(org_id, db)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Subscription already exists for organization {org_id}",
        )
    
    # Compute expiry date based on plan type
    expiry_date = _compute_expiry_date(request.start_date, request.plan_type)
    
    # Compute grace end date
    grace_end_date = SubscriptionService.compute_grace_end_date(
        expiry_date,
        request.plan_type,
    )
    
    # Create subscription
    subscription = Subscription(
        organization_id=org_id,
        plan=request.plan_type,
        term=request.plan_type,
        start_date=request.start_date,
        expiry_date=expiry_date,
        grace_end_date=grace_end_date,
        state=SubscriptionState.ACTIVE.value,
        auto_renew=True,
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    return SubscriptionResponse.model_validate(subscription)


@router.get(
    "/{org_id}",
    response_model=SubscriptionResponse,
    summary="Get current subscription",
    description="Get the current subscription for an organization",
)
def get_subscription(
    org_id: int,
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Get subscription for an organization.
    
    Args:
        org_id: Organization ID
        db: Database session
        
    Returns:
        Subscription object
        
    Raises:
        404: If organization or subscription not found
    """
    # Check if organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=404,
            detail=f"Organization {org_id} not found",
        )
    
    # Get subscription
    subscription = SubscriptionService.get_subscription_by_org(org_id, db)
    if not subscription:
        raise HTTPException(
            status_code=404,
            detail=f"No subscription found for organization {org_id}",
        )
    
    return SubscriptionResponse.model_validate(subscription)


@router.post(
    "/{org_id}/renew",
    response_model=SubscriptionResponse,
    summary="Renew subscription",
    description="Manually renew a subscription",
)
def renew_subscription(
    org_id: int,
    request: RenewalRequest,
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Renew a subscription.
    
    Args:
        org_id: Organization ID
        request: Renewal request (can include new_expiry_date)
        db: Database session
        
    Returns:
        Renewed subscription object
        
    Raises:
        404: If organization or subscription not found
        400: If subscription cannot be renewed
    """
    # Check if organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=404,
            detail=f"Organization {org_id} not found",
        )
    
    # Get subscription
    subscription = SubscriptionService.get_subscription_by_org(org_id, db)
    if not subscription:
        raise HTTPException(
            status_code=404,
            detail=f"No subscription found for organization {org_id}",
        )
    
    # Compute new expiry date if not provided
    if request.new_expiry_date:
        new_expiry_date = request.new_expiry_date
    else:
        # Auto-compute: extend from current expiry date by the term length
        new_expiry_date = _compute_expiry_date(
            subscription.expiry_date, subscription.term
        )
    
    try:
        # Renew the subscription
        SubscriptionService.renew_subscription(
            subscription,
            new_expiry_date,
            db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot renew subscription: {str(e)}",
        )
    
    db.refresh(subscription)
    return SubscriptionResponse.model_validate(subscription)


@router.get(
    "/{org_id}/state",
    response_model=SubscriptionStateResponse,
    summary="Get subscription state",
    description="Get detailed subscription state information",
)
def get_subscription_state(
    org_id: int,
    db: Session = Depends(get_db),
) -> SubscriptionStateResponse:
    """Get subscription state details.
    
    Args:
        org_id: Organization ID
        db: Database session
        
    Returns:
        Subscription state details
        
    Raises:
        404: If organization or subscription not found
    """
    # Check if organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=404,
            detail=f"Organization {org_id} not found",
        )
    
    # Get subscription
    subscription = SubscriptionService.get_subscription_by_org(org_id, db)
    if not subscription:
        raise HTTPException(
            status_code=404,
            detail=f"No subscription found for organization {org_id}",
        )
    
    # Compute state
    state = SubscriptionService.compute_current_state(subscription)
    
    # Compute days remaining until expiry
    now = datetime.utcnow()
    days_remaining = (subscription.expiry_date - now).days
    
    # Compute days in grace period
    days_in_grace = 0
    if state == SubscriptionState.GRACE:
        grace_days = SubscriptionService.days_remaining_in_grace(subscription)
        days_in_grace = grace_days if grace_days is not None else 0
    
    # Check if operational
    operational = SubscriptionService.is_operational(subscription)
    
    return SubscriptionStateResponse(
        state=state.value,
        expiry_date=subscription.expiry_date,
        grace_end_date=subscription.grace_end_date,
        days_remaining=days_remaining,
        days_in_grace=days_in_grace,
        operational=operational,
    )


def _compute_expiry_date(start_date: datetime, term: str) -> datetime:
    """Compute subscription expiry date based on term.
    
    Args:
        start_date: Subscription start date
        term: Billing term (MONTHLY or ANNUAL)
        
    Returns:
        Computed expiry date
    """
    if term.upper() == "MONTHLY":
        return start_date + timedelta(days=30)
    elif term.upper() == "ANNUAL":
        return start_date + timedelta(days=365)
    else:
        raise ValueError(f"Invalid subscription term: {term}")
