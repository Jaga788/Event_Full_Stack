from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.roles import UserRole
from app.models.user import User
from app.repositories import user_repository
from app.schemas.user import UserCreate, UserUpdate


class UserAlreadyExistsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class UserDeletionConflictError(Exception):
    pass


def create_user(db: Session, user_data: UserCreate) -> User:
    if user_repository.get_by_email(db, str(user_data.email)) is not None:
        raise UserAlreadyExistsError

    try:
        return user_repository.create_user(
            db,
            full_name=user_data.full_name,
            email=str(user_data.email),
            hashed_password=hash_password(user_data.password),
        )
    except IntegrityError as exc:
        db.rollback()
        raise UserAlreadyExistsError from exc


def list_users(db: Session, skip: int, limit: int) -> list[User]:
    return user_repository.list_users(db, skip, limit)


def get_user(db: Session, user_id: int) -> User:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise UserNotFoundError
    return user


def update_user(db: Session, user_id: int, user_data: UserUpdate) -> User:
    user = get_user(db, user_id)
    email = str(user_data.email)
    existing_user = user_repository.get_by_email(db, email)
    if existing_user is not None and existing_user.id != user_id:
        raise UserAlreadyExistsError

    hashed_password = (
        hash_password(user_data.password) if user_data.password is not None else None
    )
    try:
        return user_repository.update_user(
            db,
            user,
            full_name=user_data.full_name,
            email=email,
            hashed_password=hashed_password,
        )
    except IntegrityError as exc:
        db.rollback()
        raise UserAlreadyExistsError from exc


def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)
    try:
        user_repository.delete_user(db, user)
    except IntegrityError as exc:
        db.rollback()
        raise UserDeletionConflictError(
            "Cannot delete a user who is still referenced by events or listings"
        ) from exc


def update_user_role(db: Session, user_id: int, role: UserRole) -> User:
    user = get_user(db, user_id)
    return user_repository.update_role(db, user, role)
