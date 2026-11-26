"""Isolated API tests for tenant-scoped employee administration."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.config import Base, get_db
from src.models.entities import (
    Employee,
    EmployeeLocationAssignment,
    EmployeeTillAssignment,
    Location,
    Organization,
    Till,
    User,
)
from src.routers.employees import router
from src.security.auth import create_access_token


@pytest.fixture
def employee_api():
    """Create an independent in-memory database and employee-only API app."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = session_factory()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/organizations")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    organization = Organization(name="Employee Org", code="EMP")
    db.add(organization)
    db.flush()
    admin = User(
        organization_id=organization.id,
        email="admin@employee.test",
        username="admin",
        password_hash="not-used",
        role="admin",
    )
    db.add(admin)
    db.commit()
    client.headers["Authorization"] = "Bearer " + create_access_token(
        user_id=admin.id,
        email=admin.email,
        organization_id=organization.id,
        username=admin.username,
        role=admin.role,
    )

    yield {
        "app": app,
        "client": client,
        "db": db,
        "org": organization,
        "admin": admin,
    }

    app.dependency_overrides.clear()
    client.close()
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _employee_url(org_id: int, employee_id: int | None = None) -> str:
    base = f"/api/v1/organizations/{org_id}/employees"
    return base if employee_id is None else f"{base}/{employee_id}"


def _make_location(db, org_id: int, code: str = "LOC") -> Location:
    location = Location(
        organization_id=org_id,
        code=code,
        name=f"Location {code}",
        is_active=True,
    )
    db.add(location)
    db.commit()
    return location


def _make_till(db, org_id: int, location_id: int, code: str = "TILL") -> Till:
    till = Till(
        organization_id=org_id,
        location_id=location_id,
        code=code,
        name=f"Till {code}",
        is_active=True,
    )
    db.add(till)
    db.commit()
    return till


def _make_user(db, org_id: int, username: str = "staff", role: str = "operator") -> User:
    user = User(
        organization_id=org_id,
        email=f"{username}@employee.test",
        username=username,
        password_hash="not-used",
        role=role,
    )
    db.add(user)
    db.commit()
    return user


def _auth_for(client: TestClient, user: User) -> dict[str, str]:
    return {
        "Authorization": "Bearer " + create_access_token(
            user_id=user.id,
            email=user.email,
            organization_id=user.organization_id,
            username=user.username,
            role=user.role,
        )
    }


def test_employee_can_exist_without_login_and_requires_admin_or_manager(employee_api):
    client, db, org = (
        employee_api["client"],
        employee_api["db"],
        employee_api["org"],
    )
    url = _employee_url(org.id)
    admin_user_count = db.query(User).count()

    anonymous = TestClient(employee_api["app"])
    assert anonymous.get(url).status_code == 401
    anonymous.close()

    operator = _make_user(db, org.id, "operator")
    response = client.post(
        url,
        headers=_auth_for(client, operator),
        json={"employee_number": "E-001", "full_name": "No Login Employee"},
    )
    assert response.status_code == 403

    response = client.post(
        url,
        json={
            "employee_number": "E-001",
            "full_name": "No Login Employee",
            "email": "employee@example.test",
        },
    )
    assert response.status_code == 201
    assert response.json()["user_id"] is None
    assert response.json()["full_name"] == "No Login Employee"
    assert db.query(Employee).count() == 1
    assert db.query(User).count() == admin_user_count + 1
    employee_id = response.json()["id"]
    assert client.get(url, headers=_auth_for(client, operator)).status_code == 200
    assert client.patch(
        _employee_url(org.id, employee_id),
        headers=_auth_for(client, operator),
        json={"full_name": "Unauthorized"},
    ).status_code == 403
    assert client.post(
        _employee_url(org.id, employee_id) + "/deactivate",
        headers=_auth_for(client, operator),
    ).status_code == 403
    assert client.post(
        _employee_url(org.id, employee_id) + "/archive",
        headers=_auth_for(client, operator),
    ).status_code == 403


def test_duplicate_employee_number_and_user_link_return_conflict(employee_api):
    client, db, org = (
        employee_api["client"],
        employee_api["db"],
        employee_api["org"],
    )
    first_user = _make_user(db, org.id, "first")
    second_user = _make_user(db, org.id, "second")
    url = _employee_url(org.id)

    created = client.post(
        url,
        json={
            "employee_number": "E-100",
            "full_name": "Linked Employee",
            "user_id": first_user.id,
        },
    )
    assert created.status_code == 201
    assert created.json()["user_id"] == first_user.id

    duplicate_link = client.post(
        url,
        json={
            "employee_number": "E-101",
            "full_name": "Duplicate Link",
            "user_id": first_user.id,
        },
    )
    assert duplicate_link.status_code == 409
    assert db.query(Employee).count() == 1

    duplicate_number = client.post(
        url,
        json={
            "employee_number": "E-100",
            "full_name": "Duplicate Number",
            "user_id": second_user.id,
        },
    )
    assert duplicate_number.status_code == 409
    assert db.query(Employee).count() == 1
    assert db.query(User).filter(User.id == first_user.id).one()


