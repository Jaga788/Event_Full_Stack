from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.core.security import get_current_user, require_roles
from app.database import get_db
from app.models.user import User
from app.schemas.commerce import (
    BookingAssignmentUpdate,
    BookingCheckout,
    BookingRead,
    BookingStatusUpdate,
)
from app.services import commerce_service
from app.services.commerce_service import (
    BookingNotFoundError,
    CatalogItemNotFoundError,
    CommerceConflictError,
    CommercePermissionError,
    CommerceValidationError,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post(
    "/checkout",
    response_model=list[BookingRead],
    status_code=status.HTTP_201_CREATED,
)
def checkout_cart(
    checkout_data: BookingCheckout,
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> list[BookingRead]:
    try:
        return commerce_service.checkout_cart(db, customer, checkout_data)
    except CatalogItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A cart item is no longer available",
        ) from exc
    except CommercePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except CommerceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except CommerceValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[BookingRead])
def list_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.ORGANIZER,
            UserRole.CUSTOMER,
        )
    ),
) -> list[BookingRead]:
    return commerce_service.list_bookings(db, current_user)


@router.get("/{booking_id}", response_model=BookingRead)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.ORGANIZER,
            UserRole.CUSTOMER,
        )
    ),
) -> BookingRead:
    try:
        return commerce_service.get_booking_for_user(
            db, booking_id, current_user
        )
    except BookingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        ) from exc
    except CommercePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.patch("/{booking_id}/status", response_model=BookingRead)
def update_booking_status(
    booking_id: int,
    status_data: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.ORGANIZER,
            UserRole.CUSTOMER,
        )
    ),
) -> BookingRead:
    try:
        return commerce_service.update_booking_status(
            db, booking_id, current_user, status_data
        )
    except BookingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        ) from exc
    except CommercePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except CommerceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.patch("/{booking_id}/assignment", response_model=BookingRead)
def assign_booking_organizer(
    booking_id: int,
    assignment: BookingAssignmentUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> BookingRead:
    try:
        return commerce_service.assign_booking_organizer(
            db, booking_id, assignment.organizer_id
        )
    except BookingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        ) from exc
    except CommerceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except CommerceValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
