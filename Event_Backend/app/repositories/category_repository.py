from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.categories import CategoryKind
from app.models.category import Category


def get_by_id(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_by_name(db: Session, kind: CategoryKind, name: str) -> Category | None:
    statement = select(Category).where(
        Category.kind == kind,
        Category.name == name,
    )
    return db.scalar(statement)


def list_categories(
    db: Session,
    *,
    kind: CategoryKind | None,
    skip: int,
    limit: int,
) -> list[Category]:
    statement = select(Category).order_by(Category.kind, Category.name)
    if kind is not None:
        statement = statement.where(Category.kind == kind)
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_category(
    db: Session,
    *,
    name: str,
    kind: CategoryKind,
    description: str | None,
) -> Category:
    category = Category(name=name, kind=kind, description=description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    category: Category,
    *,
    name: str,
    description: str | None,
    is_active: bool,
) -> Category:
    category.name = name
    category.description = description
    category.is_active = is_active
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()
