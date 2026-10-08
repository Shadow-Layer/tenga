"""FastAPI application entrypoint for Tenga Inventory POS."""
from datetime import datetime, timezone
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from src.config import API_TITLE, API_DESCRIPTION, API_VERSION, CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS, DEBUG
from src.database.config import get_db, init_db
from src.routers import products, locations, organizations, users, sales, tills, inventory, sync, subscriptions, auth

# Configure logging
logging.basicConfig(level=logging.INFO if not DEBUG else logging.DEBUG)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    # Startup
    logger.info(f"Starting {API_TITLE} (v{API_VERSION})")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info(f"Shutting down {API_TITLE}")


# Create FastAPI application
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log HTTP requests."""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {process_time:.3f}s"
    )
    return response


# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness check endpoint - verifies database connectivity."""
    try:
        # Simple query to verify database is accessible
        db.execute(text("SELECT 1"))
        return {
            "ready": True,
            "version": API_VERSION,
            "database": "connected",
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database connection failed")


# Global exception handler for standardized error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Standardized HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "type": "http_error",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Standardized general exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500,
            "type": "internal_error",
        },
    )


# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(products.router, prefix="/api/v1", tags=["Products"])
app.include_router(locations.router, prefix="/api/v1", tags=["Locations"])
app.include_router(inventory.router, prefix="/api/v1/stock", tags=["Inventory"])
app.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
app.include_router(users.router, prefix="/organizations", tags=["Users"])
app.include_router(sales.router, prefix="/api/v1", tags=["Sales"])
app.include_router(tills.router, prefix="/api/v1/tills", tags=["Tills"])
app.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
app.include_router(sync.router, prefix="/api/v1/sync", tags=["Sync"])
