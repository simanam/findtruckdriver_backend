"""
Driver Models
Pydantic models for driver data validation and serialization
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator


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
    pass


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
    """Model for updating driver status with optional location"""
    status: str = Field(..., description="New status")
    latitude: Optional[float] = Field(None, description="Current latitude")
    longitude: Optional[float] = Field(None, description="Current longitude")

    @validator("status")
    def validate_status(cls, v):
        if v not in DriverStatus.all():
            raise ValueError(f"Status must be one of: {', '.join(DriverStatus.all())}")
        return v


class Driver(DriverBase):
    """Complete driver model"""
    id: UUID
    user_id: UUID
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
