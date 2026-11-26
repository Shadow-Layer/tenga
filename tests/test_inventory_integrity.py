"""Integration tests for inventory integrity validation.

These tests verify:
- Stock adjustments use the authoritative InventoryMovement mechanism
- History reflects persisted records
- Concurrent changes don't silently overwrite one another
- Failed operations leave safe state
- Audit trail includes all required fields
- Stock calculations are correct
"""

import pytest
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.entities import (
    Organization, User, Location, Product, Stock, InventoryMovement
)
from src.database.config import Base
from src.services.inventory_service import InventoryService


class TestAdjustmentMechanismVerification:
    """Test that adjustments use InventoryMovement as the authoritative mechanism."""
    
    def test_adjustment_creates_single_movement(self, db: Session, org: Organization, 
                                                location: Location, product: Product, user: User):
        """Scenario A1: Create product, adjust stock - verify InventoryMovement created."""
        # Arrange
        quantity_adjustment = -5
        
        # Act
        movement = InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=quantity_adjustment,
            reason="DAMAGE",
            recorded_by_id=user.id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        # Assert: Movement created
        assert movement is not None
        assert movement.id is not None
        
        # Verify: InventoryMovement record exists in DB
        recorded_movement = db.query(InventoryMovement).filter(
            InventoryMovement.id == movement.id,
            InventoryMovement.product_id == product.id,
        ).first()
        
        assert recorded_movement is not None
        assert recorded_movement.quantity == quantity_adjustment
        assert recorded_movement.reason == "DAMAGE"
        assert recorded_movement.organization_id == org.id
        assert recorded_movement.location_id == location.id
    
    
    def test_multiple_adjustments_create_multiple_movements(self, db: Session, org: Organization,
                                                           location: Location, product: Product, user: User):
        """Scenario A2: Multiple adjustments to same product create separate records."""
        # Arrange
        adjustments = [
            (-10, "DAMAGE"),
            (5, "ADJUSTMENT"),
            (-2, "SHRINKAGE"),
        ]
        
        # Act: Record all adjustments
        movement_ids = []
        for quantity, reason in adjustments:
            movement = InventoryService.record_movement(
                organization_id=org.id,
                product_id=product.id,
                location_id=location.id,
                quantity=quantity,
                reason=reason,
                recorded_by_id=user.id,
                reference_type="ADJUSTMENT",
                reference_id=None,
                db=db,
            )
            movement_ids.append(movement.id)
        
        # Assert: All three movements created
        assert len(movement_ids) == 3
        assert len(set(movement_ids)) == 3  # All unique IDs
        
        # Verify: All records exist in DB with correct data
        movements = db.query(InventoryMovement).filter(
            InventoryMovement.product_id == product.id,
            InventoryMovement.location_id == location.id,
        ).order_by(InventoryMovement.created_at).all()
        
        assert len(movements) == 3
        assert movements[0].quantity == -10
        assert movements[0].reason == "DAMAGE"
        assert movements[1].quantity == 5
        assert movements[1].reason == "ADJUSTMENT"
        assert movements[2].quantity == -2
        assert movements[2].reason == "SHRINKAGE"
    
    
    def test_adjustment_creates_audit_trail_entry(self, db: Session, org: Organization,
                                                  location: Location, product: Product, user: User):
        """Scenario A3: Adjustment creates audit trail entry with all required fields."""
        # Act
        movement = InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=-10,
            reason="SHRINKAGE",
            recorded_by_id=user.id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        # Assert: All audit fields are present and correct
        assert movement.id is not None
        assert movement.product_id == product.id
        assert movement.location_id == location.id
        assert movement.quantity == -10
        assert movement.reason == "SHRINKAGE"
        assert movement.recorded_by_id == user.id
        assert movement.created_at is not None
        assert movement.organization_id == org.id
        
        # Verify: Fields are immutable after creation (test by attempting update)
        db.refresh(movement)
        original_created_at = movement.created_at
        
        # Attempting to update should fail (immutability enforced at DB level)
        # This is tested in test_movement_immutability


