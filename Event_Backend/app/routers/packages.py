from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.core.security import require_roles
from app.database import get_db
from app.models.user import User
from app.schemas.package import PackageCreate, PackageRead, PackageUpdate
from app.services import package_service
from app.services.package_service import (
    PackageNotFoundError,
    PackageReferenceError,
)

router = APIRouter(prefix="/packages", tags=["packages"])


@router.post("", response_model=PackageRead, status_code=status.HTTP_201_CREATED)
def create_package(
    package_data: PackageCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> PackageRead:
    try:
        return package_service.create_package(db, package_data)
    except PackageReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[PackageRead])
def list_packages(
    event_category_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[PackageRead]:
    return package_service.list_packages(
        db,
        event_category_id=event_category_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{package_id}", response_model=PackageRead)
def get_package(
    package_id: int,
    db: Session = Depends(get_db),
) -> PackageRead:
    try:
        return package_service.get_package(db, package_id)
    except PackageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        ) from exc


@router.put("/{package_id}", response_model=PackageRead)
def update_package(
    package_id: int,
    package_data: PackageUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> PackageRead:
    try:
        return package_service.update_package(db, package_id, package_data)
    except PackageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        ) from exc
    except PackageReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
    package_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> Response:
    try:
        package_service.delete_package(db, package_id)
    except PackageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
