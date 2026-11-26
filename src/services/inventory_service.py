"""Append-only inventory ledger operations and reporting."""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from typing import List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.entities import (
    Employee,
    InventoryCount,
    InventoryCountLine,
    InventoryMovement,
    OfflineOperation,
    InventoryTransfer,
    InventoryTransferLine,
    Location,
    Organization,
    Product,
    Stock,
    TaxRule,
    User,
)


class InventoryNotFoundError(ValueError):
    """An inventory resource is not visible in the authenticated tenant."""


class InventoryConflictError(RuntimeError):
    """An inventory operation conflicts with current state or a prior replay."""


class InsufficientStockError(InventoryConflictError):
    """A non-sale operation would issue more stock than is available."""


class InventoryService:
    """Create immutable ledger entries, update the balance cache, and report stock."""

    @staticmethod
    def lock_organization(organization_id: int, db: Session) -> Organization:
        """Lock tenant configuration before an inventory write transaction.

        PostgreSQL serializes the first stock movement against concurrent settings
        changes. SQLite ignores ``FOR UPDATE``; the row lock is still useful on the
        production database and harmless in isolated SQLite tests.
        """
        organization = (
            db.query(Organization)
            .filter(Organization.id == organization_id)
            .with_for_update()
            .populate_existing()
            .first()
        )
        if not organization:
            raise InventoryNotFoundError("Organization not found")
        return organization

    @staticmethod
    def _validate_actor(organization_id: int, actor_id: int, db: Session) -> None:
        actor = db.query(User.id).filter(
            User.id == actor_id,
            User.organization_id == organization_id,
            User.is_active.is_(True),
        ).first()
        if actor is None:
            raise InventoryNotFoundError("Actor not found in this organization")

    @staticmethod
    def _validate_product(
        organization_id: int,
        product_id: int,
        db: Session,
        allow_inactive: bool = False,
    ) -> Product:
        query = db.query(Product).filter(
            Product.id == product_id,
            Product.organization_id == organization_id,
        )
        if not allow_inactive:
            query = query.filter(Product.is_active.is_(True))
        product = query.first()
        if not product:
            raise InventoryNotFoundError("Product not found in this organization")
        if product.tax_rule_id is not None:
            tax_rule = db.query(TaxRule).filter(
                TaxRule.id == product.tax_rule_id,
                TaxRule.organization_id == organization_id,
            ).first()
            if tax_rule is None:
                raise InventoryConflictError(
                    "Product tax rule does not belong to this organization"
                )
        return product

    @staticmethod
    def _validate_location(
        organization_id: int,
        location_id: int,
        db: Session,
        allow_inactive: bool = False,
    ) -> Location:
        query = db.query(Location).filter(
            Location.id == location_id,
            Location.organization_id == organization_id,
        )
        if not allow_inactive:
            query = query.filter(Location.is_active.is_(True))
        location = query.first()
        if not location:
            raise InventoryNotFoundError("Location not found in this organization")
        return location

    @staticmethod
    def _normalize_idempotency(device_id: Optional[str], device_local_id: Optional[str]):
        if (device_id is None) != (device_local_id is None):
            raise ValueError("device_id and device_local_id must be provided together")

    @staticmethod
    def _find_movement_replay(
        organization_id: int,
        device_id: Optional[str],
        device_local_id: Optional[str],
        db: Session,
    ) -> Optional[InventoryMovement]:
        if device_id is None:
            return None
        return db.query(InventoryMovement).filter(
            InventoryMovement.organization_id == organization_id,
            InventoryMovement.device_id == device_id,
            InventoryMovement.device_local_id == device_local_id,
        ).first()

    @staticmethod
    def _movement_matches(
        movement: InventoryMovement,
        *,
        product_id: int,
        location_id: int,
        to_location_id: Optional[int],
        quantity: int,
        reason: str,
        movement_type: str,
        recorded_by_id: int,
        unit_cost: Optional[Decimal],
        reference_type: Optional[str],
        reference_id: Optional[int],
    ) -> bool:
        existing_cost = (
            Decimal(str(movement.unit_cost))
            if movement.unit_cost is not None
            else None
        )
        requested_cost = Decimal(str(unit_cost)) if unit_cost is not None else None
        return all(
            (
                movement.product_id == product_id,
                movement.location_id == location_id,
                movement.to_location_id == to_location_id,
                movement.quantity == quantity,
                movement.reason == reason,
                movement.movement_type == movement_type,
                movement.recorded_by_id == recorded_by_id,
                existing_cost == requested_cost,
                movement.reference_type == reference_type,
                movement.reference_id == reference_id,
            )
        )

    @staticmethod
    def _employee_for_user(organization_id: int, user_id: int, db: Session):
        return db.query(Employee.id).filter(
            Employee.organization_id == organization_id,
            Employee.user_id == user_id,
        ).scalar()

    @staticmethod
    def record_movement(
        organization_id: int,
        product_id: int,
        location_id: int,
        quantity: int,
        reason: str,
        recorded_by_id: int,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        db: Optional[Session] = None,
        commit: bool = True,
        *,
        movement_type: Optional[str] = None,
        to_location_id: Optional[int] = None,
        unit_cost: Optional[Decimal] = None,
        device_id: Optional[str] = None,
        device_local_id: Optional[str] = None,
        update_cache: bool = False,
        allow_zero: bool = False,
    ) -> InventoryMovement:
        """Append a movement and optionally synchronize balance cache in one transaction.

        ``unit_cost`` is the optional operation cost. When omitted, the product's
        current cost is snapshotted if present. Currency always comes from the
        locked organization row; callers cannot choose or reinterpret currency.
        Opening-stock importers may pass ``movement_type="OPENING_BALANCE"`` and
        ``unit_cost=...``. The actor and tenant must be validated before commit.
        """
        if db is None:
            from src.database import get_db

            db = next(get_db())
        organization = InventoryService.lock_organization(organization_id, db)
        InventoryService._normalize_idempotency(device_id, device_local_id)
        InventoryService._validate_actor(organization_id, recorded_by_id, db)
        product = InventoryService._validate_product(organization_id, product_id, db)
        InventoryService._validate_location(organization_id, location_id, db)
        if to_location_id is not None:
            InventoryService._validate_location(organization_id, to_location_id, db)
            if to_location_id == location_id:
                raise ValueError("Source and destination locations must be different")
        if quantity == 0 and not allow_zero:
            raise ValueError("Movement quantity must be non-zero")

        effective_type = movement_type or (
            "SALE"
            if reference_type == "SALE"
            else "COUNT"
            if reference_type == "COUNT"
            else "OPENING_BALANCE"
            if reference_type == "OPENING_IMPORT"
            else "ADJUSTMENT"
        )
        if effective_type == "TRANSFER":
            if to_location_id is None or quantity <= 0:
                raise ValueError("Transfers require a destination and positive quantity")
        elif to_location_id is not None:
            raise ValueError("Only transfer movements may specify a destination")

        effective_cost = (
            Decimal(str(unit_cost))
            if unit_cost is not None
            else Decimal(str(product.cost))
            if product.cost is not None
            else None
        )
        if effective_cost is not None and effective_cost < 0:
            raise ValueError("unit_cost cannot be negative")
        if effective_cost is not None and not organization.currency_code:
            raise InventoryConflictError(
                "Configure an organization currency before recording valued inventory"
            )

        replay = InventoryService._find_movement_replay(
            organization_id, device_id, device_local_id, db
        )
        if replay:
            replay_cost = (
                Decimal(str(replay.unit_cost))
                if unit_cost is None and replay.unit_cost is not None
                else effective_cost
            )
            if InventoryService._movement_matches(
                replay,
                product_id=product_id,
                location_id=location_id,
                to_location_id=to_location_id,
                quantity=quantity,
                reason=reason,
                movement_type=effective_type,
                recorded_by_id=recorded_by_id,
                unit_cost=replay_cost,
                reference_type=reference_type,
                reference_id=reference_id,
            ):
                return replay
            raise InventoryConflictError(
                "device_local_id was already used for a different inventory operation"
            )

        if effective_type == "ISSUE":
            available = InventoryService.compute_stock_at_location(
                organization_id, product_id, location_id, db
            )
            if quantity >= 0 or -quantity > available:
                raise InsufficientStockError(
                    f"Insufficient stock. Available: {available}, "
                    f"requested: {abs(quantity)}"
                )
        if effective_type == "TRANSFER":
            available = InventoryService.compute_stock_at_location(
                organization_id, product_id, location_id, db
            )
            if quantity > available:
                raise InsufficientStockError(
                    f"Insufficient stock. Available: {available}, requested: {quantity}"
                )

        movement = InventoryMovement(
            organization_id=organization_id,
            product_id=product_id,
            location_id=location_id,
            to_location_id=to_location_id,
            movement_type=effective_type,
            quantity=quantity,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            recorded_by_id=recorded_by_id,
            recorded_by_employee_id=InventoryService._employee_for_user(
                organization_id, recorded_by_id, db
            ),
            unit_cost=effective_cost,
            currency_code=organization.currency_code,
            device_id=device_id,
            device_local_id=device_local_id,
            created_at=datetime.utcnow(),
        )
        db.add(movement)
        db.flush()
        if update_cache:
            InventoryService.update_stock_cache(
                organization_id, product_id, location_id, db, commit=False
            )
            if to_location_id is not None:
                InventoryService.update_stock_cache(
                    organization_id, product_id, to_location_id, db, commit=False
                )
        if commit:
            db.commit()
        return movement

    @staticmethod
    def receive_stock(
        organization_id: int,
        product_id: int,
        location_id: int,
        quantity: int,
        recorded_by_id: int,
        db: Session,
        *,
        unit_cost: Optional[Decimal] = None,
        reason: str = "RECEIPT",
        opening_balance: bool = False,
        device_id: Optional[str] = None,
        device_local_id: Optional[str] = None,
        commit: bool = True,
    ) -> InventoryMovement:
        InventoryService.lock_organization(organization_id, db)
        if (opening_balance and quantity == 0) or (
            not opening_balance and quantity <= 0
        ):
            raise ValueError(
                "Opening balance must be non-zero"
                if opening_balance
                else "Receipt quantity must be positive"
            )
        movement_type = "OPENING_BALANCE" if opening_balance else "RECEIPT"
        return InventoryService.record_movement(
            organization_id=organization_id,
            product_id=product_id,
            location_id=location_id,
            quantity=quantity,
            reason=reason,
            recorded_by_id=recorded_by_id,
            reference_type=movement_type,
            db=db,
            commit=commit,
            movement_type=movement_type,
            unit_cost=unit_cost,
            device_id=device_id,
            device_local_id=device_local_id,
            update_cache=True,
        )

    @staticmethod
    def issue_stock(
        organization_id: int,
        product_id: int,
        location_id: int,
        quantity: int,
        reason: str,
        recorded_by_id: int,
        db: Session,
        *,
        device_id: Optional[str] = None,
        device_local_id: Optional[str] = None,
        commit: bool = True,
    ) -> InventoryMovement:
        InventoryService.lock_organization(organization_id, db)
        if quantity <= 0:
            raise ValueError("Issue quantity must be positive")
        return InventoryService.record_movement(
            organization_id=organization_id,
            product_id=product_id,
            location_id=location_id,
            quantity=-quantity,
            reason=reason,
            recorded_by_id=recorded_by_id,
            reference_type="ISSUE",
            db=db,
            commit=commit,
            movement_type="ISSUE",
            device_id=device_id,
            device_local_id=device_local_id,
            update_cache=True,
        )

    @staticmethod
    def adjust_stock(
        organization_id: int,
        product_id: int,
        location_id: int,
        quantity: int,
        reason: str,
        recorded_by_id: int,
        db: Session,
        *,
        device_id: Optional[str] = None,
        device_local_id: Optional[str] = None,
        reference_type: Optional[str] = "ADJUSTMENT",
        reference_id: Optional[int] = None,
        commit: bool = True,
    ) -> InventoryMovement:
        InventoryService.lock_organization(organization_id, db)
        if quantity == 0:
            raise ValueError("Adjustment quantity must be non-zero")
        return InventoryService.record_movement(
            organization_id=organization_id,
            product_id=product_id,
            location_id=location_id,
            quantity=quantity,
            reason=reason,
            recorded_by_id=recorded_by_id,
            reference_type=reference_type,
            reference_id=reference_id,
            db=db,
            commit=commit,
            movement_type="ADJUSTMENT",
            device_id=device_id,
            device_local_id=device_local_id,
            update_cache=True,
        )

    @staticmethod
    def transfer_stock(
        organization_id: int,
        source_location_id: int,
        destination_location_id: int,
        lines: list,
        reason: str,
        recorded_by_id: int,
        db: Session,
        *,
        device_id: Optional[str] = None,
        device_local_id: Optional[str] = None,
        commit: bool = True,
    ) -> InventoryTransfer:
        organization = InventoryService.lock_organization(organization_id, db)
        InventoryService._normalize_idempotency(device_id, device_local_id)
        if source_location_id == destination_location_id:
            raise ValueError("Source and destination locations must be different")
        InventoryService._validate_actor(organization_id, recorded_by_id, db)
        InventoryService._validate_location(organization_id, source_location_id, db)
        InventoryService._validate_location(organization_id, destination_location_id, db)
        normalized_lines = sorted(
            ((int(line.product_id), int(line.quantity)) for line in lines),
            key=lambda item: item[0],
        )
        if not normalized_lines or any(quantity <= 0 for _, quantity in normalized_lines):
            raise ValueError("Transfer lines require positive quantities")
        if len({product_id for product_id, _ in normalized_lines}) != len(normalized_lines):
            raise ValueError("Transfer product lines must be unique")

        if device_id is not None:
            existing = db.query(InventoryTransfer).filter(
                InventoryTransfer.organization_id == organization_id,
                InventoryTransfer.device_id == device_id,
                InventoryTransfer.device_local_id == device_local_id,
            ).first()
            if existing:
                existing_lines = sorted(
                    (line.product_id, line.quantity)
                    for line in db.query(InventoryTransferLine).filter(
                        InventoryTransferLine.transfer_id == existing.id
                    ).all()
                )
                request_matches = (
                    existing.source_location_id == source_location_id
                    and existing.destination_location_id == destination_location_id
                    and existing.reason == reason
                    and existing.created_by_id == recorded_by_id
                    and existing_lines == normalized_lines
                )
                if request_matches:
                    return existing
                raise InventoryConflictError(
                    "device_local_id was already used for a different transfer"
                )

        for product_id, quantity in normalized_lines:
            product = InventoryService._validate_product(
                organization_id, product_id, db
            )
            if product.cost is not None and not organization.currency_code:
                raise InventoryConflictError(
                    "Configure an organization currency before transferring valued inventory"
                )
            available = InventoryService.compute_stock_at_location(
                organization_id, product_id, source_location_id, db
            )
            if quantity > available:
                raise InsufficientStockError(
                    f"Insufficient stock for product {product_id}. "
                    f"Available: {available}, requested: {quantity}"
                )

        transfer = InventoryTransfer(
            organization_id=organization_id,
            source_location_id=source_location_id,
            destination_location_id=destination_location_id,
            created_by_id=recorded_by_id,
            device_id=device_id,
            device_local_id=device_local_id,
            status="COMPLETED",
            reason=reason,
        )
        db.add(transfer)
        db.flush()
        for product_id, quantity in normalized_lines:
            db.add(
                InventoryTransferLine(
                    transfer_id=transfer.id,
                    product_id=product_id,
                    quantity=quantity,
                )
            )
            InventoryService.record_movement(
                organization_id=organization_id,
                product_id=product_id,
                location_id=source_location_id,
                to_location_id=destination_location_id,
                quantity=quantity,
                reason=reason,
                recorded_by_id=recorded_by_id,
                reference_type="TRANSFER",
                reference_id=transfer.id,
                db=db,
                commit=False,
                movement_type="TRANSFER",
                update_cache=True,
            )
        db.flush()
        if commit:
            db.commit()
        return transfer

    @staticmethod
    def create_count(
        organization_id: int,
        location_id: int,
        lines: list,
        created_by_id: int,
        db: Session,
        *,
        notes: Optional[str] = None,
        device_id: Optional[str] = None,
        device_local_id: Optional[str] = None,
        commit: bool = True,
    ) -> InventoryCount:
        InventoryService.lock_organization(organization_id, db)
        InventoryService._normalize_idempotency(device_id, device_local_id)
        InventoryService._validate_actor(organization_id, created_by_id, db)
        InventoryService._validate_location(organization_id, location_id, db)
        normalized = sorted(
            (int(line.product_id), line.observed_quantity) for line in lines
        )
        if not normalized:
            raise ValueError("A count must include at least one product")
        if len({product_id for product_id, _ in normalized}) != len(normalized):
            raise ValueError("Count product lines must be unique")
        payload_hash = None
        if device_id is not None:
            payload = {
                "location_id": location_id,
                "lines": normalized,
                "notes": notes,
            }
            payload_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            existing = db.query(OfflineOperation).filter(
                OfflineOperation.organization_id == organization_id,
                OfflineOperation.device_id == device_id,
                OfflineOperation.operation_id == device_local_id,
                OfflineOperation.operation_type == "INVENTORY_COUNT",
            ).first()
            if existing:
                if existing.payload_hash != payload_hash:
                    raise InventoryConflictError(
                        "device_local_id was already used for a different inventory count"
                    )
                try:
                    result = json.loads(existing.result_payload or "{}")
                    existing_count_id = int(result["count_id"])
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    raise InventoryConflictError(
                        "The prior inventory count operation has no replayable result"
                    )
                count = db.query(InventoryCount).filter(
                    InventoryCount.id == existing_count_id,
                    InventoryCount.organization_id == organization_id,
                ).first()
                if count is None:
                    raise InventoryConflictError(
                        "The prior inventory count result is no longer available"
                    )
                return count
        for product_id, _ in normalized:
            InventoryService._validate_product(organization_id, product_id, db)

        count = InventoryCount(
            organization_id=organization_id,
            location_id=location_id,
            created_by_id=created_by_id,
            status="DRAFT",
            notes=notes,
            started_at=datetime.utcnow(),
        )
        db.add(count)
        db.flush()
        for product_id, observed_quantity in normalized:
            expected_quantity = InventoryService.compute_stock_at_location(
                organization_id, product_id, location_id, db
            )
            db.add(
                InventoryCountLine(
                    count_id=count.id,
                    product_id=product_id,
                    expected_quantity=expected_quantity,
                    observed_quantity=observed_quantity,
                )
            )
        if device_id is not None:
            db.add(
                OfflineOperation(
                    organization_id=organization_id,
                    actor_id=created_by_id,
                    device_id=device_id,
                    operation_id=device_local_id,
                    operation_type="INVENTORY_COUNT",
                    payload_hash=payload_hash,
                    status="SYNCED",
                    result_payload=json.dumps({"count_id": count.id}),
                    processed_at=datetime.utcnow(),
                )
            )
        db.flush()
        if commit:
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                if device_id is None:
                    raise
                existing = db.query(OfflineOperation).filter(
                    OfflineOperation.organization_id == organization_id,
                    OfflineOperation.device_id == device_id,
                    OfflineOperation.operation_id == device_local_id,
                    OfflineOperation.operation_type == "INVENTORY_COUNT",
                ).first()
                if existing is None:
                    raise
                if existing.payload_hash != payload_hash:
                    raise InventoryConflictError(
                        "device_local_id was already used for a different inventory count"
                    )
                result = json.loads(existing.result_payload or "{}")
                count = db.query(InventoryCount).filter(
                    InventoryCount.id == int(result["count_id"]),
                    InventoryCount.organization_id == organization_id,
                ).first()
                if count is None:
                    raise InventoryConflictError(
                        "The prior inventory count result is no longer available"
                    )
                return count
        return count

    @staticmethod
    def update_count_observations(
        organization_id: int,
        count_id: int,
        lines: list,
        db: Session,
        *,
        commit: bool = True,
    ) -> InventoryCount:
        InventoryService.lock_organization(organization_id, db)
        count = db.query(InventoryCount).filter(
            InventoryCount.id == count_id,
            InventoryCount.organization_id == organization_id,
        ).with_for_update().first()
        if not count:
            raise InventoryNotFoundError("Count not found")
        if count.status != "DRAFT":
            raise InventoryConflictError("Only draft counts can be changed")
        updates = {int(line.product_id): line.observed_quantity for line in lines}
        if not updates:
            raise ValueError("At least one count observation is required")
        if len(updates) != len(lines):
            raise ValueError("Count product lines must be unique")
        count_lines = {
            line.product_id: line
            for line in db.query(InventoryCountLine).filter(
                InventoryCountLine.count_id == count_id
            ).all()
        }
        if any(product_id not in count_lines for product_id in updates):
            raise InventoryNotFoundError("Product is not part of this count")
        for product_id, observed_quantity in updates.items():
            count_lines[product_id].observed_quantity = observed_quantity
        db.flush()
        if commit:
            db.commit()
        return count

    @staticmethod
    def reconcile_count(
        organization_id: int,
        count_id: int,
        reconciled_by_id: int,
        expected_observations: list,
        db: Session,
        *,
        commit: bool = True,
    ) -> InventoryCount:
        InventoryService.lock_organization(organization_id, db)
        InventoryService._validate_actor(organization_id, reconciled_by_id, db)
        count = db.query(InventoryCount).filter(
            InventoryCount.id == count_id,
            InventoryCount.organization_id == organization_id,
        ).with_for_update().first()
        if not count:
            raise InventoryNotFoundError("Count not found")
        if count.status not in ("DRAFT", "RECONCILED"):
            raise InventoryConflictError("Count is not available for reconciliation")
        lines = db.query(InventoryCountLine).filter(
            InventoryCountLine.count_id == count.id
        ).order_by(InventoryCountLine.id).with_for_update().all()
        reviewed = {
            int(line.product_id): line.observed_quantity
            for line in expected_observations
        }
        if (
            len(reviewed) != len(expected_observations)
            or set(reviewed) != {line.product_id for line in lines}
            or any(line.observed_quantity != reviewed[line.product_id] for line in lines)
        ):
            raise InventoryConflictError(
                "Count observations changed since review; reload the count before reconciling"
            )
        if count.status == "RECONCILED":
            return count
        if not lines or any(line.observed_quantity is None for line in lines):
            raise InventoryConflictError(
                "Every count line must have an observation before reconciliation"
            )

        for line in lines:
            current_quantity = InventoryService.compute_stock_at_location(
                organization_id, line.product_id, count.location_id, db
            )
            if current_quantity != line.expected_quantity:
                raise InventoryConflictError(
                    "Inventory changed after this count began; start a new count before reconciling"
                )
            difference = line.observed_quantity - current_quantity
            if difference:
                movement = InventoryService.record_movement(
                    organization_id=organization_id,
                    product_id=line.product_id,
                    location_id=count.location_id,
                    quantity=difference,
                    reason="PHYSICAL_COUNT_DISCREPANCY",
                    recorded_by_id=reconciled_by_id,
                    reference_type="COUNT_RECONCILIATION",
                    reference_id=count.id,
                    db=db,
                    commit=False,
                    movement_type="COUNT_CORRECTION",
                    update_cache=True,
                )
                line.reconciled_movement_id = movement.id
        count.status = "RECONCILED"
        count.reconciled_by_id = reconciled_by_id
        count.reconciled_at = datetime.utcnow()
        db.flush()
        if commit:
            db.commit()
        return count

    @staticmethod
    def compute_stock_at_location(
        organization_id: int,
        product_id: int,
        location_id: int,
        db: Session,
        as_of: Optional[datetime] = None,
    ) -> int:
        query = db.query(
            InventoryMovement.location_id,
            InventoryMovement.to_location_id,
            InventoryMovement.movement_type,
            InventoryMovement.quantity,
        ).filter(
            InventoryMovement.organization_id == organization_id,
            InventoryMovement.product_id == product_id,
            or_(
                InventoryMovement.location_id == location_id,
                InventoryMovement.to_location_id == location_id,
            ),
        )
        if as_of:
            query = query.filter(InventoryMovement.created_at <= as_of)
        quantity = 0
        for source_id, destination_id, movement_type, delta in query.all():
            if movement_type == "TRANSFER":
                quantity += -delta if source_id == location_id else 0
                quantity += delta if destination_id == location_id else 0
            elif source_id == location_id:
                quantity += delta
        return quantity

    @staticmethod
    def detect_discrepancy(
        organization_id: int,
        product_id: int,
        location_id: int,
        expected_quantity: int,
        db: Session,
    ) -> Optional[int]:
        ledger_quantity = InventoryService.compute_stock_at_location(
            organization_id, product_id, location_id, db
        )
        difference = expected_quantity - ledger_quantity
        return difference if difference else None

    @staticmethod
    def record_reconciliation(
        organization_id: int,
        product_id: int,
        location_id: int,
        expected_quantity: int,
        recorded_by_id: int,
        reason: str,
        db: Session,
    ) -> Tuple[InventoryMovement, Optional[int]]:
        """Compatibility helper for legacy callers; captures a zero-delta count."""
        discrepancy = InventoryService.detect_discrepancy(
            organization_id, product_id, location_id, expected_quantity, db
        )
        movement = InventoryService.record_movement(
            organization_id=organization_id,
            product_id=product_id,
            location_id=location_id,
            quantity=0,
            reason=reason,
            recorded_by_id=recorded_by_id,
            reference_type="COUNT",
            db=db,
            allow_zero=True,
        )
        return movement, discrepancy

    @staticmethod
    def get_movements_for_product_at_location(
        organization_id: int,
        product_id: int,
        location_id: int,
        db: Session,
        limit: int = 100,
    ) -> List[InventoryMovement]:
        return db.query(InventoryMovement).filter(
            InventoryMovement.organization_id == organization_id,
            InventoryMovement.product_id == product_id,
            or_(
                InventoryMovement.location_id == location_id,
                InventoryMovement.to_location_id == location_id,
            ),
        ).order_by(
            InventoryMovement.created_at.desc(),
            InventoryMovement.id.desc(),
        ).limit(limit).all()

    @staticmethod
    def get_stock_snapshot(
        organization_id: int, location_id: int, db: Session
    ) -> List[Tuple[int, int]]:
        balances = InventoryService.get_balances_at_location(
            organization_id, location_id, db
        )
        return [
            (product_id, quantity)
            for product_id, quantity in sorted(balances.items())
        ]

    @staticmethod
    def get_balances_at_location(
        organization_id: int, location_id: int, db: Session
    ) -> dict[int, int]:
        rows = db.query(
            InventoryMovement.product_id,
            InventoryMovement.location_id,
            InventoryMovement.to_location_id,
            InventoryMovement.movement_type,
            InventoryMovement.quantity,
        ).filter(
            InventoryMovement.organization_id == organization_id,
            or_(
                InventoryMovement.location_id == location_id,
                InventoryMovement.to_location_id == location_id,
            ),
        ).all()
        balances: dict[int, int] = {}
        for product_id, source_id, destination_id, movement_type, quantity in rows:
            if movement_type == "TRANSFER":
                if source_id == location_id:
                    balances[product_id] = balances.get(product_id, 0) - quantity
                if destination_id == location_id:
                    balances[product_id] = balances.get(product_id, 0) + quantity
            elif source_id == location_id:
                balances[product_id] = balances.get(product_id, 0) + quantity
        return balances

    @staticmethod
    def update_stock_cache(
        organization_id: int,
        product_id: int,
        location_id: int,
        db: Session,
        commit: bool = True,
    ) -> None:
        quantity = InventoryService.compute_stock_at_location(
            organization_id, product_id, location_id, db
        )
        last_movement = db.query(InventoryMovement.created_at).filter(
            InventoryMovement.organization_id == organization_id,
            InventoryMovement.product_id == product_id,
            or_(
                InventoryMovement.location_id == location_id,
                InventoryMovement.to_location_id == location_id,
            ),
        ).order_by(
            InventoryMovement.created_at.desc(),
            InventoryMovement.id.desc(),
        ).first()
        last_movement_at = last_movement[0] if last_movement else datetime.utcnow()
        stock = db.query(Stock).filter(
            Stock.organization_id == organization_id,
            Stock.product_id == product_id,
            Stock.location_id == location_id,
        ).with_for_update().first()
        if stock:
            stock.quantity = quantity
            stock.last_movement_at = last_movement_at
        else:
            db.add(
                Stock(
                    organization_id=organization_id,
                    product_id=product_id,
                    location_id=location_id,
                    quantity=quantity,
                    last_movement_at=last_movement_at,
                )
            )
        db.flush()
        if commit:
            db.commit()

    @staticmethod
    def weighted_average_cost(
        organization_id: int, product_id: int, db: Session
    ) -> Optional[Decimal]:
        organization = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        if not organization or not organization.currency_code:
            return None
        InventoryService._validate_product(
            organization_id, product_id, db, allow_inactive=True
        )
        movements = db.query(
            InventoryMovement.quantity,
            InventoryMovement.movement_type,
            InventoryMovement.unit_cost,
            InventoryMovement.currency_code,
        ).filter(
            InventoryMovement.organization_id == organization_id,
            InventoryMovement.product_id == product_id,
        ).order_by(
            InventoryMovement.created_at,
            InventoryMovement.id,
        ).all()

        quantity_on_hand = Decimal("0")
        known_quantity = Decimal("0")
        unknown_quantity = Decimal("0")
        known_value = Decimal("0")
        for quantity, movement_type, unit_cost, currency_code in movements:
            # A transfer moves units between locations, not into or out of the
            # organization-wide weighted-average pool.
            if movement_type == "TRANSFER":
                continue
            delta = Decimal(quantity)
            if delta > 0:
                if quantity_on_hand < 0:
                    covered_shortage = min(delta, -quantity_on_hand)
                    quantity_on_hand += covered_shortage
                    delta -= covered_shortage
                    if quantity_on_hand == 0:
                        known_quantity = Decimal("0")
                        unknown_quantity = Decimal("0")
                        known_value = Decimal("0")
                if delta == 0:
                    continue
                quantity_on_hand += delta
                if (
                    unit_cost is None
                    or currency_code != organization.currency_code
                ):
                    unknown_quantity += delta
                else:
                    known_quantity += delta
                    known_value += delta * Decimal(str(unit_cost))
            elif delta < 0:
                consumed = -delta
                if quantity_on_hand <= 0 or consumed >= quantity_on_hand:
                    quantity_on_hand -= consumed
                    known_quantity = Decimal("0")
                    unknown_quantity = Decimal("0")
                    known_value = Decimal("0")
                    continue

                # Apply the current average proportionally to all fungible stock.
                # Unknown-cost units remain explicitly unknown rather than being
                # assigned a fabricated value.
                fraction_remaining = (quantity_on_hand - consumed) / quantity_on_hand
                known_quantity *= fraction_remaining
                unknown_quantity *= fraction_remaining
                known_value *= fraction_remaining
                quantity_on_hand -= consumed

        if (
            quantity_on_hand <= 0
            or unknown_quantity > 0
            or known_quantity != quantity_on_hand
        ):
            return None
        return (known_value / quantity_on_hand).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
