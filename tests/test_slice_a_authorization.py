"""
Tests for Phase A authorization and identity fixes.
Verifies that inventory endpoints correctly derive organization and user context from JWT tokens
and reject cross-organization and cross-location access.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from jose import jwt
from datetime import datetime, timedelta

from src.main import app
from src.models.entities import (
    User, Organization, Product, Location, InventoryMovement
)
from src.schemas.inventory import AdjustmentCreate
from src.security.auth import create_access_token


class TestAdjustmentAuthorizationAndIdentity:
    """Verify that stock adjustments derive user context from JWT, not client request."""
    
    def test_adjustment_requires_authentication(self, db: Session):
        """Test that unauthenticated requests to adjust endpoint are rejected."""
        client = TestClient(app)
        
        org = Organization(name="Test Org", code="TEST", is_active=True)
        db.add(org)
        db.commit()
        db.refresh(org)
        
        location = Location(name="Main", code="MAIN", organization_id=org.id)
        product = Product(
            name="Test Product",
            sku="SKU001",
            price=100.0,
            organization_id=org.id,
        )
        db.add_all([location, product])
        db.commit()
        db.refresh(location)
        db.refresh(product)
        
        # Attempt adjustment without authentication
        response = client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": 5,
                "reason": "ADJUSTMENT",
                "note": "Test",
            }
        )
        
        assert response.status_code in [401, 403], "Unauthenticated request should be rejected"

    def test_adjustment_records_current_user_id(self, db: Session, user: User):
        """Test that adjustment records the authenticated user's ID, not a client-supplied value."""
        client = TestClient(app)
        
        # Create second user in same organization
        user2 = User(
            email="user2@test.com",
            full_name="User Two",
            hashed_password="hash2",
            organization_id=user.organization_id,
            role="operator",
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)
        
        location = Location(name="Main", code="MAIN", organization_id=user.organization_id)
        product = Product(
            name="Test Product",
            sku="SKU001",
            price=100.0,
            organization_id=user.organization_id,
        )
        db.add_all([location, product])
        db.commit()
        db.refresh(location)
        db.refresh(product)
        
        # User makes an adjustment
        token = create_access_token(data={"sub": user.email})
        response = client.post(
            "/api/v1/stock/stock/adjust",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": 5,
                "reason": "ADJUSTMENT",
                "note": "Test adjustment",
            }
        )
        
        assert response.status_code == 200, f"Adjustment should succeed: {response.text}"
        
        # Verify the movement was recorded with user's ID, not user2
        movement = db.query(InventoryMovement).filter(
            InventoryMovement.product_id == product.id,
            InventoryMovement.location_id == location.id,
        ).first()
        
        assert movement is not None
        assert movement.recorded_by_id == user.id, "Movement should record the authenticated user's ID"
        assert movement.recorded_by_id != user2.id, "Should not record a different user's ID"

    def test_adjustment_derives_organization_from_user(self, db: Session):
        """Test that adjustment uses the user's organization, ignoring any client-supplied org."""
        client = TestClient(app)
        
        org1 = Organization(name="Org One", code="ORG1", is_active=True)
        org2 = Organization(name="Org Two", code="ORG2", is_active=True)
        db.add_all([org1, org2])
        db.commit()
        db.refresh(org1)
        db.refresh(org2)
        
        user_org1 = User(
            email="user@org1.com",
            full_name="User Org1",
            hashed_password="hash",
            organization_id=org1.id,
            role="operator",
        )
        db.add(user_org1)
        db.commit()
        db.refresh(user_org1)
        
        # Create location and product in org1
        location_org1 = Location(name="Main", code="MAIN", organization_id=org1.id)
        product_org1 = Product(
            name="Product Org1",
            sku="SKU001",
            price=100.0,
            organization_id=org1.id,
        )
        db.add_all([location_org1, product_org1])
        db.commit()
        db.refresh(location_org1)
        db.refresh(product_org1)
        
        # Create location in org2
        location_org2 = Location(name="Main", code="MAIN", organization_id=org2.id)
        db.add(location_org2)
        db.commit()
        db.refresh(location_org2)
        
        token = create_access_token(data={"sub": user_org1.email})
        
        # User from org1 attempts adjustment at location in org2
        # Client request might include org2.id, but backend should use org1 from JWT
        response = client.post(
            "/api/v1/stock/stock/adjust",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "product_id": product_org1.id,
                "location_id": location_org2.id,  # Location in different org
                "quantity": 5,
                "reason": "ADJUSTMENT",
                "note": "Cross-org attempt",
            }
        )
        
        # Should be rejected because location belongs to different org
        assert response.status_code in [401, 403], "Cross-organization location access should be denied"

    def test_adjustment_verifies_location_ownership(self, db: Session):
        """Test that adjustment is rejected if location doesn't belong to user's org."""
        client = TestClient(app)
        
        org1 = Organization(name="Org One", code="ORG1", is_active=True)
        org2 = Organization(name="Org Two", code="ORG2", is_active=True)
        db.add_all([org1, org2])
        db.commit()
        db.refresh(org1)
        db.refresh(org2)
        
        user_org1 = User(
            email="user@org1.com",
            full_name="User",
            hashed_password="hash",
            organization_id=org1.id,
            role="operator",
        )
        db.add(user_org1)
        db.commit()
        db.refresh(user_org1)
        
        # Create resource in org1
        location_org1 = Location(name="Main", code="MAIN", organization_id=org1.id)
        product_org1 = Product(
            name="Product",
            sku="SKU001",
            price=100.0,
            organization_id=org1.id,
        )
        db.add_all([location_org1, product_org1])
        db.commit()
        db.refresh(location_org1)
        db.refresh(product_org1)
        
        # Create location in org2
        location_org2 = Location(name="Other", code="OTHER", organization_id=org2.id)
        db.add(location_org2)
        db.commit()
        db.refresh(location_org2)
        
        token = create_access_token(data={"sub": user_org1.email})
        
        # Attempt to adjust at location in different org
        response = client.post(
            "/api/v1/stock/stock/adjust",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "product_id": product_org1.id,
                "location_id": location_org2.id,
                "quantity": 5,
                "reason": "ADJUSTMENT",
            }
        )
        
        assert response.status_code in [401, 403], "Location in different org should be denied"


