from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.package import Package


def get_by_id(db: Session, package_id: int) -> Package | None:
    return db.get(Package, package_id)


def list_packages(
    db: Session,
    *,
    event_category_id: int | None,
    skip: int,
    limit: int,
) -> list[Package]:
    statement = select(Package).order_by(Package.id)
    if event_category_id is not None:
        statement = statement.where(
            Package.event_categories.any(Category.id == event_category_id)
        )
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_package(
    db: Session,
    *,
    event_categories: list[Category],
    title: str,
    description: str,
    organizer_id: int | None,
    category_id: int,
    price: Decimal,
    price_unit: str,
    image_url: str | None,
    badge: str | None,
    max_guests: int | None,
    included_items: list[str],
    average_rating: float,
    review_count: int,
) -> Package:
    package = Package(
        title=title,
        description=description,
        organizer_id=organizer_id,
        category_id=category_id,
        price=price,
        price_unit=price_unit,
        image_url=image_url,
        badge=badge,
        max_guests=max_guests,
        included_items=included_items,
        average_rating=average_rating,
        review_count=review_count,
        event_categories=event_categories,
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


def update_package(
    db: Session,
    package: Package,
    *,
    event_categories: list[Category],
    title: str,
    description: str,
    organizer_id: int | None,
    category_id: int,
    price: Decimal,
    price_unit: str,
    image_url: str | None,
    badge: str | None,
    max_guests: int | None,
    included_items: list[str],
    average_rating: float,
    review_count: int,
    is_active: bool,
) -> Package:
    package.title = title
    package.description = description
    package.organizer_id = organizer_id
    package.category_id = category_id
    package.price = price
    package.price_unit = price_unit
    package.image_url = image_url
    package.badge = badge
    package.max_guests = max_guests
    package.included_items = included_items
    package.average_rating = average_rating
    package.review_count = review_count
    package.is_active = is_active
    package.event_categories = event_categories
    db.commit()
    db.refresh(package)
    return package


def delete_package(db: Session, package: Package) -> None:
    db.delete(package)
    db.commit()
