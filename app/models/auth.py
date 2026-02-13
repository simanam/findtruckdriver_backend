"""
Authentication Models
Pydantic models for authentication and authorization
"""

from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator
import re


class OTPRequest(BaseModel):
    """Request OTP code via phone"""
    phone: str = Field(..., description="Phone number with country code")

    @validator("phone")
    def validate_phone(cls, v):
        # Remove spaces, dashes, parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', v)

        # Check if it starts with + and has 10-15 digits
        if not re.match(r'^\+\d{10,15}$', cleaned):
            raise ValueError("Phone must be in format: +1234567890")

        return cleaned


class OTPVerify(BaseModel):
    """Verify OTP code"""
    phone: str = Field(..., description="Phone number")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")

    @validator("phone")
    def validate_phone(cls, v):
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+\d{10,15}$', cleaned):
            raise ValueError("Phone must be in format: +1234567890")
        return cleaned

    @validator("code")
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError("Code must be 6 digits")
        return v


class EmailOTPRequest(BaseModel):
    """Request OTP code via email (passwordless)"""
    email: EmailStr = Field(..., description="Email address")


class EmailOTPVerify(BaseModel):
    """Verify email OTP code"""
    email: EmailStr = Field(..., description="Email address")
    code: str = Field(..., min_length=6, max_length=8, description="OTP code (6-8 digits)")

    @validator("code")
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError("Code must be digits only")
        if len(v) < 6 or len(v) > 8:
            raise ValueError("Code must be 6-8 digits")
        return v


class MagicLinkRequest(BaseModel):
    """Request magic link via email"""
    email: EmailStr = Field(..., description="Email address")


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")


class TokenRefresh(BaseModel):
    """Refresh token request"""
    refresh_token: str


class AuthUser(BaseModel):
    """Authenticated user information"""
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Complete authentication response"""
    user: AuthUser
    tokens: TokenResponse
    driver: Optional[dict] = Field(None, description="Driver profile if exists")


class SignupRequest(BaseModel):
    """Email + password signup"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password")

    @validator("password")
    def validate_password(cls, v):
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class LoginRequest(BaseModel):
    """Email + password login"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class PasswordResetRequest(BaseModel):
    """Request password reset email"""
    email: EmailStr = Field(..., description="Email address")


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with new password"""
    access_token: str = Field(..., description="Access token from reset email")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

    @validator("new_password")
    def validate_password(cls, v):
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v
