from collections.abc import Iterator
from pathlib import Path

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


def login(client: TestClient, email: str, password: str = "safe-password-123"):
    return client.post(
        "/auth/token",
        data={"username": email, "password": password},
    )


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_cors_allows_deployed_frontend_preflight(client: TestClient) -> None:
    origin = "https://event-full-stack-sigma.vercel.app"

    response = client.options(
        "/categories?kind=event",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_login_rejects_bad_credentials_and_me_requires_valid_token(
    client: TestClient,
) -> None:
    user_id = register_user(client, "login@example.com")
    assert login(client, "login@example.com", "wrong-password").status_code == 401

    token_response = login(client, "login@example.com")
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    me = client.get("/auth/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["id"] == user_id
    assert me.json()["role"] == "customer"

    assert client.get("/auth/me").status_code == 401
    assert client.get(
        "/auth/me", headers=auth_header("invalid-token")
    ).status_code == 401


def test_admin_can_assign_roles_and_customers_cannot(client: TestClient) -> None:
    admin_id = register_user(client, "admin@example.com")
    organizer_id = register_user(client, "organizer@example.com")
    customer_id = register_user(client, "role-customer@example.com")
    set_role(admin_id, UserRole.ADMIN)

    admin_token = login(client, "admin@example.com").json()["access_token"]
    customer_token = login(client, "role-customer@example.com").json()[
        "access_token"
    ]

    promoted = client.patch(
        f"/users/{organizer_id}/role",
        json={"role": "organizer"},
        headers=auth_header(admin_token),
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "organizer"

    forbidden = client.patch(
        f"/users/{customer_id}/role",
        json={"role": "admin"},
        headers=auth_header(customer_token),
    )
    assert forbidden.status_code == 403
    assert client.patch(
        f"/users/{customer_id}/role",
        json={"role": "admin"},
    ).status_code == 401


def test_only_admin_can_upload_supported_images(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    static_files = next(
        route.app
        for route in app.routes
        if getattr(route, "name", None) == "uploads"
    )
    monkeypatch.setattr(static_files, "directory", str(tmp_path))
    monkeypatch.setattr(static_files, "all_directories", [str(tmp_path)])
    register_user(client, "image-customer@example.com")
    image_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    assert client.post(
        "/uploads/images",
        files={"file": ("sample.png", image_data, "image/png")},
    ).status_code == 401

    customer_token = login(client, "image-customer@example.com").json()[
        "access_token"
    ]
    denied = client.post(
        "/uploads/images",
        headers=auth_header(customer_token),
        files={"file": ("sample.png", image_data, "image/png")},
    )
    assert denied.status_code == 403

    admin_id = register_user(client, "image-admin@example.com")
    set_role(admin_id, UserRole.ADMIN)
    admin_token = login(client, "image-admin@example.com").json()["access_token"]
    uploaded = client.post(
        "/uploads/images",
        headers=auth_header(admin_token),
        files={"file": ("sample.png", image_data, "image/png")},
    )
    assert uploaded.status_code == 201
    image_url = uploaded.json()["image_url"]
    assert image_url.startswith("/uploads/")
    assert (tmp_path / Path(image_url).name).read_bytes() == image_data
    assert client.get(image_url).content == image_data

    invalid = client.post(
        "/uploads/images",
        headers=auth_header(admin_token),
        files={"file": ("sample.png", b"not an image", "image/png")},
    )
    assert invalid.status_code == 415


def test_only_admin_can_write_categories(client: TestClient) -> None:
    customer_id = register_user(client, "category-customer@example.com")
    customer_token = login(client, "category-customer@example.com").json()[
        "access_token"
    ]
    category_data = {"name": "Private Category", "kind": "event"}

    assert client.post("/categories", json=category_data).status_code == 401
    assert client.post(
        "/categories",
        json=category_data,
        headers=auth_header(customer_token),
    ).status_code == 403

    admin_id = register_user(client, "category-admin@example.com")
    set_role(admin_id, UserRole.ADMIN)
    admin_token = login(client, "category-admin@example.com").json()[
        "access_token"
    ]
    created = client.post(
        "/categories",
        json=category_data,
        headers=auth_header(admin_token),
    )
    assert created.status_code == 201


def test_customer_event_requires_admin_acceptance_and_assignment(
    client: TestClient,
) -> None:
    customer_id = register_user(client, "event-customer@example.com")
    other_customer_id = register_user(client, "other-customer@example.com")
    organizer_id = register_user(client, "event-organizer@example.com")
    admin_id = register_user(client, "event-admin@example.com")
    set_role(organizer_id, UserRole.ORGANIZER)
    set_role(admin_id, UserRole.ADMIN)

    customer_token = login(client, "event-customer@example.com").json()[
        "access_token"
    ]
    other_customer_token = login(client, "other-customer@example.com").json()[
        "access_token"
    ]
    organizer_token = login(client, "event-organizer@example.com").json()[
        "access_token"
    ]
    admin_token = login(client, "event-admin@example.com").json()["access_token"]

    wedding = next(
        category
        for category in client.get("/categories?kind=event").json()
        if category["name"] == "Wedding"
    )
    event_data = {
        "title": "Private Wedding",
        "category_id": wedding["id"],
        "customer_phone": "9876543210",
        "event_date": "2027-06-15T10:00:00Z",
        "venue": "Garden Hall",
    }
    created = client.post(
        "/events",
        json=event_data,
        headers=auth_header(customer_token),
    )
    assert created.status_code == 201
    event_id = created.json()["id"]
    assert created.json()["customer_id"] == customer_id
    assert created.json()["customer_phone"] == "9876543210"

    customer_status_update = client.put(
        f"/events/{event_id}",
        json={
            "title": event_data["title"],
            "category_id": event_data["category_id"],
            "event_date": event_data["event_date"],
            "venue": event_data["venue"],
            "status": "confirmed",
        },
        headers=auth_header(customer_token),
    )
    assert customer_status_update.status_code == 403

    assert client.get(
        f"/events/{event_id}", headers=auth_header(other_customer_token)
    ).status_code == 403
    assert client.get(
        "/events", headers=auth_header(other_customer_token)
    ).json() == []
    assert client.get(
        f"/events/{event_id}", headers=auth_header(organizer_token)
    ).status_code == 403
    assert client.get("/events", headers=auth_header(organizer_token)).json() == []
    assert client.patch(
        f"/events/{event_id}/assignment",
        json={"organizer_id": organizer_id},
        headers=auth_header(admin_token),
    ).status_code == 422
    assert client.patch(
        f"/events/{event_id}/assignment",
        json={"organizer_id": organizer_id},
        headers=auth_header(organizer_token),
    ).status_code == 403

    assert client.patch(
        f"/events/{event_id}/status",
        json={"status": "completed"},
        headers=auth_header(organizer_token),
    ).status_code == 403

    accepted = client.patch(
        f"/events/{event_id}/status",
        json={"status": "confirmed"},
        headers=auth_header(admin_token),
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "confirmed"
    assigned = client.patch(
        f"/events/{event_id}/assignment",
        json={"organizer_id": organizer_id},
        headers=auth_header(admin_token),
    )
    assert assigned.status_code == 200
    assert assigned.json()["organizer_id"] == organizer_id
    customer_detail_update = client.put(
        f"/events/{event_id}",
        json={
            **event_data,
            "status": "confirmed",
        },
        headers=auth_header(customer_token),
    )
    assert customer_detail_update.status_code == 200
    assert customer_detail_update.json()["organizer_id"] == organizer_id
    assert client.get(
        f"/events/{event_id}", headers=auth_header(organizer_token)
    ).status_code == 200
    assert [event["id"] for event in client.get(
        "/events", headers=auth_header(organizer_token)
    ).json()] == [event_id]

    completed = client.patch(
        f"/events/{event_id}/status",
        json={"status": "completed"},
        headers=auth_header(organizer_token),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    created_by_organizer = client.post(
        "/events",
        json={**event_data, "customer_id": other_customer_id},
        headers=auth_header(organizer_token),
    )
    assert created_by_organizer.status_code == 403
