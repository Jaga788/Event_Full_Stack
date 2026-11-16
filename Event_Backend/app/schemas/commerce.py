from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.commerce import BookingStatus, CatalogItemType


PriceUnit = Literal["per_event", "per_plate", "per_person"]


class CartItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_id: int | None = Field(default=None, gt=0)
    service_listing_id: int | None = Field(default=None, gt=0)
    quantity: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def require_one_product(self) -> "CartItemCreate":
        if (self.package_id is None) == (self.service_listing_id is None):
            raise ValueError("Provide exactly one of package_id or service_listing_id")
        return self


class CartItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(ge=1)


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: CatalogItemType
    package_id: int | None
    service_listing_id: int | None
    item_title: str
    quantity: int
    unit_price: Decimal
    price_unit: PriceUnit
    subtotal: Decimal
    created_at: datetime


class CartRead(BaseModel):
    items: list[CartItemRead]
    subtotal: Decimal


class FavoriteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_id: int | None = Field(default=None, gt=0)
    service_listing_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_one_product(self) -> "FavoriteCreate":
        if (self.package_id is None) == (self.service_listing_id is None):
            raise ValueError("Provide exactly one of package_id or service_listing_id")
        return self


class FavoriteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: CatalogItemType
    package_id: int | None
    service_listing_id: int | None
    item_title: str
    unit_price: Decimal
    price_unit: PriceUnit
    created_at: datetime


class BookingCheckout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(gt=0)


class BookingStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: BookingStatus


class BookingAssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organizer_id: int = Field(gt=0)


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    organizer_id: int | None
    event_id: int
    item_type: CatalogItemType
    package_id: int | None
    service_listing_id: int | None
    item_title: str
    price_unit: PriceUnit
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    status: BookingStatus
    created_at: datetime
