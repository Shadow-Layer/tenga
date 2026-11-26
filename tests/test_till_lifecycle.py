"""Isolated API tests for till administration and session lifecycle."""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # Ensure all shared tables are registered before create_all.
from src.database.config import Base, get_db
from src.main import app
from src.models.entities import (
    Employee,
    EmployeeTillAssignment,
    Location,
    Organization,
    PaymentAttempt,
    Sale,
    Till,
    TillSession,
    User,
)
from src.models import entities as entity_models
from src.security.authorization import get_current_user


@pytest.fixture
def world():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)
    db = test_session()
    organization = Organization(name="Lifecycle Org", code="LIFECYCLE", currency_code="USD")
    db.add(organization)
    db.flush()
    location = Location(
        organization_id=organization.id,
        code="MAIN",
        name="Main",
        is_active=True,
    )
    db.add(location)
    db.flush()
    till = Till(
        organization_id=organization.id,
        location_id=location.id,
        code="TILL-1",
        name="Front",
        is_active=True,
    )
    db.add(till)
    db.commit()

    def add_user(username, role="operator", org=organization, active=True):
        user = User(
            organization_id=org.id,
            email=f"{username}@example.test",
            username=username,
            full_name=username,
            password_hash="not-used",
            role=role,
            is_active=active,
        )
        db.add(user)
        db.flush()
        return user

    def add_employee(user, employee_number=None, org=organization, active=True):
        employee = Employee(
            organization_id=org.id,
            user_id=user.id,
            employee_number=employee_number or user.username,
            full_name=user.full_name,
            is_active=active,
        )
        db.add(employee)
        db.commit()
        return employee

    def assign(employee, assigned_till=till):
        db.add(EmployeeTillAssignment(employee_id=employee.id, till_id=assigned_till.id))
        db.commit()

    def client(actor=None):
        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        if actor is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = lambda: actor
        return TestClient(app)

    yield {
        "db": db,
        "org": organization,
        "location": location,
        "till": till,
        "add_user": add_user,
        "add_employee": add_employee,
        "assign": assign,
        "client": client,
    }
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def assigned_user(world, username="cashier", role="operator"):
    user = world["add_user"](username, role)
    employee = world["add_employee"](user)
    world["assign"](employee)
    return user, employee


def open_session(client, till_id, opening_balance="0.00", **extra):
    return client.post(
        f"/api/v1/tills/{till_id}/open",
        json={"opening_balance": opening_balance, **extra},
    )


def close_session(client, till_id, closing_balance="0.00", **extra):
    status = client.get(f"/api/v1/tills/{till_id}/status").json()
    return client.post(
        f"/api/v1/tills/{till_id}/close",
        json={
            "session_id": status["session_id"],
            "closing_balance": closing_balance,
            **extra,
        },
    )


def add_sale(db, org, till, user, session, amount="10.00"):
    sale = Sale(
        organization_id=org.id,
        till_id=till.id,
        till_session_id=session.id,
        cashier_id=user.id,
        total_amount=Decimal(amount),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        amount_tendered=Decimal(amount),
        change_given=Decimal("0.00"),
        payment_method="CASH",
        status="COMPLETED",
        currency_code="USD",
    )
    db.add(sale)
    db.commit()
    return sale


