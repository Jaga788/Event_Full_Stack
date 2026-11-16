from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.models.user import User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def list_users(db: Session, skip: int, limit: int) -> list[User]:
    statement = select(User).order_by(User.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    hashed_password: str,
) -> User:
    user = User(
        full_name=full_name,
        email=email,
        hashed_password=hashed_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user: User,
    *,
    full_name: str,
    email: str,
    hashed_password: str | None,
) -> User:
    user.full_name = full_name
    user.email = email
    if hashed_password is not None:
        user.hashed_password = hashed_password
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def update_role(db: Session, user: User, role: UserRole) -> User:
    user.role = role
    db.commit()
    db.refresh(user)
    return user
