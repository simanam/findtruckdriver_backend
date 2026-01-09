"""
FastAPI Application Entry Point
Main application setup with middleware, CORS, and route registration
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict

from app.config import settings
from app import __version__

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for startup and shutdown events.
    Handles connection pool initialization and cleanup.
    """
    # Startup
    logger.info("🚀 Starting Find a Truck Driver API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug Mode: {settings.debug}")

    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection pool
    # TODO: Initialize Supabase client

    yield

    # Shutdown
    logger.info("🛑 Shutting down Find a Truck Driver API")

    # TODO: Close database connections
    # TODO: Close Redis connections
    # TODO: Cleanup resources


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Real-time truck driver tracking platform API",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    debug=settings.debug,
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests with timing information.
    """
    start_time = time.time()

    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"Status: {response.status_code} Duration: {duration:.3f}s"
    )

    # Add custom headers
    response.headers["X-Process-Time"] = str(duration)

    return response


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors with detailed error messages.
    """
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": exc.errors(),
                "timestamp": time.time()
            }
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler for unexpected errors.
    """
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": time.time()
            }
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict:
    """
    Health check endpoint for monitoring and load balancers.
    """
    return {
        "status": "healthy",
        "version": __version__,
        "environment": settings.environment,
        "timestamp": time.time()
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> Dict:
    """
    Root endpoint with API information.
    """
    return {
        "name": settings.app_name,
        "version": __version__,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


# API v1 routes
# TODO: Import and register routers
# from app.routers import auth, onboarding, location, status, map, stats, facilities
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
# app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["Onboarding"])
# app.include_router(location.router, prefix="/api/v1/location", tags=["Location"])
# app.include_router(status.router, prefix="/api/v1/status", tags=["Status"])
# app.include_router(map.router, prefix="/api/v1/map", tags=["Map"])
# app.include_router(stats.router, prefix="/api/v1/stats", tags=["Statistics"])
# app.include_router(facilities.router, prefix="/api/v1/facilities", tags=["Facilities"])


# Run with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
