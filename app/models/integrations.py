"""
Integration Models
Pydantic models for FMCSA confirm, Google Places search/confirm, and role details updates.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class GooglePlacesSearchRequest(BaseModel):
    """Request body for Google Places search."""
    query: str = Field(..., min_length=2, max_length=200, description="Search text")
    location: Optional[str] = Field(None, max_length=100, description="Location bias (e.g. 'Dallas, TX')")


class FMCSAConfirmRequest(BaseModel):
    """Request body to confirm and save FMCSA verification data."""
    fmcsa_data: Dict[str, Any] = Field(..., description="FMCSA carrier data to save")


class GooglePlacesConfirmRequest(BaseModel):
    """Request body to confirm and save Google Places verification data."""
    google_data: Dict[str, Any] = Field(..., description="Google Place data to save")


class RoleDetailsUpdateRequest(BaseModel):
    """Request body for updating role-specific details."""
    role_details: Dict[str, Any] = Field(..., description="Role-specific field updates to merge")