def test_cross_tenant_employee_user_and_assignment_ids_are_hidden(employee_api):
    client, db, org = (
        employee_api["client"],
        employee_api["db"],
        employee_api["org"],
    )
    other_org = Organization(name="Other Employee Org", code="OTHER")
    db.add(other_org)
    db.flush()
    foreign_user = _make_user(db, other_org.id, "foreign")
    foreign_location = _make_location(db, other_org.id, "FOREIGN")
    foreign_till = _make_till(db, other_org.id, foreign_location.id, "FOREIGN")
    foreign_employee = Employee(
        organization_id=other_org.id,
        employee_number="OTHER-1",
        full_name="Foreign Employee",
    )
    db.add(foreign_employee)
    db.commit()

    assert client.get(_employee_url(org.id, foreign_employee.id)).status_code == 404
    assert client.get(_employee_url(other_org.id)).status_code == 404
    assert client.patch(
        _employee_url(org.id, foreign_employee.id),
        json={"full_name": "Attempted Change"},
    ).status_code == 404
    assert client.post(
        _employee_url(org.id, foreign_employee.id) + "/deactivate"
    ).status_code == 404
    assert client.post(
        _employee_url(org.id, foreign_employee.id) + "/archive"
    ).status_code == 404

    bad_user = client.post(
        _employee_url(org.id),
        json={
            "employee_number": "E-201",
            "full_name": "Foreign User",
            "user_id": foreign_user.id,
        },
    )
    assert bad_user.status_code == 404
    for assignments in (
        {"location_ids": [foreign_location.id]},
        {"till_ids": [foreign_till.id]},
    ):
        response = client.post(
            _employee_url(org.id),
            json={
                "employee_number": f"E-{300 + len(assignments)}",
                "full_name": "Foreign Assignment",
                **assignments,
            },
        )
        assert response.status_code == 404
    assert db.query(Employee).filter(Employee.organization_id == org.id).count() == 0


def test_invalid_assignment_ids_are_rejected(employee_api):
    client, org = employee_api["client"], employee_api["org"]
    response = client.post(
        _employee_url(org.id),
        json={
            "employee_number": "E-400",
            "full_name": "Invalid Assignment",
            "location_ids": [987654],
        },
    )
    assert response.status_code == 404

    response = client.post(
        _employee_url(org.id),
        json={
            "employee_number": "E-401",
            "full_name": "Invalid Till",
            "till_ids": [987654],
        },
    )
    assert response.status_code == 404