class TestMovementEndpointAuthorization:
    """Verify that movement list/detail endpoints enforce org scoping."""
    
    def test_list_movements_requires_authentication(self, db: Session):
        """Test that unauthenticated movement list requests are rejected."""
        client = TestClient(app)
        
        response = client.get("/api/v1/stock/stock/movements")
        assert response.status_code in [401, 403], "Unauthenticated movement list should be rejected"

    def test_list_movements_scoped_to_user_org(self, db: Session, user: User):
        """Test that movement list only shows movements in user's organization."""
        client = TestClient(app)
        
        # Create second org with own location and product
        org2 = Organization(name="Org Two", code="ORG2", is_active=True)
        db.add(org2)
        db.commit()
        db.refresh(org2)
        
        # Create product and location in user's org
        location_user = Location(name="Main", code="MAIN", organization_id=user.organization_id)
        product_user = Product(
            name="Product User Org",
            sku="SKU001",
            price=100.0,
            organization_id=user.organization_id,
        )
        db.add_all([location_user, product_user])
        db.commit()
        db.refresh(location_user)
        db.refresh(product_user)
        
        # Create location and product in org2
        location_org2 = Location(name="Main", code="MAIN", organization_id=org2.id)
        product_org2 = Product(
            name="Product Org2",
            sku="SKU002",
            price=100.0,
            organization_id=org2.id,
        )
        db.add_all([location_org2, product_org2])
        db.commit()
        db.refresh(location_org2)
        db.refresh(product_org2)
        
        # Create movements in both orgs
        movement_user = InventoryMovement(
            organization_id=user.organization_id,
            product_id=product_user.id,
            location_id=location_user.id,
            quantity=10,
            reason="ADJUSTMENT",
            recorded_by_id=user.id,
        )
        movement_org2 = InventoryMovement(
            organization_id=org2.id,
            product_id=product_org2.id,
            location_id=location_org2.id,
            quantity=5,
            reason="ADJUSTMENT",
            recorded_by_id=1,  # Dummy user
        )
        db.add_all([movement_user, movement_org2])
        db.commit()
        db.refresh(movement_user)
        db.refresh(movement_org2)
        
        token = create_access_token(data={"sub": user.email})
        response = client.get(
            "/api/v1/stock/stock/movements",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        
        # Should only see movement from user's org
        assert data["total"] >= 1, "Should have at least one movement"
        for item in data["items"]:
            assert item["product_id"] == product_user.id, "Should not see movements from other orgs"

    def test_get_movement_detail_requires_auth(self, db: Session):
        """Test that movement detail requires authentication."""
        client = TestClient(app)
        
        response = client.get("/api/v1/stock/movements/1")
        assert response.status_code in [401, 403], "Unauthenticated movement detail should be rejected"

    def test_get_movement_detail_denied_for_other_org(self, db: Session, user: User):
        """Test that user cannot view movement details from other organization."""
        client = TestClient(app)
        
        # Create second org
        org2 = Organization(name="Org Two", code="ORG2", is_active=True)
        db.add(org2)
        db.commit()
        db.refresh(org2)
        
        # Create user in org2
        user2 = User(
            email="user@org2.com",
            full_name="User Org2",
            hashed_password="hash",
            organization_id=org2.id,
            role="operator",
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)
        
        # Create location and product in org2
        location_org2 = Location(name="Main", code="MAIN", organization_id=org2.id)
        product_org2 = Product(
            name="Product",
            sku="SKU001",
            price=100.0,
            organization_id=org2.id,
        )
        db.add_all([location_org2, product_org2])
        db.commit()
        db.refresh(location_org2)
        db.refresh(product_org2)
        
        # Create movement in org2
        movement_org2 = InventoryMovement(
            organization_id=org2.id,
            product_id=product_org2.id,
            location_id=location_org2.id,
            quantity=5,
            reason="ADJUSTMENT",
            recorded_by_id=user2.id,
        )
        db.add(movement_org2)
        db.commit()
        db.refresh(movement_org2)
        
        # User from first org attempts to view movement from org2
        token = create_access_token(data={"sub": user.email})
        response = client.get(
            f"/api/v1/stock/movements/{movement_org2.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [401, 403], "Should not allow access to movements from other orgs"


class TestAdjustmentSchemaChanges:
    """Verify that AdjustmentCreate schema no longer accepts recorded_by_id."""
    
    def test_adjustment_create_excludes_recorded_by_id(self):
        """Test that AdjustmentCreate schema does not have recorded_by_id field."""
        # AdjustmentCreate should not accept recorded_by_id
        schema = AdjustmentCreate.__fields__
        
        assert "recorded_by_id" not in schema, "AdjustmentCreate should not have recorded_by_id field"
        assert "product_id" in schema, "Should have product_id"
        assert "location_id" in schema, "Should have location_id"
        assert "quantity" in schema, "Should have quantity"
        assert "reason" in schema, "Should have reason"

    def test_adjustment_create_excludes_organization_id(self):
        """Test that AdjustmentCreate schema does not have organization_id field."""
        schema = AdjustmentCreate.__fields__
        
        assert "organization_id" not in schema, "AdjustmentCreate should not have organization_id field"