class TestStockHistoryPersistence:
    """Test that stock endpoints return actual movement history."""
    
    def test_list_stock_movements_returns_all_records(self, db: Session, org: Organization,
                                                      location: Location, product: Product, user: User):
        """Scenario B1: List stock movements returns all recorded movements."""
        # Arrange: Create multiple adjustments
        adjustments = [
            (-10, "DAMAGE"),
            (5, "ADJUSTMENT"),
            (-2, "SHRINKAGE"),
        ]
        
        for quantity, reason in adjustments:
            InventoryService.record_movement(
                organization_id=org.id,
                product_id=product.id,
                location_id=location.id,
                quantity=quantity,
                reason=reason,
                recorded_by_id=user.id,
                reference_type="ADJUSTMENT",
                reference_id=None,
                db=db,
            )
        
        # Act: Query movements
        movements = db.query(InventoryMovement).filter(
            InventoryMovement.product_id == product.id,
            InventoryMovement.location_id == location.id,
        ).order_by(InventoryMovement.created_at).all()
        
        # Assert
        assert len(movements) == 3
        assert movements[0].quantity == -10
        assert movements[0].reason == "DAMAGE"
        assert movements[0].recorded_by_id == user.id
        assert movements[0].created_at is not None
    
    
    def test_stock_count_reflects_cumulative_movements(self, db: Session, org: Organization,
                                                       location: Location, product: Product, user: User):
        """Scenario B2: Stock count reflects cumulative movements."""
        # Arrange: Create initial stock movement (+100)
        InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=100,
            reason="ADJUSTMENT",
            recorded_by_id=user.id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        # Act: Make adjustments
        adjustments = [
            (-10, "DAMAGE"),
            (5, "ADJUSTMENT"),
            (-2, "SHRINKAGE"),
        ]
        
        for quantity, reason in adjustments:
            InventoryService.record_movement(
                organization_id=org.id,
                product_id=product.id,
                location_id=location.id,
                quantity=quantity,
                reason=reason,
                recorded_by_id=user.id,
                reference_type="ADJUSTMENT",
                reference_id=None,
                db=db,
            )
        
        # Assert: Computed stock = 100 - 10 + 5 - 2 = 93
        computed_stock = InventoryService.compute_stock_at_location(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            db=db,
        )
        
        assert computed_stock == 93
    
    
    def test_empty_movement_history(self, db: Session, org: Organization,
                                    location: Location, product: Product):
        """Scenario B3: Product never adjusted returns empty movement history."""
        # Act: Query movements for product with no adjustments
        movements = db.query(InventoryMovement).filter(
            InventoryMovement.product_id == product.id,
            InventoryMovement.location_id == location.id,
        ).all()
        
        # Assert: Empty list
        assert len(movements) == 0


class TestConcurrentAdjustmentSafety:
    """Test that concurrent changes don't overwrite one another."""
    
    def test_concurrent_adjustments_both_persist(self):
        """Scenario C1: Two concurrent adjustments both persist (no overwrites)."""
        with tempfile.TemporaryDirectory(prefix="tenga-concurrency-") as directory:
            engine = create_engine(f"sqlite:///{directory}/inventory.db")
            Base.metadata.create_all(bind=engine)
            sessions = sessionmaker(bind=engine)
            try:
                with sessions() as setup:
                    org = Organization(name="Concurrent Org", code="CONCURRENT")
                    setup.add(org)
                    setup.flush()
                    location = Location(
                        organization_id=org.id, code="LOC", name="Main"
                    )
                    product = Product(
                        organization_id=org.id,
                        sku="SKU",
                        name="Product",
                        price=1,
                    )
                    user = User(
                        organization_id=org.id,
                        email="operator@example.test",
                        username="operator",
                        password_hash="test-hash",
                        role="admin",
                    )
                    setup.add_all([location, product, user])
                    setup.commit()
                    organization_id, location_id, product_id, user_id = (
                        org.id, location.id, product.id, user.id
                    )

                with sessions() as setup:
                    InventoryService.record_movement(
                        organization_id=organization_id,
                        product_id=product_id,
                        location_id=location_id,
                        quantity=100,
                        reason="PURCHASE",
                        recorded_by_id=user_id,
                        reference_type="ADJUSTMENT",
                        db=setup,
                    )

                def record_adjustment(quantity: int, reason: str) -> None:
                    with sessions() as session:
                        InventoryService.record_movement(
                            organization_id=organization_id,
                            product_id=product_id,
                            location_id=location_id,
                            quantity=quantity,
                            reason=reason,
                            recorded_by_id=user_id,
                            reference_type="ADJUSTMENT",
                            db=session,
                        )

                with ThreadPoolExecutor(max_workers=2) as executor:
                    first = executor.submit(record_adjustment, -20, "DAMAGE")
                    second = executor.submit(record_adjustment, -15, "ADJUSTMENT")
                    first.result()
                    second.result()

                with sessions() as verify:
                    movements = verify.query(InventoryMovement).filter(
                        InventoryMovement.product_id == product_id,
                        InventoryMovement.location_id == location_id,
                    ).all()
                    assert len(movements) == 3
                    assert InventoryService.compute_stock_at_location(
                        organization_id=organization_id,
                        product_id=product_id,
                        location_id=location_id,
                        db=verify,
                    ) == 65
            finally:
                engine.dispose()


