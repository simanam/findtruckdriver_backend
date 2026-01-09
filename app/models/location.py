"""
Location Models
Pydantic models for driver location data
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator


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
