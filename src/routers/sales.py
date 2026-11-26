"""Sales router for POS transactions.

This module provides endpoints for managing Point-of-Sale transactions.
Operations include:
- Create sales (can be online or offline/pending)
- Retrieve sale details and sales history
- Commit pending sales to the system
- Query sales by till or cashier

Sales can be created as:
- COMPLETED: Immediately committed online sales
- PENDING: Offline sales that need to be synced later

Supports multiple payment methods:
- CASH
- CARD
- MOBILE
- Other custom payment methods

Note: Stock oversell is allowed per design (U006).
"""
import logging
from typing import Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from src.database.config import get_db
from src.services.sale_service import SaleService
from src.services.paynow_service import PaynowService
from src.services.fiscal_service import FiscalService
from src.services.paynow_adapter import PaynowConfigurationError, PaynowTransportError
from src.services.tengavfd_adapter import FiscalConfigurationError
from src.services.till_service import TillService
from src.models.entities import (
    FiscalSubmission,
    PaymentAttempt,
    Sale,
    Till,
    TillSession,
    User,
)
from src.schemas.sale import (
    SaleCreate,
    SaleResponse,
    SaleListResponse,
    SaleCommitRequest,
    SaleCommitResponse,
    SaleItemResponse,
)
from src.schemas.paynow import PaynowAttemptResponse, PaynowRetryRequest
from src.schemas.fiscal import (
    FiscalStatusResponse,
    FiscalSubmissionResponse,
    FiscalSubmitRequest,
)
from src.security.authorization import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/sales",
    status_code=201,
    response_model=Union[SaleResponse, PaynowAttemptResponse],
)
def create_sale(
    sale_data: SaleCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new sale (online or offline).

    - **till_id**: Till where sale is made
    - Cashier identity is derived from the authenticated user
    - **payment_method**: Payment method
    - **items**: List of items with product_id, quantity, unit_price
    - **is_offline**: If true, sale is queued as PENDING (offline)
    - Returns: 201 Created with Sale object
    - Error: 404 if till not found, 422 if invalid items

    Note: Oversell is allowed (no stock validation per U006)
    """
    try:
        operation_key = idempotency_key or sale_data.idempotency_key
        if (
            idempotency_key
            and sale_data.idempotency_key
            and idempotency_key != sale_data.idempotency_key
        ):
            raise HTTPException(
                status_code=422,
                detail="Header and body idempotency keys must match",
                headers={"X-Sale-Outcome": "NOT_CREATED"},
            )
        if not operation_key or not operation_key.strip():
            raise HTTPException(
                status_code=422,
                detail="Idempotency-Key is required for sale creation",
                headers={"X-Sale-Outcome": "NOT_CREATED"},
            )
        operation_key = operation_key.strip()
        if len(operation_key) < 8 or len(operation_key) > 90:
            raise HTTPException(
                status_code=422,
                detail="Idempotency-Key must be between 8 and 90 characters",
                headers={"X-Sale-Outcome": "NOT_CREATED"},
            )
        if sale_data.expected_total is not None and any(
            item.unit_price is None
            or item.tax_rate is None
            or item.tax_inclusive is None
            for item in sale_data.items
        ):
            raise HTTPException(
                status_code=422,
                detail="A confirmed checkout total requires price and tax snapshots for every item",
                headers={"X-Sale-Outcome": "NOT_CREATED"},
            )
        if sale_data.is_offline:
            raise HTTPException(
                status_code=422,
                detail="Offline sales must be submitted through the offline sync workflow",
                headers={"X-Sale-Outcome": "NOT_CREATED"},
            )
        # Validate till exists and belongs to user's organization
        till = db.query(Till).filter(
            Till.id == sale_data.till_id,
            Till.organization_id == current_user.organization_id,
        ).first()
        if not till:
            raise HTTPException(
                status_code=404,
                detail=f"Till {sale_data.till_id} not found",
                headers={"X-Sale-Outcome": "NOT_CREATED"},
            )

        # Convert items to service format
        items = [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "tax_rate": item.tax_rate,
                "tax_inclusive": item.tax_inclusive,
            }
            for item in sale_data.items
        ]

        # Create sale
        sale = SaleService.create_sale(
            organization_id=till.organization_id,
            till_id=sale_data.till_id,
            cashier_id=current_user.id,
            payment_method=sale_data.payment_method,
            amount_tendered=sale_data.amount_tendered,
            items=items,
            till_session_id=sale_data.till_session_id,
            idempotency_key=operation_key,
            expected_total=sale_data.expected_total,
            paynow_method=sale_data.paynow_method,
            paynow_phone_number=sale_data.phone_number,
            notes=sale_data.notes,
            db=db,
        )

        if sale.payment_method.upper() == "PAYNOW":
            attempt = db.query(PaymentAttempt).filter(
                PaymentAttempt.sale_id == sale.id,
                PaymentAttempt.organization_id == current_user.organization_id,
            ).order_by(PaymentAttempt.id.desc()).first()
            if attempt is None:
                raise HTTPException(status_code=500, detail="Payment attempt was not persisted")
            # A replay returns the prior attempt. Only an uninitiated PENDING attempt
            # may make the one provider initiation call.
            if attempt.status == "PENDING" and not attempt.provider_reference and not attempt.redirect_url:
                attempt = PaynowService.initiate(
                    attempt.id,
                    sale_data.phone_number,
                    db,
                )
            return _paynow_response(attempt, sale)
        return SaleResponse.from_orm(sale)

    except HTTPException:
        raise
    except ValueError as e:
        db.rollback()
        message = str(e)
        headers = (
            None
            if "already used with a different sale" in message.lower()
            else {"X-Sale-Outcome": "NOT_CREATED"}
        )
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message, headers=headers)
        if "different sale" in message.lower() or "idempotency key" in message.lower():
            raise HTTPException(status_code=409, detail=message, headers=headers)
        if "assigned" in message.lower() or "operator" in message.lower() or "employee" in message.lower():
            raise HTTPException(status_code=403, detail=message, headers=headers)
        if "session" in message.lower() or "open" in message.lower():
            raise HTTPException(status_code=409, detail=message, headers=headers)
        raise HTTPException(status_code=422, detail=message, headers=headers)
    except Exception:
        db.rollback()
        logger.exception("Failed to create sale")
        raise HTTPException(status_code=500, detail="Failed to create sale")


def _paynow_response(attempt: PaymentAttempt, sale: Sale) -> PaynowAttemptResponse:
    return PaynowAttemptResponse(
        id=attempt.id,
        sale_id=attempt.sale_id,
        merchant_reference=attempt.merchant_reference,
        provider_reference=attempt.provider_reference,
        payment_method=attempt.payment_method,
        amount=attempt.amount,
        currency_code=attempt.currency_code,
        status=attempt.status,
        redirect_url=attempt.redirect_url,
        verified_at=attempt.verified_at,
        failure_reason=attempt.failure_reason,
        sale_status=sale.status,
    )


@router.get("/sales/{sale_id}/paynow", response_model=PaynowAttemptResponse)
def get_paynow_status(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = db.query(Sale).filter(
        Sale.id == sale_id,
        Sale.organization_id == current_user.organization_id,
    ).first()
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    attempt = db.query(PaymentAttempt).filter(
        PaymentAttempt.sale_id == sale.id,
        PaymentAttempt.organization_id == current_user.organization_id,
    ).order_by(PaymentAttempt.id.desc()).first()
    if attempt is None:
        raise HTTPException(status_code=404, detail="Paynow attempt not found")
    if attempt.status != "SETTLED":
        try:
            attempt, sale = PaynowService.verify(attempt.id, db)
        except PaynowConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except PaynowTransportError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _paynow_response(attempt, sale)


@router.post("/paynow/callback")
async def paynow_callback(
    request: Request,
    x_paynow_signature: str = Header("", alias="X-Paynow-Signature"),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    if len(raw_body) > 16_384:
        raise HTTPException(status_code=413, detail="Payment callback is too large")
    try:
        if not PaynowService.verify_callback_signature(raw_body, x_paynow_signature):
            raise HTTPException(status_code=401, detail="Invalid payment callback signature")
        payload = PaynowService.callback_payload(raw_body)
    except PaynowConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    attempt = db.query(PaymentAttempt).filter(
        PaymentAttempt.provider == "PAYNOW",
        PaymentAttempt.merchant_reference == str(payload.get("merchant_reference", "")),
    ).first()
    if attempt is None:
        raise HTTPException(status_code=404, detail="Payment attempt not found")
    if not PaynowService.validate_callback_matches(payload, attempt):
        raise HTTPException(status_code=409, detail="Callback does not match the payment attempt")
    try:
        attempt, sale = PaynowService.verify(attempt.id, db)
    except PaynowConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _paynow_response(attempt, sale)


@router.post(
    "/paynow/{attempt_id}/retry",
    response_model=PaynowAttemptResponse,
    status_code=201,
)
def retry_paynow_attempt(
    attempt_id: int,
    request_data: PaynowRetryRequest = PaynowRetryRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    previous = db.query(PaymentAttempt).filter(
        PaymentAttempt.id == attempt_id,
        PaymentAttempt.organization_id == current_user.organization_id,
    ).first()
    if previous is None:
        raise HTTPException(status_code=404, detail="Payment attempt not found")
    sale = db.query(Sale).filter(
        Sale.id == previous.sale_id,
        Sale.organization_id == current_user.organization_id,
    ).first()
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    session = db.query(TillSession).filter(
        TillSession.id == previous.till_session_id,
        TillSession.organization_id == current_user.organization_id,
        TillSession.till_id == sale.till_id,
        TillSession.status == "OPEN",
        TillSession.operator_id == current_user.id,
    ).first()
    if session is None:
        raise HTTPException(status_code=409, detail="An owned open till session is required to retry")
    try:
        till = db.query(Till).filter(
            Till.id == session.till_id,
            Till.organization_id == current_user.organization_id,
        ).first()
        if till is None:
            raise HTTPException(status_code=404, detail="Till not found")
        TillService.require_assigned_user(till, current_user, db)
        if previous.payment_method == "MOBILE_MONEY" and not (
            request_data.phone_number or ""
        ).strip():
            raise HTTPException(
                status_code=422,
                detail="A phone number is required to retry a mobile-money payment",
            )
        attempt, created = PaynowService.retry_failed(attempt_id, db)
        if created:
            attempt = PaynowService.initiate(
                attempt.id,
                request_data.phone_number,
                db,
            )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _paynow_response(attempt, sale)


@router.post("/sales/{sale_id}/fiscal/submit", response_model=FiscalSubmissionResponse)
def submit_fiscal_sale(
    sale_id: int,
    request_data: FiscalSubmitRequest = FiscalSubmitRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = db.query(Sale).filter(
        Sale.id == sale_id,
        Sale.organization_id == current_user.organization_id,
    ).first()
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    try:
        submission = FiscalService.submit(
            sale,
            current_user.id,
            db,
            retry_failed=request_data.retry_failed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FiscalSubmissionResponse.from_orm(submission)


@router.get("/sales/{sale_id}/fiscal/status", response_model=FiscalStatusResponse)
def get_fiscal_status(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = db.query(Sale).filter(
        Sale.id == sale_id,
        Sale.organization_id == current_user.organization_id,
    ).first()
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    submissions = db.query(FiscalSubmission).filter(
        FiscalSubmission.organization_id == current_user.organization_id,
        FiscalSubmission.sale_id == sale.id,
    ).order_by(FiscalSubmission.attempt_number).all()
    return FiscalStatusResponse(
        sale_id=sale.id,
        fiscal_status=sale.fiscal_status,
        fiscal_number=sale.fiscal_number,
        submissions=[FiscalSubmissionResponse.from_orm(row) for row in submissions],
    )


@router.post(
    "/sales/{sale_id}/fiscal/reconcile",
    response_model=FiscalSubmissionResponse,
)
def reconcile_fiscal_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = db.query(Sale).filter(
        Sale.id == sale_id,
        Sale.organization_id == current_user.organization_id,
    ).first()
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    submission = db.query(FiscalSubmission).filter(
        FiscalSubmission.organization_id == current_user.organization_id,
        FiscalSubmission.sale_id == sale.id,
    ).order_by(FiscalSubmission.attempt_number.desc()).first()
    if submission is None:
        raise HTTPException(status_code=404, detail="Fiscal submission not found")
    try:
        submission = FiscalService.reconcile(submission, db)
    except FiscalConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return FiscalSubmissionResponse.from_orm(submission)


@router.get("/sales", response_model=SaleListResponse)
def list_sales(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    till_id: int = Query(None, description="Optional filter by till ID"),
    status: str = Query(None, description="Optional filter by status (PENDING, COMPLETED)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List sales with optional filtering.

    - **skip**: Pagination offset
    - **limit**: Pagination limit
    - **till_id**: Optional filter by till
    - **status**: Optional filter by status
    - Returns: 200 with paginated list of sales
    """
    query = db.query(Sale).filter(Sale.organization_id == current_user.organization_id)

    # Apply filters
    if till_id:
        # Verify till belongs to user's organization
        till = db.query(Till).filter(
            Till.id == till_id,
            Till.organization_id == current_user.organization_id,
        ).first()
        if not till:
            raise HTTPException(status_code=403, detail="Access denied to this till")
        query = query.filter(Sale.till_id == till_id)
    
    if status:
        query = query.filter(Sale.status == status)

    # Count total
    total = query.count()

    # Apply pagination
    sales = query.order_by(Sale.created_at.desc()).offset(skip).limit(limit).all()

    return SaleListResponse(
        items=[SaleResponse.from_orm(sale) for sale in sales],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/sales/{sale_id}", response_model=SaleResponse)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get sale details including line items.

    - **sale_id**: Sale ID
    - Returns: 200 with Sale details including line items
    - Error: 404 if not found or 403 if not authorized
    """
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail=f"Sale {sale_id} not found")
    
    # Check authorization
    if sale.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this sale")

    return SaleResponse.from_orm(sale)



@router.post("/sales/{sale_id}/commit", response_model=SaleCommitResponse)
def commit_sale(
    sale_id: int,
    commit_data: SaleCommitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Commit a pending sale (idempotent).

    - **sale_id**: Sale ID to commit
    - Commit identity is derived from the authenticated user
    - Returns: 200 with committed Sale
    - IDEMPOTENT: Calling twice returns 200, doesn't double-process
    - Error: 404 if sale not found, 409 if already committed

    On commit:
    - Sale status changes from PENDING to COMPLETED
    - InventoryMovements are generated (idempotent - only if not already created)
    """
    # Get sale
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail=f"Sale {sale_id} not found")
    
    # Check authorization
    if sale.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this sale")

    # Check if already committed (idempotency)
    if sale.status == "COMPLETED":
        # Return 200 with the sale (idempotent - no error)
        return SaleCommitResponse.from_orm(sale)

    try:
        # Commit the sale
        SaleService.commit_pending_sale(
            sale_id=sale_id,
            recorded_by_id=current_user.id,
            db=db,
        )

        # Refresh sale to get updated status
        db.refresh(sale)
        return SaleCommitResponse.from_orm(sale)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        db.rollback()
        logger.exception("Failed to commit sale %s", sale_id)
        raise HTTPException(status_code=500, detail="Failed to commit sale")
