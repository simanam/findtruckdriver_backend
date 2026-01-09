"""
Status Models
Pydantic models for driver status and status history
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator


class StatusType:
    """Status type constants"""
    ROLLING = "rolling"
    WAITING = "waiting"
    PARKED = "parked"

    @classmethod
    def all(cls) -> list[str]:
        return [cls.ROLLING, cls.WAITING, cls.PARKED]


class StatusUpdate(BaseModel):
    """Model for updating driver status"""
    status: str = Field(..., description="New status")

    @validator("status")
    def validate_status(cls, v):
        if v not in StatusType.all():
            raise ValueError(f"Status must be one of: {', '.join(StatusType.all())}")
        return v


class StatusHistoryBase(BaseModel):
    """Base status history model"""
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None

    @validator("status")
    def validate_status(cls, v):
        if v not in StatusType.all():
            raise ValueError(f"Status must be one of: {', '.join(StatusType.all())}")
        return v


class StatusHistoryCreate(StatusHistoryBase):
    """Model for creating status history record"""
    driver_id: UUID
    location_id: Optional[UUID] = None


class StatusHistory(StatusHistoryBase):
    """Complete status history model"""
    id: UUID
    driver_id: UUID
    location_id: Optional[UUID] = None
    duration_mins: Optional[int] = Field(None, description="Duration in minutes (calculated)")

    class Config:
        from_attributes = True


class StatusHistoryPublic(BaseModel):
    """Public status history (without sensitive IDs)"""
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_mins: Optional[int] = None

    class Config:
        from_attributes = True


class StatusStats(BaseModel):
    """Statistics about driver status usage"""
    driver_id: UUID
    rolling_count: int = 0
    waiting_count: int = 0
    parked_count: int = 0
    rolling_mins: int = 0
    waiting_mins: int = 0
    parked_mins: int = 0
    current_status: str
    current_status_started: datetime
