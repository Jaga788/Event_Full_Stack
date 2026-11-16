from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.models.booking import Booking
from app.models.event import Event
from app.models.message import EventMessage
from app.models.user import User
from app.repositories import message_repository
from app.schemas.message import MessageCreate


class MessageEventNotFoundError(Exception):
    pass


class MessageNotFoundError(Exception):
    pass


class MessagePermissionError(Exception):
    pass


class MessageRecipientError(Exception):
    pass


def _get_event(db: Session, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise MessageEventNotFoundError
    return event


def _organizer_is_assigned(
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


def _ensure_can_access_event(db: Session, user: User, event: Event) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.ORGANIZER and _organizer_is_assigned(
        db, event, user.id
    ):
        return
    if user.role == UserRole.CUSTOMER and user.id == event.customer_id:
        return
    raise MessagePermissionError


def _get_active_organizer(db: Session, organizer_id: int) -> User:
    organizer = db.get(User, organizer_id)
    if (
        organizer is None
        or not organizer.is_active
        or organizer.role != UserRole.ORGANIZER
    ):
        raise MessageRecipientError(
            "The recipient must be an active organizer"
        )
    return organizer


def _get_active_customer(db: Session, customer_id: int) -> User:
    customer = db.get(User, customer_id)
    if (
        customer is None
        or not customer.is_active
        or customer.role != UserRole.CUSTOMER
    ):
        raise MessageRecipientError("The event customer is not active")
    return customer


def list_event_messages(
    db: Session,
    *,
    event_id: int,
    current_user: User,
    skip: int,
    limit: int,
) -> list[EventMessage]:
    event = _get_event(db, event_id)
    _ensure_can_access_event(db, current_user, event)
    return message_repository.list_event_messages(
        db,
        event_id=event_id,
        participant_id=(
            None if current_user.role == UserRole.ADMIN else current_user.id
        ),
        skip=skip,
        limit=limit,
    )


def create_event_message(
    db: Session,
    *,
    event_id: int,
    current_user: User,
    message_data: MessageCreate,
) -> EventMessage:
    event = _get_event(db, event_id)
    _ensure_can_access_event(db, current_user, event)

    if current_user.role == UserRole.CUSTOMER:
        recipient_id = message_data.recipient_id or event.organizer_id
        if recipient_id is None:
            raise MessageRecipientError(
                "Choose an assigned organizer to message"
            )
        _get_active_organizer(db, recipient_id)
        if not _organizer_is_assigned(db, event, recipient_id):
            raise MessageRecipientError(
                "You can message only an organizer assigned to this event or booking"
            )
    elif current_user.role == UserRole.ORGANIZER:
        recipient_id = event.customer_id
        _get_active_customer(db, recipient_id)
        if (
            message_data.recipient_id is not None
            and message_data.recipient_id != recipient_id
        ):
            raise MessagePermissionError(
                "Organizers may message only the event's customer"
            )
    elif current_user.role == UserRole.ADMIN:
        recipient_id = message_data.recipient_id
        if recipient_id is None:
            raise MessageRecipientError(
                "Admins must specify a message recipient"
            )
        if recipient_id == event.customer_id:
            _get_active_customer(db, recipient_id)
        else:
            _get_active_organizer(db, recipient_id)
            if not _organizer_is_assigned(db, event, recipient_id):
                raise MessageRecipientError(
                    "The recipient must be assigned to this event or booking"
                )
    else:
        raise MessagePermissionError

    if recipient_id == current_user.id:
        raise MessageRecipientError("You cannot send a message to yourself")

    return message_repository.create_event_message(
        db,
        event_id=event_id,
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=message_data.content,
    )


def mark_event_message_read(
    db: Session,
    *,
    event_id: int,
    message_id: int,
    current_user: User,
) -> EventMessage:
    event = _get_event(db, event_id)
    _ensure_can_access_event(db, current_user, event)

    message = message_repository.get_event_message(
        db, event_id=event_id, message_id=message_id
    )
    if message is None:
        raise MessageNotFoundError
    if (
        current_user.role != UserRole.ADMIN
        and message.recipient_id != current_user.id
    ):
        raise MessagePermissionError(
            "Only the message recipient can mark it as read"
        )
    return message_repository.mark_message_read(db, message)
