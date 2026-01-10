"""
Authentication Router
Endpoints for phone OTP, magic link, and token management
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from supabase import Client
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db_client
from app.models.auth import (
    EmailOTPRequest,
    EmailOTPVerify,
    OTPRequest,
    OTPVerify,
    MagicLinkRequest,
    TokenResponse,
    TokenRefresh,
    AuthResponse,
    AuthUser
)
from app.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Rate limiter for auth endpoints
limiter = Limiter(key_func=get_remote_address)


@router.post("/otp/request", status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def request_otp(
    request: OTPRequest,
    req: Request,
    db: Client = Depends(get_db_client)
):
    """
    Request OTP code via SMS to phone number.
    Uses Supabase Auth phone authentication.

    Rate limited: 5 requests per hour per IP.
    """
    try:
        # Supabase will send OTP via SMS
        response = db.auth.sign_in_with_otp({
            "phone": request.phone
        })

        logger.info(f"OTP requested for phone: {request.phone}")

        return {
            "success": True,
            "message": f"OTP sent to {request.phone}",
            "phone": request.phone
        }

    except Exception as e:
        logger.error(f"OTP request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send OTP: {str(e)}"
        )


@router.post("/otp/verify", response_model=AuthResponse)
@limiter.limit("10/minute")
async def verify_otp(
    request: OTPVerify,
    req: Request,
    db: Client = Depends(get_db_client)
):
    """
    Verify OTP code and return access tokens.
    Creates user session if OTP is valid.

    Rate limited: 10 attempts per minute per IP (prevents brute force).
    """
    try:
        # Verify OTP with Supabase
        response = db.auth.verify_otp({
            "phone": request.phone,
            "token": request.code,
            "type": "sms"
        })

        if not response.user or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired OTP code"
            )

        # Check if driver profile exists
        driver_response = db.from_("drivers").select("*").eq(
            "user_id", response.user.id
        ).execute()

        driver = driver_response.data[0] if driver_response.data else None

        # Build response
        # Convert created_at to string if it's a datetime object
        created_at_str = response.user.created_at
        if hasattr(created_at_str, 'isoformat'):
            created_at_str = created_at_str.isoformat()

        auth_user = AuthUser(
            id=response.user.id,
            phone=response.user.phone,
            email=response.user.email,
            created_at=created_at_str
        )

        tokens = TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
            expires_in=response.session.expires_in or 3600
        )

        return AuthResponse(
            user=auth_user,
            tokens=tokens,
            driver=driver
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OTP verification failed: {str(e)}"
        )


@router.post("/email/otp/request", status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def request_email_otp(
    request: EmailOTPRequest,
    req: Request,
    db: Client = Depends(get_db_client)
):
    """
    Request OTP code via email (passwordless).
    User receives an 8-digit code in their email (configurable in Supabase).
    No password required!

    Rate limited: 5 requests per hour per IP.
    """
    try:
        # Try direct API call to ensure OTP code is sent (not magic link)
        # The Python SDK might not properly support the channel parameter
        response = db.auth.sign_in_with_otp({
            "email": request.email,
            "options": {
                "should_create_user": True,
            }
        })

        logger.info(f"Email OTP requested for: {request.email}")
        logger.debug(f"Supabase OTP response: {response}")

        return {
            "success": True,
            "message": f"Verification code sent to {request.email}",
            "email": request.email
        }

    except Exception as e:
        logger.error(f"Email OTP request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send email OTP: {str(e)}"
        )


@router.post("/email/otp/verify", response_model=AuthResponse)
@limiter.limit("10/minute")
async def verify_email_otp(
    request: EmailOTPVerify,
    req: Request,
    db: Client = Depends(get_db_client)
):
    """
    Verify email OTP code and return access tokens.
    Creates user session if OTP is valid.

    Rate limited: 10 attempts per minute per IP (prevents brute force).
    """
    try:
        # For email OTP, we use 'email' field instead of 'phone'
        # The request model has a 'phone' field, but we'll treat it as email
        response = db.auth.verify_otp({
            "email": request.email,
            "token": request.code,
            "type": "email"
        })

        if not response.user or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired verification code"
            )

        # Check if driver profile exists
        driver_response = db.from_("drivers").select("*").eq(
            "user_id", response.user.id
        ).execute()

        driver = driver_response.data[0] if driver_response.data else None

        # Build response
        # Convert created_at to string if it's a datetime object
        created_at_str = response.user.created_at
        if hasattr(created_at_str, 'isoformat'):
            created_at_str = created_at_str.isoformat()

        auth_user = AuthUser(
            id=response.user.id,
            phone=response.user.phone,
            email=response.user.email,
            created_at=created_at_str
        )

        tokens = TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
            expires_in=response.session.expires_in or 3600
        )

        return AuthResponse(
            user=auth_user,
            tokens=tokens,
            driver=driver
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email OTP verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email OTP verification failed: {str(e)}"
        )


@router.post("/magic-link/request", status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def request_magic_link(
    request: MagicLinkRequest,
    req: Request,
    db: Client = Depends(get_db_client)
):
    """
    Request magic link via email (alternative to OTP).
    User clicks link in email instead of entering code.

    Rate limited: 5 requests per hour per IP.
    """
    try:
        # Supabase will send magic link via email
        response = db.auth.sign_in_with_otp({
            "email": request.email,
            "options": {
                "should_create_user": True
            }
        })

        logger.info(f"Magic link requested for email: {request.email}")

        return {
            "success": True,
            "message": f"Magic link sent to {request.email}",
            "email": request.email
        }

    except Exception as e:
        logger.error(f"Magic link request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send magic link: {str(e)}"
        )


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefresh,
    db: Client = Depends(get_db_client)
):
    """
    Refresh access token using refresh token.
    Returns new access and refresh tokens.
    """
    try:
        # Refresh session with Supabase
        response = db.auth.refresh_session(request.refresh_token)

        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
            expires_in=response.session.expires_in or 3600
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token"
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db_client)
):
    """
    Logout current user and invalidate session.
    """
    try:
        # Sign out with Supabase
        db.auth.sign_out()

        logger.info(f"User logged out: {current_user.id}")

        return {
            "success": True,
            "message": "Successfully logged out"
        }

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout failed"
        )


@router.get("/me", response_model=AuthUser)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    # Convert created_at to string if it's a datetime object
    created_at_str = current_user.created_at
    if hasattr(created_at_str, 'isoformat'):
        created_at_str = created_at_str.isoformat()

    return AuthUser(
        id=current_user.id,
        phone=current_user.phone,
        email=current_user.email,
        created_at=created_at_str
    )
