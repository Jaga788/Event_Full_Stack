from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=5000)
    recipient_id: int | None = Field(default=None, gt=0)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        content = value.strip()
        if not content:
            raise ValueError("Message content cannot be blank")
        return content


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    sender_id: int
    sender_name: str
    recipient_id: int
    recipient_name: str
    content: str
    created_at: datetime
    read_at: datetime | None
