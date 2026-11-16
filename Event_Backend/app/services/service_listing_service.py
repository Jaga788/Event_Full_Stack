from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.categories import CategoryKind
from app.core.roles import UserRole
from app.models.category import Category
from app.models.service_listing import ServiceListing
from app.models.user import User
from app.repositories import category_repository, service_listing_repository
from app.schemas.service_listing import ServiceListingCreate, ServiceListingUpdate


class ListingNotFoundError(Exception):
    pass


class ListingReferenceError(Exception):
    pass


def _validate_category(
    db: Session, category_id: int, kind: CategoryKind
) -> Category:
    category = category_repository.get_by_id(db, category_id)
    if category is None or category.kind != kind or not category.is_active:
        raise ListingReferenceError(f"Active {kind.value} category not found")
    return category


def _validate_organizer(db: Session, organizer_id: int | None) -> None:
    if organizer_id is None:
        return
    organizer = db.get(User, organizer_id)
    if (
        organizer is None
        or not organizer.is_active
        or organizer.role != UserRole.ORGANIZER
    ):
        raise ListingReferenceError("An active organizer account is required")


def _validate_dietary_type(category: Category, dietary_type: str | None) -> None:
    if category.name.strip().casefold() == "catering" and dietary_type is None:
        raise ListingReferenceError(
            "Catering listings require a dietary type"
        )


def _validate_event_categories(
    db: Session, event_category_ids: list[int]
) -> list[Category]:
    if len(event_category_ids) != len(set(event_category_ids)):
        raise ListingReferenceError("Event category IDs must be unique")

    categories = [
        _validate_category(db, category_id, CategoryKind.EVENT)
        for category_id in event_category_ids
    ]
    return categories


def list_listings(
    db: Session,
    *,
    category_id: int | None,
    event_category_id: int | None,
    skip: int,
    limit: int,
) -> list[ServiceListing]:
    return service_listing_repository.list_listings(
        db,
        category_id=category_id,
        event_category_id=event_category_id,
        skip=skip,
        limit=limit,
    )


def get_listing(db: Session, listing_id: int) -> ServiceListing:
    listing = service_listing_repository.get_by_id(db, listing_id)
    if listing is None:
        raise ListingNotFoundError
    return listing


def create_listing(
    db: Session, listing_data: ServiceListingCreate
) -> ServiceListing:
    category = _validate_category(
        db, listing_data.category_id, CategoryKind.SERVICE
    )
    _validate_dietary_type(category, listing_data.dietary_type)
    _validate_organizer(db, listing_data.organizer_id)
    event_categories = _validate_event_categories(
        db, listing_data.event_category_ids
    )
    try:
        return service_listing_repository.create_listing(
            db,
            title=listing_data.title,
            description=listing_data.description,
            category_id=listing_data.category_id,
            organizer_id=listing_data.organizer_id,
            price=listing_data.price,
            price_unit=listing_data.price_unit,
            dietary_type=listing_data.dietary_type,
            image_url=listing_data.image_url,
            event_categories=event_categories,
        )
    except IntegrityError as exc:
        db.rollback()
        raise ListingReferenceError("A service listing reference is invalid") from exc


def update_listing(
    db: Session,
    listing_id: int,
    listing_data: ServiceListingUpdate,
) -> ServiceListing:
    listing = get_listing(db, listing_id)
    category = _validate_category(
        db, listing_data.category_id, CategoryKind.SERVICE
    )
    if listing.category_id != listing_data.category_id:
        _validate_dietary_type(category, listing_data.dietary_type)
    _validate_organizer(db, listing_data.organizer_id)
    event_categories = _validate_event_categories(
        db, listing_data.event_category_ids
    )
    try:
        return service_listing_repository.update_listing(
            db,
            listing,
            title=listing_data.title,
            description=listing_data.description,
            category_id=listing_data.category_id,
            organizer_id=listing_data.organizer_id,
            price=listing_data.price,
            price_unit=listing_data.price_unit,
            dietary_type=listing_data.dietary_type,
            image_url=listing_data.image_url,
            is_active=listing_data.is_active,
            event_categories=event_categories,
        )
    except IntegrityError as exc:
        db.rollback()
        raise ListingReferenceError("A service listing reference is invalid") from exc


def delete_listing(db: Session, listing_id: int) -> None:
    listing = get_listing(db, listing_id)
    service_listing_repository.delete_listing(db, listing)
