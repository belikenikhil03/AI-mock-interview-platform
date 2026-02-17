"""Authentication service."""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta
from ...models.user import User
from ...api.schemas.user import UserCreate, UserLogin
from ...core.security import get_password_hash, verify_password, create_access_token
from ...core.config import settings


class AuthService:
    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> Optional[User]:
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user or not verify_password(login_data.password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
    
    @staticmethod
    def create_user_token(user: User) -> str:
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
