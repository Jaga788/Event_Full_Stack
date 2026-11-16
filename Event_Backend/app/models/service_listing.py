from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.category import Category

service_event_categories = Table(
    "service_event_categories",
    Base.metadata,
    Column(
        "service_listing_id",
        ForeignKey("service_listings.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "event_category_id",
        ForeignKey("categories.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)


class ServiceListing(Base):
    __tablename__ = "service_listings"
    __table_args__ = (
        CheckConstraint(
            "dietary_type IS NULL OR dietary_type IN ('veg', 'non_veg')",
            name="ck_service_listing_dietary_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organizer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    dietary_type: Mapped[str | None] = mapped_column(String(7))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    event_categories: Mapped[list[Category]] = relationship(
        secondary=service_event_categories, lazy="selectin"
    )

    @property
    def event_category_ids(self) -> list[int]:
        return [category.id for category in self.event_categories]
