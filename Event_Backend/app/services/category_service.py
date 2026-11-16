from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.categories import CategoryKind
from app.models.category import Category
from app.repositories import category_repository
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryConflictError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


def list_categories(
    db: Session,
    *,
    kind: CategoryKind | None,
    skip: int,
    limit: int,
) -> list[Category]:
    return category_repository.list_categories(
        db, kind=kind, skip=skip, limit=limit
    )


def get_category(db: Session, category_id: int) -> Category:
    category = category_repository.get_by_id(db, category_id)
    if category is None:
        raise CategoryNotFoundError
    return category


def create_category(db: Session, category_data: CategoryCreate) -> Category:
    if (
        category_repository.get_by_name(
            db, category_data.kind, category_data.name
        )
        is not None
    ):
        raise CategoryConflictError

    try:
        return category_repository.create_category(
            db,
            name=category_data.name,
            kind=category_data.kind,
            description=category_data.description,
        )
    except IntegrityError as exc:
        db.rollback()
        raise CategoryConflictError from exc


def update_category(
    db: Session,
    category_id: int,
    category_data: CategoryUpdate,
) -> Category:
    category = get_category(db, category_id)
    existing = category_repository.get_by_name(
        db, category.kind, category_data.name
    )
    if existing is not None and existing.id != category_id:
        raise CategoryConflictError

    try:
        return category_repository.update_category(
            db,
            category,
            name=category_data.name,
            description=category_data.description,
            is_active=category_data.is_active,
        )
    except IntegrityError as exc:
        db.rollback()
        raise CategoryConflictError from exc


def delete_category(db: Session, category_id: int) -> None:
    category = get_category(db, category_id)
    try:
        category_repository.delete_category(db, category)
    except IntegrityError as exc:
        db.rollback()
        raise CategoryConflictError from exc
