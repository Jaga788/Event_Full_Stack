from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.core.security import require_roles
from app.database import get_db
from app.models.user import User
from app.schemas.commerce import FavoriteCreate, FavoriteRead
from app.services import commerce_service
from app.services.commerce_service import (
    CatalogItemNotFoundError,
    CommerceConflictError,
    FavoriteNotFoundError,
)

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoriteRead])
def list_favorites(
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> list[FavoriteRead]:
    return commerce_service.get_favorites(db, customer.id)


@router.post(
    "",
    response_model=FavoriteRead,
    status_code=status.HTTP_201_CREATED,
)
def add_favorite(
    favorite_data: FavoriteCreate,
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> FavoriteRead:
    try:
        return commerce_service.add_favorite(
            db, customer.id, favorite_data
        )
    except CatalogItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active package or service listing not found",
        ) from exc
    except CommerceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(
    favorite_id: int,
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> Response:
    try:
        commerce_service.delete_favorite(db, customer.id, favorite_id)
    except FavoriteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved item not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
