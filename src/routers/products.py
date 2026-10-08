"""Products API router.

This module provides endpoints for managing products in the catalog.
Operations include:
- Create new products
- Retrieve product details and lists
- Update product information
- Delete products

Products are organization-specific and have SKUs that must be unique per organization.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.database.config import get_db
from src.models.entities import Product, Organization, User
from src.schemas.product import ProductCreate, ProductResponse, ProductListResponse
from src.security.authorization import get_current_user

router = APIRouter()


@router.post("/products", response_model=ProductResponse, status_code=201, tags=["products"])
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new product.
    
    Args:
        product_data: Product creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created product
        
    Raises:
        401: If not authenticated
        403: If user is not in the same organization
        404: Organization not found
        409: SKU already exists for this organization
    """
    # Check authorization - user must be in the same organization
    if current_user.organization_id != product_data.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    
    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == product_data.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Create product
    product = Product(
        name=product_data.name,
        sku=product_data.sku,
        description=product_data.description,
        category=product_data.category,
        price=product_data.price,
        cost=product_data.cost,
        organization_id=product_data.organization_id,
    )
    
    try:
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product SKU already exists for this organization")


@router.get("/products", response_model=ProductListResponse, tags=["products"])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    organization_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List products with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Number of records to return
        organization_id: Optional filter by organization
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Paginated list of products
        
    Raises:
        401: If not authenticated
        403: If trying to access another organization's products
    """
    # Default to current user's organization if not specified
    if organization_id is None:
        organization_id = current_user.organization_id
    
    # Check authorization - can only list own organization's products
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    
    query = db.query(Product).filter(Product.organization_id == organization_id)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return ProductListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/products/{product_id}", response_model=ProductResponse, tags=["products"])
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get product details.
    
    Args:
        product_id: Product ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Product details
        
    Raises:
        401: If not authenticated
        403: If product belongs to another organization
        404: Product not found
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check authorization - product must belong to user's organization
    if product.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this product")
    
    return product

