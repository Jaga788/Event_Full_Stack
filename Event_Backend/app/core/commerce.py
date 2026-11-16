from enum import Enum


class CatalogItemType(str, Enum):
    PACKAGE = "package"
    SERVICE = "service"


class BookingStatus(str, Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
