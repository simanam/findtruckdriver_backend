"""
Location Models
Pydantic models for driver location data
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from pydantic import BaseModel, Field, validator

if TYPE_CHECKING:
    from app.models.follow_up import FollowUpQuestion


class LocationBase(BaseModel):
    """Base location model"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    accuracy: Optional[float] = Field(None, ge=0, description="Location accuracy in meters")
    heading: Optional[float] = Field(None, ge=0, lt=360, description="Direction of travel (0-360 degrees)")
    speed: Optional[float] = Field(None, ge=0, description="Speed in mph")


class LocationCreate(LocationBase):
    """Model for creating a new location record"""
    driver_id: UUID


class LocationUpdate(BaseModel):
    """Model for updating location (rarely used)"""
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0)
    heading: Optional[float] = Field(None, ge=0, lt=360)
    speed: Optional[float] = Field(None, ge=0)


class Location(LocationBase):
    """Complete location model with database fields"""
    id: UUID
    driver_id: UUID
    fuzzed_latitude: float = Field(..., description="Privacy-fuzzed latitude")
    fuzzed_longitude: float = Field(..., description="Privacy-fuzzed longitude")
    geohash: str = Field(..., description="Geohash for spatial queries")
    recorded_at: datetime

    class Config:
        from_attributes = True


class LocationPublic(BaseModel):
    """Public location data (only fuzzed coordinates exposed)"""
    driver_id: UUID
    latitude: float = Field(..., description="Fuzzed latitude")
    longitude: float = Field(..., description="Fuzzed longitude")
    accuracy: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


class LocationStats(BaseModel):
    """Location statistics for a driver"""
    driver_id: UUID
    total_locations: int
    latest_location: Optional[LocationPublic] = None
    first_recorded: Optional[datetime] = None
    last_recorded: Optional[datetime] = None


class CheckInRequest(BaseModel):
    """Request model for manual check-in"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0)
    heading: Optional[float] = Field(None, ge=0, lt=360)
    speed: Optional[float] = Field(None, ge=0)


class LocationResponse(BaseModel):
    """Response model for location data"""
    latitude: float
    longitude: float
    facility_name: Optional[str] = None
    updated_at: datetime


class MyLocationResponse(BaseModel):
    """Response model for /locations/me endpoint"""
    driver_id: UUID
    handle: str
    status: str
    latitude: float
    longitude: float
    facility_name: Optional[str] = None
    updated_at: datetime


class CheckInResponse(BaseModel):
    """Response model for check-in"""
    success: bool
    status: str
    location: LocationResponse
    message: str


class StatusChangeRequest(BaseModel):
    """Request model for status change with location"""
    status: str = Field(..., description="New status: rolling, waiting, or parked")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0)
    heading: Optional[float] = Field(None, ge=0, lt=360)
    speed: Optional[float] = Field(None, ge=0)

    @validator("status")
    def validate_status(cls, v):
        valid_statuses = ["rolling", "waiting", "parked"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class WaitContext(BaseModel):
    """Context information for waiting status"""
    others_waiting: int
    avg_wait_hours: float


class StatusChangeResponse(BaseModel):
    """Response model for status change with optional follow-up question"""
    success: bool
    old_status: str
    new_status: str
    location: LocationResponse
    wait_context: Optional[WaitContext] = None
    follow_up_question: Optional['FollowUpQuestion'] = None  # Forward reference
    status_update_id: Optional[UUID] = None
    message: str


class AppOpenRequest(BaseModel):
    """Request model for app open/focus event"""
    latitude: float = Field(..., ge=-90, le=90, description="Current latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Current longitude")
    accuracy: Optional[float] = Field(None, ge=0, description="Location accuracy in meters")
    heading: Optional[float] = Field(None, ge=0, lt=360, description="Direction of travel")
    speed: Optional[float] = Field(None, ge=0, description="Speed in mph")


class AppOpenResponse(BaseModel):
    """Response model for app open detection"""
    action: str = Field(..., description="Action to take: 'none' or 'prompt_status'")
    reason: Optional[str] = Field(None, description="Reason for prompt: 'welcome_back', 'location_changed', or null")
    message: Optional[str] = Field(None, description="Message to show user")
    current_status: str = Field(..., description="Current driver status")
    last_status: Optional[str] = Field(None, description="Last known status")
    last_location_name: Optional[str] = Field(None, description="Last facility name")
    distance_moved: Optional[float] = Field(None, description="Distance moved in miles")
    hours_since_update: Optional[float] = Field(None, description="Hours since last update")
    suggested_status: Optional[str] = Field(None, description="Suggested new status")


# Resolve forward references after FollowUpQuestion is imported
from app.models.follow_up import FollowUpQuestion
StatusChangeResponse.model_rebuild()

