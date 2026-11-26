"""Products API router.

This module provides endpoints for managing products in inventory.
Operations include:
- Create and list products with optional search
- Retrieve product details
- Update product information
- Search products by name, SKU, or barcode
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.database.config import get_db
from src.models.entities import Product, Organization, TaxRule, User
from src.schemas.product import ProductCreate, ProductResponse, ProductListResponse, ProductUpdate
from src.schemas.catalog_import import (
    CatalogImportHistory,
    CatalogImportHistoryItem,
    CSVImportCommitResult,
    CSVImportPreview,
    CSVImportRequest,
)
from src.security.authorization import get_current_user
from src.services.catalog_import_service import (
    CatalogImportFailure,
    CatalogImportService,
    OPENING_STOCK_IMPORT_TYPE,
    PRODUCT_IMPORT_TYPE,
)

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
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=403,
            detail="Only an admin or manager can create products",
        )

    # Check authorization
    if current_user.organization_id != product_data.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    if product_data.tax_rule_id is not None and not db.query(TaxRule).filter(
        TaxRule.id == product_data.tax_rule_id,
        TaxRule.organization_id == current_user.organization_id,
        TaxRule.is_active.is_(True),
    ).first():
        raise HTTPException(status_code=422, detail="Active tax rule not found")
    
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
        unit_of_measure=product_data.unit_of_measure,
        minimum_stock_level=product_data.minimum_stock_level,
        tax_rule_id=product_data.tax_rule_id,
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
    include_inactive: bool = Query(False),
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
    if not include_inactive:
        query = query.filter(Product.is_active.is_(True))
    
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


def _require_catalog_import_admin(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can run catalog imports.")


def _run_catalog_import(operation):
    try:
        return operation()
    except CatalogImportFailure as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=jsonable_encoder(error.detail),
        ) from error


@router.get("/products/imports/template", tags=["products"])
def get_product_import_template(
    current_user: User = Depends(get_current_user),
):
    """Download a blank product catalog CSV template."""
    return Response(
        content=CatalogImportService.product_template(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="products-template.csv"'},
    )


@router.get("/products/imports/opening-stock/template", tags=["products"])
def get_opening_stock_import_template(
    current_user: User = Depends(get_current_user),
):
    """Download a blank opening-stock CSV template."""
    return Response(
        content="sku,location_code,quantity\r\n",
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="opening-stock-template.csv"'},
    )


@router.post(
    "/products/imports/products/preview",
    response_model=CSVImportPreview,
    tags=["products"],
)
def preview_product_import(
    request: CSVImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_catalog_import_admin(current_user)
    existing = CatalogImportService.import_status(
        request.csv_text, current_user.organization_id, PRODUCT_IMPORT_TYPE, db
    )
    if existing:
        return {
            "valid": True,
            "already_imported": True,
            "row_count": existing.row_count,
            "valid_count": existing.row_count,
            "errors": [],
            "rows": [],
        }
    return _run_catalog_import(
        lambda: CatalogImportService.validate_products(
            request.csv_text, current_user.organization_id, db
        )[0]
    )


@router.post(
    "/products/imports/products/commit",
    response_model=CSVImportCommitResult,
    tags=["products"],
)
def commit_product_import(
    request: CSVImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_catalog_import_admin(current_user)
    return _run_catalog_import(
        lambda: CatalogImportService.commit_products(
            request.csv_text, current_user.organization_id, current_user, db
        )
    )


@router.post(
    "/products/imports/opening-stock/preview",
    response_model=CSVImportPreview,
    tags=["products"],
)
def preview_opening_stock_import(
    request: CSVImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_catalog_import_admin(current_user)
    existing = CatalogImportService.import_status(
        request.csv_text, current_user.organization_id, OPENING_STOCK_IMPORT_TYPE, db
    )
    if existing:
        return {
            "valid": True,
            "already_imported": True,
            "row_count": existing.row_count,
            "valid_count": existing.row_count,
            "errors": [],
            "rows": [],
        }
    return _run_catalog_import(
        lambda: CatalogImportService.validate_opening_stock(
            request.csv_text, current_user.organization_id, db
        )[0]
    )


@router.post(
    "/products/imports/opening-stock/commit",
    response_model=CSVImportCommitResult,
    tags=["products"],
)
def commit_opening_stock_import(
    request: CSVImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_catalog_import_admin(current_user)
    return _run_catalog_import(
        lambda: CatalogImportService.commit_opening_stock(
            request.csv_text, current_user.organization_id, current_user, db
        )
    )


@router.get("/products/imports", response_model=CatalogImportHistory, tags=["products"])
def list_catalog_imports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = CatalogImportService.import_history(
        current_user.organization_id, skip, limit, db
    )
    return CatalogImportHistory(
        items=[CatalogImportHistoryItem.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/products/export", tags=["products"])
def export_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download this organization's product catalog as CSV."""
    return Response(
        content=CatalogImportService.export_products(current_user.organization_id, db),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="products.csv"'},
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
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=403,
            detail="Only an admin or manager can update products",
        )

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
    if "unit_of_measure" in product_data.model_fields_set:
        if product_data.unit_of_measure is None:
            raise HTTPException(status_code=422, detail="Unit of measure cannot be empty.")
        product.unit_of_measure = product_data.unit_of_measure
    if "minimum_stock_level" in product_data.model_fields_set:
        if product_data.minimum_stock_level is None:
            raise HTTPException(status_code=422, detail="Minimum stock level cannot be empty.")
        product.minimum_stock_level = product_data.minimum_stock_level
    if "is_active" in product_data.model_fields_set:
        if product_data.is_active is None:
            raise HTTPException(status_code=422, detail="Product active status cannot be empty.")
        product.is_active = product_data.is_active
    if "tax_rule_id" in product_data.model_fields_set:
        if product_data.tax_rule_id is not None and not db.query(TaxRule).filter(
            TaxRule.id == product_data.tax_rule_id,
            TaxRule.organization_id == current_user.organization_id,
            TaxRule.is_active.is_(True),
        ).first():
            raise HTTPException(status_code=422, detail="Active tax rule not found")
        product.tax_rule_id = product_data.tax_rule_id
    
    db.commit()
    db.refresh(product)
    return product
