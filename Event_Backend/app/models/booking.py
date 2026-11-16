from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.commerce import BookingStatus, CatalogItemType
from app.database import Base


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "(item_type = 'package' AND package_id IS NOT NULL "
            "AND service_listing_id IS NULL) OR "
            "(item_type = 'service' AND package_id IS NULL "
            "AND service_listing_id IS NOT NULL)",
            name="ck_booking_product_matches_type",
        ),
        CheckConstraint("quantity > 0", name="ck_booking_quantity_positive"),
        CheckConstraint(
            "unit_price >= 0 AND total_price >= 0",
            name="ck_booking_prices_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organizer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_type: Mapped[CatalogItemType] = mapped_column(
        SqlEnum(
            CatalogItemType,
            name="booking_item_type",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda types: [item_type.value for item_type in types],
        ),
        nullable=False,
    )
    package_id: Mapped[int | None] = mapped_column(
        ForeignKey("packages.id", ondelete="RESTRICT"), index=True
    )
    service_listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_listings.id", ondelete="RESTRICT"), index=True
    )
    item_title: Mapped[str] = mapped_column(String(150), nullable=False)
    price_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        SqlEnum(
            BookingStatus,
            name="booking_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=BookingStatus.REQUESTED,
        server_default=BookingStatus.REQUESTED.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
