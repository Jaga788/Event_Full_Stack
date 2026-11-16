from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
from app.core.config import settings
from app.core.roles import UserRole
from app.main import app
from app.models.user import User


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
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


def create_admin(client: TestClient) -> int:
    response = client.post(
        "/users",
        json={
            "full_name": "Package Admin",
            "email": "package-admin@example.com",
            "password": "safe-password-123",
        },
    )
    assert response.status_code == 201
    admin_id = response.json()["id"]

    with database.SessionLocal() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        admin.role = UserRole.ADMIN
        db.commit()
    return admin_id


def login_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/token",
        data={
            "username": "package-admin@example.com",
            "password": "safe-password-123",
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_package_crud_matches_catalog_fields(client: TestClient) -> None:
    create_admin(client)
    headers = login_headers(client)
    wedding = next(
        category
        for category in client.get("/categories?kind=event").json()
        if category["name"] == "Wedding"
    )
    package_data = {
        "title": "Silver Wedding Package",
        "description": "A simple elegant wedding, handled by one team.",
        "organizer_id": None,
        "event_category_ids": [wedding["id"]],
        "price": "150000.00",
        "price_unit": "per_event",
        "image_url": "https://example.com/silver-wedding.jpg",
        "badge": "Best Value",
        "max_guests": 200,
        "included_items": [
            "Stage & mandap decoration",
            "Floral entrance gate",
            "1 photographer",
            "Sound system & MC",
            "On-day event coordinator",
        ],
        "average_rating": 4.7,
        "review_count": 33,
    }

    created = client.post("/packages", json=package_data, headers=headers)
    assert created.status_code == 201, created.text
    package = created.json()
    assert package["title"] == "Silver Wedding Package"
    assert package["price_unit"] == "per_event"
    assert package["badge"] == "Best Value"
    assert package["max_guests"] == 200
    assert package["included_items"] == package_data["included_items"]
    assert package["average_rating"] == 4.7
    assert package["review_count"] == 33
    assert package["event_category_ids"] == [wedding["id"]]

    filtered = client.get(f"/packages?event_category_id={wedding['id']}")
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [package["id"]]

    fetched = client.get(f"/packages/{package['id']}")
    assert fetched.status_code == 200

    updated_data = {
        **package_data,
        "title": "Gold Wedding Package",
        "price": "350000.00",
        "badge": "Most Popular",
        "is_active": True,
    }
    updated = client.put(
        f"/packages/{package['id']}", json=updated_data, headers=headers
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Gold Wedding Package"
    assert updated.json()["price"] == "350000.00"

    deleted = client.delete(
        f"/packages/{package['id']}", headers=headers
    )
    assert deleted.status_code == 204
    assert client.get(f"/packages/{package['id']}").status_code == 404


def test_admin_package_rejects_customer_as_legacy_owner(client: TestClient) -> None:
    customer_response = client.post(
        "/users",
        json={
            "full_name": "Customer",
            "email": "customer-package@example.com",
            "password": "safe-password-123",
        },
    )
    assert customer_response.status_code == 201
    create_admin(client)
    admin_token = client.post(
        "/auth/token",
        data={
            "username": "package-admin@example.com",
            "password": "safe-password-123",
        },
    ).json()["access_token"]
    wedding = next(
        category
        for category in client.get("/categories?kind=event").json()
        if category["name"] == "Wedding"
    )

    response = client.post(
        "/packages",
        json={
            "title": "Unauthorized Package",
            "description": "Should not be created by a customer",
            "organizer_id": customer_response.json()["id"],
            "event_category_ids": [wedding["id"]],
            "price": "1000.00",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_package_rejects_service_category_as_event_category(
    client: TestClient,
) -> None:
    create_admin(client)
    headers = login_headers(client)
    catering = next(
        category
        for category in client.get("/categories?kind=service").json()
        if category["name"] == "Catering"
    )

    response = client.post(
        "/packages",
        json={
            "title": "Invalid Package",
            "description": "Has a service category passed as an event type",
            "organizer_id": None,
            "event_category_ids": [catering["id"]],
            "price": "1000.00",
        },
        headers=headers,
    )
    assert response.status_code == 422
