"""
FastAPI Application Entry Point
Main application setup with middleware, CORS, and route registration
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import logging
import time
from typing import Dict

from app.config import settings
from app import __version__

# Configure logging
# In production (Railway), only log to stdout - no file handler
log_handlers = [logging.StreamHandler()]

# Only add file handler in development if logs directory exists
if settings.environment.lower() != "production":
    import os
    if os.path.exists("logs"):
        log_handlers.append(logging.FileHandler("logs/app.log"))

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=log_handlers
)

logger = logging.getLogger(__name__)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for startup and shutdown events.
    Handles connection pool initialization and cleanup.
    """
    # Startup
    logger.info("Starting Find a Truck Driver API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug Mode: {settings.debug}")

    # Initialize database connections
    from app.database import initialize_database
    await initialize_database()

    # TODO: Initialize Redis connection pool

    yield

    # Shutdown
    logger.info("Shutting down Find a Truck Driver API")

    # Close database connections
    from app.database import close_database
    await close_database()

    # TODO: Close Redis connections


# Determine docs URLs based on environment
# Disable docs in production for security
is_production = settings.environment.lower() == "production"
docs_url = None if is_production else "/docs"
redoc_url = None if is_production else "/redoc"
openapi_url = None if is_production else "/openapi.json"

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Real-time truck driver tracking platform API",
    version=__version__,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    lifespan=lifespan,
    debug=settings.debug,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# CORS Middleware - configured via environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Add security headers to all responses.
    """
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Remove server header
    if "server" in response.headers:
        del response.headers["server"]

    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests with timing information.
    """
    start_time = time.time()

    # Log request (skip health checks to reduce noise)
    if request.url.path != "/health":
        logger.info(f"Request: {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response (skip health checks)
    if request.url.path != "/health":
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

    # In production, don't expose detailed validation errors
    if is_production:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request data",
                    "timestamp": time.time()
                }
            }
        )

    # Sanitize errors: convert non-serializable objects (like ValueError) to strings
    sanitized_errors = []
    for err in exc.errors():
        clean_err = {k: (str(v) if k == "ctx" else v) for k, v in err.items() if k != "ctx"}
        clean_err["msg"] = err.get("msg", "Validation error")
        sanitized_errors.append(clean_err)

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": sanitized_errors,
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

    # Never expose internal error details in production
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
    response = {
        "name": settings.app_name,
        "version": __version__,
        "status": "running",
        "health": "/health"
    }

    # Only show docs URLs in non-production
    if not is_production:
        response["docs"] = "/docs"
        response["redoc"] = "/redoc"

    return response


# API v1 routes
from app.routers import auth, drivers, locations, map, follow_ups, professional_profile, integrations, jobs, reviews, detention

app.include_router(auth.router, prefix="/api/v1")
app.include_router(drivers.router, prefix="/api/v1")
app.include_router(locations.router, prefix="/api/v1")
app.include_router(map.router, prefix="/api/v1")
app.include_router(follow_ups.router, prefix="/api/v1")
app.include_router(professional_profile.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(detention.router, prefix="/api/v1")


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
