"""Organization-scoped tax-rule management."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.config import get_db
from src.models.entities import TaxRule, User
from src.schemas.tax import TaxRuleCreate, TaxRuleResponse, TaxRuleUpdate
from src.security.authorization import get_current_user

router = APIRouter()


def _require_manager(current_user: User) -> None:
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=403,
            detail="Only an admin or manager can manage tax rules",
        )


@router.get("", response_model=list[TaxRuleResponse])
def list_tax_rules(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(TaxRule).filter(
        TaxRule.organization_id == current_user.organization_id
    )
    if not include_inactive:
        query = query.filter(TaxRule.is_active.is_(True))
    return query.order_by(TaxRule.name).all()


@router.post("", response_model=TaxRuleResponse, status_code=201)
def create_tax_rule(
    rule_data: TaxRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    rule = TaxRule(
        organization_id=current_user.organization_id,
        name=rule_data.name.strip(),
        rate=rule_data.rate,
        tax_inclusive=rule_data.tax_inclusive,
    )
    db.add(rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A tax rule with this name already exists",
        )
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=TaxRuleResponse)
def update_tax_rule(
    rule_id: int,
    rule_data: TaxRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    rule = db.query(TaxRule).filter(
        TaxRule.id == rule_id,
        TaxRule.organization_id == current_user.organization_id,
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Tax rule not found")

    changes = rule_data.model_dump(exclude_unset=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
    for field, value in changes.items():
        setattr(rule, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A tax rule with this name already exists",
        )
    db.refresh(rule)
    return rule
