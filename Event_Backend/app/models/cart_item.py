from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.package import Package
from app.models.service_listing import ServiceListing


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        CheckConstraint(
            "(package_id IS NOT NULL AND service_listing_id IS NULL) OR "
            "(package_id IS NULL AND service_listing_id IS NOT NULL)",
            name="ck_cart_item_exactly_one_product",
        ),
        CheckConstraint("quantity > 0", name="ck_cart_item_quantity_positive"),
        UniqueConstraint("customer_id", "package_id", name="uq_cart_customer_package"),
        UniqueConstraint(
            "customer_id",
            "service_listing_id",
            name="uq_cart_customer_service",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    package_id: Mapped[int | None] = mapped_column(
        ForeignKey("packages.id", ondelete="RESTRICT"), index=True
    )
    service_listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_listings.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    package: Mapped[Package | None] = relationship(
        foreign_keys=[package_id], lazy="joined"
    )
    service_listing: Mapped[ServiceListing | None] = relationship(
        foreign_keys=[service_listing_id], lazy="joined"
    )

    @property
    def item_type(self) -> str:
        return "package" if self.package is not None else "service"

    @property
    def item_title(self) -> str:
        if self.package is not None:
            return self.package.title
        if self.service_listing is not None:
            return self.service_listing.title
        raise ValueError("Cart item has no catalog product")

    @property
    def unit_price(self) -> Decimal:
        if self.package is not None:
            return self.package.price
        if self.service_listing is not None:
            return self.service_listing.price
        raise ValueError("Cart item has no catalog product")

    @property
    def price_unit(self) -> str:
        if self.package is not None:
            return self.package.price_unit
        if self.service_listing is not None:
            return self.service_listing.price_unit
        raise ValueError("Cart item has no catalog product")

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity
