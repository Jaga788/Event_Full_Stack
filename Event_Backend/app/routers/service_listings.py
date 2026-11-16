from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.core.security import require_roles
from app.database import get_db
from app.models.user import User
from app.schemas.service_listing import (
    ServiceListingCreate,
    ServiceListingRead,
    ServiceListingUpdate,
)
from app.services import service_listing_service
from app.services.service_listing_service import (
    ListingNotFoundError,
    ListingReferenceError,
)

router = APIRouter(prefix="/services", tags=["services"])


@router.post(
    "",
    response_model=ServiceListingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_listing(
    listing_data: ServiceListingCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> ServiceListingRead:
    try:
        return service_listing_service.create_listing(db, listing_data)
    except ListingReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[ServiceListingRead])
def list_listings(
    category_id: int | None = Query(default=None, gt=0),
    event_category_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ServiceListingRead]:
    return service_listing_service.list_listings(
        db,
        category_id=category_id,
        event_category_id=event_category_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{listing_id}", response_model=ServiceListingRead)
def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
) -> ServiceListingRead:
    try:
        return service_listing_service.get_listing(db, listing_id)
    except ListingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service listing not found",
        ) from exc


@router.put("/{listing_id}", response_model=ServiceListingRead)
def update_listing(
    listing_id: int,
    listing_data: ServiceListingUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> ServiceListingRead:
    try:
        return service_listing_service.update_listing(
            db, listing_id, listing_data
        )
    except ListingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service listing not found",
        ) from exc
    except ListingReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{listing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> Response:
    try:
        service_listing_service.delete_listing(db, listing_id)
    except ListingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service listing not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