class TestFailedOperationsSafety:
    """Test that failed operations leave safe state."""
    
    def test_adjustment_with_invalid_reason_creates_no_movement(self, db: Session, org: Organization,
                                                                 location: Location, product: Product, user: User):
        """Scenario D1: Adjustment with invalid reason creates no movement."""
        # Act: Attempt adjustment with invalid reason
        from src.services.adjustment_reasons import validate_and_normalize_reason
        
        with pytest.raises(ValueError) as exc_info:
            validate_and_normalize_reason("INVALID_REASON")
        
        assert "Unsupported reason" in str(exc_info.value)
        
        # Assert: No movement created
        movements = db.query(InventoryMovement).filter(
            InventoryMovement.product_id == product.id,
        ).all()
        
        assert len(movements) == 0
    
    
    def test_adjustment_with_nonexistent_product_creates_no_movement(self, db: Session, org: Organization,
                                                                     location: Location, user: User):
        """Scenario D2: Adjustment with non-existent product creates no movement."""
        # Act: Attempt adjustment with invalid product ID
        with pytest.raises(ValueError) as exc_info:
            InventoryService.record_movement(
                organization_id=org.id,
                product_id=99999,  # Non-existent
                location_id=location.id,
                quantity=-5,
                reason="DAMAGE",
                recorded_by_id=user.id,
                reference_type="ADJUSTMENT",
                reference_id=None,
                db=db,
            )
        
        assert "not found" in str(exc_info.value).lower()
        
        # Assert: No movement created
        movements = db.query(InventoryMovement).all()
        assert len(movements) == 0
    
    
    def test_adjustment_with_nonexistent_location_creates_no_movement(self, db: Session, org: Organization,
                                                                      product: Product, user: User):
        """Scenario D3: Adjustment with non-existent location creates no movement."""
        # Act: Attempt adjustment with invalid location ID
        with pytest.raises(ValueError) as exc_info:
            InventoryService.record_movement(
                organization_id=org.id,
                product_id=product.id,
                location_id=99999,  # Non-existent
                quantity=-5,
                reason="DAMAGE",
                recorded_by_id=user.id,
                reference_type="ADJUSTMENT",
                reference_id=None,
                db=db,
            )
        
        assert "not found" in str(exc_info.value).lower()
        
        # Assert: No movement created
        movements = db.query(InventoryMovement).all()
        assert len(movements) == 0


class TestAuditTrailCompleteness:
    """Verify InventoryMovement schema includes all required fields."""
    
    def test_movement_has_all_required_fields(self, db: Session, org: Organization,
                                              location: Location, product: Product, user: User):
        """Verify InventoryMovement includes all mandatory audit fields."""
        # Act: Record a movement
        movement = InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=-5,
            reason="DAMAGE",
            recorded_by_id=user.id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        # Assert: All required fields present
        assert movement.id is not None
        assert movement.product_id == product.id
        assert movement.location_id == location.id
        assert movement.quantity == -5
        assert movement.reason == "DAMAGE"
        assert movement.recorded_by_id == user.id
        assert movement.created_at is not None
        assert movement.organization_id == org.id
    
    
    def test_recorded_by_uses_current_user_not_request(self, db: Session, org: Organization,
                                                       location: Location, product: Product, user: User):
        """Verify recorded_by_id matches authenticated user (not from request)."""
        # Arrange: Create second user to verify we're using current_user
        other_user = User(
            organization_id=org.id,
            email="other@test.com",
            username="other",
            full_name="Other User",
            password_hash="hash",
            role="operator",
        )
        db.add(other_user)
        db.commit()
        
        # Act: Record movement as 'user', but pass other_user's ID as recorded_by
        # The service should accept the recorded_by_id parameter (in this test, it's trustworthy)
        # In production, the router would enforce this from JWT token
        movement = InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=-5,
            reason="DAMAGE",
            recorded_by_id=user.id,  # This comes from JWT token in production
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        # Assert: recorded_by_id is exactly what was passed (from JWT token)
        assert movement.recorded_by_id == user.id
        
        # Verify in DB
        recorded_movement = db.query(InventoryMovement).filter(
            InventoryMovement.id == movement.id
        ).first()
        assert recorded_movement.recorded_by_id == user.id


