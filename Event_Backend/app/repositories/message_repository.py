from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.message import EventMessage


def list_event_messages(
    db: Session,
    *,
    event_id: int,
    participant_id: int | None,
    skip: int,
    limit: int,
) -> list[EventMessage]:
    statement = select(EventMessage).where(EventMessage.event_id == event_id)
    if participant_id is not None:
        statement = statement.where(
            or_(
                EventMessage.sender_id == participant_id,
                EventMessage.recipient_id == participant_id,
            )
        )
    statement = statement.order_by(EventMessage.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_event_message(
    db: Session,
    *,
    event_id: int,
    message_id: int,
) -> EventMessage | None:
    statement = select(EventMessage).where(
        EventMessage.event_id == event_id,
        EventMessage.id == message_id,
    )
    return db.scalar(statement)


def create_event_message(
    db: Session,
    *,
    event_id: int,
    sender_id: int,
    recipient_id: int,
    content: str,
) -> EventMessage:
    message = EventMessage(
        event_id=event_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def mark_message_read(db: Session, message: EventMessage) -> EventMessage:
    if message.read_at is None:
        message.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(message)
    return message
