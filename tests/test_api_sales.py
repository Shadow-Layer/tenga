"""API tests for sales."""
import pytest
from fastapi.testclient import TestClient
from src.models.entities import InventoryMovement, Payment, ReceiptAudit, Sale, User
from src.services.inventory_service import InventoryService
from src.services.till_service import TillService


class TestSales:
    """Tests for sales endpoints."""
    
    def test_create_sale(self, client: TestClient, till, product, user, open_pos_session, db):
        """Test creating sale."""
        session = open_pos_session(user)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "create-sale-0001",
                "cashier_id": user.id,
                "payment_method": "CASH",
                "amount_tendered": "55.00",
                "items": [
                    {"product_id": product.id, "quantity": 5, "unit_price": 10.00}
                ],
                "is_offline": False
            }
        )
        assert response.status_code == 201
        assert response.json()["amount_tendered"] == "55.00"
        assert response.json()["change_given"] == "5.00"
        assert db.query(Payment).count() == 1
        assert db.query(ReceiptAudit).count() == 1
    
    def test_get_sale(self, client: TestClient, till, product, user, open_pos_session):
        """Test getting sale."""
        session = open_pos_session(user)
        # Create sale first
        create_resp = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "get-sale-0001",
                "cashier_id": user.id,
                "payment_method": "CASH",
                "amount_tendered": "50.00",
                "items": [
                    {"product_id": product.id, "quantity": 5, "unit_price": 10.00}
                ],
                "is_offline": False
            }
        )
        sale_id = create_resp.json()["id"]
        
        # Get sale
        response = client.get(f"/api/v1/sales/{sale_id}")
        assert response.status_code == 200
    
    def test_list_sales(self, client: TestClient, till, product, user, open_pos_session):
        """Test listing sales."""
        session = open_pos_session(user)
        # Create sale first
        client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "list-sale-0001",
                "cashier_id": user.id,
                "payment_method": "CASH",
                "amount_tendered": "50.00",
                "items": [
                    {"product_id": product.id, "quantity": 5, "unit_price": 10.00}
                ],
                "is_offline": False
            }
        )
        
        response = client.get(f"/api/v1/sales?till_id={till.id}")
        assert response.status_code == 200
    
    def test_commit_sale(self, client: TestClient, till, product, user, open_pos_session):
        """Test committing sale."""
        session = open_pos_session(user)
        # Create sale
        create_resp = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "commit-sale-0001",
                "cashier_id": user.id,
                "payment_method": "CASH",
                "amount_tendered": "50.00",
                "items": [
                    {"product_id": product.id, "quantity": 5, "unit_price": 10.00}
                ],
                "is_offline": False
            }
        )
        sale_id = create_resp.json()["id"]
        
        # Commit sale
        response = client.post(
            f"/api/v1/sales/{sale_id}/commit",
            json={"user_id": user.id}
        )
        assert response.status_code == 200
    
    def test_oversell_allowed(self, client: TestClient, till, product, user, open_pos_session):
        """Test that overselling is allowed."""
        session = open_pos_session(user)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "oversell-sale-0001",
                "cashier_id": user.id,
                "payment_method": "CASH",
                "amount_tendered": "10000.00",
                "items": [
                    {"product_id": product.id, "quantity": 1000, "unit_price": 10.00}
                ],
                "is_offline": False
            }
        )
        # Should succeed despite overselling
        assert response.status_code == 201

    def test_cashier_identity_comes_from_authenticated_user(
        self, client: TestClient, till, product, user, open_pos_session
    ):
        session = open_pos_session(user)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "cashier-sale-0001",
                "cashier_id": user.id + 1000,
                "payment_method": "CASH",
                "amount_tendered": "10.00",
                "items": [
                    {"product_id": product.id, "quantity": 1, "unit_price": 10.00}
                ],
            },
        )

        assert response.status_code == 201
        assert response.json()["cashier_id"] == user.id

    def test_sale_rejects_insufficient_cash_without_persisting(
        self, client: TestClient, db, till, product, user, open_pos_session
    ):
        session = open_pos_session(user)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "insufficient-sale-001",
                "payment_method": "CASH",
                "amount_tendered": "9.99",
                "items": [
                    {"product_id": product.id, "quantity": 1, "unit_price": "10.00"}
                ],
            },
        )

        assert response.status_code == 422
        assert db.query(Sale).count() == 0

    def test_sale_and_inventory_movement_roll_back_together(
        self, client: TestClient, db, till, product, user, monkeypatch, open_pos_session
    ):
        session = open_pos_session(user)
        def fail_stock_update(*args, **kwargs):
            raise RuntimeError("simulated projection update failure")

        monkeypatch.setattr(InventoryService, "update_stock_cache", fail_stock_update)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "rollback-sale-0001",
                "cashier_id": user.id,
                "payment_method": "CASH",
                "amount_tendered": "20.00",
                "items": [
                    {"product_id": product.id, "quantity": 2, "unit_price": 10.00}
                ],
            },
        )

        assert response.status_code == 500
        assert db.query(Sale).count() == 0
        assert db.query(InventoryMovement).count() == 0
        assert db.query(Payment).count() == 0
        assert db.query(ReceiptAudit).count() == 0

    def test_sale_requires_an_open_session(
        self, client: TestClient, db, till, product
    ):
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "payment_method": "CASH",
                "amount_tendered": "10.00",
                "items": [{"product_id": product.id, "quantity": 1}],
            },
        )
        assert response.status_code == 422
        assert db.query(Sale).count() == 0

    def test_sale_rejects_closed_session(
        self, client: TestClient, db, till, product, user, open_pos_session
    ):
        session = open_pos_session(user)
        session.status = "CLOSED"
        db.commit()
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "closed-session-sale",
                "payment_method": "CASH",
                "amount_tendered": "10.00",
                "items": [{"product_id": product.id, "quantity": 1}],
            },
        )
        assert response.status_code == 409
        assert db.query(Sale).count() == 0

    def test_sale_requires_active_till_assignment(
        self, client: TestClient, db, org, till, product, user
    ):
        session = TillService.open_session(
            organization_id=org.id,
            till_id=till.id,
            operator_id=user.id,
            db=db,
            enforce_assignment=False,
        )
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "unassigned-sale-001",
                "payment_method": "CASH",
                "amount_tendered": "10.00",
                "items": [{"product_id": product.id, "quantity": 1}],
            },
        )
        assert response.status_code == 403
        assert db.query(Sale).count() == 0

    def test_sale_cannot_use_another_operators_session(
        self, client: TestClient, db, org, till, product, open_pos_session
    ):
        other_user = User(
            organization_id=org.id,
            email="other-pos@test.com",
            username="other-pos",
            full_name="Other POS User",
            password_hash="unused",
            role="operator",
        )
        db.add(other_user)
        db.commit()
        other_session = open_pos_session(other_user)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": other_session.id,
                "idempotency_key": "wrong-session-sale",
                "payment_method": "CASH",
                "amount_tendered": "10.00",
                "items": [{"product_id": product.id, "quantity": 1}],
            },
        )
        assert response.status_code == 403
        assert db.query(Sale).count() == 0

    def test_idempotent_cash_replay_and_payload_conflict(
        self, client: TestClient, db, till, product, user, open_pos_session
    ):
        session = open_pos_session(user)
        payload = {
            "till_id": till.id,
            "till_session_id": session.id,
            "idempotency_key": "cash-operation-0001",
            "payment_method": "CASH",
            "amount_tendered": "20.00",
            "items": [{
                "product_id": product.id,
                "quantity": 2,
                "unit_price": "10.00",
                "tax_rate": "0",
                "tax_inclusive": False,
            }],
        }
        first = client.post("/api/v1/sales", json=payload)
        replay = client.post("/api/v1/sales", json=payload)
        assert first.status_code == replay.status_code == 201
        assert first.json()["id"] == replay.json()["id"]
        assert db.query(Sale).count() == 1
        assert db.query(Payment).count() == 1
        assert db.query(InventoryMovement).count() == 1

        changed_payload = {**payload, "items": [{"product_id": product.id, "quantity": 1}]}
        conflict = client.post("/api/v1/sales", json=changed_payload)
        assert conflict.status_code == 409
        assert db.query(Sale).count() == 1
        assert db.query(InventoryMovement).count() == 1

    def test_confirmed_total_mismatch_is_rejected_without_persisting(
        self, client: TestClient, db, till, product, user, open_pos_session
    ):
        session = open_pos_session(user)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "confirmed-total-001",
                "payment_method": "CASH",
                "expected_total": "9.99",
                "amount_tendered": "20.00",
                "items": [{
                    "product_id": product.id,
                    "quantity": 1,
                    "unit_price": "10.00",
                    "tax_rate": "0",
                    "tax_inclusive": False,
                }],
            },
            headers={"Origin": "http://pos.example.test"},
        )

        assert response.status_code == 422
        assert response.headers.get("x-sale-outcome") == "NOT_CREATED", response.text
        assert "x-sale-outcome" in response.headers["access-control-expose-headers"].lower()
        assert db.query(Sale).count() == 0
        assert db.query(Payment).count() == 0
        assert db.query(InventoryMovement).count() == 0

    def test_idempotent_replay_returns_original_price_snapshot_after_product_change(
        self, client: TestClient, db, till, product, user, open_pos_session
    ):
        session = open_pos_session(user)
        payload = {
            "till_id": till.id,
            "till_session_id": session.id,
            "idempotency_key": "price-snapshot-retry",
            "payment_method": "CASH",
            "expected_total": "20.00",
            "amount_tendered": "20.00",
            "items": [{
                "product_id": product.id,
                "quantity": 2,
                "unit_price": "10.00",
                "tax_rate": "0",
                "tax_inclusive": False,
            }],
        }
        first = client.post("/api/v1/sales", json=payload)
        product.price = 12
        db.commit()
        replay = client.post("/api/v1/sales", json=payload)

        assert first.status_code == replay.status_code == 201
        assert replay.json()["id"] == first.json()["id"]
        assert replay.json()["total_amount"] == 20
        assert db.query(Sale).count() == 1
        assert db.query(InventoryMovement).count() == 1

    def test_confirmed_sale_rejects_tax_snapshot_mismatch(
        self, client: TestClient, db, till, product, user, open_pos_session
    ):
        session = open_pos_session(user)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "tax-snapshot-mismatch",
                "payment_method": "CASH",
                "expected_total": "10.00",
                "amount_tendered": "20.00",
                "items": [{
                    "product_id": product.id,
                    "quantity": 1,
                    "unit_price": "10.00",
                    "tax_rate": "1",
                    "tax_inclusive": False,
                }],
            },
        )

        assert response.status_code == 422
        assert response.headers.get("x-sale-outcome") == "NOT_CREATED"
        assert db.query(Sale).count() == 0
        assert db.query(InventoryMovement).count() == 0

    def test_missing_till_rejection_is_marked_not_created(
        self, client: TestClient, till, product, user, open_pos_session
    ):
        session = open_pos_session(user)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id + 10000,
                "till_session_id": session.id,
                "idempotency_key": "missing-till-sale",
                "payment_method": "CASH",
                "expected_total": "10.00",
                "amount_tendered": "10.00",
                "items": [{
                    "product_id": product.id,
                    "quantity": 1,
                    "unit_price": "10.00",
                    "tax_rate": "0",
                    "tax_inclusive": False,
                }],
            },
        )

        assert response.status_code == 404
        assert response.headers.get("x-sale-outcome") == "NOT_CREATED"

    def test_request_validation_rejection_is_cors_readable_and_not_created(
        self, client: TestClient, till
    ):
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": "not-an-integer",
                "idempotency_key": "invalid-request-sale",
                "payment_method": "CASH",
                "expected_total": "10.00",
                "amount_tendered": "10.00",
                "items": [],
            },
            headers={"Origin": "http://pos.example.test"},
        )

        assert response.status_code == 422
        assert response.headers.get("x-sale-outcome") == "NOT_CREATED"
        assert "x-sale-outcome" in response.headers["access-control-expose-headers"].lower()

    def test_expected_total_requires_all_item_snapshots(
        self, client: TestClient, db, till, product, user, open_pos_session
    ):
        session = open_pos_session(user)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "till_session_id": session.id,
                "idempotency_key": "incomplete-snapshot",
                "payment_method": "CASH",
                "expected_total": "10.00",
                "amount_tendered": "10.00",
                "items": [{"product_id": product.id, "quantity": 1}],
            },
        )

        assert response.status_code == 422
        assert response.headers.get("x-sale-outcome") == "NOT_CREATED"
        assert db.query(Sale).count() == 0

    def test_missing_till_rejection_is_marked_not_created(
        self, client: TestClient, till, product, user, open_pos_session
    ):
        session = open_pos_session(user)
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id + 10000,
                "till_session_id": session.id,
                "idempotency_key": "missing-till-sale",
                "payment_method": "CASH",
                "expected_total": "10.00",
                "amount_tendered": "10.00",
                "items": [{
                    "product_id": product.id,
                    "quantity": 1,
                    "unit_price": "10.00",
                    "tax_rate": "0",
                    "tax_inclusive": False,
                }],
            },
        )

        assert response.status_code == 404
        assert response.headers.get("x-sale-outcome") == "NOT_CREATED"
