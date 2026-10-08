"""Authorization and dependency injection for secured endpoints."""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.database.config import get_db
from src.models.entities import User, Organization, Location, Till
from src.security.auth import decode_access_token, TokenData


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        Authenticated User object
        
    Raises:
        401: If token is invalid or user not found
    """
    token = credentials.credentials
    
    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(
        User.id == token_data.user_id,
        User.organization_id == token_data.organization_id,
        User.is_active == True,
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get the current authenticated user, or None if not provided.
    
    Args:
        credentials: HTTP Bearer token credentials (optional)
        db: Database session
        
    Returns:
        Authenticated User object or None
    """
    if not credentials:
        return None
    
    return await get_current_user(credentials, db)


def check_organization_access(required_org_id: int):
    """Create a dependency to check organization access.
    
    Args:
        required_org_id: Required organization ID
        
    Returns:
        Dependency function
    """
    async def _check_org_access(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.organization_id != required_org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization",
            )
        return current_user
    
    return _check_org_access


def check_location_access(location_id: int):
    """Create a dependency to check location access.
    
    Args:
        location_id: Location ID to check
        
    Returns:
        Dependency function
    """
    async def _check_location_access(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        location = db.query(Location).filter(
            Location.id == location_id,
            Location.organization_id == current_user.organization_id,
        ).first()
        
        if not location:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this location",
            )
        
        return current_user
    
    return _check_location_access


def check_till_access(till_id: int):
    """Create a dependency to check till access.
    
    Args:
        till_id: Till ID to check
        
    Returns:
        Dependency function
    """
    async def _check_till_access(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        till = db.query(Till).filter(
            Till.id == till_id,
            Till.organization_id == current_user.organization_id,
        ).first()
        
        if not till:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this till",
            )
        
        return current_user
    
    return _check_till_access


def check_role(*required_roles: str):
    """Create a dependency to check user role.
    
    Args:
        required_roles: Allowed roles
        
    Returns:
        Dependency function
    """
    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role must be one of: {', '.join(required_roles)}",
            )
        return current_user
    
    return _check_role

