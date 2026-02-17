"""
Authentication API endpoints.
Handles user registration, login, and profile retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.api.dependencies.deps import get_current_user
from app.services.auth.auth_service import AuthService
from app.models.user import User

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user"
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **full_name**: User's full name
    - **password**: Minimum 8 characters
    """
    try:
        user = AuthService.register_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/login",
    response_model=Token,
    summary="Login and get access token"
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.

    Returns a **JWT access token** to use in subsequent requests.

    Add to request headers:
    ```
    Authorization: Bearer <token>
    ```
    """
    user = AuthService.authenticate_user(db, login_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = AuthService.create_user_token(user)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current logged-in user"
)
def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get the profile of the currently logged-in user.

    Requires a valid JWT token in the Authorization header.
    """
    return current_user


@router.post(
    "/logout",
    summary="Logout (client-side token removal)"
)
def logout():
    """
    Logout endpoint.

    Since JWT is stateless, actual logout happens on the client
    by deleting the stored token. This endpoint is a placeholder
    for future token blacklisting if needed.
    """
    return {"message": "Successfully logged out"}
