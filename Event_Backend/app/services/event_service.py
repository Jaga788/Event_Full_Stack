from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.categories import CategoryKind, EventStatus
from app.core.roles import UserRole
from app.models.booking import Booking
from app.models.event import Event
from app.models.user import User
from app.repositories import category_repository, event_repository
from app.schemas.event import EventCreate, EventUpdate


class EventNotFoundError(Exception):
    pass


class EventReferenceError(Exception):
    pass


def _validate_event_category(db: Session, category_id: int) -> None:
    category = category_repository.get_by_id(db, category_id)
    if (
        category is None
        or category.kind != CategoryKind.EVENT
        or not category.is_active
    ):
        raise EventReferenceError("Event category not found or inactive")


def _validate_user(db: Session, user_id: int, role: UserRole) -> None:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise EventReferenceError("User not found or inactive")
    if user.role != role:
        raise EventReferenceError(f"User must have the {role.value} role")


def list_events(
    db: Session,
    *,
    category_id: int | None,
    customer_id: int | None,
    organizer_id: int | None,
    skip: int,
    limit: int,
) -> list[Event]:
    return event_repository.list_events(
        db,
        category_id=category_id,
        customer_id=customer_id,
        organizer_id=organizer_id,
        skip=skip,
        limit=limit,
    )


def get_event(db: Session, event_id: int) -> Event:
    event = event_repository.get_by_id(db, event_id)
    if event is None:
        raise EventNotFoundError
    return event


def create_event(
    db: Session,
    event_data: EventCreate,
    *,
    customer_id: int,
) -> Event:
    _validate_event_category(db, event_data.category_id)
    _validate_user(db, customer_id, UserRole.CUSTOMER)
    if event_data.organizer_id is not None:
        _validate_user(db, event_data.organizer_id, UserRole.ORGANIZER)

    try:
        return event_repository.create_event(
            db,
            title=event_data.title,
            description=event_data.description,
            category_id=event_data.category_id,
            customer_id=customer_id,
            organizer_id=event_data.organizer_id,
            customer_phone=event_data.customer_phone,
            event_date=event_data.event_date,
            venue=event_data.venue,
            budget=event_data.budget,
        )
    except IntegrityError as exc:
        db.rollback()
        raise EventReferenceError("An event reference is invalid") from exc


def update_event(
    db: Session,
    event_id: int,
    event_data: EventUpdate,
    *,
    customer_id: int | None = None,
) -> Event:
    event = get_event(db, event_id)
    selected_customer_id = customer_id or event.customer_id
    if selected_customer_id != event.customer_id:
        _validate_user(db, selected_customer_id, UserRole.CUSTOMER)
    _validate_event_category(db, event_data.category_id)
    if event_data.organizer_id is not None:
        _validate_user(db, event_data.organizer_id, UserRole.ORGANIZER)

    try:
        return event_repository.update_event(
            db,
            event,
            title=event_data.title,
            description=event_data.description,
            category_id=event_data.category_id,
            customer_id=selected_customer_id,
            organizer_id=event_data.organizer_id,
            customer_phone=event_data.customer_phone,
            event_date=event_data.event_date,
            venue=event_data.venue,
            budget=event_data.budget,
            status=event_data.status,
        )
    except IntegrityError as exc:
        db.rollback()
        raise EventReferenceError("An event reference is invalid") from exc


def delete_event(db: Session, event_id: int) -> None:
    event = get_event(db, event_id)
    event_repository.delete_event(db, event)


def organizer_has_event_access(
    db: Session, event: Event, organizer_id: int
) -> bool:
    if event.organizer_id == organizer_id:
        return True
    return (
        db.scalar(
            select(Booking.id)
            .where(
                Booking.event_id == event.id,
                Booking.organizer_id == organizer_id,
            )
            .limit(1)
        )
        is not None
    )


def assign_event_organizer(
    db: Session, event_id: int, organizer_id: int
) -> Event:
    event = get_event(db, event_id)
    if event.status != EventStatus.CONFIRMED:
        raise EventReferenceError(
            "Accept the event before assigning an organizer"
        )
    _validate_user(db, organizer_id, UserRole.ORGANIZER)
    return event_repository.assign_event_organizer(
        db, event, organizer_id
    )


def update_event_status(
    db: Session,
    event_id: int,
    status: EventStatus,
    current_user: User,
) -> Event:
    event = get_event(db, event_id)
    if current_user.role == UserRole.ORGANIZER:
        if event.organizer_id != current_user.id:
            raise EventReferenceError(
                "Only the event's assigned organizer can update its status"
            )
        if event.status != EventStatus.CONFIRMED or status not in {
            EventStatus.CANCELLED,
            EventStatus.COMPLETED,
        }:
            raise EventReferenceError(
                "Assigned organizers can only complete or cancel accepted events"
            )
    return event_repository.update_event_status(db, event, status)
