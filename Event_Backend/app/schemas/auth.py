from pydantic import BaseModel

from app.schemas.user import UserRead


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthenticatedUserRead(BaseModel):
    user: UserRead
