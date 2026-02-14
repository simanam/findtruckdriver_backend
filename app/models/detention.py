"""
Detention Tracking Models
Pydantic models for detention session check-in/check-out, heatmap, and proof generation
"""

from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ── Request Models ──────────────────────────────────────────────────

class DetentionCheckInRequest(BaseModel):
    """Request to check in at a facility (start detention tracking)."""
    reviewed_facility_id: UUID
    latitude: float = Field(..., ge=-90, le=90, description="Driver's current latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Driver's current longitude")
    load_type: Optional[str] = Field(None, description="pickup, dropoff, both, or none")

    @field_validator("load_type")
    @classmethod
    def validate_load_type(cls, v):
        if v is not None and v not in ("pickup", "dropoff", "both", "none"):
            raise ValueError("load_type must be one of: pickup, dropoff, both, none")
        return v


class DetentionCheckOutRequest(BaseModel):
    """Request to check out from a facility (end detention tracking)."""
    session_id: UUID
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    notes: Optional[str] = Field(None, max_length=500)


class DetentionManualCheckoutRequest(BaseModel):
    """Manual time entry for forgotten checkout."""
    session_id: UUID
    actual_checkout_time: datetime = Field(..., description="When the driver actually left the facility")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("actual_checkout_time")
    @classmethod
    def validate_checkout_time(cls, v):
        if v.replace(tzinfo=None) > datetime.utcnow():
            raise ValueError("Checkout time cannot be in the future")
        return v


class DetentionSettingsRequest(BaseModel):
    """Update driver's detention free time preference."""
    free_time_minutes: int = Field(..., ge=0, le=1440, description="Free time in minutes before detention starts (0-24 hours)")


# ── Response Models ──────────────────────────────────────────────────

class DetentionSessionResponse(BaseModel):
    """Full detention session with facility info."""
    id: UUID
    driver_id: UUID
    reviewed_facility_id: UUID
    facility_name: str
    facility_type: str
    facility_address: Optional[str] = None
    facility_latitude: Optional[float] = None
    facility_longitude: Optional[float] = None
    checked_in_at: datetime
    checked_out_at: Optional[datetime] = None
    checkin_latitude: float
    checkin_longitude: float
    checkout_latitude: Optional[float] = None
    checkout_longitude: Optional[float] = None
    free_time_minutes: int
    total_time_minutes: Optional[int] = None
    detention_time_minutes: Optional[int] = None
    checkout_type: Optional[str] = None
    load_type: Optional[str] = None
    status: str
    notes: Optional[str] = None
    proof_generated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DetentionSessionListResponse(BaseModel):
    """Paginated list of detention sessions."""
    sessions: List[DetentionSessionResponse]
    total: int
    limit: int
    offset: int


class DetentionSettingsResponse(BaseModel):
    """Driver's detention settings."""
    free_time_minutes: int


class DetentionFacilityStatsResponse(BaseModel):
    """Detention statistics for a single facility."""
    reviewed_facility_id: UUID
    facility_name: str
    facility_type: str
    avg_total_time_minutes: float = 0
    avg_detention_minutes: float = 0
    total_sessions: int = 0
    detention_percentage: float = 0
    recent_sessions: int = 0  # Sessions in last 30 days


class DetentionHeatmapPoint(BaseModel):
    """Single point for heatmap rendering."""
    latitude: float
    longitude: float
    weight: float  # Normalized detention severity (0-1)
    facility_name: str
    facility_type: str
    avg_detention_minutes: float
    total_sessions: int


class DetentionHeatmapResponse(BaseModel):
    """Heatmap data for map rendering."""
    facilities: List[DetentionHeatmapPoint]
    total: int


class DetentionProofResponse(BaseModel):
    """Data for generating detention proof PDF."""
    session: DetentionSessionResponse
    driver_name: str
    driver_handle: str
    generated_at: datetime


class AutoCheckoutAlert(BaseModel):
    """Alert when driver appears to have left a facility without checking out."""
    session_id: UUID
    facility_name: str
    facility_type: str
    checked_in_at: datetime
    distance_from_facility_miles: float
