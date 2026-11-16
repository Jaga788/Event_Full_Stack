from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.categories import CategoryKind
from app.core.roles import UserRole
from app.models.category import Category
from app.models.package import Package
from app.models.user import User
from app.repositories import category_repository, package_repository
from app.schemas.package import PackageCreate, PackageUpdate


class PackageNotFoundError(Exception):
    pass


class PackageReferenceError(Exception):
    pass


def _get_package_category(db: Session) -> Category:
    category = category_repository.get_by_name(
        db, CategoryKind.SERVICE, "Packages"
    )
    if category is None or not category.is_active:
        raise PackageReferenceError("The Packages service category is unavailable")
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
        raise PackageReferenceError("An active organizer account is required")


def _get_event_categories(db: Session, category_ids: list[int]) -> list[Category]:
    if len(category_ids) != len(set(category_ids)):
        raise PackageReferenceError("Event category IDs must be unique")

    categories = []
    for category_id in category_ids:
        category = category_repository.get_by_id(db, category_id)
        if (
            category is None
            or category.kind != CategoryKind.EVENT
            or not category.is_active
        ):
            raise PackageReferenceError(
                f"Active event category {category_id} not found"
            )
        categories.append(category)
    return categories


def list_packages(
    db: Session,
    *,
    event_category_id: int | None,
    skip: int,
    limit: int,
) -> list[Package]:
    return package_repository.list_packages(
        db,
        event_category_id=event_category_id,
        skip=skip,
        limit=limit,
    )


def get_package(db: Session, package_id: int) -> Package:
    package = package_repository.get_by_id(db, package_id)
    if package is None:
        raise PackageNotFoundError
    return package


def create_package(db: Session, package_data: PackageCreate) -> Package:
    package_category = _get_package_category(db)
    _validate_organizer(db, package_data.organizer_id)
    event_categories = _get_event_categories(
        db, package_data.event_category_ids
    )
    try:
        return package_repository.create_package(
            db,
            event_categories=event_categories,
            title=package_data.title,
            description=package_data.description,
            organizer_id=package_data.organizer_id,
            category_id=package_category.id,
            price=package_data.price,
            price_unit=package_data.price_unit,
            image_url=package_data.image_url,
            badge=package_data.badge,
            max_guests=package_data.max_guests,
            included_items=package_data.included_items,
            average_rating=package_data.average_rating,
            review_count=package_data.review_count,
        )
    except IntegrityError as exc:
        db.rollback()
        raise PackageReferenceError("A package reference is invalid") from exc


def update_package(
    db: Session,
    package_id: int,
    package_data: PackageUpdate,
) -> Package:
    package = get_package(db, package_id)
    package_category = _get_package_category(db)
    _validate_organizer(db, package_data.organizer_id)
    event_categories = _get_event_categories(
        db, package_data.event_category_ids
    )
    try:
        return package_repository.update_package(
            db,
            package,
            event_categories=event_categories,
            title=package_data.title,
            description=package_data.description,
            organizer_id=package_data.organizer_id,
            category_id=package_category.id,
            price=package_data.price,
            price_unit=package_data.price_unit,
            image_url=package_data.image_url,
            badge=package_data.badge,
            max_guests=package_data.max_guests,
            included_items=package_data.included_items,
            average_rating=package_data.average_rating,
            review_count=package_data.review_count,
            is_active=package_data.is_active,
        )
    except IntegrityError as exc:
        db.rollback()
        raise PackageReferenceError("A package reference is invalid") from exc


def delete_package(db: Session, package_id: int) -> None:
    package = get_package(db, package_id)
    package_repository.delete_package(db, package)