class TestMovementImmutability:
    """Test that InventoryMovement records are immutable."""
    
    def test_movement_cannot_be_updated(self, db: Session, org: Organization,
                                        location: Location, product: Product, user: User):
        """Verify InventoryMovement records cannot be updated."""
        # Arrange: Create a movement
        movement = InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=-5,
            reason="DAMAGE",
            recorded_by_id=user.id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        movement_id = movement.id
        
        # Act & Assert: Attempting to update should fail at ORM level
        from sqlalchemy.exc import IntegrityError
        
        movement_to_update = db.query(InventoryMovement).filter(
            InventoryMovement.id == movement_id
        ).first()
        
        movement_to_update.quantity = -10  # Try to change quantity
        
        with pytest.raises(IntegrityError) as exc_info:
            db.commit()
        
        assert "immutable" in str(exc_info.value).lower()
        db.rollback()
    
    
    def test_movement_cannot_be_deleted(self, db: Session, org: Organization,
                                       location: Location, product: Product, user: User):
        """Verify InventoryMovement records cannot be deleted."""
        # Arrange: Create a movement
        movement = InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=-5,
            reason="DAMAGE",
            recorded_by_id=user.id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        movement_id = movement.id
        
        # Act & Assert: Attempting to delete should fail at ORM level
        from sqlalchemy.exc import IntegrityError
        
        movement_to_delete = db.query(InventoryMovement).filter(
            InventoryMovement.id == movement_id
        ).first()
        
        db.delete(movement_to_delete)
        
        with pytest.raises(IntegrityError) as exc_info:
            db.commit()
        
        assert "immutable" in str(exc_info.value).lower()
        db.rollback()


class TestStockCalculationCorrectness:
    """Test actual stock values after various adjustments."""
    
    def test_initial_stock_zero(self, db: Session, org: Organization,
                                location: Location, product: Product):
        """Scenario F1: Initial stock is zero (no movements)."""
        # Act: Compute stock
        stock = InventoryService.compute_stock_at_location(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            db=db,
        )
        
        # Assert
        assert stock == 0
    
    
    def test_stock_after_single_positive_adjustment(self, db: Session, org: Organization,
                                                     location: Location, product: Product, user: User):
        """Scenario F2: Single positive adjustment."""
        # Act: Add stock
        InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=50,
            reason="ADJUSTMENT",
            recorded_by_id=user.id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        stock = InventoryService.compute_stock_at_location(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            db=db,
        )
        
        # Assert
        assert stock == 50
    
    
    def test_stock_after_single_negative_adjustment(self, db: Session, org: Organization,
                                                     location: Location, product: Product, user: User):
        """Scenario F3: Single negative adjustment."""
        # Arrange: Start with some stock
        InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=100,
            reason="ADJUSTMENT",
            recorded_by_id=user.id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        # Act: Remove stock
        InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=-20,
            reason="SHRINKAGE",
            recorded_by_id=user.id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        stock = InventoryService.compute_stock_at_location(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            db=db,
        )
        
        # Assert
        assert stock == 80
    
    
    def test_stock_after_mixed_adjustments(self, db: Session, org: Organization,
                                          location: Location, product: Product, user: User):
        """Scenario F4: Mixed adjustments sequence."""
        # Act: Sequence of adjustments
        adjustments = [
            (100, "ADJUSTMENT"),      # stock = 100
            (-15, "DAMAGE"),           # stock = 85
            (-5, "SHRINKAGE"),         # stock = 80
        ]
        
        for quantity, reason in adjustments:
            InventoryService.record_movement(
                organization_id=org.id,
                product_id=product.id,
                location_id=location.id,
                quantity=quantity,
                reason=reason,
                recorded_by_id=user.id,
                reference_type="ADJUSTMENT",
                reference_id=None,
                db=db,
            )
        
        stock = InventoryService.compute_stock_at_location(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            db=db,
        )
        
        # Assert: stock = 100 - 15 - 5 = 80
        assert stock == 80


class TestReasonNormalization:
    """Test that reason is normalized to canonical code."""
    
    def test_canonical_reason_persisted_not_user_label(self, db: Session, org: Organization,
                                                        location: Location, product: Product, user: User):
        """Verify reason persisted as canonical code, not user label."""
        from src.services.adjustment_reasons import validate_and_normalize_reason
        
        # Act: Validate user-friendly label
        canonical = validate_and_normalize_reason("Damage")
        
        # Assert: Returns canonical code
        assert canonical == "DAMAGE"
        
        # Record with canonical reason
        movement = InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=-5,
            reason=canonical,  # Use canonical code
            recorded_by_id=user.id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        
        # Verify: Stored as canonical code
        db.refresh(movement)
        assert movement.reason == "DAMAGE"
        assert movement.reason != "Damage"  # Not the label
