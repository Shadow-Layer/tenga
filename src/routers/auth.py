"""Authentication router - handles login, logout, and token endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database.config import get_db
from src.models.entities import User
from src.schemas.user import LoginRequest, TokenResponse, CurrentUserResponse, UserResponse
from src.security.password import hash_password, verify_password
from src.security.auth import create_access_token
from src.security.authorization import get_current_user


router = APIRouter()


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    status_code=200,
    summary="Authenticate user and get JWT token",
    description="Login with email and password to receive a JWT access token",
)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate user and return JWT token.
    
    Args:
        credentials: Email and password
        db: Database session
        
    Returns:
        TokenResponse with JWT token and user details
        
    Raises:
        401: If credentials are invalid
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        organization_id=user.organization_id,
        username=user.username,
        role=user.role,
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user),
    )


@router.get(
    "/auth/me",
    response_model=CurrentUserResponse,
    status_code=200,
    summary="Get current authenticated user",
    description="Get details of the currently authenticated user",
)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get information about the current authenticated user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        CurrentUserResponse with user details
    """
    return CurrentUserResponse.from_orm(current_user)
