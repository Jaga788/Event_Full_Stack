import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
from app.core.config import settings
from app.core.roles import UserRole
from app.main import app
from app.models.user import User


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", test_session_local)
    monkeypatch.setattr(
        settings,
        "JWT_SECRET_KEY",
        SecretStr("test-jwt-secret-key-that-is-at-least-32-bytes"),
    )

    with TestClient(app) as test_client:
        yield test_client

    engine.dispose()


def test_user_crud(client: TestClient) -> None:
    created = client.post(
        "/users",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "safe-password-123",
        },
    )
    assert created.status_code == 201
    user = created.json()
    assert user["email"] == "test@example.com"
    assert user["role"] == "customer"
    assert "hashed_password" not in user

    login = client.post(
        "/auth/token",
        data={"username": "test@example.com", "password": "safe-password-123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get("/users").status_code == 401
    assert client.get("/users", headers=headers).status_code == 403

    with database.SessionLocal() as db:
        db_user = db.get(User, user["id"])
        assert db_user is not None
        db_user.role = UserRole.ADMIN
        db.commit()

    listed = client.get("/users", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [user["id"]]

    updated = client.put(
        f"/users/{user['id']}",
        json={
            "full_name": "Updated User",
            "email": "updated@example.com",
            "password": "new-safe-password-456",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated User"
    assert updated.json()["email"] == "updated@example.com"

    fetched = client.get(f"/users/{user['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["email"] == "updated@example.com"

    deleted = client.delete(f"/users/{user['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/users/{user['id']}", headers=headers).status_code == 401


def test_duplicate_user_email_returns_conflict(client: TestClient) -> None:
    user_data = {
        "full_name": "Test User",
        "email": "duplicate@example.com",
        "password": "safe-password-123",
    }
    assert client.post("/users", json=user_data).status_code == 201

    duplicate = client.post("/users", json=user_data)
    assert duplicate.status_code == 409


def test_public_user_creation_cannot_assign_privileged_role(client: TestClient) -> None:
    response = client.post(
        "/users",
        json={
            "full_name": "Admin User",
            "email": "admin@example.com",
            "password": "safe-password-123",
            "role": "admin",
        },
    )

    assert response.status_code == 422


def test_password_is_hashed_in_database(client: TestClient) -> None:
    client.post(
        "/users",
        json={
            "full_name": "Test User",
            "email": "hashed@example.com",
            "password": "safe-password-123",
        },
    )
    with database.SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "hashed@example.com"))

    assert user is not None
    assert user.hashed_password != "safe-password-123"
