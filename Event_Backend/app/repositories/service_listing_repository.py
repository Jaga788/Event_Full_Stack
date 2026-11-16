from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.service_listing import ServiceListing


def get_by_id(db: Session, listing_id: int) -> ServiceListing | None:
    return db.get(ServiceListing, listing_id)


def list_listings(
    db: Session,
    *,
    category_id: int | None,
    event_category_id: int | None,
    skip: int,
    limit: int,
) -> list[ServiceListing]:
    statement = select(ServiceListing).order_by(ServiceListing.id)
    if category_id is not None:
        statement = statement.where(ServiceListing.category_id == category_id)
    if event_category_id is not None:
        statement = statement.where(
            ServiceListing.event_categories.any(Category.id == event_category_id)
        )
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_listing(
    db: Session,
    *,
    event_categories: list[Category],
    title: str,
    description: str | None,
    category_id: int,
    organizer_id: int | None,
    price: Decimal,
    price_unit: str,
    dietary_type: str | None,
    image_url: str | None,
) -> ServiceListing:
    listing = ServiceListing(
        title=title,
        description=description,
        category_id=category_id,
        organizer_id=organizer_id,
        price=price,
        price_unit=price_unit,
        dietary_type=dietary_type,
        image_url=image_url,
    )
    listing.event_categories = event_categories
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def update_listing(
    db: Session,
    listing: ServiceListing,
    *,
    event_categories: list[Category],
    title: str,
    description: str | None,
    category_id: int,
    organizer_id: int | None,
    price: Decimal,
    price_unit: str,
    dietary_type: str | None,
    image_url: str | None,
    is_active: bool,
) -> ServiceListing:
    listing.title = title
    listing.description = description
    listing.category_id = category_id
    listing.organizer_id = organizer_id
    listing.price = price
    listing.price_unit = price_unit
    listing.dietary_type = dietary_type
    listing.image_url = image_url
    listing.is_active = is_active
    listing.event_categories = event_categories
    db.commit()
    db.refresh(listing)
    return listing


def delete_listing(db: Session, listing: ServiceListing) -> None:
    db.delete(listing)
    db.commit()