def test_list_update_deactivate_archive_preserve_employee_and_assignments(employee_api):
    client, db, org = (
        employee_api["client"],
        employee_api["db"],
        employee_api["org"],
    )
    first_location = _make_location(db, org.id, "ONE")
    second_location = _make_location(db, org.id, "TWO")
    till = _make_till(db, org.id, second_location.id)
    url = _employee_url(org.id)

    created = client.post(
        url,
        json={
            "employee_number": "E-500",
            "full_name": "Original Name",
            "location_ids": [first_location.id],
        },
    )
    assert created.status_code == 201
    employee_id = created.json()["id"]
    assert created.json()["location_ids"] == [first_location.id]
    assert client.get(_employee_url(org.id, employee_id)).status_code == 200
    assert client.get(url).json()["total"] == 1
    for field in ("employee_number", "full_name"):
        invalid_update = client.patch(
            _employee_url(org.id, employee_id),
            json={field: None},
        )
        assert invalid_update.status_code == 422
    for field in ("location_ids", "till_ids"):
        invalid_assignments = client.patch(
            _employee_url(org.id, employee_id),
            json={field: None},
        )
        assert invalid_assignments.status_code == 422
        invalid_create = client.post(
            url,
            json={
                "employee_number": f"E-501-{field}",
                "full_name": "Null Assignment",
                field: None,
            },
        )
        assert invalid_create.status_code == 422

    unchanged = client.patch(
        _employee_url(org.id, employee_id),
        json={"title": "No Assignment Change"},
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["location_ids"] == [first_location.id]
    assert unchanged.json()["till_ids"] == []

    updated = client.patch(
        _employee_url(org.id, employee_id),
        json={
            "full_name": "Updated Name",
            "title": "Store Manager",
            "location_ids": [second_location.id],
            "till_ids": [till.id],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated Name"
    assert updated.json()["location_ids"] == [second_location.id]
    assert updated.json()["till_ids"] == [till.id]

    repeated_assignment = client.patch(
        _employee_url(org.id, employee_id),
        json={"location_ids": [second_location.id]},
    )
    assert repeated_assignment.status_code == 200
    assert repeated_assignment.json()["till_ids"] == [till.id]
    assert db.query(EmployeeLocationAssignment).filter(
        EmployeeLocationAssignment.employee_id == employee_id,
        EmployeeLocationAssignment.ended_at.is_(None),
    ).count() == 1
    assert db.query(EmployeeTillAssignment).filter(
        EmployeeTillAssignment.employee_id == employee_id,
        EmployeeTillAssignment.ended_at.is_(None),
    ).count() == 1

    removed = client.patch(
        _employee_url(org.id, employee_id),
        json={"location_ids": []},
    )
    assert removed.status_code == 200
    assert removed.json()["location_ids"] == []
    assert removed.json()["till_ids"] == [till.id]
    ended_location_assignment = db.query(EmployeeLocationAssignment).filter(
        EmployeeLocationAssignment.employee_id == employee_id,
        EmployeeLocationAssignment.location_id == second_location.id,
    ).one()
    assert ended_location_assignment.ended_at is not None

    reassigned = client.patch(
        _employee_url(org.id, employee_id),
        json={"location_ids": [second_location.id]},
    )
    assert reassigned.status_code == 200
    assert reassigned.json()["location_ids"] == [second_location.id]
    assert db.query(EmployeeLocationAssignment).filter(
        EmployeeLocationAssignment.employee_id == employee_id,
        EmployeeLocationAssignment.location_id == second_location.id,
    ).count() == 2

    deactivated = client.post(_employee_url(org.id, employee_id) + "/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert client.get(url + "?active=false").json()["total"] == 1

    archived = client.post(_employee_url(org.id, employee_id) + "/archive")
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert client.get(url).json()["total"] == 0
    assert client.get(url + "?include_archived=true").json()["total"] == 1
    assert client.patch(
        _employee_url(org.id, employee_id), json={"full_name": "Cannot Update"}
    ).status_code == 409

    db.expire_all()
    persisted = db.query(Employee).filter(Employee.id == employee_id).one()
    assert persisted.is_active is False
    assert persisted.archived_at is not None
    assert db.query(EmployeeLocationAssignment).filter(
        EmployeeLocationAssignment.employee_id == employee_id
    ).count() == 3
    assert db.query(EmployeeLocationAssignment).filter(
        EmployeeLocationAssignment.employee_id == employee_id,
        EmployeeLocationAssignment.ended_at.is_(None),
    ).count() == 0
    assert db.query(EmployeeTillAssignment).filter(
        EmployeeTillAssignment.employee_id == employee_id
    ).count() == 1
    assert db.query(EmployeeTillAssignment).filter(
        EmployeeTillAssignment.employee_id == employee_id,
        EmployeeTillAssignment.ended_at.is_(None),
    ).count() == 0


def test_manager_can_administer_and_archive_disables_linked_user(employee_api):
    client, db, org = (
        employee_api["client"],
        employee_api["db"],
        employee_api["org"],
    )
    manager = _make_user(db, org.id, "manager", role="manager")
    linked_user = _make_user(db, org.id, "employee_login")
    created = client.post(
        _employee_url(org.id),
        headers=_auth_for(client, manager),
        json={
            "employee_number": "E-600",
            "full_name": "Employee Login",
            "user_id": linked_user.id,
        },
    )
    assert created.status_code == 201
    employee_id = created.json()["id"]

    archived = client.post(
        _employee_url(org.id, employee_id) + "/archive",
        headers=_auth_for(client, manager),
    )
    assert archived.status_code == 200
    db.expire_all()
    assert db.query(User).filter(User.id == linked_user.id).one().is_active is False
    assert db.query(Employee).filter(Employee.id == employee_id).one().user_id == linked_user.id


def test_deactivate_disables_linked_user_and_ends_assignments(employee_api):
    client, db, org = (
        employee_api["client"],
        employee_api["db"],
        employee_api["org"],
    )
    location = _make_location(db, org.id, "DEACTIVATE")
    till = _make_till(db, org.id, location.id, "DEACTIVATE")
    linked_user = _make_user(db, org.id, "deactivated_login")
    response = client.post(
        _employee_url(org.id),
        json={
            "employee_number": "E-700",
            "full_name": "Deactivate Login",
            "user_id": linked_user.id,
            "location_ids": [location.id],
            "till_ids": [till.id],
        },
    )
    assert response.status_code == 201
    employee_id = response.json()["id"]

    deactivated = client.post(_employee_url(org.id, employee_id) + "/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["location_ids"] == []
    assert deactivated.json()["till_ids"] == []
    db.expire_all()
    assert db.query(User).filter(User.id == linked_user.id).one().is_active is False
    assert db.query(EmployeeLocationAssignment).filter(
        EmployeeLocationAssignment.employee_id == employee_id,
        EmployeeLocationAssignment.ended_at.is_not(None),
    ).count() == 1
    assert db.query(EmployeeTillAssignment).filter(
        EmployeeTillAssignment.employee_id == employee_id,
        EmployeeTillAssignment.ended_at.is_not(None),
    ).count() == 1
