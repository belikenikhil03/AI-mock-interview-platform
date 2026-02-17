"""
Authentication service - handles all auth business logic.
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta

from app.models.user import User
from app.api.schemas.user import UserCreate, UserLogin
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings


class AuthService:

    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        """
        Register a new user.
        Raises ValueError if email already exists.
        """
        # Check if email already registered
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise ValueError("Email already registered")

        # Create user with hashed password
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password)
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> Optional[User]:
        """
        Verify email + password. Returns user if valid, None if not.
        """
        user = db.query(User).filter(User.email == login_data.email).first()

        if not user:
            return None
        if not verify_password(login_data.password, user.hashed_password):
            return None
        if not user.is_active:
            return None

        return user

    @staticmethod
    def create_user_token(user: User) -> str:
        """Create a JWT access token for the user."""
        expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(
            data={"sub": str(user.id)},
            expires_delta=expires
        )

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Fetch user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Fetch user by email."""
        return db.query(User).filter(User.email == email).first()
