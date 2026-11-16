from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.categories import EventStatus
from app.core.commerce import BookingStatus, CatalogItemType
from app.core.roles import UserRole
from app.models.booking import Booking
from app.models.cart_item import CartItem
from app.models.event import Event
from app.models.favorite import Favorite
from app.models.package import Package
from app.models.service_listing import ServiceListing
from app.models.user import User
from app.repositories import commerce_repository
from app.schemas.commerce import (
    BookingCheckout,
    BookingStatusUpdate,
    CartItemCreate,
    CartItemUpdate,
    FavoriteCreate,
)


class CatalogItemNotFoundError(Exception):
    pass


class CartItemNotFoundError(Exception):
    pass


class FavoriteNotFoundError(Exception):
    pass


class BookingNotFoundError(Exception):
    pass


class CommerceConflictError(Exception):
    pass


class CommerceValidationError(Exception):
    pass


class CommercePermissionError(Exception):
    pass


def _get_catalog_item(
    db: Session,
    *,
    package_id: int | None,
    service_listing_id: int | None,
) -> Package | ServiceListing:
    if package_id is not None:
        item = db.get(Package, package_id)
    elif service_listing_id is not None:
        item = db.get(ServiceListing, service_listing_id)
    else:
        raise CommerceValidationError(
            "Provide exactly one package or service listing"
        )

    if item is None or not item.is_active:
        raise CatalogItemNotFoundError
    return item


def _validate_quantity(price_unit: str, quantity: int) -> None:
    if price_unit == "per_event" and quantity != 1:
        raise CommerceValidationError(
            "Items priced per event must have quantity 1"
        )


def get_cart(db: Session, customer_id: int) -> list[CartItem]:
    return commerce_repository.list_cart_items(db, customer_id)


def add_cart_item(
    db: Session,
    customer_id: int,
    item_data: CartItemCreate,
) -> CartItem:
    item = _get_catalog_item(
        db,
        package_id=item_data.package_id,
        service_listing_id=item_data.service_listing_id,
    )
    _validate_quantity(item.price_unit, item_data.quantity)
    if commerce_repository.get_matching_cart_item(
        db,
        customer_id=customer_id,
        package_id=item_data.package_id,
        service_listing_id=item_data.service_listing_id,
    ):
        raise CommerceConflictError("This item is already in your cart")

    try:
        return commerce_repository.create_cart_item(
            db,
            customer_id=customer_id,
            package_id=item_data.package_id,
            service_listing_id=item_data.service_listing_id,
            quantity=item_data.quantity,
        )
    except IntegrityError as exc:
        db.rollback()
        raise CommerceConflictError("This item is already in your cart") from exc


def update_cart_item(
    db: Session,
    customer_id: int,
    cart_item_id: int,
    item_data: CartItemUpdate,
) -> CartItem:
    cart_item = commerce_repository.get_cart_item(
        db, customer_id=customer_id, cart_item_id=cart_item_id
    )
    if cart_item is None:
        raise CartItemNotFoundError
    catalog_item = _get_catalog_item(
        db,
        package_id=cart_item.package_id,
        service_listing_id=cart_item.service_listing_id,
    )
    _validate_quantity(catalog_item.price_unit, item_data.quantity)
    return commerce_repository.update_cart_item_quantity(
        db, cart_item, item_data.quantity
    )


def delete_cart_item(
    db: Session, customer_id: int, cart_item_id: int
) -> None:
    cart_item = commerce_repository.get_cart_item(
        db, customer_id=customer_id, cart_item_id=cart_item_id
    )
    if cart_item is None:
        raise CartItemNotFoundError
    commerce_repository.delete_cart_item(db, cart_item)


def clear_cart(db: Session, customer_id: int) -> None:
    commerce_repository.clear_cart(db, customer_id)


def get_favorites(db: Session, customer_id: int) -> list[Favorite]:
    return commerce_repository.list_favorites(db, customer_id)


def add_favorite(
    db: Session,
    customer_id: int,
    favorite_data: FavoriteCreate,
) -> Favorite:
    _get_catalog_item(
        db,
        package_id=favorite_data.package_id,
        service_listing_id=favorite_data.service_listing_id,
    )
    if commerce_repository.get_matching_favorite(
        db,
        customer_id=customer_id,
        package_id=favorite_data.package_id,
        service_listing_id=favorite_data.service_listing_id,
    ):
        raise CommerceConflictError("This item is already saved")

    try:
        return commerce_repository.create_favorite(
            db,
            customer_id=customer_id,
            package_id=favorite_data.package_id,
            service_listing_id=favorite_data.service_listing_id,
        )
    except IntegrityError as exc:
        db.rollback()
        raise CommerceConflictError("This item is already saved") from exc


def delete_favorite(
    db: Session, customer_id: int, favorite_id: int
) -> None:
    favorite = commerce_repository.get_favorite(
        db, customer_id=customer_id, favorite_id=favorite_id
    )
    if favorite is None:
        raise FavoriteNotFoundError
    commerce_repository.delete_favorite(db, favorite)


