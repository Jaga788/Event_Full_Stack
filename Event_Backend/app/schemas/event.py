from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.categories import EventStatus


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150)
    description: str | None = None
    category_id: int = Field(gt=0)
    customer_id: int | None = Field(default=None, gt=0)
    organizer_id: int | None = Field(default=None, gt=0)
    customer_phone: str | None = Field(default=None, max_length=20)
    event_date: datetime
    venue: str = Field(min_length=1, max_length=255)
    budget: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class EventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150)
    description: str | None = None
    category_id: int = Field(gt=0)
    customer_id: int | None = Field(default=None, gt=0)
    organizer_id: int | None = Field(default=None, gt=0)
    customer_phone: str | None = Field(default=None, max_length=20)
    event_date: datetime
    venue: str = Field(min_length=1, max_length=255)
    budget: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    status: EventStatus


class EventAssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organizer_id: int = Field(gt=0)


class EventStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EventStatus


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    category_id: int
    customer_id: int
    customer_name: str
    customer_email: str
    organizer_id: int | None
    customer_phone: str | None
    event_date: datetime
    venue: str
    budget: Decimal | None
    status: EventStatus
    created_at: datetime
