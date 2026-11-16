from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.categories import EventStatus
from app.models.booking import Booking
from app.models.event import Event


def get_by_id(db: Session, event_id: int) -> Event | None:
    return db.get(Event, event_id)


def list_events(
    db: Session,
    *,
    category_id: int | None,
    customer_id: int | None,
    organizer_id: int | None,
    skip: int,
    limit: int,
) -> list[Event]:
    statement = select(Event).order_by(Event.event_date, Event.id)
    if category_id is not None:
        statement = statement.where(Event.category_id == category_id)
    if customer_id is not None:
        statement = statement.where(Event.customer_id == customer_id)
    if organizer_id is not None:
        statement = statement.where(
            or_(
                Event.organizer_id == organizer_id,
                Event.id.in_(
                    select(Booking.event_id).where(
                        Booking.organizer_id == organizer_id
                    )
                ),
            )
        )
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_event(
    db: Session,
    *,
    title: str,
    description: str | None,
    category_id: int,
    customer_id: int,
    organizer_id: int | None,
    customer_phone: str | None,
    event_date: datetime,
    venue: str,
    budget: Decimal | None,
) -> Event:
    event = Event(
        title=title,
        description=description,
        category_id=category_id,
        customer_id=customer_id,
        organizer_id=organizer_id,
        customer_phone=customer_phone,
        event_date=event_date,
        venue=venue,
        budget=budget,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_event(
    db: Session,
    event: Event,
    *,
    title: str,
    description: str | None,
    category_id: int,
    customer_id: int,
    organizer_id: int | None,
    customer_phone: str | None,
    event_date: datetime,
    venue: str,
    budget: Decimal | None,
    status: EventStatus,
) -> Event:
    event.title = title
    event.description = description
    event.category_id = category_id
    event.customer_id = customer_id
    event.organizer_id = organizer_id
    event.customer_phone = customer_phone
    event.event_date = event_date
    event.venue = venue
    event.budget = budget
    event.status = status
    db.commit()
    db.refresh(event)
    return event


def assign_event_organizer(
    db: Session, event: Event, organizer_id: int
) -> Event:
    event.organizer_id = organizer_id
    db.commit()
    db.refresh(event)
    return event


def update_event_status(
    db: Session, event: Event, status: EventStatus
) -> Event:
    event.status = status
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event: Event) -> None:
    db.delete(event)
    db.commit()
