from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.category import Category

package_event_categories = Table(
    "package_event_categories",
    Base.metadata,
    Column(
        "package_id",
        ForeignKey("packages.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "event_category_id",
        ForeignKey("categories.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    organizer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048))
    badge: Mapped[str | None] = mapped_column(String(30))
    max_guests: Mapped[int | None] = mapped_column(Integer)
    included_items: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    average_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    event_categories: Mapped[list[Category]] = relationship(
        secondary=package_event_categories, lazy="selectin"
    )

    @property
    def event_category_ids(self) -> list[int]:
        return [category.id for category in self.event_categories]
