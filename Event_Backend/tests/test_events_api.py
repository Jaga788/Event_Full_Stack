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


def create_user(client: TestClient, email: str) -> int:
    response = client.post(
        "/users",
        json={
            "full_name": "Test Account",
            "email": email,
            "password": "safe-password-123",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def login_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/token",
        data={"username": email, "password": "safe-password-123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def promote_user(user_id: int, role: UserRole) -> None:
    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        user.role = role
        db.commit()


def test_seeded_categories_are_returned_by_kind(client: TestClient) -> None:
    event_categories = client.get("/categories?kind=event")
    service_categories = client.get("/categories?kind=service")

    assert event_categories.status_code == 200
    assert [category["name"] for category in event_categories.json()] == [
        "Baby Shower & Naming",
        "Birthday",
        "Corporate & Parties",
        "Engagement",
        "Maturity Function",
        "Wedding",
    ]
    assert {category["kind"] for category in event_categories.json()} == {"event"}
    assert {category["kind"] for category in service_categories.json()} == {"service"}


def test_category_crud(client: TestClient) -> None:
    admin_id = create_user(client, "category-admin@example.com")
    promote_user(admin_id, UserRole.ADMIN)
    headers = login_headers(client, "category-admin@example.com")
    created = client.post(
        "/categories",
        json={
            "name": "Anniversary",
            "kind": "event",
            "description": "Anniversary celebrations",
        },
        headers=headers,
    )
    assert created.status_code == 201
    category_id = created.json()["id"]

    duplicate = client.post(
        "/categories",
        json={"name": "Anniversary", "kind": "event"},
        headers=headers,
    )
    assert duplicate.status_code == 409

    updated = client.put(
        f"/categories/{category_id}",
        json={
            "name": "Anniversary Party",
            "description": "Updated description",
            "is_active": True,
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Anniversary Party"

    assert client.delete(
        f"/categories/{category_id}", headers=headers
    ).status_code == 204


def test_planned_event_crud(client: TestClient) -> None:
    customer_id = create_user(client, "customer@example.com")
    headers = login_headers(client, "customer@example.com")
    wedding = next(
        category
        for category in client.get("/categories?kind=event").json()
        if category["name"] == "Wedding"
    )
    event_data = {
        "title": "Family Wedding",
        "description": "A planned wedding event",
        "category_id": wedding["id"],
        "event_date": "2027-06-15T10:00:00Z",
        "venue": "Garden Hall",
        "budget": "250000.00",
    }

    created = client.post("/events", json=event_data, headers=headers)
    assert created.status_code == 201
    event = created.json()
    assert event["status"] == "planning"

    updated = client.put(
        f"/events/{event['id']}",
        json={
            "title": event_data["title"],
            "description": event_data["description"],
            "category_id": event_data["category_id"],
            "event_date": event_data["event_date"],
            "venue": event_data["venue"],
            "budget": event_data["budget"],
            "status": "planning",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "planning"
    assert client.get(f"/events/{event['id']}", headers=headers).status_code == 200
    assert len(
        client.get(
            f"/events?customer_id={customer_id}", headers=headers
        ).json()
    ) == 1

    assert client.delete(
        f"/events/{event['id']}", headers=headers
    ).status_code == 204
    assert client.get(
        f"/events/{event['id']}", headers=headers
    ).status_code == 404


def test_admin_service_listing_filters_by_service_and_event_categories(
    client: TestClient,
) -> None:
    admin_id = create_user(client, "catalog-admin@example.com")
    promote_user(admin_id, UserRole.ADMIN)
    headers = login_headers(client, "catalog-admin@example.com")

    categories = client.get("/categories").json()
    catering = next(
        category for category in categories if category["name"] == "Catering"
    )
    wedding = next(
        category for category in categories if category["name"] == "Wedding"
    )
    birthday = next(
        category for category in categories if category["name"] == "Birthday"
    )
    created = client.post(
        "/services",
        json={
            "title": "Traditional Wedding Feast",
            "description": "Vegetarian catering package",
            "category_id": catering["id"],
            "event_category_ids": [wedding["id"], birthday["id"]],
            "organizer_id": None,
            "price": "650.00",
            "price_unit": "per_plate",
            "dietary_type": "veg",
            "image_url": "https://example.com/catering.jpg",
        },
        headers=headers,
    )
    assert created.status_code == 201
    listing = created.json()
    assert set(listing["event_category_ids"]) == {wedding["id"], birthday["id"]}

    wedding_filtered = client.get(
        f"/services?category_id={catering['id']}&event_category_id={wedding['id']}"
    )
    birthday_filtered = client.get(
        f"/services?category_id={catering['id']}&event_category_id={birthday['id']}"
    )
    assert wedding_filtered.status_code == 200
    assert birthday_filtered.status_code == 200
    assert [item["id"] for item in wedding_filtered.json()] == [listing["id"]]
    assert [item["id"] for item in birthday_filtered.json()] == [listing["id"]]

    fetched = client.get(f"/services/{listing['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Traditional Wedding Feast"

    updated = client.put(
        f"/services/{listing['id']}",
        json={
            "title": "Wedding Feast",
            "description": "Updated catering package",
            "category_id": catering["id"],
            "event_category_ids": [wedding["id"], birthday["id"]],
            "organizer_id": None,
            "price": "700.00",
            "price_unit": "per_plate",
            "dietary_type": "veg",
            "image_url": "https://example.com/catering.jpg",
            "is_active": True,
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Wedding Feast"
    assert set(updated.json()["event_category_ids"]) == {wedding["id"], birthday["id"]}
    assert client.delete(
        f"/services/{listing['id']}", headers=headers
    ).status_code == 204


def test_service_listing_rejects_event_category_as_service_category(
    client: TestClient,
) -> None:
    admin_id = create_user(client, "catalog-admin2@example.com")
    promote_user(admin_id, UserRole.ADMIN)
    headers = login_headers(client, "catalog-admin2@example.com")

    wedding = next(
        category
        for category in client.get("/categories?kind=event").json()
        if category["name"] == "Wedding"
    )
    response = client.post(
        "/services",
        json={
            "title": "Invalid Listing",
            "category_id": wedding["id"],
            "organizer_id": None,
            "price": "100.00",
            "price_unit": "per_event",
        },
        headers=headers,
    )

    assert response.status_code == 422
