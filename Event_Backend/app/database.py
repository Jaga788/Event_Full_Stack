
from sqlalchemy import create_engine
from sqlalchemy import select, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.categories import CategoryKind, EventStatus
from app.core.commerce import BookingStatus
from app.core.config import settings

database_url = make_url(settings.DATABASE_URL)
if database_url.drivername in {"postgres", "postgresql"}:
    database_url = database_url.set(drivername="postgresql+psycopg")

engine = create_engine(database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    from app.models.category import Category
    from app.models.booking import Booking
    from app.models.cart_item import CartItem
    from app.models.event import Event
    from app.models.favorite import Favorite
    from app.models.message import EventMessage
    from app.models.package import Package, package_event_categories
    from app.models.service_listing import ServiceListing, service_event_categories
    from app.models.user import User

    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            Category.__table__,
            Event.__table__,
            EventMessage.__table__,
            CartItem.__table__,
            Favorite.__table__,
            Booking.__table__,
            ServiceListing.__table__,
            service_event_categories,
            Package.__table__,
            package_event_categories,
        ],
    )
    seed_categories()
    with SessionLocal() as db:
        db.execute(
            update(Booking)
            .where(
                Booking.status == BookingStatus.REQUESTED,
                Booking.event_id.in_(
                    select(Event.id).where(
                        Event.status == EventStatus.CONFIRMED
                    )
                ),
            )
            .values(status=BookingStatus.CONFIRMED)
        )
        db.commit()


def seed_categories() -> None:
    from app.models.category import Category

    seed_data = (
        (CategoryKind.EVENT, "Wedding"),
        (CategoryKind.EVENT, "Engagement"),
        (CategoryKind.EVENT, "Birthday"),
        (CategoryKind.EVENT, "Maturity Function"),
        (CategoryKind.EVENT, "Baby Shower & Naming"),
        (CategoryKind.EVENT, "Corporate & Parties"),
        (CategoryKind.SERVICE, "Packages"),
        (CategoryKind.SERVICE, "Decoration"),
        (CategoryKind.SERVICE, "Catering"),
        (CategoryKind.SERVICE, "Photography"),
        (CategoryKind.SERVICE, "Entertainment"),
        (CategoryKind.SERVICE, "Beauty & Styling"),
        (CategoryKind.SERVICE, "Invitations & Gifts"),
    )
    with SessionLocal() as db:
        for kind, name in seed_data:
            category = db.scalar(
                select(Category).where(
                    Category.kind == kind,
                    Category.name == name,
                )
            )
            if category is None:
                db.add(Category(kind=kind, name=name))
        db.commit()
