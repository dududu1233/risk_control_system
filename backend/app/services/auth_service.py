from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.auth import User


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if not user or user.status != "ENABLED":
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
