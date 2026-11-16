from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.categories import EventStatus
from app.database import Base
from app.models.user import User


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organizer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    customer_phone: Mapped[str | None] = mapped_column(String(20))
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    venue: Mapped[str] = mapped_column(String(255), nullable=False)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[EventStatus] = mapped_column(
        SqlEnum(
            EventStatus,
            name="event_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=EventStatus.PLANNING,
        server_default=EventStatus.PLANNING.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    customer: Mapped[User] = relationship(foreign_keys=[customer_id], lazy="joined")

    @property
    def customer_name(self) -> str:
        return self.customer.full_name

    @property
    def customer_email(self) -> str:
        return self.customer.email
