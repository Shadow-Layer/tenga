"""Users router - REST API for user management.

This module provides endpoints for managing users within organizations.
Operations include:
- Create and list users
- Retrieve user details
- Update user information
- Manage user roles and permissions

Users are organization-scoped and can have roles:
- operator: Basic POS operator
- manager: Store manager with more permissions
- admin: Organization administrator
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database.config import get_db
from src.models.entities import Organization, User
from src.schemas.user import (
    UserCreate,
    UserResponse,
    UserListResponse,
)
from src.security.password import hash_password
from src.security.authorization import get_current_user, check_role

router = APIRouter()


@router.post(
    "/{org_id}/users",
    response_model=UserResponse,
    status_code=201,
    summary="Add user to organization",
    description="Create a new user in an organization",
)
def create_user(
    org_id: int,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new user in an organization.
    
    Args:
        org_id: Organization ID
        user_data: User creation data
        db: Database session
        current_user: Current authenticated user (must be admin or manager)
        
    Returns:
        UserResponse: Created user
        
    Raises:
        401: If not authenticated
        403: If user lacks permission to create users
        404: If organization not found
        409: If email already exists in organization
    """
    # Check authorization - only admins and managers can create users
    if current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=403,
            detail="Only admin or manager can create users"
        )
    
    # Check if organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check if email already exists in organization
    existing_user = db.query(User).filter(
        (User.organization_id == org_id) & (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail=f"User with email '{user_data.email}' already exists in this organization"
        )
    
    # Hash password
    password_hash = hash_password(user_data.password)
    
    # Create new user
    user = User(
        organization_id=org_id,
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        password_hash=password_hash,
        role=user_data.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.get(
    "/{org_id}/users",
    response_model=UserListResponse,
    summary="List users in organization",
    description="Get list of all users in an organization",
)
def list_users(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all users in an organization.
    
    Args:
        org_id: Organization ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        UserListResponse: List of users in organization
        
    Raises:
        401: If not authenticated
        403: If user is not in the same organization
        404: If organization not found
    """
    # Check authorization
    if current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    
    # Check if organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    total = db.query(User).filter(User.organization_id == org_id).count()
    users = db.query(User).filter(User.organization_id == org_id).all()
    
    return UserListResponse(
        items=users,
        total=total,
    )


@router.get(
    "/{org_id}/users/{user_id}",
    response_model=UserResponse,
    summary="Get user details",
    description="Get details of a specific user in an organization",
)
def get_user(
    org_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific user.
    
    Args:
        org_id: Organization ID
        user_id: User ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        UserResponse: User details
        
    Raises:
        401: If not authenticated
        403: If user is not in the same organization
        404: If organization or user not found
    """
    # Check authorization
    if current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    
    # Check if organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get user
    user = db.query(User).filter(
        (User.id == user_id) & (User.organization_id == org_id)
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

