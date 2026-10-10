"""Products API router.

This module provides endpoints for managing products in inventory.
Operations include:
- Create and list products with optional search
- Retrieve product details
- Update product information
- Search products by name, SKU, or barcode
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.database.config import get_db
from src.models.entities import Product, Organization, User
from src.schemas.product import ProductCreate, ProductResponse, ProductListResponse, ProductUpdate
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
        409: Product with same SKU already exists in organization
    """
    # Check authorization
    if current_user.organization_id != product_data.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    
    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == product_data.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check for duplicate SKU within organization
    existing = db.query(Product).filter(
        Product.organization_id == product_data.organization_id,
        Product.sku == product_data.sku
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Product with this SKU already exists in this organization")
    
    # Create product
    product = Product(
        sku=product_data.sku,
        name=product_data.name,
        description=product_data.description,
        category=product_data.category,
        price=product_data.price,
        cost=product_data.cost,
        barcode=product_data.barcode,
        organization_id=product_data.organization_id,
        is_active=True,
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products", response_model=ProductListResponse, tags=["products"])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    organization_id: int = Query(None),
    search: str = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List products with optional search and pagination.
    
    Search supports partial matching on:
    - Product name (case-insensitive)
    - Product SKU (case-insensitive)
    - Product barcode (if provided)
    
    Args:
        skip: Number of records to skip
        limit: Number of records to return (max 100)
        organization_id: Optional filter by organization (defaults to current user's org)
        search: Optional search query for name/SKU/barcode
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
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_term),
                Product.sku.ilike(search_term),
                Product.barcode.ilike(search_term) if search_term else False
            )
        )
    
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


@router.put("/products/{product_id}", response_model=ProductResponse, tags=["products"])
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update product information.
    
    Args:
        product_id: Product ID
        product_data: Product update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated product
        
    Raises:
        401: If not authenticated
        403: If product belongs to another organization
        404: Product not found
        409: New SKU conflicts with another product in organization
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check authorization
    if product.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this product")
    
    # Check for SKU conflicts if changing SKU
    if product_data.sku and product_data.sku != product.sku:
        existing = db.query(Product).filter(
            Product.organization_id == product.organization_id,
            Product.sku == product_data.sku,
            Product.id != product.id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Product with this SKU already exists in this organization")
    
    # Update fields
    if product_data.sku is not None:
        product.sku = product_data.sku
    if product_data.name is not None:
        product.name = product_data.name
    if product_data.description is not None:
        product.description = product_data.description
    if product_data.category is not None:
        product.category = product_data.category
    if product_data.price is not None:
        product.price = product_data.price
    if product_data.cost is not None:
        product.cost = product_data.cost
    if product_data.barcode is not None:
        product.barcode = product_data.barcode
    
    db.commit()
    db.refresh(product)
    return product
