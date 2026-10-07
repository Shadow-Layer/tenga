"""Tests for inventory and sales services."""
import pytest
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models.entities import InventoryMovement, Sale, Stock
from src.services.inventory_service import InventoryService
from src.services.sale_service import SaleService


class TestInventoryService:
    """Test inventory movement ledger service."""

    def test_record_sale_movement(
        self,
        db: Session,
        org,
        product,
        location,
        user,
    ):
        """Test recording a sale movement (stock out)."""
        movement = InventoryService.record_movement(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=-5,
            reason="SALE",
            recorded_by_id=user.id,
            reference_type="SALE",
            reference_id=123,
            db=db,
        )

        assert movement.quantity == -5
        assert movement.reason == "SALE"
        assert movement.product_id == product.id

    def test_compute_stock_after_movement(
        self,
        db: Session,
        org,
        product,
        location,
        user,
    ):
        """Test stock computation after movements."""
        # Record in movement
        InventoryService.record_movement(
            org.id, product.id, location.id, 10, "PURCHASE", user.id, db=db
        )

        # Record out movement
        InventoryService.record_movement(
            org.id, product.id, location.id, -3, "SALE", user.id, db=db
        )

        stock = InventoryService.compute_stock_at_location(
            org.id, product.id, location.id, db
        )
        assert stock == 7

    def test_detect_discrepancy_shortage(
        self,
        db: Session,
        org,
        product,
        location,
        user,
    ):
        """Test detecting shortage from physical count."""
        # Record 10 units in
        InventoryService.record_movement(
            org.id, product.id, location.id, 10, "PURCHASE", user.id, db=db
        )

        # Physical count shows 8 (shortage of 2)
        discrepancy = InventoryService.detect_discrepancy(
            org.id, product.id, location.id, 8, db
        )
        assert discrepancy == -2

    def test_detect_discrepancy_surplus(
        self,
        db: Session,
        org,
        product,
        location,
        user,
    ):
        """Test detecting surplus from physical count."""
        # Record 10 units in
        InventoryService.record_movement(
            org.id, product.id, location.id, 10, "PURCHASE", user.id, db=db
        )

        # Physical count shows 12 (surplus of 2)
        discrepancy = InventoryService.detect_discrepancy(
            org.id, product.id, location.id, 12, db
        )
        assert discrepancy == 2

    def test_no_discrepancy(
        self,
        db: Session,
        org,
        product,
        location,
        user,
    ):
        """Test when count matches ledger."""
        # Record 10 units in
        InventoryService.record_movement(
            org.id, product.id, location.id, 10, "PURCHASE", user.id, db=db
        )

        # Physical count matches
        discrepancy = InventoryService.detect_discrepancy(
            org.id, product.id, location.id, 10, db
        )
        assert discrepancy is None


class TestSaleService:
    """Test POS sale service."""

    def test_create_online_sale(
        self,
        db: Session,
        org,
        till,
        user,
        product,
    ):
        """Test creating an online sale (immediately COMPLETED)."""
        sale = SaleService.create_sale(
            organization_id=org.id,
            till_id=till.id,
            cashier_id=user.id,
            payment_method="CASH",
            items=[
                {
                    "product_id": product.id,
                    "quantity": 5,
                    "unit_price": 10.00,
                }
            ],
            db=db,
        )

        assert sale.status == "COMPLETED"
        assert sale.total_amount == 50.00
        assert len(sale.sale_items) == 1
        assert sale.sale_items[0].quantity == 5

    def test_create_offline_sale(
        self,
        db: Session,
        org,
        till,
        user,
        product,
    ):
        """Test creating an offline sale (queued as PENDING)."""
        sale = SaleService.create_sale(
            organization_id=org.id,
            till_id=till.id,
            cashier_id=user.id,
            payment_method="CARD",
            items=[
                {
                    "product_id": product.id,
                    "quantity": 2,
                    "unit_price": 15.00,
                }
            ],
            offline_device_id="DEVICE123",
            db=db,
        )

        assert sale.status == "PENDING"
        assert sale.total_amount == 30.00

    def test_create_sale_no_items_fails(
        self,
        db: Session,
        org,
        till,
        user,
    ):
        """Test that sale with no items is rejected."""
        with pytest.raises(ValueError, match="at least one item"):
            SaleService.create_sale(
                organization_id=org.id,
                till_id=till.id,
                cashier_id=user.id,
                payment_method="CASH",
                items=[],
                db=db,
            )

    def test_create_sale_invalid_product_fails(
        self,
        db: Session,
        org,
        till,
        user,
    ):
        """Test that sale with invalid product is rejected."""
        with pytest.raises(ValueError, match="Product .* not found"):
            SaleService.create_sale(
                organization_id=org.id,
                till_id=till.id,
                cashier_id=user.id,
                payment_method="CASH",
                items=[
                    {
                        "product_id": 99999,  # Invalid
                        "quantity": 1,
                        "unit_price": 10.00,
                    }
                ],
                db=db,
            )

    def test_commit_pending_sale(
        self,
        db: Session,
        org,
        till,
        user,
        product,
        location,
    ):
        """Test committing a pending sale generates movements."""
        # Create pending sale
        sale = SaleService.create_sale(
            organization_id=org.id,
            till_id=till.id,
            cashier_id=user.id,
            payment_method="CASH",
            items=[
                {
                    "product_id": product.id,
                    "quantity": 3,
                    "unit_price": 10.00,
                }
            ],
            offline_device_id="DEVICE123",
            db=db,
        )

        assert sale.status == "PENDING"

        # Commit during sync
        SaleService.commit_pending_sale(sale.id, user.id, db)

        # Refresh sale
        db.refresh(sale)
        assert sale.status == "COMPLETED"

        # Check movement was created
        movement = db.query(InventoryMovement).filter(
            InventoryMovement.reference_type == "SALE",
            InventoryMovement.reference_id == sale.id,
        ).first()

        assert movement is not None
        assert movement.quantity == -3  # Negative for sale

    def test_commit_pending_sale_idempotent(
        self,
        db: Session,
        org,
        till,
        user,
        product,
    ):
        """Test that committing pending sale twice is idempotent."""
        # Create pending sale
        sale = SaleService.create_sale(
            organization_id=org.id,
            till_id=till.id,
            cashier_id=user.id,
            payment_method="CASH",
            items=[
                {
                    "product_id": product.id,
                    "quantity": 2,
                    "unit_price": 10.00,
                }
            ],
            offline_device_id="DEVICE123",
            db=db,
        )

        # Commit twice
        SaleService.commit_pending_sale(sale.id, user.id, db)
        SaleService.commit_pending_sale(sale.id, user.id, db)

        # Check only one movement was created
        movements = db.query(InventoryMovement).filter(
            InventoryMovement.reference_type == "SALE",
            InventoryMovement.reference_id == sale.id,
        ).all()

        assert len(movements) == 1

    def test_oversell_allowed(
        self,
        db: Session,
        org,
        till,
        user,
        product,
    ):
        """Test that sale is allowed even if quantity exceeds stock (U006)."""
        # No stock movements recorded (stock is 0)
        # But sale should still be created
        sale = SaleService.create_sale(
            organization_id=org.id,
            till_id=till.id,
            cashier_id=user.id,
            payment_method="CASH",
            items=[
                {
                    "product_id": product.id,
                    "quantity": 100,  # More than available stock
                    "unit_price": 10.00,
                }
            ],
            db=db,
        )

        # Sale should succeed
        assert sale.status == "COMPLETED"
        assert sale.total_amount == 1000.00
