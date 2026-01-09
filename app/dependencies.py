"""
Shared Dependencies
FastAPI dependencies for authentication, database access, etc.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.database import get_db_client, get_db_admin
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Client = Depends(get_db_client)
) -> dict:
    """
    Get current authenticated user from JWT token.
    Validates token with Supabase and returns user data.

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        token = credentials.credentials

        # Get user from Supabase using the token
        response = db.auth.get_user(token)

        if not response:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return response.user

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Client = Depends(get_db_client)
) -> Optional[dict]:
    """
    Get current user if authenticated, otherwise return None.
    Useful for endpoints that work for both authenticated and unauthenticated users.
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        response = db.auth.get_user(token)
        return response.user if response else None
    except Exception as e:
        logger.warning(f"Optional auth failed: {e}")
        return None


async def get_current_driver(
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db_admin)
) -> dict:
    """
    Get the driver profile for the current authenticated user.

    Raises:
        HTTPException: If driver profile not found
    """
    try:
        # Query drivers table for this user (without .single())
        response = db.from_("drivers") \
            .select("*") \
            .eq("user_id", current_user.id) \
            .execute()

        # Check if driver profile exists
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Driver profile not found. Please complete onboarding."
            )

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching driver: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch driver profile"
        )


async def get_db_session(db: Client = Depends(get_db_client)) -> Client:
    """
    Get database session (client that respects RLS).
    Use for user-level operations.
    """
    return db


async def get_db_admin_session(db: Client = Depends(get_db_admin)) -> Client:
    """
    Get admin database session (bypasses RLS).
    Use for system-level operations, stats, aggregation.
    """
    return db


def verify_api_key(api_key: Optional[str] = None) -> bool:
    """
    Verify API key for external integrations (if needed).
    Returns True if valid, False otherwise.
    """
    # TODO: Implement API key validation if needed
    # For now, this is a placeholder
    return True
