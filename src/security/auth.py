"""JWT token handling for authentication."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from src.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES


class TokenData:
    """Represents decoded JWT token data."""
    
    def __init__(
        self,
        user_id: int,
        email: str,
        organization_id: int,
        username: str,
        role: str,
        exp: Optional[int] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.organization_id = organization_id
        self.username = username
        self.role = role
        self.exp = exp


def create_access_token(
    user_id: int,
    email: str,
    organization_id: int,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.
    
    Args:
        user_id: User ID
        email: User email
        organization_id: Organization ID
        username: Username
        role: User role
        expires_delta: Optional custom expiration delta
        
    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    to_encode: Dict[str, Any] = {
        "user_id": user_id,
        "email": email,
        "organization_id": organization_id,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        user_id: int = payload.get("user_id")
        email: str = payload.get("email")
        organization_id: int = payload.get("organization_id")
        username: str = payload.get("username")
        role: str = payload.get("role")
        exp: int = payload.get("exp")
        
        if not all([user_id, email, organization_id, username, role]):
            return None
        
        return TokenData(
            user_id=user_id,
            email=email,
            organization_id=organization_id,
            username=username,
            role=role,
            exp=exp,
        )
    except (jwt.InvalidTokenError, jwt.DecodeError, jwt.ExpiredSignatureError):
        return None
