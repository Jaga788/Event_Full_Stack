from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.commerce import BookingStatus
from app.models.booking import Booking
from app.models.cart_item import CartItem
from app.models.event import Event
from app.models.favorite import Favorite


def list_cart_items(db: Session, customer_id: int) -> list[CartItem]:
    statement = (
        select(CartItem)
        .where(CartItem.customer_id == customer_id)
        .order_by(CartItem.id)
    )
    return list(db.scalars(statement).all())


def get_cart_item(
    db: Session, *, customer_id: int, cart_item_id: int
) -> CartItem | None:
    statement = select(CartItem).where(
        CartItem.customer_id == customer_id,
        CartItem.id == cart_item_id,
    )
    return db.scalar(statement)


def get_matching_cart_item(
    db: Session,
    *,
    customer_id: int,
    package_id: int | None,
    service_listing_id: int | None,
) -> CartItem | None:
    statement = select(CartItem).where(CartItem.customer_id == customer_id)
    if package_id is not None:
        statement = statement.where(CartItem.package_id == package_id)
    else:
        statement = statement.where(
            CartItem.service_listing_id == service_listing_id
        )
    return db.scalar(statement)


def create_cart_item(
    db: Session,
    *,
    customer_id: int,
    package_id: int | None,
    service_listing_id: int | None,
    quantity: int,
) -> CartItem:
    item = CartItem(
        customer_id=customer_id,
        package_id=package_id,
        service_listing_id=service_listing_id,
        quantity=quantity,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_cart_item_quantity(
    db: Session, item: CartItem, quantity: int
) -> CartItem:
    item.quantity = quantity
    db.commit()
    db.refresh(item)
    return item


def delete_cart_item(db: Session, item: CartItem) -> None:
    db.delete(item)
    db.commit()


def clear_cart(db: Session, customer_id: int) -> None:
    db.execute(delete(CartItem).where(CartItem.customer_id == customer_id))
    db.commit()


def list_favorites(db: Session, customer_id: int) -> list[Favorite]:
    statement = (
        select(Favorite)
        .where(Favorite.customer_id == customer_id)
        .order_by(Favorite.id)
    )
    return list(db.scalars(statement).all())


def get_favorite(
    db: Session, *, customer_id: int, favorite_id: int
) -> Favorite | None:
    statement = select(Favorite).where(
        Favorite.customer_id == customer_id,
        Favorite.id == favorite_id,
    )
    return db.scalar(statement)


def get_matching_favorite(
    db: Session,
    *,
    customer_id: int,
    package_id: int | None,
    service_listing_id: int | None,
) -> Favorite | None:
    statement = select(Favorite).where(Favorite.customer_id == customer_id)
    if package_id is not None:
        statement = statement.where(Favorite.package_id == package_id)
    else:
        statement = statement.where(
            Favorite.service_listing_id == service_listing_id
        )
    return db.scalar(statement)


def create_favorite(
    db: Session,
    *,
    customer_id: int,
    package_id: int | None,
    service_listing_id: int | None,
) -> Favorite:
    favorite = Favorite(
        customer_id=customer_id,
        package_id=package_id,
        service_listing_id=service_listing_id,
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


def delete_favorite(db: Session, favorite: Favorite) -> None:
    db.delete(favorite)
    db.commit()


def list_bookings(
    db: Session,
    *,
    customer_id: int | None,
    organizer_id: int | None,
) -> list[Booking]:
    statement = select(Booking).order_by(Booking.created_at.desc(), Booking.id.desc())
    if customer_id is not None:
        statement = statement.where(Booking.customer_id == customer_id)
    if organizer_id is not None:
        statement = statement.join(Event, Event.id == Booking.event_id).where(
            or_(
                Booking.organizer_id == organizer_id,
                Event.organizer_id == organizer_id,
            )
        )
    return list(db.scalars(statement).all())


def get_booking(db: Session, booking_id: int) -> Booking | None:
    return db.get(Booking, booking_id)


def update_booking_status(
    db: Session, booking: Booking, new_status: BookingStatus
) -> Booking:
    booking.status = new_status
    db.commit()
    db.refresh(booking)
    return booking


def assign_booking_organizer(
    db: Session, booking: Booking, organizer_id: int
) -> Booking:
    booking.organizer_id = organizer_id
    db.commit()
    db.refresh(booking)
    return booking