def checkout_cart(
    db: Session,
    customer: User,
    checkout_data: BookingCheckout,
) -> list[Booking]:
    event = db.get(Event, checkout_data.event_id)
    if event is None:
        raise CommerceValidationError("Event not found")
    if event.customer_id != customer.id:
        raise CommercePermissionError("You can book only for your own event")
    if event.status in (EventStatus.CANCELLED, EventStatus.COMPLETED):
        raise CommerceValidationError(
            "Bookings cannot be placed for cancelled or completed events"
        )

    cart_items = commerce_repository.list_cart_items(db, customer.id)
    if not cart_items:
        raise CommerceConflictError("Your cart is empty")

    bookings: list[Booking] = []
    for cart_item in cart_items:
        product = _get_catalog_item(
            db,
            package_id=cart_item.package_id,
            service_listing_id=cart_item.service_listing_id,
        )
        _validate_quantity(product.price_unit, cart_item.quantity)
        bookings.append(
            Booking(
                customer_id=customer.id,
                organizer_id=None,
                event_id=event.id,
                item_type=(
                    CatalogItemType.PACKAGE
                    if cart_item.package_id is not None
                    else CatalogItemType.SERVICE
                ),
                package_id=cart_item.package_id,
                service_listing_id=cart_item.service_listing_id,
                item_title=product.title,
                price_unit=product.price_unit,
                quantity=cart_item.quantity,
                unit_price=product.price,
                total_price=product.price * cart_item.quantity,
                status=(
                    BookingStatus.CONFIRMED
                    if event.status == EventStatus.CONFIRMED
                    else BookingStatus.REQUESTED
                ),
            )
        )

    try:
        db.add_all(bookings)
        for cart_item in cart_items:
            db.delete(cart_item)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise CommerceConflictError(
            "Checkout could not be completed; your cart was not cleared"
        ) from exc

    for booking in bookings:
        db.refresh(booking)
    return bookings


def list_bookings(db: Session, current_user: User) -> list[Booking]:
    customer_id = (
        current_user.id if current_user.role == UserRole.CUSTOMER else None
    )
    organizer_id = (
        current_user.id if current_user.role == UserRole.ORGANIZER else None
    )
    return commerce_repository.list_bookings(
        db, customer_id=customer_id, organizer_id=organizer_id
    )


def get_booking_for_user(
    db: Session, booking_id: int, current_user: User
) -> Booking:
    booking = commerce_repository.get_booking(db, booking_id)
    if booking is None:
        raise BookingNotFoundError
    if (
        current_user.role == UserRole.CUSTOMER
        and booking.customer_id != current_user.id
    ):
        raise CommercePermissionError(
            "You can view only your own bookings"
        )
    if current_user.role == UserRole.ORGANIZER:
        event = db.get(Event, booking.event_id)
        if (
            booking.organizer_id != current_user.id
            and (event is None or event.organizer_id != current_user.id)
        ):
            raise CommercePermissionError(
                "You can view only bookings assigned to you or your event"
            )
    return booking


def update_booking_status(
    db: Session,
    booking_id: int,
    current_user: User,
    status_data: BookingStatusUpdate,
) -> Booking:
    booking = get_booking_for_user(db, booking_id, current_user)
    if current_user.role == UserRole.CUSTOMER:
        if status_data.status != BookingStatus.CANCELLED:
            raise CommercePermissionError(
                "Customers can only cancel their own booking"
            )
        if booking.status != BookingStatus.REQUESTED:
            raise CommerceConflictError(
                "Only requested bookings can be cancelled by the customer"
            )
    elif current_user.role != UserRole.ADMIN:
        if booking.status != BookingStatus.CONFIRMED:
            raise CommercePermissionError(
                "Only admins can accept or decline booking requests"
            )
        allowed_transitions = {
            BookingStatus.CONFIRMED: {
                BookingStatus.COMPLETED,
                BookingStatus.CANCELLED,
            },
            BookingStatus.REQUESTED: set(),
            BookingStatus.CANCELLED: set(),
            BookingStatus.COMPLETED: set(),
        }
        if status_data.status not in allowed_transitions[booking.status]:
            raise CommerceConflictError(
                f"Cannot change a {booking.status.value} booking to "
                f"{status_data.status.value}"
            )
    elif (
        booking.status == BookingStatus.REQUESTED
        and status_data.status == BookingStatus.CONFIRMED
    ):
        raise CommerceConflictError(
            "Accept the related event to confirm its service bookings"
        )
    return commerce_repository.update_booking_status(
        db, booking, status_data.status
    )


def assign_booking_organizer(
    db: Session, booking_id: int, organizer_id: int
) -> Booking:
    booking = commerce_repository.get_booking(db, booking_id)
    if booking is None:
        raise BookingNotFoundError
    if booking.status != BookingStatus.CONFIRMED:
        raise CommerceConflictError(
            "Accept the booking before assigning an organizer"
        )
    organizer = db.get(User, organizer_id)
    if (
        organizer is None
        or not organizer.is_active
        or organizer.role != UserRole.ORGANIZER
    ):
        raise CommerceValidationError("An active organizer account is required")
    return commerce_repository.assign_booking_organizer(
        db, booking, organizer_id
    )
