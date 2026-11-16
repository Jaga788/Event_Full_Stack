from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PriceUnit = Literal["per_event", "per_plate", "per_person"]
DietaryType = Literal["veg", "non_veg"]


class ServiceListingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150)
    description: str | None = None
    category_id: int = Field(gt=0)
    event_category_ids: list[int] = Field(default_factory=list)
    organizer_id: int | None = Field(default=None, gt=0)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    price_unit: PriceUnit
    dietary_type: DietaryType | None = None
    image_url: str | None = Field(default=None, max_length=2048)


class ServiceListingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150)
    description: str | None = None
    category_id: int = Field(gt=0)
    event_category_ids: list[int] = Field(default_factory=list)
    organizer_id: int | None = Field(default=None, gt=0)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    price_unit: PriceUnit
    dietary_type: DietaryType | None = None
    image_url: str | None = Field(default=None, max_length=2048)
    is_active: bool


class ServiceListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    category_id: int
    event_category_ids: list[int]
    organizer_id: int | None
    price: Decimal
    price_unit: PriceUnit
    dietary_type: DietaryType | None
    image_url: str | None
    is_active: bool
    created_at: datetime
