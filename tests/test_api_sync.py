"""API and authoritative-ledger tests for offline operation synchronization."""
from fastapi.testclient import TestClient

from src.models.entities import (
    InventoryCount,
    InventoryMovement,
    InventoryTransfer,
    OfflineOperation,
    Organization,
    Payment,
    ReceiptAudit,
    Sale,
)
from src.services.inventory_service import InventoryService
from src.services.sale_service import SaleService


def _request(org_id: int, *operations, device_id: str = "device-1"):
    return {
        "device_id": device_id,
        "organization_id": org_id,
        "operations": list(operations),
    }


def _operation(operation_id: str, operation_type: str, payload: dict):
    return {
        "operation_id": operation_id,
        "operation_type": operation_type,
        "payload": payload,
    }


class TestSync:
    def test_batch_requires_authentication(self, unauthenticated_client: TestClient, org):
        response = unauthenticated_client.post(
            "/api/v1/sync/batch",
            json=_request(
                org.id,
                _operation("receipt-1", "INVENTORY_RECEIPT", {
                    "product_id": 1,
                    "location_id": 1,
                    "quantity": 3,
                }),
            ),
        )

        assert response.status_code == 401

    def test_sync_is_authenticated_to_one_organization(self, client: TestClient, db):
        other_org = Organization(name="Other Org", code="OTHER")
        db.add(other_org)
        db.commit()

        response = client.post(
            "/api/v1/sync/batch",
            json=_request(
                other_org.id,
                _operation("receipt-1", "INVENTORY_RECEIPT", {
                    "product_id": 1,
                    "location_id": 1,
                    "quantity": 3,
                }),
            ),
        )

        assert response.status_code == 403
        assert db.query(OfflineOperation).count() == 0

    def test_receipt_replay_is_idempotent_and_payload_reuse_is_reconciled(
        self, client: TestClient, db, org, product, location, user
    ):
        event = _operation(
            "receipt-local-1",
            "INVENTORY_RECEIPT",
            {
                "product_id": product.id,
                "location_id": location.id,
                "quantity": 5,
                "unit_cost": "4.25",
            },
        )
        request = _request(org.id, event)
        first = client.post("/api/v1/sync/batch", json=request)
        replay = client.post("/api/v1/sync/batch", json=request)

        assert first.status_code == replay.status_code == 200
        first_ack = first.json()["acknowledgements"][0]
        assert first_ack["status"] == "APPLIED"
        assert replay.json()["acknowledgements"][0] == first_ack
        assert db.query(InventoryMovement).filter_by(
            organization_id=org.id,
            device_id="device-1",
            device_local_id="receipt-local-1",
        ).count() == 1
        assert InventoryService.compute_stock_at_location(
            org.id, product.id, location.id, db
        ) == 5

        changed = _request(
            org.id,
            _operation(
                "receipt-local-1",
                "INVENTORY_RECEIPT",
                {
                    "product_id": product.id,
                    "location_id": location.id,
                    "quantity": 6,
                    "unit_cost": "4.25",
                },
            ),
        )
        conflict = client.post("/api/v1/sync/batch", json=changed)
        assert conflict.status_code == 200
        assert conflict.json()["acknowledgements"][0]["status"] == "RECONCILIATION_REQUIRED"
        assert db.query(InventoryMovement).filter_by(
            device_id="device-1",
            device_local_id="receipt-local-1",
        ).count() == 1
        operation_record = db.query(OfflineOperation).filter_by(
            organization_id=org.id,
            device_id="device-1",
            operation_id="receipt-local-1",
        ).one()
        assert operation_record.actor_id == user.id

    def test_receipt_transfer_and_adjustment_apply_to_authoritative_ledger(
        self, admin_client: TestClient, db, org, product, location
    ):
        destination = type(location)(
            organization_id=org.id,
            code="LOC002",
            name="Second Store",
            is_active=True,
        )
        db.add(destination)
        db.commit()

        response = admin_client.post(
            "/api/v1/sync/batch",
            json=_request(
                org.id,
                _operation("receipt-2", "INVENTORY_RECEIPT", {
                    "product_id": product.id,
                    "location_id": location.id,
                    "quantity": 5,
                }),
                _operation("transfer-2", "INVENTORY_TRANSFER", {
                    "source_location_id": location.id,
                    "destination_location_id": destination.id,
                    "lines": [{"product_id": product.id, "quantity": 2}],
                    "reason": "TRANSFER",
                }),
                _operation("adjustment-2", "INVENTORY_ADJUSTMENT", {
                    "product_id": product.id,
                    "location_id": location.id,
                    "quantity": 1,
                    "reason": "ADJUSTMENT",
                }),
            ),
        )

        assert response.status_code == 200
        assert [ack["status"] for ack in response.json()["acknowledgements"]] == [
            "APPLIED",
            "APPLIED",
            "APPLIED",
        ]
        assert InventoryService.compute_stock_at_location(
            org.id, product.id, location.id, db
        ) == 4
        assert InventoryService.compute_stock_at_location(
            org.id, product.id, destination.id, db
        ) == 2
        assert db.query(InventoryTransfer).filter_by(
            device_id="device-1",
            device_local_id="transfer-2",
        ).count() == 1
        transfer = db.query(InventoryTransfer).filter_by(
            device_id="device-1",
            device_local_id="transfer-2",
        ).one()
        assert db.query(InventoryMovement).filter_by(
            reference_type="TRANSFER",
            reference_id=transfer.id,
        ).count() == 1

    def test_operator_cannot_transfer_stock_through_offline_sync(
        self, client: TestClient, db, org, product, location
    ):
        destination = type(location)(
            organization_id=org.id,
            code="LOC002",
            name="Second Store",
            is_active=True,
        )
        db.add(destination)
        db.commit()

        response = client.post(
            "/api/v1/sync/batch",
            json=_request(
                org.id,
                _operation("operator-transfer-1", "INVENTORY_TRANSFER", {
                    "source_location_id": location.id,
                    "destination_location_id": destination.id,
                    "lines": [{"product_id": product.id, "quantity": 2}],
                    "reason": "TRANSFER",
                }),
            ),
        )

        acknowledgement = response.json()["acknowledgements"][0]
        assert response.status_code == 200
        assert acknowledgement["status"] == "TERMINAL_FAILURE"
        assert acknowledgement["error_code"] == "FORBIDDEN_OPERATION"
        assert db.query(InventoryTransfer).count() == 0
        assert db.query(InventoryMovement).count() == 0

    def test_offline_count_is_saved_as_draft_without_posting_stock(
        self, client: TestClient, db, org, product, location
    ):
        response = client.post(
            "/api/v1/sync/batch",
            json=_request(
                org.id,
                _operation("count-1", "INVENTORY_COUNT", {
                    "location_id": location.id,
                    "lines": [{"product_id": product.id, "observed_quantity": 7}],
                    "notes": "Offline physical count",
                }),
            ),
        )

        acknowledgement = response.json()["acknowledgements"][0]
        assert response.status_code == 200
        assert acknowledgement["status"] == "RECONCILIATION_REQUIRED"
        count = db.query(InventoryCount).filter_by(id=int(acknowledgement["applied_entity_id"])).one()
        assert count.status == "DRAFT"
        assert count.lines[0].observed_quantity == 7
        assert db.query(InventoryMovement).count() == 0

    def test_offline_sale_commit_uses_authenticated_actor_and_is_idempotent(
        self, client: TestClient, db, org, user, till, product, open_pos_session
    ):
        session = open_pos_session(user)
        sale = SaleService.create_sale(
            organization_id=org.id,
            till_id=till.id,
            cashier_id=user.id,
            payment_method="CASH",
            amount_tendered="20.00",
            till_session_id=session.id,
            items=[{"product_id": product.id, "quantity": 2, "unit_price": 10}],
            offline_device_id="device-1",
            db=db,
        )
        request = _request(
            org.id,
            _operation("sale-commit-1", "SALE_COMMIT", {
                "sale_id": sale.id,
                "user_id": user.id + 1000,
            }),
        )

        first = client.post("/api/v1/sync/batch", json=request)
        second = client.post("/api/v1/sync/batch", json=request)

        assert first.status_code == second.status_code == 200
        assert first.json()["acknowledgements"][0]["status"] == "APPLIED"
        assert second.json()["acknowledgements"][0] == first.json()["acknowledgements"][0]
        db.refresh(sale)
        assert sale.status == "COMPLETED"
        movements = db.query(InventoryMovement).filter_by(
            reference_type="SALE",
            reference_id=sale.id,
        ).all()
        assert len(movements) == 1
        assert movements[0].recorded_by_id == user.id
        assert db.query(Payment).filter_by(sale_id=sale.id).count() == 1
        assert db.query(ReceiptAudit).filter_by(sale_id=sale.id).count() == 1

    def test_offline_sale_commit_requires_its_open_owned_session(
        self, client: TestClient, db, org, user, till, product, open_pos_session
    ):
        session = open_pos_session(user)
        sale = SaleService.create_sale(
            organization_id=org.id,
            till_id=till.id,
            cashier_id=user.id,
            payment_method="CASH",
            amount_tendered="10.00",
            till_session_id=session.id,
            items=[{"product_id": product.id, "quantity": 1}],
            offline_device_id="device-1",
            db=db,
        )
        session.status = "CLOSED"
        db.commit()
        response = client.post(
            "/api/v1/sync/batch",
            json=_request(
                org.id,
                _operation("sale-closed-session", "SALE_COMMIT", {"sale_id": sale.id}),
            ),
        )

        assert response.status_code == 200
        acknowledgement = response.json()["acknowledgements"][0]
        assert acknowledgement["status"] == "TERMINAL_FAILURE"
        assert acknowledgement["error_code"] == "INVALID_OPERATION"
        db.refresh(sale)
        assert sale.status == "PENDING"
        assert db.query(InventoryMovement).filter_by(
            reference_type="SALE", reference_id=sale.id
        ).count() == 0

    def test_offline_sale_commit_rejects_a_foreign_session_operator(
        self, client: TestClient, db, org, till, product, open_pos_session
    ):
        from src.models.entities import User

        other_user = User(
            organization_id=org.id,
            email="other-cashier@test.com",
            username="other-cashier",
            full_name="Other Cashier",
            password_hash="unused",
            role="operator",
        )
        db.add(other_user)
        db.commit()
        session = open_pos_session(other_user)
        sale = SaleService.create_sale(
            organization_id=org.id,
            till_id=till.id,
            cashier_id=other_user.id,
            payment_method="CASH",
            amount_tendered="10.00",
            till_session_id=session.id,
            items=[{"product_id": product.id, "quantity": 1}],
            offline_device_id="device-other",
            db=db,
        )
        response = client.post(
            "/api/v1/sync/batch",
            json=_request(
                org.id,
                _operation("sale-other-operator", "SALE_COMMIT", {"sale_id": sale.id}),
            ),
        )

        assert response.status_code == 200
        assert response.json()["acknowledgements"][0]["status"] == "TERMINAL_FAILURE"
        db.refresh(sale)
        assert sale.status == "PENDING"
        assert db.query(InventoryMovement).filter_by(
            reference_type="SALE", reference_id=sale.id
        ).count() == 0

    def test_inventory_conflict_and_unsupported_return_are_explicit(
        self, client: TestClient, db, org, product, location
    ):
        response = client.post(
            "/api/v1/sync/batch",
            json=_request(
                org.id,
                _operation("issue-too-much", "INVENTORY_ISSUE", {
                    "product_id": product.id,
                    "location_id": location.id,
                    "quantity": 1,
                    "reason": "DAMAGE",
                }),
                _operation("return-1", "INVENTORY_RETURN", {"sale_id": 99}),
            ),
        )

        acknowledgements = response.json()["acknowledgements"]
        assert response.status_code == 200
        assert acknowledgements[0]["status"] == "RECONCILIATION_REQUIRED"
        assert acknowledgements[0]["error_code"] == "INVENTORY_CONFLICT"
        assert acknowledgements[1]["status"] == "TERMINAL_FAILURE"
        assert acknowledgements[1]["error_code"] == "UNSUPPORTED_OPERATION"
        assert db.query(OfflineOperation).filter_by(
            operation_id="return-1"
        ).one().status == "TERMINAL_FAILURE"

    def test_sale_commit_cannot_reference_another_organization(
        self, client: TestClient, db, org
    ):
        response = client.post(
            "/api/v1/sync/batch",
            json=_request(
                org.id,
                _operation("foreign-sale", "SALE_COMMIT", {"sale_id": 789}),
            ),
        )

        assert response.status_code == 200
        acknowledgement = response.json()["acknowledgements"][0]
        assert acknowledgement["status"] == "TERMINAL_FAILURE"
        assert acknowledgement["error_code"] == "ENTITY_NOT_FOUND"
        assert db.query(Sale).filter_by(id=789).count() == 0
