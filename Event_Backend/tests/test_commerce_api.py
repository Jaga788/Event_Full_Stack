from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
from app.core.config import settings
from app.core.commerce import BookingStatus
from app.core.roles import UserRole
from app.main import app
from app.models.booking import Booking
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


def register_user(client: TestClient, email: str) -> int:
    response = client.post(
        "/users",
        json={
            "full_name": email.split("@")[0],
            "email": email,
            "password": "safe-password-123",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def set_role(user_id: int, role: UserRole) -> None:
    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        user.role = role
        db.commit()


def login_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/token",
        data={"username": email, "password": "safe-password-123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_can_create_multiple_catering_listings(
    client: TestClient,
) -> None:
    admin_id = register_user(client, "catalog-admin@example.com")
    set_role(admin_id, UserRole.ADMIN)
    admin_headers = login_headers(client, "catalog-admin@example.com")
    organizer_id = register_user(client, "catalog-organizer@example.com")
    set_role(organizer_id, UserRole.ORGANIZER)
    organizer_headers = login_headers(client, "catalog-organizer@example.com")
    catering = next(
        category
        for category in client.get("/categories?kind=service").json()
        if category["name"] == "Catering"
    )

    missing_food_type = client.post(
        "/services",
        json={
            "title": "Unclassified Catering",
            "category_id": catering["id"],
            "organizer_id": None,
            "price": "500.00",
            "price_unit": "per_plate",
        },
        headers=admin_headers,
    )
    assert missing_food_type.status_code == 422

    listings = []
    for title, dietary_type in (
        ("Vegetarian Buffet", "veg"),
        ("Non-vegetarian Buffet", "non_veg"),
    ):
        response = client.post(
            "/services",
            json={
                "title": title,
                "category_id": catering["id"],
                "organizer_id": None,
                "price": "500.00",
                "price_unit": "per_plate",
                "dietary_type": dietary_type,
            },
            headers=admin_headers,
        )
        assert response.status_code == 201, response.text
        listings.append(response.json())

    assert [listing["dietary_type"] for listing in listings] == [
        "veg",
        "non_veg",
    ]
    category_listings = client.get(
        f"/services?category_id={catering['id']}"
    ).json()
    assert {listing["title"] for listing in category_listings} >= {
        "Vegetarian Buffet",
        "Non-vegetarian Buffet",
    }


def test_cart_favorites_and_checkout_booking_lifecycle(
    client: TestClient,
) -> None:
    customer_id = register_user(client, "shopper@example.com")
    other_customer_id = register_user(client, "other-shopper@example.com")
    organizer_id = register_user(client, "shop-organizer@example.com")
    admin_id = register_user(client, "shop-admin@example.com")
    set_role(organizer_id, UserRole.ORGANIZER)
    set_role(admin_id, UserRole.ADMIN)

    customer_headers = login_headers(client, "shopper@example.com")
    other_customer_headers = login_headers(client, "other-shopper@example.com")
    organizer_headers = login_headers(client, "shop-organizer@example.com")
    admin_headers = login_headers(client, "shop-admin@example.com")

    service_categories = client.get("/categories?kind=service").json()
    event_categories = client.get("/categories?kind=event").json()
    packages_category = next(
        item for item in service_categories if item["name"] == "Packages"
    )
    catering_category = next(
        item for item in service_categories if item["name"] == "Catering"
    )
    wedding_category = next(
        item for item in event_categories if item["name"] == "Wedding"
    )

    organizer_catalog_write = client.post(
        "/services",
        json={
            "title": "Organizer-managed catering",
            "category_id": catering_category["id"],
            "organizer_id": organizer_id,
            "price": "500.00",
            "price_unit": "per_plate",
            "dietary_type": "veg",
        },
        headers=organizer_headers,
    )
    assert organizer_catalog_write.status_code == 403

    package_response = client.post(
        "/packages",
        json={
            "title": "Wedding Package",
            "description": "A complete wedding package.",
            "organizer_id": None,
            "event_category_ids": [wedding_category["id"]],
            "price": "150000.00",
            "price_unit": "per_event",
            "included_items": ["Decoration", "Photography"],
        },
        headers=admin_headers,
    )
    assert package_response.status_code == 201, package_response.text
    package_id = package_response.json()["id"]
    assert package_response.json()["category_id"] == packages_category["id"]

    service_response = client.post(
        "/services",
        json={
            "title": "Wedding Catering",
            "description": "Vegetarian catering",
            "category_id": catering_category["id"],
            "event_category_ids": [wedding_category["id"]],
            "organizer_id": None,
            "price": "650.00",
            "price_unit": "per_plate",
            "dietary_type": "veg",
        },
        headers=admin_headers,
    )
    assert service_response.status_code == 201, service_response.text
    service_listing_id = service_response.json()["id"]

    saved_package = client.post(
        "/favorites",
        json={"package_id": package_id},
        headers=customer_headers,
    )
    assert saved_package.status_code == 201
    assert saved_package.json()["item_type"] == "package"
    saved_service = client.post(
        "/favorites",
        json={"service_listing_id": service_listing_id},
        headers=customer_headers,
    )
    assert saved_service.status_code == 201
    assert len(client.get("/favorites", headers=customer_headers).json()) == 2
    assert client.post(
        "/favorites",
        json={"package_id": package_id},
        headers=customer_headers,
    ).status_code == 409
    assert client.get("/favorites", headers=other_customer_headers).json() == []
    assert client.delete(
        f"/favorites/{saved_package.json()['id']}",
        headers=customer_headers,
    ).status_code == 204

    cart_package = client.post(
        "/cart/items",
        json={"package_id": package_id},
        headers=customer_headers,
    )
    assert cart_package.status_code == 201, cart_package.text
    cart_service = client.post(
        "/cart/items",
        json={"service_listing_id": service_listing_id, "quantity": 2},
        headers=customer_headers,
    )
    assert cart_service.status_code == 201, cart_service.text
    assert cart_service.json()["subtotal"] == "1300.00"
    assert client.post(
        "/cart/items",
        json={"package_id": package_id, "quantity": 2},
        headers=customer_headers,
    ).status_code == 422
    assert client.get("/cart", headers=other_customer_headers).json()[
        "items"
    ] == []

    updated_cart_item = client.patch(
        f"/cart/items/{cart_service.json()['id']}",
        json={"quantity": 3},
        headers=customer_headers,
    )
    assert updated_cart_item.status_code == 200
    assert updated_cart_item.json()["subtotal"] == "1950.00"

    event = client.post(
        "/events",
        json={
            "title": "Shopper Wedding",
            "category_id": wedding_category["id"],
            "event_date": "2027-06-15T10:00:00Z",
            "venue": "Garden Hall",
        },
        headers=customer_headers,
    )
    assert event.status_code == 201, event.text
    assert event.json()["customer_id"] == customer_id

    wrong_event = client.post(
        "/events",
        json={
            "title": "Other Wedding",
            "category_id": wedding_category["id"],
            "event_date": "2027-06-15T10:00:00Z",
            "venue": "Other Hall",
        },
        headers=other_customer_headers,
    )
    assert wrong_event.status_code == 201
    assert client.post(
        "/bookings/checkout",
        json={"event_id": wrong_event.json()["id"]},
        headers=customer_headers,
    ).status_code == 403
    assert len(client.get("/cart", headers=customer_headers).json()["items"]) == 2

    checkout = client.post(
        "/bookings/checkout",
        json={"event_id": event.json()["id"]},
        headers=customer_headers,
    )
    assert checkout.status_code == 201, checkout.text
    bookings = checkout.json()
    assert len(bookings) == 2
    assert {booking["status"] for booking in bookings} == {"requested"}
    assert sum(
        (float(booking["total_price"]) for booking in bookings)
    ) == 151950.0
    assert client.get("/cart", headers=customer_headers).json()["items"] == []

    customer_bookings = client.get("/bookings", headers=customer_headers)
    assert customer_bookings.status_code == 200
    assert len(customer_bookings.json()) == 2
    assert client.get("/bookings", headers=organizer_headers).status_code == 200
    assert client.get("/bookings", headers=organizer_headers).json() == []
    assert client.get("/bookings", headers=admin_headers).status_code == 200
    assert client.get(
        f"/bookings/{bookings[0]['id']}", headers=other_customer_headers
    ).status_code == 403

    customer_cancelled = client.patch(
        f"/bookings/{bookings[0]['id']}/status",
        json={"status": "cancelled"},
        headers=customer_headers,
    )
    assert customer_cancelled.status_code == 200

    organizer_confirmed = client.patch(
        f"/bookings/{bookings[1]['id']}/status",
        json={"status": "confirmed"},
        headers=organizer_headers,
    )
    assert organizer_confirmed.status_code == 403
    booking_confirmed_before_event = client.patch(
        f"/bookings/{bookings[1]['id']}/status",
        json={"status": "confirmed"},
        headers=admin_headers,
    )
    assert booking_confirmed_before_event.status_code == 409
    assignment_before_accept = client.patch(
        f"/bookings/{bookings[1]['id']}/assignment",
        json={"organizer_id": organizer_id},
        headers=admin_headers,
    )
    assert assignment_before_accept.status_code == 409
    event_confirmed = client.patch(
        f"/events/{event.json()['id']}/status",
        json={"status": "confirmed"},
        headers=admin_headers,
    )
    assert event_confirmed.status_code == 200
    assert event_confirmed.json()["status"] == "confirmed"
    with database.SessionLocal() as db:
        legacy_booking = db.get(Booking, bookings[1]["id"])
        assert legacy_booking is not None
        legacy_booking.status = BookingStatus.REQUESTED
        db.commit()
    database.create_tables()
    confirmed_bookings = {
        booking["id"]: booking["status"]
        for booking in client.get("/bookings", headers=admin_headers).json()
    }
    assert confirmed_bookings == {
        bookings[0]["id"]: "cancelled",
        bookings[1]["id"]: "confirmed",
    }
    assigned = client.patch(
        f"/bookings/{bookings[1]['id']}/assignment",
        json={"organizer_id": organizer_id},
        headers=admin_headers,
    )
    assert assigned.status_code == 200
    assert assigned.json()["organizer_id"] == organizer_id
    assert [
        booking["id"]
        for booking in client.get(
            "/bookings", headers=organizer_headers
        ).json()
    ] == [bookings[1]["id"]]
    organizer_completed = client.patch(
        f"/bookings/{bookings[1]['id']}/status",
        json={"status": "completed"},
        headers=organizer_headers,
    )
    assert organizer_completed.status_code == 200

    assert client.post(
        "/cart/items",
        json={"package_id": package_id},
        headers=customer_headers,
    ).status_code == 201
    later_checkout = client.post(
        "/bookings/checkout",
        json={"event_id": event.json()["id"]},
        headers=customer_headers,
    )
    assert later_checkout.status_code == 201
    assert later_checkout.json()[0]["status"] == "confirmed"

    assert client.delete(
        f"/cart/items/{cart_package.json()['id']}",
        headers=customer_headers,
    ).status_code == 404
