"""Concurrency coverage for one-time installation bootstrap."""
from concurrent.futures import ThreadPoolExecutor
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.config as app_config
from src.database.config import Base, get_db
from src.main import app


def test_concurrent_bootstrap_creates_only_one_organization_and_owner(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="tenga-bootstrap-") as directory:
        engine = create_engine(
            f"sqlite:///{Path(directory) / 'bootstrap.db'}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        sessions = sessionmaker(bind=engine)
        secret = "concurrent-bootstrap-test-secret-" + "x" * 32
        monkeypatch.setattr(app_config, "INITIAL_SETUP_SECRET", secret)

        def override_get_db():
            with sessions() as session:
                yield session

        previous_override = app.dependency_overrides.get(get_db)
        app.dependency_overrides[get_db] = override_get_db
        payload = {
            "organization": {"name": "Concurrent Setup", "code": "CONCURRENT"},
            "owner": {
                "username": "owner",
                "email": "owner@example.test",
                "password": "secure-owner-password",
            },
        }

        try:
            with TestClient(app) as client:
                def bootstrap():
                    return client.post(
                        "/api/v1/organizations/bootstrap",
                        json=payload,
                        headers={"X-Setup-Secret": secret},
                    ).status_code

                with ThreadPoolExecutor(max_workers=2) as executor:
                    statuses = list(executor.map(lambda _: bootstrap(), range(2)))

            assert sorted(statuses) == [201, 409]
            with sessions() as verify:
                from src.models.entities import Organization, User

                assert verify.query(Organization).count() == 1
                assert verify.query(User).count() == 1
        finally:
            if previous_override is None:
                app.dependency_overrides.pop(get_db, None)
            else:
                app.dependency_overrides[get_db] = previous_override
            engine.dispose()
