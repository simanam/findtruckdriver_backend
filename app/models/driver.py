"""
Driver Models
Pydantic models for driver data validation and serialization
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, validator

VALID_ROLES = [
    "company_driver", "owner_operator", "team_driver", "lease_operator",
    "student_driver", "dispatcher", "freight_broker", "mechanic",
    "fleet_manager", "lumper", "warehouse", "shipper", "other"
]


class DriverStatus:
    """Driver status constants"""
    ROLLING = "rolling"
    WAITING = "waiting"
    PARKED = "parked"

    @classmethod
    def all(cls) -> list[str]:
        return [cls.ROLLING, cls.WAITING, cls.PARKED]


class DriverBase(BaseModel):
    """Base driver model with common fields"""
    handle: str = Field(..., min_length=3, max_length=30, description="Unique driver handle")
    avatar_id: str = Field(..., description="Avatar identifier or URL")
    status: str = Field(default=DriverStatus.PARKED, description="Current driver status")

    @validator("status")
    def validate_status(cls, v):
        if v not in DriverStatus.all():
            raise ValueError(f"Status must be one of: {', '.join(DriverStatus.all())}")
        return v

    @validator("handle")
    def validate_handle(cls, v):
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Handle can only contain letters, numbers, underscores, and hyphens")
        return v.lower()


class DriverCreateRequest(DriverBase):
    """Model for driver creation request from frontend (no user_id)"""
    role: str = Field(default="company_driver", description="Industry role")
    cb_handle: Optional[str] = Field(None, max_length=50, description="CB Handle for map display")

    @validator("role")
    def validate_role(cls, v):
        if v not in VALID_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(VALID_ROLES)}")
        return v


class DriverCreate(DriverBase):
    """Model for creating a new driver (internal, includes user_id)"""
    user_id: UUID = Field(..., description="Supabase auth user ID")


class DriverUpdate(BaseModel):
    """Model for updating driver information"""
    handle: Optional[str] = Field(None, min_length=3, max_length=30)
    avatar_id: Optional[str] = None
    status: Optional[str] = None

    @validator("status")
    def validate_status(cls, v):
        if v is not None and v not in DriverStatus.all():
            raise ValueError(f"Status must be one of: {', '.join(DriverStatus.all())}")
        return v


class StatusUpdate(BaseModel):
    """
    Model for updating driver status with location.

    Note: latitude and longitude are technically optional in the model for backwards
    compatibility, but the API will reject requests without location data.
    Frontend should always provide current location when updating status.
    """
    status: str = Field(..., description="New status")
    latitude: Optional[float] = Field(None, description="Current latitude (required by API)")
    longitude: Optional[float] = Field(None, description="Current longitude (required by API)")

    @validator("status")
    def validate_status(cls, v):
        if v not in DriverStatus.all():
            raise ValueError(f"Status must be one of: {', '.join(DriverStatus.all())}")
        return v


class Driver(DriverBase):
    """Complete driver model"""
    id: UUID
    user_id: UUID
    role: Optional[str] = None
    cb_handle: Optional[str] = None
    show_on_map_as: Optional[str] = None
    profile_photo_url: Optional[str] = None
    last_active: datetime
    created_at: datetime

    class Config:
        from_attributes = True  # For Pydantic v2 (was orm_mode in v1)


class DriverPublic(BaseModel):
    """Public driver information (safe to expose)"""
    id: UUID
    handle: str
    avatar_id: str
    status: str
    role: Optional[str] = None
    cb_handle: Optional[str] = None
    show_on_map_as: Optional[str] = None
    profile_photo_url: Optional[str] = None
    last_active: datetime

    class Config:
        from_attributes = True


class DriverWithLocation(Driver):
    """Driver with their latest location"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProfileStats(BaseModel):
    """Driver profile statistics"""
    total_status_updates: int = 0
    days_active: int = 0
    rolling_count: int = 0
    waiting_count: int = 0
    parked_count: int = 0
    member_since: datetime
    last_active: datetime


class DriverProfileUpdate(BaseModel):
    """Model for updating driver profile"""
    handle: Optional[str] = Field(None, min_length=3, max_length=30, description="Unique driver handle")
    avatar_id: Optional[str] = Field(None, description="Avatar identifier")
    role: Optional[str] = Field(None, description="Industry role")
    cb_handle: Optional[str] = Field(None, max_length=50, description="CB Handle for map display")
    show_on_map_as: Optional[str] = Field(None, description="What name to show on map")
    profile_photo_url: Optional[str] = Field(None, description="Profile photo URL")

    @validator("handle")
    def validate_handle(cls, v):
        if v is not None:
            if not v.replace("_", "").replace("-", "").isalnum():
                raise ValueError("Handle can only contain letters, numbers, underscores, and hyphens")
            return v.lower()
        return v

    @validator("role")
    def validate_role(cls, v):
        if v is not None and v not in VALID_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(VALID_ROLES)}")
        return v

    @validator("show_on_map_as")
    def validate_show_on_map_as(cls, v):
        if v is not None and v not in ("cb_handle", "handle"):
            raise ValueError("show_on_map_as must be 'cb_handle' or 'handle'")
        return v


class CBHandleCheck(BaseModel):
    """Model for checking CB handle availability"""
    cb_handle: str = Field(..., min_length=3, max_length=50, description="CB Handle to check")


class AccountDeletionRequest(BaseModel):
    """Model for account deletion confirmation"""
    confirmation: str = Field(..., description="Must be 'DELETE' to confirm")
    reason: Optional[str] = Field(None, max_length=500, description="Optional deletion reason")

    @validator("confirmation")
    def validate_confirmation(cls, v):
        if v != "DELETE":
            raise ValueError("Confirmation must be 'DELETE' to proceed with account deletion")
        return v
