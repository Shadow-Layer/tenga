"""Till administration and session lifecycle service."""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, List, Optional

from sqlalchemy import func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.entities import (
    Employee,
    EmployeeTillAssignment,
    Location,
    Organization,
    PaymentAttempt,
    Sale,
    Till,
    TillCashMovement,
    TillSession,
    User,
)
from src.models.subscription import SubscriptionState
from src.services.subscription_service import SubscriptionService


_MONEY_QUANTUM = Decimal("0.01")
_TERMINAL_ATTEMPT_STATUSES = {
    "SETTLED",
    "SUCCEEDED",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "EXPIRED",
}


class TillService:
    """Manages tills, assignments, sessions, and operational restrictions."""

    @staticmethod
    def _lock_till_row(till_id: int, organization_id: int, db: Session) -> None:
        result = db.execute(
            update(Till)
            .where(Till.id == till_id, Till.organization_id == organization_id)
            .values(updated_at=Till.updated_at)
        )
        if not result.rowcount:
            raise ValueError(f"Till {till_id} not found in org {organization_id}")

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def require_assigned_user(
        till: Till,
        user: User,
        db: Session,
    ) -> Employee:
        """Return the active employee assignment required to operate a till."""
        if not user.is_active or user.organization_id != till.organization_id:
            raise ValueError("An active organization user is required")
        employee = db.query(Employee).filter(
            Employee.organization_id == till.organization_id,
            Employee.user_id == user.id,
            Employee.is_active.is_(True),
            Employee.archived_at.is_(None),
        ).first()
        if employee is None:
            raise ValueError("An active employee record is required to operate a till")
        assignment = db.query(EmployeeTillAssignment.id).filter(
            EmployeeTillAssignment.employee_id == employee.id,
            EmployeeTillAssignment.till_id == till.id,
            EmployeeTillAssignment.ended_at.is_(None),
        ).first()
        if assignment is None:
            raise ValueError("User is not assigned to this till")
        return employee

    @staticmethod
    def create_till(
        organization_id: int,
        location_id: int,
        code: str,
        name: str,
        db: Session,
    ) -> Till:
        normalized_code = code.strip()
        normalized_name = name.strip()
        if not normalized_code or not normalized_name:
            raise ValueError("Till code and name cannot be blank")
        location = db.query(Location).filter(
            Location.id == location_id,
            Location.organization_id == organization_id,
            Location.is_active.is_(True),
        ).first()
        if location is None:
            raise ValueError("Location not found")
        till = Till(
            organization_id=organization_id,
            location_id=location_id,
            code=normalized_code,
            name=normalized_name,
            is_active=True,
        )
        db.add(till)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("A till with this code already exists") from exc
        db.refresh(till)
        return till

    @staticmethod
    def update_till(till: Till, changes: dict, db: Session) -> Till:
        try:
            TillService._lock_till_row(till.id, till.organization_id, db)
            db.refresh(till)
            if "location_id" in changes and changes["location_id"] != till.location_id:
                location = db.query(Location).filter(
                    Location.id == changes["location_id"],
                    Location.organization_id == till.organization_id,
                    Location.is_active.is_(True),
                ).first()
                if location is None:
                    raise ValueError("Location not found")
                has_history = (
                    db.query(TillSession.id).filter(TillSession.till_id == till.id).first()
                    or db.query(Sale.id).filter(Sale.till_id == till.id).first()
                )
                if has_history:
                    raise ValueError("Cannot move a till after it has transaction history")
            for field in ("name", "code"):
                if field in changes:
                    changes[field] = changes[field].strip()
                    if not changes[field]:
                        raise ValueError(f"{field} cannot be blank")
            for field, value in changes.items():
                setattr(till, field, value)
            till.updated_at = datetime.utcnow()
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("A till with this code already exists") from exc
        except Exception:
            db.rollback()
            raise
        db.refresh(till)
        return till

    @staticmethod
    def deactivate_till(till: Till, db: Session) -> Till:
        try:
            TillService._lock_till_row(till.id, till.organization_id, db)
            db.refresh(till)
            if TillService.get_current_open_session(
                till.id, db, organization_id=till.organization_id
            ):
                raise ValueError("Cannot deactivate a till with an open session")
            till.is_active = False
            till.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(till)
            return till
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def set_assignments(till: Till, employee_ids: List[int], db: Session) -> List[Employee]:
        if len(set(employee_ids)) != len(employee_ids):
            raise ValueError("Employee assignments must be unique")
        try:
            TillService._lock_till_row(till.id, till.organization_id, db)
            db.refresh(till)
            employees = []
            if employee_ids:
                employees = db.query(Employee).filter(
                    Employee.id.in_(employee_ids),
                    Employee.organization_id == till.organization_id,
                    Employee.is_active.is_(True),
                    Employee.archived_at.is_(None),
                ).all()
                if len(employees) != len(set(employee_ids)):
                    raise ValueError("One or more employees are unavailable")
            now = datetime.utcnow()
            active_assignments = db.query(EmployeeTillAssignment).filter(
                EmployeeTillAssignment.till_id == till.id,
                EmployeeTillAssignment.ended_at.is_(None),
            ).all()
            requested_employee_ids = set(employee_ids)
            open_session = TillService.get_current_open_session(
                till.id, db, organization_id=till.organization_id
            )
            if open_session:
                current_operator = db.query(Employee.id).filter(
                    Employee.organization_id == till.organization_id,
                    Employee.user_id == open_session.operator_id,
                    Employee.is_active.is_(True),
                    Employee.archived_at.is_(None),
                ).first()
                if current_operator and current_operator[0] not in requested_employee_ids:
                    raise ValueError(
                        "Cannot remove the assigned operator while a session is open"
                    )
            active_by_employee = {
                assignment.employee_id: assignment for assignment in active_assignments
            }
            for employee_id, assignment in active_by_employee.items():
                if employee_id not in requested_employee_ids:
                    assignment.ended_at = now
            for employee in employees:
                if employee.id not in active_by_employee:
                    db.add(EmployeeTillAssignment(
                        employee_id=employee.id,
                        till_id=till.id,
                        ended_at=None,
                    ))
            db.commit()
        except Exception:
            db.rollback()
            raise
        return employees

    @staticmethod
    def create_cash_movement(
        till_id: int,
        organization_id: int,
        actor: User,
        operation_id: str,
        movement_type: str,
        amount: Decimal,
        reason: str,
        reference: Optional[str],
        db: Session,
    ):
        """Record an idempotent, append-only paid-in or paid-out movement."""
        normalized_type = movement_type.strip().upper()
        if normalized_type not in {"CASH_IN", "CASH_OUT"}:
            raise ValueError("Movement type must be CASH_IN or CASH_OUT")
        amount = TillService._money(amount)
        if amount <= 0:
            raise ValueError("Cash movement amount must be positive")
        if not operation_id.strip():
            raise ValueError("Operation ID cannot be blank")
        reason = reason.strip()
        if not reason:
            raise ValueError("Cash movement reason cannot be blank")
        reference = reference.strip() if reference else None

        try:
            TillService._lock_till_row(till_id, organization_id, db)
            till = db.query(Till).filter(
                Till.id == till_id,
                Till.organization_id == organization_id,
            ).first()
            if till is None:
                raise ValueError("Till not found")
            authenticated_actor = db.query(User).filter(
                User.id == actor.id,
                User.organization_id == organization_id,
                User.is_active.is_(True),
            ).first()
            if authenticated_actor is None:
                raise ValueError("An active organization user is required")
            employee = TillService.require_assigned_user(till, authenticated_actor, db)

            existing = db.query(TillCashMovement).filter(
                TillCashMovement.organization_id == organization_id,
                TillCashMovement.operation_id == operation_id,
            ).first()
            if existing is not None:
                session = db.query(TillSession).filter(
                    TillSession.id == existing.till_session_id,
                    TillSession.organization_id == organization_id,
                    TillSession.till_id == till_id,
                ).first()
                if session is None:
                    raise ValueError("Cash movement operation ID conflicts with existing data")
                if (
                    existing.direction != normalized_type
                    or TillService._money(existing.amount) != amount
                    or existing.currency_code != session.currency_code
                    or existing.reason != reason
                    or existing.reference != reference
                    or existing.actor_id != authenticated_actor.id
                    or existing.employee_id != employee.id
                ):
                    raise ValueError("Operation ID was already used with a different payload")
                if session.operator_id != authenticated_actor.id and (
                    authenticated_actor.role or ""
                ).lower() not in ("admin", "manager"):
                    raise ValueError(
                        "Only the session operator or an admin/manager can replay this movement"
                    )
                return TillService._serialize_cash_movement(existing), True

            session = TillService.get_current_open_session(
                till_id, db, organization_id=organization_id
            )
            if session is None:
                raise ValueError("Cash movements require an open till session")
            if session.operator_id != authenticated_actor.id and (
                authenticated_actor.role or ""
            ).lower() not in ("admin", "manager"):
                raise ValueError(
                    "Only the session operator or an admin/manager can record cash movements"
                )
            if not session.currency_code:
                raise ValueError("Till session has no currency snapshot")
            values = {
                "organization_id": organization_id,
                "till_id": till_id,
                "till_session_id": session.id,
                "direction": normalized_type,
                "amount": amount,
                "currency_code": session.currency_code,
                "actor_id": authenticated_actor.id,
                "employee_id": employee.id,
                "operation_id": operation_id,
                "reason": reason,
                "reference": reference,
            }
            movement = TillCashMovement(**values)
            db.add(movement)
            db.commit()
            db.refresh(movement)
            return TillService._serialize_cash_movement(movement), False
        except IntegrityError as exc:
            db.rollback()
            replay = db.query(TillCashMovement).filter(
                TillCashMovement.organization_id == organization_id,
                TillCashMovement.operation_id == operation_id,
            ).first()
            if replay is not None:
                return TillService.create_cash_movement(
                    till_id=till_id,
                    organization_id=organization_id,
                    actor=actor,
                    operation_id=operation_id,
                    movement_type=normalized_type,
                    amount=amount,
                    reason=reason,
                    reference=reference,
                    db=db,
                )
            raise ValueError("Unable to record cash movement") from exc
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _serialize_cash_movement(movement) -> dict:
        return {
            "id": movement.id,
            "organization_id": movement.organization_id,
            "till_id": movement.till_id,
            "till_session_id": movement.till_session_id,
            "movement_type": movement.direction,
            "amount": movement.amount,
            "currency_code": movement.currency_code,
            "actor_user_id": movement.actor_id,
            "actor_employee_id": movement.employee_id,
            "operation_id": movement.operation_id,
            "reason": movement.reason,
            "reference": movement.reference,
            "created_at": movement.created_at,
        }

    @staticmethod
    def open_session(
        organization_id: int,
        till_id: int,
        operator_id: int,
        opening_balance: Decimal = Decimal("0.00"),
        db: Optional[Session] = None,
        enforce_assignment: bool = False,
    ) -> TillSession:
        if db is None:
            from src.database import get_db
            db = next(get_db())

        try:
            # A no-op write acts as a row lock on PostgreSQL and a write lock
            # on SQLite, where SELECT FOR UPDATE is ignored.
            TillService._lock_till_row(till_id, organization_id, db)
            till = db.query(Till).filter(
                Till.id == till_id,
                Till.organization_id == organization_id,
            ).with_for_update().first()
            if till is None:
                raise ValueError(f"Till {till_id} not found in org {organization_id}")
            db.refresh(till)
            if not till.is_active:
                raise ValueError("Till is inactive")
            org = db.query(Organization).filter(
                Organization.id == organization_id
            ).first()
            if org is None:
                raise ValueError(f"Organization {organization_id} not found")
            currency = (org.currency_code or "").strip().upper()
            if len(currency) != 3 or not currency.isalpha():
                raise ValueError(
                    "A valid three-letter organization currency must be configured before opening a till"
                )
            operator = db.query(User).filter(
                User.id == operator_id,
                User.organization_id == organization_id,
                User.is_active.is_(True),
            ).first()
            if operator is None:
                raise ValueError(f"Operator {operator_id} not found in org {organization_id}")
            if enforce_assignment:
                TillService.require_assigned_user(till, operator, db)
            amount = TillService._money(opening_balance)
            if amount < 0:
                raise ValueError("Opening balance cannot be negative")
            existing_open = db.query(TillSession.id).filter(
                TillSession.till_id == till_id,
                TillSession.organization_id == organization_id,
                func.upper(TillSession.status) == "OPEN",
            ).first()
            if existing_open:
                raise ValueError(f"Till {till_id} already has an open session")

            now = datetime.utcnow()
            till_session = TillSession(
                organization_id=organization_id,
                till_id=till_id,
                operator_id=operator_id,
                session_number=f"{till_id}-{int(now.timestamp() * 1000000)}",
                opening_balance=amount,
                currency_code=currency,
                status="OPEN",
                opened_at=now,
            )
            db.add(till_session)
            db.flush()
            db.commit()
            db.refresh(till_session)
            return till_session
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(f"Till {till_id} already has an open session") from exc
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _expected_cash(
        session: TillSession,
        closed_at: datetime,
        db: Session,
    ) -> Decimal:
        currency = (session.currency_code or "").strip().upper()
        if not currency:
            raise ValueError("Till session has no currency snapshot and cannot be closed")
        cash_sales = db.query(Sale).filter(
            Sale.organization_id == session.organization_id,
            Sale.till_id == session.till_id,
            func.upper(Sale.payment_method) == "CASH",
            func.upper(Sale.status) == "COMPLETED",
        )
        sales = cash_sales.filter(Sale.till_session_id == session.id).all()
        detached_sale = cash_sales.filter(
            Sale.created_at >= session.opened_at,
            Sale.created_at <= closed_at,
            or_(
                Sale.till_session_id.is_(None),
                Sale.till_session_id != session.id,
            ),
        ).first()
        if detached_sale:
            raise ValueError(
                "A completed cash sale is not linked to this till session; reconcile it before closing"
            )
        expected = Decimal("0.00")
        for sale in sales:
            if sale.created_at < session.opened_at or sale.created_at > closed_at:
                raise ValueError(
                    "A cash sale is outside this till session's time window; reconcile it before closing"
                )
            if (sale.currency_code or "").strip().upper() != currency:
                raise ValueError(
                    "A cash sale has no matching currency snapshot; reconcile it before closing"
                )
            expected += Decimal(sale.total_amount)
        cash_movements = db.query(TillCashMovement).filter(
            TillCashMovement.organization_id == session.organization_id,
            TillCashMovement.till_id == session.till_id,
            TillCashMovement.till_session_id == session.id,
        ).all()
        for movement in cash_movements:
            if (movement.currency_code or "").strip().upper() != currency:
                raise ValueError(
                    "A cash movement has no matching currency snapshot; reconcile it before closing"
                )
            movement_type = (movement.direction or "").strip().upper()
            amount = Decimal(movement.amount)
            if amount <= 0:
                raise ValueError("A cash movement has an invalid amount")
            if movement_type == "CASH_IN":
                expected += amount
            elif movement_type == "CASH_OUT":
                expected -= amount
            else:
                raise ValueError("A cash movement has an invalid movement type")
        return TillService._money(Decimal(session.opening_balance) + expected)

    @staticmethod
    def close_session(
        till_session_id: int,
        closing_balance: Decimal,
        notes: Optional[str] = None,
        db: Optional[Session] = None,
        closed_by_id: Optional[int] = None,
        actor: Optional[User] = None,
    ) -> TillSession:
        if db is None:
            from src.database import get_db
            db = next(get_db())

        try:
            identity = db.query(TillSession).filter(
                TillSession.id == till_session_id
            ).first()
            if identity is None:
                raise ValueError(f"Till session {till_session_id} not found")
            TillService._lock_till_row(
                identity.till_id, identity.organization_id, db
            )
            db.execute(
                update(TillSession)
                .where(TillSession.id == till_session_id)
                .values(status=TillSession.status)
            )
            till_session = db.query(TillSession).filter(
                TillSession.id == till_session_id
            ).with_for_update().first()
            if till_session is None:
                raise ValueError(f"Till session {till_session_id} not found")
            db.refresh(till_session)
            if (till_session.status or "").upper() != "OPEN":
                raise ValueError(
                    f"Till session {till_session_id} is not open (status={till_session.status})"
                )
            if actor is not None:
                till = db.query(Till).filter(
                    Till.id == till_session.till_id,
                    Till.organization_id == till_session.organization_id,
                ).first()
                if till is None:
                    raise ValueError("Till session has invalid organization linkage")
                authenticated_actor = db.query(User).filter(
                    User.id == actor.id,
                    User.organization_id == till_session.organization_id,
                    User.is_active.is_(True),
                ).first()
                if authenticated_actor is None:
                    raise ValueError("An active organization user is required")
                if (
                    till_session.operator_id != authenticated_actor.id
                    and (authenticated_actor.role or "").lower() not in ("admin", "manager")
                ):
                    raise ValueError(
                        "Only the session operator or an admin/manager can close this till"
                    )
            pending_attempt = db.query(PaymentAttempt.id).filter(
                PaymentAttempt.organization_id == till_session.organization_id,
                PaymentAttempt.till_session_id == till_session.id,
                func.upper(PaymentAttempt.status).notin_(_TERMINAL_ATTEMPT_STATUSES),
            ).first()
            if pending_attempt:
                raise ValueError(
                    "Cannot close till session while Paynow attempts are unresolved"
                )
            actual = TillService._money(closing_balance)
            if actual < 0:
                raise ValueError("Closing balance cannot be negative")
            now = datetime.utcnow()
            expected = TillService._expected_cash(till_session, now, db)
            till_session.closing_balance = actual
            till_session.expected_closing_balance = expected
            till_session.cash_variance = TillService._money(actual - expected)
            till_session.closed_by_id = closed_by_id
            till_session.status = "CLOSED"
            till_session.closed_at = now
            till_session.notes = notes
            till_session.updated_at = now
            db.commit()
            db.refresh(till_session)
            return till_session
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_current_open_session(
        till_id: int,
        db: Session,
        organization_id: Optional[int] = None,
    ) -> Optional[TillSession]:
        query = db.query(TillSession).filter(
            TillSession.till_id == till_id,
            func.upper(TillSession.status) == "OPEN",
        )
        if organization_id is not None:
            query = query.filter(TillSession.organization_id == organization_id)
        return query.order_by(TillSession.id.desc()).first()

    @staticmethod
    def get_sessions_for_till(
        till_id: int,
        limit: int = 100,
        db: Optional[Session] = None,
        skip: int = 0,
        organization_id: Optional[int] = None,
    ) -> List[TillSession]:
        if db is None:
            from src.database import get_db
            db = next(get_db())
        query = db.query(TillSession).filter(
            TillSession.till_id == till_id
        )
        if organization_id is not None:
            query = query.filter(TillSession.organization_id == organization_id)
        return query.order_by(TillSession.created_at.desc(), TillSession.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_sales_in_session(till_session_id: int, db: Session) -> List[Sale]:
        return db.query(Sale).filter(
            Sale.till_session_id == till_session_id
        ).order_by(Sale.created_at).all()

    @staticmethod
    def check_limited_mode(subscription_or_state: str) -> bool:
        if isinstance(subscription_or_state, str):
            return subscription_or_state == SubscriptionState.LIMITED.value
        return subscription_or_state == SubscriptionState.LIMITED

    @staticmethod
    def get_limited_mode_guard(organization_id: int, db: Session) -> Callable[[], bool]:
        def guard() -> bool:
            subscription = SubscriptionService.get_subscription_by_org(
                organization_id, db
            )
            if not subscription:
                return True
            return not SubscriptionService.is_limited(subscription)
        return guard

    @staticmethod
    def assert_open_allowed(organization_id: int, db: Session) -> None:
        subscription = SubscriptionService.get_subscription_by_org(organization_id, db)
        if subscription and SubscriptionService.is_limited(subscription):
            raise ValueError("Cannot open till session: subscription is in LIMITED mode")

    @staticmethod
    def assert_offline_cached_allowed(cached_state: str) -> None:
        if cached_state == SubscriptionState.LIMITED.value:
            raise ValueError(
                "Cannot perform operation: cached subscription state is LIMITED"
            )
