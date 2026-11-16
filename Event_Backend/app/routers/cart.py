from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.core.security import require_roles
from app.database import get_db
from app.models.user import User
from app.schemas.commerce import CartItemCreate, CartItemRead, CartItemUpdate, CartRead
from app.services import commerce_service
from app.services.commerce_service import (
    CartItemNotFoundError,
    CatalogItemNotFoundError,
    CommerceConflictError,
    CommerceValidationError,
)

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartRead)
def get_cart(
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> CartRead:
    items = commerce_service.get_cart(db, customer.id)
    return CartRead(
        items=items,
        subtotal=sum((item.subtotal for item in items), Decimal("0.00")),
    )


@router.post(
    "/items",
    response_model=CartItemRead,
    status_code=status.HTTP_201_CREATED,
)
def add_cart_item(
    item_data: CartItemCreate,
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> CartItemRead:
    try:
        return commerce_service.add_cart_item(db, customer.id, item_data)
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
    except CommerceValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.patch("/items/{cart_item_id}", response_model=CartItemRead)
def update_cart_item(
    cart_item_id: int,
    item_data: CartItemUpdate,
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> CartItemRead:
    try:
        return commerce_service.update_cart_item(
            db, customer.id, cart_item_id, item_data
        )
    except CartItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        ) from exc
    except CatalogItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active package or service listing not found",
        ) from exc
    except CommerceValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.delete("/items/{cart_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart_item(
    cart_item_id: int,
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> Response:
    try:
        commerce_service.delete_cart_item(db, customer.id, cart_item_id)
    except CartItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> Response:
    commerce_service.clear_cart(db, customer.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
