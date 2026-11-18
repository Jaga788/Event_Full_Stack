from pydantic import BaseModel

from app.schemas.user import UserRead


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class AuthenticatedUserRead(BaseModel):
    user: UserRead
