from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PackagePriceUnit = Literal["per_event", "per_plate", "per_person"]


class PackageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1, max_length=5000)
    organizer_id: int | None = Field(default=None, gt=0)
    event_category_ids: list[int] = Field(default_factory=list, max_length=20)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    price_unit: PackagePriceUnit = "per_event"
    image_url: str | None = Field(default=None, max_length=2048)
    badge: str | None = Field(default=None, max_length=30)
    max_guests: int | None = Field(default=None, gt=0)
    included_items: list[str] = Field(default_factory=list, max_length=30)
    average_rating: float = Field(default=0.0, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)


class PackageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1, max_length=5000)
    organizer_id: int | None = Field(default=None, gt=0)
    event_category_ids: list[int] = Field(default_factory=list, max_length=20)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    price_unit: PackagePriceUnit
    image_url: str | None = Field(default=None, max_length=2048)
    badge: str | None = Field(default=None, max_length=30)
    max_guests: int | None = Field(default=None, gt=0)
    included_items: list[str] = Field(default_factory=list, max_length=30)
    average_rating: float = Field(ge=0, le=5)
    review_count: int = Field(ge=0)
    is_active: bool


class PackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    organizer_id: int | None
    category_id: int
    event_category_ids: list[int]
    price: Decimal
    price_unit: PackagePriceUnit
    image_url: str | None
    badge: str | None
    max_guests: int | None
    included_items: list[str]
    average_rating: float
    review_count: int
    is_active: bool
    created_at: datetime
