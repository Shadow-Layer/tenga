"""API integration tests for products endpoints.

This module provides comprehensive tests for the products API, covering:
- CRUD operations (Create, Read, Update, List)
- Search functionality by name, SKU, and barcode
- Authorization and organization isolation
- Error handling and conflict detection
- Pagination
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from sqlalchemy.orm import Session
from src.models.entities import Product, User, Organization
from src.security.password import hash_password


class TestProductsAPI:
    """Tests for product API endpoints."""

    # ========== CRUD Operations Tests ==========

    def test_create_product_with_barcode(self, authenticated_client: TestClient, org: Organization):
        """Test creating product with barcode.
        
        POST /api/v1/products with all fields including barcode.
        Expected: 201 Created with barcode, is_active=true, created_at/updated_at.
        """
        response = authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU001",
                "name": "Test Product",
                "price": 10.00,
                "cost": 5.00,
                "barcode": "1234567890",
                "organization_id": org.id
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "SKU001"
        assert data["name"] == "Test Product"
        assert data["barcode"] == "1234567890"
        assert data["is_active"] is True
        assert "created_at" in data
        assert "updated_at" in data
        assert data["organization_id"] == org.id

    def test_create_product_without_barcode(self, authenticated_client: TestClient, org: Organization):
        """Test creating product without barcode (barcode is optional)."""
        response = authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU002",
                "name": "Product Without Barcode",
                "price": 20.00,
                "cost": 10.00,
                "organization_id": org.id
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "SKU002"
        assert data["barcode"] is None
        assert data["is_active"] is True

    def test_get_product(self, authenticated_client: TestClient, org: Organization):
        """Test getting product by ID.
        
        POST to create product, then GET /api/v1/products/{product_id}.
        Expected: 200 OK with all fields including barcode.
        """
        # Create product
        create_response = authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU003",
                "name": "Get Test Product",
                "price": 15.00,
                "cost": 7.50,
                "barcode": "9876543210",
                "organization_id": org.id
            }
        )
        assert create_response.status_code == 201
        product_id = create_response.json()["id"]

        # Get product
        response = authenticated_client.get(f"/api/v1/products/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product_id
        assert data["sku"] == "SKU003"
        assert data["name"] == "Get Test Product"
        assert data["barcode"] == "9876543210"
        assert data["price"] == "15.00" or data["price"] == 15.00
        assert data["organization_id"] == org.id

    def test_update_product_barcode(self, authenticated_client: TestClient, org: Organization):
        """Test updating product with barcode.
        
        Create product (no barcode), then PUT /api/v1/products/{id} with barcode.
        Expected: 200 OK with new barcode in response.
        """
        # Create product without barcode
        create_response = authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU004",
                "name": "Product to Update",
                "price": 25.00,
                "cost": 12.00,
                "organization_id": org.id
            }
        )
        product_id = create_response.json()["id"]

        # Update with barcode
        response = authenticated_client.put(
            f"/api/v1/products/{product_id}",
            json={"barcode": "1111111111"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product_id
        assert data["barcode"] == "1111111111"
        assert data["name"] == "Product to Update"  # Should not change

    def test_list_products(self, authenticated_client: TestClient, org: Organization):
        """Test listing products.
        
        Create 3 products, then GET /api/v1/products.
        Expected: 200 OK with items array containing all products and total=3.
        """
        # Create 3 products
        for i in range(3):
            authenticated_client.post(
                "/api/v1/products",
                json={
                    "sku": f"LIST_SKU{i:03d}",
                    "name": f"List Product {i}",
                    "price": 10.00 + i,
                    "cost": 5.00 + i,
                    "organization_id": org.id
                }
            )

        # List products
        response = authenticated_client.get(f"/api/v1/products?organization_id={org.id}")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) == 3
        assert data["total"] == 3

    # ========== Search Functionality Tests ==========

    def test_search_by_name(self, authenticated_client: TestClient, org: Organization):
        """Test search by name.
        
        Create products: "Laptop", "Mouse", "Keyboard"
        GET /api/v1/products?search=board
        Expected: 200 OK with 1 item (Keyboard).
        """
        # Create products
        authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_LAPTOP",
                "name": "Laptop",
                "price": 1000.00,
                "cost": 500.00,
                "organization_id": org.id
            }
        )
        authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_MOUSE",
                "name": "Mouse",
                "price": 25.00,
                "cost": 10.00,
                "organization_id": org.id
            }
        )
        authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_KEYBOARD",
                "name": "Keyboard",
                "price": 75.00,
                "cost": 35.00,
                "organization_id": org.id
            }
        )

        # Search for "board"
        response = authenticated_client.get(
            f"/api/v1/products?organization_id={org.id}&search=board"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Keyboard"

    def test_search_by_sku(self, authenticated_client: TestClient, org: Organization):
        """Test search by SKU.
        
        Create product with sku="SKU123"
        GET /api/v1/products?search=SKU123
        Expected: 200 OK with 1 item.
        """
        authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU123",
                "name": "SKU Test Product",
                "price": 50.00,
                "cost": 25.00,
                "organization_id": org.id
            }
        )

        # Search by SKU
        response = authenticated_client.get(
            f"/api/v1/products?organization_id={org.id}&search=SKU123"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["sku"] == "SKU123"

    def test_search_by_barcode(self, authenticated_client: TestClient, org: Organization):
        """Test search by barcode.
        
        Create product with barcode="9876543210"
        GET /api/v1/products?search=9876543210
        Expected: 200 OK with 1 item.
        """
        authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_BARCODE",
                "name": "Barcode Test",
                "price": 30.00,
                "cost": 15.00,
                "barcode": "9876543210",
                "organization_id": org.id
            }
        )

        # Search by barcode
        response = authenticated_client.get(
            f"/api/v1/products?organization_id={org.id}&search=9876543210"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["barcode"] == "9876543210"

    def test_search_case_insensitive(self, authenticated_client: TestClient, org: Organization):
        """Test case-insensitive search.
        
        Create product with name="TestProduct"
        GET /api/v1/products?search=testproduct
        Expected: 200 OK with 1 item (case-insensitive match).
        """
        authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_CASE",
                "name": "TestProduct",
                "price": 40.00,
                "cost": 20.00,
                "organization_id": org.id
            }
        )

        # Search with lowercase
        response = authenticated_client.get(
            f"/api/v1/products?organization_id={org.id}&search=testproduct"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "TestProduct"

    # ========== Authorization Tests ==========

    def test_create_product_requires_auth(self, unauthenticated_client: TestClient, org: Organization):
        """Test create product requires authentication.
        
        POST /api/v1/products without Authorization header.
        Expected: 401 Unauthorized.
        """
        response = unauthenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_UNAUTH",
                "name": "Unauthorized Product",
                "price": 10.00,
                "cost": 5.00,
                "organization_id": org.id
            }
        )
        assert response.status_code == 401

    def test_cross_org_access_denied(self, db: Session, authenticated_client: TestClient, org: Organization):
        """Test cross-organization access is denied.
        
        Create org1, user1, product1
        Create org2, user2
        Authenticate as user2
        Try GET /api/v1/products/{product1.id}
        Expected: 403 Forbidden.
        """
        # Create second organization
        org2 = Organization(name="Test Org 2", code="TEST2")
        db.add(org2)
        db.commit()

        # Create product in first organization
        product = Product(
            organization_id=org.id,
            sku="SKU_ORG1",
            name="Org1 Product",
            price=50.00,
            cost=25.00
        )
        db.add(product)
        db.commit()

        # Create user in second organization
        user2 = User(
            organization_id=org2.id,
            email="user2@test.com",
            username="user2",
            full_name="User 2",
            password_hash=hash_password("user2_password"),
            role="operator"
        )
        db.add(user2)
        db.commit()

        # Create authenticated client for org2 user
        from fastapi.testclient import TestClient
        from src.main import app
        from src.database.config import get_db

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        org2_client = TestClient(app)

        # Login as org2 user
        login_response = org2_client.post(
            "/api/v1/auth/login",
            json={"email": "user2@test.com", "password": "user2_password"}
        )
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            org2_client.headers["Authorization"] = f"Bearer {token}"

        # Try to access org1 product
        response = org2_client.get(f"/api/v1/products/{product.id}")
        assert response.status_code == 403

        app.dependency_overrides.clear()

    def test_list_products_cross_org_denied(self, db: Session, authenticated_client: TestClient, org: Organization):
        """Test listing products from another organization is denied."""
        # Create second organization
        org2 = Organization(name="Test Org 2b", code="TEST2B")
        db.add(org2)
        db.commit()

        # Try to list products from org2
        response = authenticated_client.get(f"/api/v1/products?organization_id={org2.id}")
        assert response.status_code == 403

    # ========== Error Handling Tests ==========

    def test_duplicate_sku_conflict(self, authenticated_client: TestClient, org: Organization):
        """Test duplicate SKU returns conflict.
        
        Create product with sku="SKU001"
        Try to create another with same sku
        Expected: 409 Conflict.
        """
        # Create first product
        response1 = authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "UNIQUE_SKU",
                "name": "First Product",
                "price": 10.00,
                "cost": 5.00,
                "organization_id": org.id
            }
        )
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "UNIQUE_SKU",
                "name": "Second Product",
                "price": 20.00,
                "cost": 10.00,
                "organization_id": org.id
            }
        )
        assert response2.status_code == 409

    def test_invalid_product_not_found(self, authenticated_client: TestClient, org: Organization):
        """Test getting non-existent product returns 404.
        
        GET /api/v1/products/99999
        Expected: 404 Not Found.
        """
        response = authenticated_client.get("/api/v1/products/99999")
        assert response.status_code == 404

    # ========== Pagination Tests ==========

    def test_pagination_skip_limit(self, authenticated_client: TestClient, org: Organization):
        """Test pagination with skip and limit.
        
        Create 25 products
        GET /api/v1/products?skip=0&limit=10 should return 10 items
        GET /api/v1/products?skip=10&limit=10 should return 10 different items
        Expected: 200 OK with correct pagination.
        """
        # Create 25 products
        for i in range(25):
            authenticated_client.post(
                "/api/v1/products",
                json={
                    "sku": f"PAGINATE_{i:03d}",
                    "name": f"Pagination Product {i}",
                    "price": 10.00 + i,
                    "cost": 5.00 + i,
                    "organization_id": org.id
                }
            )

        # Get first page
        response1 = authenticated_client.get(
            f"/api/v1/products?organization_id={org.id}&skip=0&limit=10"
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["items"]) == 10
        assert data1["total"] == 25
        first_page_ids = [item["id"] for item in data1["items"]]

        # Get second page
        response2 = authenticated_client.get(
            f"/api/v1/products?organization_id={org.id}&skip=10&limit=10"
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["items"]) == 10
        assert data2["total"] == 25
        second_page_ids = [item["id"] for item in data2["items"]]

        # Verify pages are different
        assert first_page_ids != second_page_ids

    def test_pagination_last_page(self, authenticated_client: TestClient, org: Organization):
        """Test pagination on last page with fewer items."""
        # Create 25 products
        for i in range(25):
            authenticated_client.post(
                "/api/v1/products",
                json={
                    "sku": f"LAST_PAGE_{i:03d}",
                    "name": f"Last Page Product {i}",
                    "price": 10.00 + i,
                    "cost": 5.00 + i,
                    "organization_id": org.id
                }
            )

        # Get last page (should have 5 items since 25 % 10 = 5)
        response = authenticated_client.get(
            f"/api/v1/products?organization_id={org.id}&skip=20&limit=10"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 25

    # ========== Additional Update Tests ==========

    def test_update_product_name_only(self, authenticated_client: TestClient, org: Organization):
        """Test updating only product name."""
        # Create product
        create_response = authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_UPDATE_NAME",
                "name": "Original Name",
                "price": 50.00,
                "cost": 25.00,
                "organization_id": org.id
            }
        )
        product_id = create_response.json()["id"]

        # Update only name
        response = authenticated_client.put(
            f"/api/v1/products/{product_id}",
            json={"name": "Updated Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["sku"] == "SKU_UPDATE_NAME"

    def test_update_product_sku_conflict(self, authenticated_client: TestClient, org: Organization):
        """Test updating product SKU to conflict with another product."""
        # Create two products
        response1 = authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_CONFLICT_1",
                "name": "Product 1",
                "price": 10.00,
                "cost": 5.00,
                "organization_id": org.id
            }
        )
        product_id_1 = response1.json()["id"]

        authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_CONFLICT_2",
                "name": "Product 2",
                "price": 20.00,
                "cost": 10.00,
                "organization_id": org.id
            }
        )

        # Try to update product 1 SKU to conflict with product 2
        response = authenticated_client.put(
            f"/api/v1/products/{product_id_1}",
            json={"sku": "SKU_CONFLICT_2"}
        )
        assert response.status_code == 409

    def test_search_no_results(self, authenticated_client: TestClient, org: Organization):
        """Test search with no matching results."""
        # Create a product
        authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_SEARCH_TEST",
                "name": "Specific Product",
                "price": 50.00,
                "cost": 25.00,
                "organization_id": org.id
            }
        )

        # Search for non-existent term
        response = authenticated_client.get(
            f"/api/v1/products?organization_id={org.id}&search=nonexistent_product"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_update_price_and_cost(self, authenticated_client: TestClient, org: Organization):
        """Test updating product price and cost."""
        # Create product
        create_response = authenticated_client.post(
            "/api/v1/products",
            json={
                "sku": "SKU_PRICE_UPDATE",
                "name": "Price Test",
                "price": 100.00,
                "cost": 50.00,
                "organization_id": org.id
            }
        )
        product_id = create_response.json()["id"]

        # Update price and cost
        response = authenticated_client.put(
            f"/api/v1/products/{product_id}",
            json={"price": 150.00, "cost": 75.00}
        )
        assert response.status_code == 200
        data = response.json()
        assert float(data["price"]) == 150.00
        assert float(data["cost"]) == 75.00
