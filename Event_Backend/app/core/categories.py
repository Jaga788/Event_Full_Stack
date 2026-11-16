from enum import Enum


class CategoryKind(str, Enum):
    EVENT = "event"
    SERVICE = "service"


class EventStatus(str, Enum):
    PLANNING = "planning"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
