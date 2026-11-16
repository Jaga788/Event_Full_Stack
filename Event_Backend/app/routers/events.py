from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.core.security import get_current_user, require_roles
from app.database import get_db
from app.models.user import User
from app.schemas.event import (
    EventAssignmentUpdate,
    EventCreate,
    EventRead,
    EventStatusUpdate,
    EventUpdate,
)
from app.services import event_service
from app.services.event_service import EventNotFoundError, EventReferenceError

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.CUSTOMER)
    ),
) -> EventRead:
    if event_data.organizer_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assign an organizer after accepting the event request",
        )
    if current_user.role == UserRole.CUSTOMER:
        if event_data.customer_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customers can only create events for their own account",
            )
        customer_id = current_user.id
    else:
        if event_data.customer_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="customer_id is required when an admin creates an event",
            )
        customer_id = event_data.customer_id
    try:
        return event_service.create_event(
            db, event_data, customer_id=customer_id
        )
    except EventReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[EventRead])
def list_events(
    category_id: int | None = Query(default=None, gt=0),
    customer_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EventRead]:
    if current_user.role == UserRole.CUSTOMER:
        if customer_id is not None and customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customers may only view their own events",
            )
        customer_id = current_user.id
    organizer_id = (
        current_user.id if current_user.role == UserRole.ORGANIZER else None
    )
    return event_service.list_events(
        db,
        category_id=category_id,
        customer_id=customer_id,
        organizer_id=organizer_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{event_id}", response_model=EventRead)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventRead:
    try:
        event = event_service.get_event(db, event_id)
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    if (
        current_user.role == UserRole.CUSTOMER
        and event.customer_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers may only view their own events",
        )
    if (
        current_user.role == UserRole.ORGANIZER
        and not event_service.organizer_has_event_access(
            db, event, current_user.id
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only view events assigned to you",
        )
    return event


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: int,
    event_data: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventRead:
    if current_user.role == UserRole.ORGANIZER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizers cannot edit event details",
        )
    try:
        event = event_service.get_event(db, event_id)
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    if (
        current_user.role == UserRole.CUSTOMER
        and event.customer_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers may only update their own events",
        )
    if current_user.role == UserRole.CUSTOMER and event_data.customer_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers cannot reassign event ownership",
        )
    if current_user.role == UserRole.CUSTOMER:
        if (
            event_data.organizer_id is not None
            and event_data.organizer_id != event.organizer_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customers cannot assign event organizers",
            )
        event_data = event_data.model_copy(
            update={"organizer_id": event.organizer_id}
        )
    elif event_data.organizer_id != event.organizer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Use the admin assignment action to assign an organizer",
        )
    if (
        current_user.role == UserRole.CUSTOMER
        and event_data.status != event.status
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and organizers can change event status",
        )
    try:
        return event_service.update_event(
            db,
            event_id,
            event_data,
            customer_id=event_data.customer_id,
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    except EventReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.patch("/{event_id}/assignment", response_model=EventRead)
def assign_event_organizer(
    event_id: int,
    assignment: EventAssignmentUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> EventRead:
    try:
        return event_service.assign_event_organizer(
            db, event_id, assignment.organizer_id
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    except EventReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.patch("/{event_id}/status", response_model=EventRead)
def update_event_status(
    event_id: int,
    status_data: EventStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.ORGANIZER)
    ),
) -> EventRead:
    try:
        return event_service.update_event_status(
            db, event_id, status_data.status, current_user
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    except EventReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        event = event_service.get_event(db, event_id)
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    if (
        current_user.role == UserRole.CUSTOMER
        and event.customer_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers may only delete their own events",
        )
    if current_user.role == UserRole.ORGANIZER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizers cannot delete events",
        )
    event_service.delete_event(db, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
