from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.categories import CategoryKind


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    kind: CategoryKind
    description: str | None = Field(default=None, max_length=500)


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: CategoryKind
    description: str | None
    is_active: bool
    created_at: datetime
