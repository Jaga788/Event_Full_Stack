from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


CatalogKind = Literal["package", "service"]


class EventPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_category_id: int = Field(gt=0)
    event_date: date
    city: str = Field(min_length=1, max_length=120)
    guest_count: int = Field(ge=1, le=10000)
    budget: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    preferences: str = Field(default="", max_length=1200)

    @field_validator("event_date")
    @classmethod
    def event_date_must_not_be_in_the_past(cls, value: date) -> date:
        if value < date.today():
            raise ValueError("Event date cannot be in the past")
        return value


class GeneratedTimelineItem(BaseModel):
    time: str = Field(min_length=1, max_length=60)
    activity: str = Field(min_length=1, max_length=120)
    details: str = Field(min_length=1, max_length=500)


class GeneratedRecommendation(BaseModel):
    kind: CatalogKind
    item_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=500)


class GeneratedEventPlan(BaseModel):
    summary: str = Field(min_length=1, max_length=800)
    budget_advice: str = Field(min_length=1, max_length=800)
    timeline: list[GeneratedTimelineItem] = Field(max_length=12)
    recommendations: list[GeneratedRecommendation] = Field(max_length=6)


class EventPlanRecommendation(BaseModel):
    kind: CatalogKind
    item_id: int
    title: str
    reason: str
    unit_price: Decimal
    price_unit: str
    estimated_total: Decimal
    image_url: str | None


class EventPlanRead(BaseModel):
    event_category: str
    event_date: date
    city: str
    guest_count: int
    summary: str
    budget_advice: str
    timeline: list[GeneratedTimelineItem]
    recommendations: list[EventPlanRecommendation]
    total_estimate: Decimal
    within_budget: bool | None