def add_attempt(db, org, till, user, session, status_value):
    sale = Sale(
        organization_id=org.id,
        till_id=till.id,
        till_session_id=session.id,
        cashier_id=user.id,
        total_amount=Decimal("10.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        amount_tendered=Decimal("0.00"),
        change_given=Decimal("0.00"),
        payment_method="PAYNOW",
        status="PENDING",
        currency_code="USD",
    )
    db.add(sale)
    db.flush()
    attempt = PaymentAttempt(
        organization_id=org.id,
        sale_id=sale.id,
        till_session_id=session.id,
        initiated_by_id=user.id,
        provider="PAYNOW",
        payment_method="MOBILE",
        merchant_reference=f"merchant-{session.id}-{status_value}",
        amount=Decimal("10.00"),
        currency_code="USD",
        status=status_value,
    )
    db.add(attempt)
    db.commit()
    return attempt


def test_admin_till_lifecycle_assignments_and_tenant_checks(world):
    admin = world["add_user"]("admin", "admin")
    other_org = Organization(name="Other Org", code="OTHER", currency_code="USD")
    world["db"].add(other_org)
    world["db"].commit()
    foreign_location = Location(
        organization_id=other_org.id,
        code="FOREIGN",
        name="Foreign",
        is_active=True,
    )
    world["db"].add(foreign_location)
    world["db"].commit()
    client = world["client"](admin)

    assert client.post(
        "/api/v1/tills/",
        json={"location_id": foreign_location.id, "code": "BAD", "name": "Bad"},
    ).status_code == 404
    created = client.post(
        "/api/v1/tills/",
        json={"location_id": world["location"].id, "code": "TILL-2", "name": "Back"},
    )
    assert created.status_code == 201
    till_id = created.json()["id"]
    employee_user = world["add_user"]("assigned")
    employee = world["add_employee"](employee_user)
    assigned = client.put(
        f"/api/v1/tills/{till_id}/assignments",
        json={"employee_ids": [employee.id]},
    )
    assert assigned.status_code == 200
    assert assigned.json()["employee_ids"] == [employee.id]
    assert client.get(f"/api/v1/tills/{till_id}/assignments").json()["employee_ids"] == [
        employee.id
    ]
    assert client.patch(
        f"/api/v1/tills/{till_id}",
        json={"name": "Rear"},
    ).json()["name"] == "Rear"
    assert client.get(f"/api/v1/tills/{till_id}").status_code == 200
    assert client.post(f"/api/v1/tills/{till_id}/deactivate").json()["is_active"] is False
    assert client.get(f"/api/v1/tills/{till_id}").status_code == 200
    assert client.get(f"/api/v1/tills/{till_id}/open").status_code == 405
    assert client.put(
        f"/api/v1/tills/{till_id}/assignments",
        json={"employee_ids": [999999]},
    ).status_code == 422
    assert client.get(f"/api/v1/tills/{till_id + 9999}").status_code == 404


def test_assignment_history_is_retained_and_only_active_assignments_are_listed(world):
    admin = world["add_user"]("assignment-admin", "admin")
    employee_user = world["add_user"]("history-employee")
    employee = world["add_employee"](employee_user)
    admin_client = world["client"](admin)
    endpoint = f"/api/v1/tills/{world['till'].id}/assignments"

    assert admin_client.put(endpoint, json={"employee_ids": [employee.id]}).status_code == 200
    first = world["db"].query(EmployeeTillAssignment).filter_by(
        employee_id=employee.id, till_id=world["till"].id
    ).one()
    first_id = first.id
    assert first.ended_at is None

    assert admin_client.put(endpoint, json={"employee_ids": []}).status_code == 200
    world["db"].refresh(first)
    assert first.ended_at is not None
    assert admin_client.get(endpoint).json()["employee_ids"] == []

    assert admin_client.put(endpoint, json={"employee_ids": [employee.id]}).status_code == 200
    active_rows = world["db"].query(EmployeeTillAssignment).filter_by(
        employee_id=employee.id, till_id=world["till"].id, ended_at=None
    ).all()
    assert len(active_rows) == 1
    assert active_rows[0].id != first_id
    assert admin_client.get(endpoint).json()["employee_ids"] == [employee.id]
    assert world["db"].query(EmployeeTillAssignment).filter_by(
        employee_id=employee.id, till_id=world["till"].id
    ).count() == 2


def test_open_close_snapshots_expected_cash_and_variance(world):
    user, _ = assigned_user(world)
    client = world["client"](user)
    opened = open_session(client, world["till"].id, "25.00")
    assert opened.status_code == 201, opened.text
    body = opened.json()
    assert body["currency_code"] == "USD"
    session = world["db"].get(TillSession, body["session_id"])
    add_sale(world["db"], world["org"], world["till"], user, session)

    closed = close_session(client, world["till"].id, "33.00")
    assert closed.status_code == 200, closed.text
    data = closed.json()
    assert Decimal(str(data["expected_closing_balance"])) == Decimal("35.00")
    assert Decimal(str(data["cash_variance"])) == Decimal("-2.00")
    assert data["currency_code"] == "USD"
    assert world["db"].get(TillSession, session.id).closed_by_id == user.id


def test_stale_close_request_cannot_close_a_newer_session(world):
    user, _ = assigned_user(world)
    client = world["client"](user)
    first_open = open_session(client, world["till"].id)
    first_session_id = first_open.json()["session_id"]
    assert close_session(client, world["till"].id).status_code == 200

    second_open = open_session(client, world["till"].id)
    second_session_id = second_open.json()["session_id"]
    stale_close = close_session(
        client,
        world["till"].id,
        session_id=first_session_id,
    )

    assert stale_close.status_code == 409
    status = client.get(f"/api/v1/tills/{world['till'].id}/status").json()
    assert status["is_open"] is True
    assert status["session_id"] == second_session_id


def test_currency_snapshot_survives_org_change_and_currencyless_legacy_sale_blocks(world):
    user, _ = assigned_user(world)
    client = world["client"](user)
    opened = open_session(client, world["till"].id)
    session = world["db"].get(TillSession, opened.json()["session_id"])
    world["org"].currency_code = "EUR"
    world["db"].commit()
    closed = close_session(client, world["till"].id)
    assert closed.status_code == 200
    assert closed.json()["currency_code"] == "USD"

    world["org"].currency_code = "USD"
    world["db"].commit()
    opened = open_session(client, world["till"].id)
    session = world["db"].get(TillSession, opened.json()["session_id"])
    sale = add_sale(world["db"], world["org"], world["till"], user, session)
    sale.currency_code = None
    world["db"].commit()
    blocked = close_session(client, world["till"].id)
    assert blocked.status_code == 409
    assert "currency snapshot" in blocked.json()["detail"].lower()


def test_unlinked_cash_sale_blocks_silent_understatement(world):
    user, _ = assigned_user(world)
    client = world["client"](user)
    opened = open_session(client, world["till"].id)
    sale = Sale(
        organization_id=world["org"].id,
        till_id=world["till"].id,
        till_session_id=None,
        cashier_id=user.id,
        total_amount=Decimal("10.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        amount_tendered=Decimal("10.00"),
        change_given=Decimal("0.00"),
        payment_method="CASH",
        status="COMPLETED",
        currency_code="USD",
    )
    world["db"].add(sale)
    world["db"].commit()
    blocked = close_session(client, world["till"].id, "10.00")
    assert blocked.status_code == 409
    assert "not linked" in blocked.json()["detail"].lower()
    session = world["db"].get(TillSession, opened.json()["session_id"])
    assert session.status == "OPEN"


def test_assignment_required_inactive_actor_and_client_actor_id_rejected(world):
    unassigned = world["add_user"]("unassigned")
    assert open_session(world["client"](unassigned), world["till"].id).status_code == 403

    inactive, employee = assigned_user(world, "inactive")
    inactive.is_active = False
    world["db"].commit()
    assert open_session(world["client"](inactive), world["till"].id).status_code == 403

    inactive_employee_user, inactive_employee = assigned_user(
        world, "inactive-employee"
    )
    inactive_employee.is_active = False
    world["db"].commit()
    assert open_session(
        world["client"](inactive_employee_user), world["till"].id
    ).status_code == 403

    active, _ = assigned_user(world, "active")
    response = open_session(
        world["client"](active),
        world["till"].id,
        user_id=active.id + 100,
    )
    assert response.status_code == 422
    assert open_session(world["client"](active), world["till"].id).status_code == 201


def test_duplicate_open_wrong_owner_and_manager_override(world):
    operator, _ = assigned_user(world, "operator")
    other_operator, _ = assigned_user(world, "other")
    manager, _ = assigned_user(world, "manager", "manager")
    admin = world["add_user"]("admin", "admin")
    operator_employee = operator.employee
    manager_employee = manager.employee
    opened = open_session(world["client"](operator), world["till"].id)
    assert opened.status_code == 201
    assert open_session(world["client"](operator), world["till"].id).status_code == 409
    assert close_session(world["client"](other_operator), world["till"].id).status_code == 403
    assignment_change = world["client"](admin).put(
        f"/api/v1/tills/{world['till'].id}/assignments",
        json={"employee_ids": [manager_employee.id]},
    )
    assert assignment_change.status_code == 409
    assert operator_employee.id in world["client"](admin).get(
        f"/api/v1/tills/{world['till'].id}/assignments"
    ).json()["employee_ids"]
    unassigned_manager = world["add_user"]("unassigned-manager", "manager")
    assert close_session(
        world["client"](unassigned_manager), world["till"].id
    ).status_code == 200


def test_unresolved_paynow_blocks_close_but_terminal_attempts_do_not(world):
    operator, _ = assigned_user(world)
    client = world["client"](operator)
    for status_value in ("PENDING", "UNCERTAIN"):
        opened = open_session(client, world["till"].id)
        assert opened.status_code == 201
        session = world["db"].get(TillSession, opened.json()["session_id"])
        add_attempt(
            world["db"], world["org"], world["till"], operator, session, status_value
        )
        blocked = close_session(client, world["till"].id)
        assert blocked.status_code == 409
        assert "unresolved" in blocked.json()["detail"].lower()
        attempt = world["db"].query(PaymentAttempt).filter_by(
            till_session_id=session.id
        ).one()
        attempt.status = "FAILED"
        world["db"].commit()
        assert close_session(client, world["till"].id).status_code == 200

    for status_value in ("SETTLED", "FAILED"):
        opened = open_session(client, world["till"].id)
        session = world["db"].get(TillSession, opened.json()["session_id"])
        add_attempt(
            world["db"], world["org"], world["till"], operator, session, status_value
        )
        assert close_session(client, world["till"].id).status_code == 200


def test_tenant_safe_history_and_currencyless_organization(world):
    operator, _ = assigned_user(world)
    client = world["client"](operator)
    opened = open_session(client, world["till"].id, "4.00")
    assert opened.status_code == 201
    assert client.get(f"/api/v1/tills/{world['till'].id}/sessions").status_code == 200

    foreign_org = Organization(name="Currencyless", code="NO-CURRENCY", currency_code=None)
    world["db"].add(foreign_org)
    world["db"].flush()
    foreign_org.currency_code = None
    foreign_user = User(
        organization_id=foreign_org.id,
        email="foreign@example.test",
        username="foreign",
        full_name="Foreign User",
        password_hash="unused",
        role="operator",
        is_active=True,
    )
    world["db"].add(foreign_user)
    world["db"].flush()
    foreign_location = Location(
        organization_id=foreign_org.id,
        code="F",
        name="Foreign",
        is_active=True,
    )
    world["db"].add(foreign_location)
    world["db"].flush()
    foreign_till = Till(
        organization_id=foreign_org.id,
        location_id=foreign_location.id,
        code="F-TILL",
        name="Foreign",
        is_active=True,
    )
    world["db"].add(foreign_till)
    world["db"].commit()
    foreign_employee = world["add_employee"](
        foreign_user, "foreign-employee", org=foreign_org
    )
    world["assign"](foreign_employee, foreign_till)
    assert client.get(f"/api/v1/tills/{foreign_till.id}").status_code == 404

    # Create a separate currencyless tenant user and verify monetary opening is rejected.
    currencyless = world["client"](foreign_user)
    response = open_session(currencyless, foreign_till.id)
    assert response.status_code == 409
    assert "currency" in response.json()["detail"].lower()


def test_unauthenticated_api_access_is_rejected(world):
    response = world["client"]().get("/api/v1/tills/")
    assert response.status_code in (401, 403)


@pytest.mark.skipif(
    not hasattr(entity_models, "TillCashMovement"),
    reason="TillCashMovement is being added by the shared-schema migration",
)
def test_cash_movement_idempotency_and_close_reconciliation(world):
    user, _ = assigned_user(world)
    other_user, _ = assigned_user(world, "cash-movement-other")
    manager, _ = assigned_user(world, "cash-movement-manager", "manager")
    client = world["client"](user)
    opened = open_session(client, world["till"].id, "4.00")
    assert opened.status_code == 201
    url = f"/api/v1/tills/{world['till'].id}/cash-movements"
    unauthorized = world["client"](other_user).post(
        url,
        json={
            "operation_id": "wrong-owner-cash",
            "movement_type": "CASH_IN",
            "amount": "1.00",
            "reason": "Unauthorized",
        },
    )
    assert unauthorized.status_code == 403
    client = world["client"](user)
    payload = {
        "operation_id": "cash-in-operation-001",
        "movement_type": "CASH_IN",
        "amount": "20.00",
        "reason": "Float correction",
        "reference": "REF-1",
    }
    created = client.post(url, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["currency_code"] == "USD"
    replay = client.post(url, json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == created.json()["id"]

    mismatch = dict(payload, amount="21.00")
    assert client.post(url, json=mismatch).status_code == 409
    manager_movement = world["client"](manager).post(
        url,
        json={
            "operation_id": "manager-cash-in",
            "movement_type": "CASH_IN",
            "amount": "1.00",
            "reason": "Manager override",
        },
    )
    assert manager_movement.status_code == 201, manager_movement.text
    client = world["client"](user)
    cash_out = client.post(
        url,
        json={
            "operation_id": "cash-out-operation-001",
            "movement_type": "CASH_OUT",
            "amount": "5.00",
            "reason": "Petty cash",
            "reference": "REF-2",
        },
    )
    assert cash_out.status_code == 201, cash_out.text
    closed = close_session(client, world["till"].id, "16.00")
    assert closed.status_code == 200, closed.text
    assert Decimal(str(closed.json()["expected_closing_balance"])) == Decimal("20.00")
    assert Decimal(str(closed.json()["cash_variance"])) == Decimal("-4.00")
