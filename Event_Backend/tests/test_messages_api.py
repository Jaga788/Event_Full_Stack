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


def test_event_messaging_permission_and_read_receipts(client: TestClient) -> None:
    customer_id = register_user(client, "message-customer@example.com")
    register_user(client, "other-message-customer@example.com")
    organizer_id = register_user(client, "message-organizer@example.com")
    second_organizer_id = register_user(client, "second-organizer@example.com")
    admin_id = register_user(client, "message-admin@example.com")
    set_role(organizer_id, UserRole.ORGANIZER)
    set_role(second_organizer_id, UserRole.ORGANIZER)
    set_role(admin_id, UserRole.ADMIN)

    customer_headers = login_headers(client, "message-customer@example.com")
    other_customer_headers = login_headers(
        client, "other-message-customer@example.com"
    )
    organizer_headers = login_headers(client, "message-organizer@example.com")
    second_organizer_headers = login_headers(
        client, "second-organizer@example.com"
    )
    admin_headers = login_headers(client, "message-admin@example.com")

    wedding = next(
        category
        for category in client.get("/categories?kind=event").json()
        if category["name"] == "Wedding"
    )
    event = client.post(
        "/events",
        json={
            "title": "Messaging Wedding",
            "category_id": wedding["id"],
            "event_date": "2027-06-15T10:00:00Z",
            "venue": "Garden Hall",
        },
        headers=customer_headers,
    )
    assert event.status_code == 201
    event_id = event.json()["id"]
    assert event.json()["customer_id"] == customer_id

    path = f"/events/{event_id}/messages"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=other_customer_headers).status_code == 403
    assert client.post(
        path,
        json={"content": "Not assigned yet"},
        headers=organizer_headers,
    ).status_code == 403

    accepted = client.patch(
        f"/events/{event_id}/status",
        json={"status": "confirmed"},
        headers=admin_headers,
    )
    assert accepted.status_code == 200
    assigned = client.patch(
        f"/events/{event_id}/assignment",
        json={"organizer_id": organizer_id},
        headers=admin_headers,
    )
    assert assigned.status_code == 200

    sent = client.post(
        path,
        json={"content": "Hello, I can help plan your event."},
        headers=organizer_headers,
    )
    assert sent.status_code == 201, sent.text
    message = sent.json()
    assert message["sender_id"] == organizer_id
    assert message["recipient_id"] == customer_id
    assert message["sender_name"] == "message-organizer"

    assert client.get(
        path, headers=second_organizer_headers
    ).status_code == 403

    unauthorized_message = client.post(
        path,
        json={"content": "Not this customer's event"},
        headers=other_customer_headers,
    )
    assert unauthorized_message.status_code == 403

    customer_reply = client.post(
        path,
        json={
            "content": "Thank you!",
            "recipient_id": organizer_id,
        },
        headers=customer_headers,
    )
    assert customer_reply.status_code == 201
    assert customer_reply.json()["recipient_id"] == organizer_id
    organizer_history = client.get(path, headers=organizer_headers)
    assert organizer_history.json()[-1]["id"] == customer_reply.json()["id"]

    marked_read = client.patch(
        f"{path}/{message['id']}/read",
        headers=customer_headers,
    )
    assert marked_read.status_code == 200
    assert marked_read.json()["read_at"] is not None

    sender_cannot_mark_read = client.patch(
        f"{path}/{message['id']}/read",
        headers=organizer_headers,
    )
    assert sender_cannot_mark_read.status_code == 403

    admin_history = client.get(path, headers=admin_headers)
    assert admin_history.status_code == 200
    admin_message = client.post(
        path,
        json={
            "content": "Admin support message",
            "recipient_id": customer_id,
        },
        headers=admin_headers,
    )
    assert admin_message.status_code == 201
    assert admin_message.json()["sender_id"] == admin_id
