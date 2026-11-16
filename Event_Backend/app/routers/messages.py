from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.message import MessageCreate, MessageRead
from app.services import message_service
from app.services.message_service import (
    MessageEventNotFoundError,
    MessageNotFoundError,
    MessagePermissionError,
    MessageRecipientError,
)

router = APIRouter(
    prefix="/events/{event_id}/messages",
    tags=["event messages"],
)


@router.get("", response_model=list[MessageRead])
def list_messages(
    event_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageRead]:
    try:
        return message_service.list_event_messages(
            db,
            event_id=event_id,
            current_user=current_user,
            skip=skip,
            limit=limit,
        )
    except MessageEventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    except MessagePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this event conversation",
        ) from exc


@router.post(
    "",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    event_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageRead:
    try:
        return message_service.create_event_message(
            db,
            event_id=event_id,
            current_user=current_user,
            message_data=message_data,
        )
    except MessageEventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    except MessagePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc) or "You cannot message this event customer",
        ) from exc
    except MessageRecipientError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.patch("/{message_id}/read", response_model=MessageRead)
def mark_message_read(
    event_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageRead:
    try:
        return message_service.mark_event_message_read(
            db,
            event_id=event_id,
            message_id=message_id,
            current_user=current_user,
        )
    except MessageEventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    except MessageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        ) from exc
    except MessagePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc) or "You cannot mark this message as read",
        ) from exc
