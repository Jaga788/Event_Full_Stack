from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
from app.core.categories import CategoryKind
from app.core.config import settings
from app.main import app
from app.models.category import Category
from app.models.package import Package
from app.models.service_listing import ServiceListing
from app.schemas.ai_planner import (
    GeneratedEventPlan,
    GeneratedRecommendation,
    GeneratedTimelineItem,
)
from app.services import ai_planner_service


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


def create_customer_headers(client: TestClient) -> dict[str, str]:
    created = client.post(
        "/users",
        json={
            "full_name": "Planner Customer",
            "email": "planner-customer@example.com",
            "password": "safe-password-123",
        },
    )
    assert created.status_code == 201
    login = client.post(
        "/auth/token",
        data={
            "username": "planner-customer@example.com",
            "password": "safe-password-123",
        },
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_event_plan_uses_active_catalog_prices(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = create_customer_headers(client)
    with database.SessionLocal() as db:
        wedding = db.scalar(
            select(Category).where(
                Category.kind == CategoryKind.EVENT,
                Category.name == "Wedding",
            )
        )
        package_category = db.scalar(
            select(Category).where(
                Category.kind == CategoryKind.SERVICE,
                Category.name == "Packages",
            )
        )
        catering_category = db.scalar(
            select(Category).where(
                Category.kind == CategoryKind.SERVICE,
                Category.name == "Catering",
            )
        )
        assert wedding is not None
        assert package_category is not None
        assert catering_category is not None

        package = Package(
            title="Wedding Coordination Package",
            description="Coordination for a wedding.",
            category_id=package_category.id,
            price=Decimal("50000.00"),
            price_unit="per_event",
            included_items=["Event coordination"],
            event_categories=[wedding],
        )
        catering = ServiceListing(
            title="Vegetarian Catering",
            description="Vegetarian meal service.",
            category_id=catering_category.id,
            price=Decimal("700.00"),
            price_unit="per_plate",
            dietary_type="veg",
            is_active=True,
            event_categories=[wedding],
        )
        inactive_package = Package(
            title="Inactive Package",
            description="This must not be recommended.",
            category_id=package_category.id,
            price=Decimal("1.00"),
            price_unit="per_event",
            included_items=[],
            is_active=False,
            event_categories=[wedding],
        )
        db.add_all([package, catering, inactive_package])
        db.commit()
        package_id = package.id
        catering_id = catering.id
        wedding_id = wedding.id

    async def fake_generator(*, request, event_category, catalog):
        assert event_category == "Wedding"
        assert {item["id"] for item in catalog if item["kind"] == "package"} == {
            package_id
        }
        assert {item["id"] for item in catalog if item["kind"] == "service"} == {
            catering_id
        }
        return GeneratedEventPlan(
            summary="A practical wedding plan.",
            budget_advice="Keep a small contingency for last-minute needs.",
            timeline=[
                GeneratedTimelineItem(
                    time="Morning",
                    activity="Set up",
                    details="Confirm the venue and supplier setup.",
                )
            ],
            recommendations=[
                GeneratedRecommendation(
                    kind="package",
                    item_id=package_id,
                    reason="It includes event coordination.",
                ),
                GeneratedRecommendation(
                    kind="service",
                    item_id=catering_id,
                    reason="It matches the vegetarian preference.",
                ),
            ],
        )

    monkeypatch.setattr(
        settings,
        "OPENAI_API_KEY",
        SecretStr("test-openai-key"),
    )
    monkeypatch.setattr(
        ai_planner_service,
        "_generate_with_openai",
        fake_generator,
    )

    response = client.post(
        "/ai/event-plan",
        headers=headers,
        json={
            "event_category_id": wedding_id,
            "event_date": (date.today() + timedelta(days=30)).isoformat(),
            "city": "Chennai",
            "guest_count": 100,
            "budget": "150000.00",
            "preferences": "Vegetarian meals",
        },
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["total_estimate"] == "120000.00"
    assert result["within_budget"] is True
    assert [item["title"] for item in result["recommendations"]] == [
        "Wedding Coordination Package",
        "Vegetarian Catering",
    ]
    assert result["recommendations"][1]["estimated_total"] == "70000.00"


def test_event_plan_requires_customer_authentication(client: TestClient) -> None:
    response = client.post(
        "/ai/event-plan",
        json={
            "event_category_id": 1,
            "event_date": (date.today() + timedelta(days=30)).isoformat(),
            "city": "Chennai",
            "guest_count": 100,
        },
    )

    assert response.status_code == 401


def test_event_plan_reports_missing_provider_configuration(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = create_customer_headers(client)
    wedding = next(
        category
        for category in client.get("/categories?kind=event").json()
        if category["name"] == "Wedding"
    )
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)

    response = client.post(
        "/ai/event-plan",
        headers=headers,
        json={
            "event_category_id": wedding["id"],
            "event_date": (date.today() + timedelta(days=30)).isoformat(),
            "city": "Chennai",
            "guest_count": 100,
        },
    )

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_event_plan_returns_safe_provider_diagnostic(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = create_customer_headers(client)
    wedding = next(
        category
        for category in client.get("/categories?kind=event").json()
        if category["name"] == "Wedding"
    )

    async def fail_generation(**_kwargs):
        raise ai_planner_service.PlannerProviderError(
            "OpenAI usage limits were reached. Check API billing."
        )

    monkeypatch.setattr(
        ai_planner_service,
        "_generate_with_openai",
        fail_generation,
    )
    response = client.post(
        "/ai/event-plan",
        headers=headers,
        json={
            "event_category_id": wedding["id"],
            "event_date": (date.today() + timedelta(days=30)).isoformat(),
            "city": "Chennai",
            "guest_count": 100,
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "OpenAI usage limits were reached. Check API billing."
    )
