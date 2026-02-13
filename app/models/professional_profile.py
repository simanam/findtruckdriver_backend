"""
Professional Profile Models
Pydantic models for professional profile data validation and serialization
"""

from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator
import re


# Valid options for constrained fields
VALID_HAUL_TYPES = ["long_haul", "regional", "local", "otr", "dedicated"]
VALID_EQUIPMENT_TYPES = ["dry_van", "flatbed", "reefer", "tanker", "hazmat", "auto_carrier"]
VALID_CDL_CLASSES = ["A", "B", "C"]
VALID_ENDORSEMENTS = ["H", "N", "P", "S", "T", "X"]
VALID_LOOKING_FOR = ["company_driver", "owner_operator", "team_driver"]
VALID_PREFERRED_HAUL = ["long_haul", "regional", "local"]


class WorkHistoryEntry(BaseModel):
    """A single work history entry"""
    company_name: str = Field(..., min_length=1, max_length=200)
    dot_number: Optional[str] = Field(None, max_length=20)
    mc_number: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = Field(None, max_length=100)
    start_date: str = Field(..., description="Start date in YYYY-MM format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM format, null if current")

    @validator("start_date")
    def validate_start_date(cls, v):
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", v):
            raise ValueError("start_date must be in YYYY-MM format")
        return v

    @validator("end_date")
    def validate_end_date(cls, v):
        if v is not None and not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", v):
            raise ValueError("end_date must be in YYYY-MM format")
        return v


class ProfessionalProfileCreate(BaseModel):
    """Model for creating a new professional profile"""
    years_experience: Optional[int] = Field(None, ge=0, le=60, description="Years of driving experience")
    haul_type: Optional[str] = Field(None, description="Primary haul type")
    equipment_type: Optional[str] = Field(None, description="Primary equipment type")

    cdl_class: Optional[str] = Field(None, description="CDL class (A, B, or C)")
    cdl_state: Optional[str] = Field(None, min_length=2, max_length=2, description="CDL issuing state (2-letter code)")
    endorsements: Optional[List[str]] = Field(None, description="CDL endorsements")

    company_name: Optional[str] = Field(None, max_length=100, description="Current company name")
    mc_number: Optional[str] = Field(None, max_length=20, description="MC number")
    dot_number: Optional[str] = Field(None, max_length=20, description="DOT number")
    company_start_date: Optional[str] = Field(None, description="Start date at current company in YYYY-MM format")
    bio: Optional[str] = Field(None, max_length=1000, description="Short bio")
    specialties: Optional[List[str]] = Field(None, description="Driving specialties")

    is_public: bool = Field(True, description="Whether profile is publicly visible")
    show_experience: bool = Field(True, description="Show experience info publicly")
    show_equipment: bool = Field(True, description="Show equipment info publicly")
    show_company: bool = Field(True, description="Show company info publicly")
    show_cdl: bool = Field(True, description="Show CDL info publicly")

    open_to_work: bool = Field(False, description="Whether driver is open to work opportunities")
    looking_for: Optional[List[str]] = Field(None, description="Types of positions looking for")
    preferred_haul: Optional[List[str]] = Field(None, description="Preferred haul types")

    work_history: Optional[List[WorkHistoryEntry]] = Field(None, description="Past work experience")
    role_details: Optional[dict] = Field(None, description="Role-specific data (FMCSA, Google verification, specialties)")

    @validator("haul_type")
    def validate_haul_type(cls, v):
        if v is not None and v not in VALID_HAUL_TYPES:
            raise ValueError(f"haul_type must be one of: {', '.join(VALID_HAUL_TYPES)}")
        return v

    @validator("equipment_type")
    def validate_equipment_type(cls, v):
        if v is not None and v not in VALID_EQUIPMENT_TYPES:
            raise ValueError(f"equipment_type must be one of: {', '.join(VALID_EQUIPMENT_TYPES)}")
        return v

    @validator("cdl_class")
    def validate_cdl_class(cls, v):
        if v is not None and v not in VALID_CDL_CLASSES:
            raise ValueError(f"cdl_class must be one of: {', '.join(VALID_CDL_CLASSES)}")
        return v

    @validator("cdl_state")
    def validate_cdl_state(cls, v):
        if v is not None:
            return v.upper()
        return v

    @validator("endorsements", each_item=True)
    def validate_endorsements(cls, v):
        if v not in VALID_ENDORSEMENTS:
            raise ValueError(f"Each endorsement must be one of: {', '.join(VALID_ENDORSEMENTS)}")
        return v

    @validator("looking_for", each_item=True)
    def validate_looking_for(cls, v):
        if v not in VALID_LOOKING_FOR:
            raise ValueError(f"Each looking_for value must be one of: {', '.join(VALID_LOOKING_FOR)}")
        return v

    @validator("preferred_haul", each_item=True)
    def validate_preferred_haul(cls, v):
        if v not in VALID_PREFERRED_HAUL:
            raise ValueError(f"Each preferred_haul value must be one of: {', '.join(VALID_PREFERRED_HAUL)}")
        return v


class ProfessionalProfileUpdate(BaseModel):
    """Model for updating professional profile (all fields optional for PATCH)"""
    years_experience: Optional[int] = Field(None, ge=0, le=60)
    haul_type: Optional[str] = None
    equipment_type: Optional[str] = None

    cdl_class: Optional[str] = None
    cdl_state: Optional[str] = Field(None, min_length=2, max_length=2)
    endorsements: Optional[List[str]] = None

    company_name: Optional[str] = Field(None, max_length=100)
    mc_number: Optional[str] = Field(None, max_length=20)
    dot_number: Optional[str] = Field(None, max_length=20)
    company_start_date: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=1000)
    specialties: Optional[List[str]] = None

    is_public: Optional[bool] = None
    show_experience: Optional[bool] = None
    show_equipment: Optional[bool] = None
    show_company: Optional[bool] = None
    show_cdl: Optional[bool] = None

    open_to_work: Optional[bool] = None
    looking_for: Optional[List[str]] = None
    preferred_haul: Optional[List[str]] = None

    work_history: Optional[List[WorkHistoryEntry]] = None
    role_details: Optional[dict] = None

    @validator("haul_type")
    def validate_haul_type(cls, v):
        if v is not None and v not in VALID_HAUL_TYPES:
            raise ValueError(f"haul_type must be one of: {', '.join(VALID_HAUL_TYPES)}")
        return v

    @validator("equipment_type")
    def validate_equipment_type(cls, v):
        if v is not None and v not in VALID_EQUIPMENT_TYPES:
            raise ValueError(f"equipment_type must be one of: {', '.join(VALID_EQUIPMENT_TYPES)}")
        return v

    @validator("cdl_class")
    def validate_cdl_class(cls, v):
        if v is not None and v not in VALID_CDL_CLASSES:
            raise ValueError(f"cdl_class must be one of: {', '.join(VALID_CDL_CLASSES)}")
        return v

    @validator("cdl_state")
    def validate_cdl_state(cls, v):
        if v is not None:
            return v.upper()
        return v

    @validator("endorsements", each_item=True)
    def validate_endorsements(cls, v):
        if v not in VALID_ENDORSEMENTS:
            raise ValueError(f"Each endorsement must be one of: {', '.join(VALID_ENDORSEMENTS)}")
        return v

    @validator("looking_for", each_item=True)
    def validate_looking_for(cls, v):
        if v not in VALID_LOOKING_FOR:
            raise ValueError(f"Each looking_for value must be one of: {', '.join(VALID_LOOKING_FOR)}")
        return v

    @validator("preferred_haul", each_item=True)
    def validate_preferred_haul(cls, v):
        if v not in VALID_PREFERRED_HAUL:
            raise ValueError(f"Each preferred_haul value must be one of: {', '.join(VALID_PREFERRED_HAUL)}")
        return v


class ProfessionalProfileResponse(BaseModel):
    """Full professional profile response (returned to profile owner)"""
    id: UUID
    driver_id: UUID

    years_experience: Optional[int] = None
    haul_type: Optional[str] = None
    equipment_type: Optional[str] = None

    cdl_class: Optional[str] = None
    cdl_state: Optional[str] = None
    endorsements: Optional[List[str]] = None

    company_name: Optional[str] = None
    mc_number: Optional[str] = None
    dot_number: Optional[str] = None
    company_start_date: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[List[str]] = None

    estimated_miles: Optional[int] = None
    estimated_miles_display: Optional[str] = None

    is_public: bool = True
    show_experience: bool = True
    show_equipment: bool = True
    show_company: bool = True
    show_cdl: bool = True

    open_to_work: bool = False
    looking_for: Optional[List[str]] = None
    preferred_haul: Optional[List[str]] = None

    work_history: Optional[List[WorkHistoryEntry]] = []
    role_details: Optional[dict] = None

    badges: Optional[List[Any]] = []
    completion_percentage: int = 0

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProfessionalProfilePublic(BaseModel):
    """Privacy-filtered public view of a professional profile"""
    id: UUID
    driver_id: UUID

    # Always visible (if profile is public)
    bio: Optional[str] = None
    open_to_work: bool = False
    badges: Optional[List[Any]] = []

    # Conditionally visible based on show_* flags
    years_experience: Optional[int] = None
    haul_type: Optional[str] = None
    estimated_miles: Optional[int] = None
    estimated_miles_display: Optional[str] = None

    equipment_type: Optional[str] = None

    company_name: Optional[str] = None

    cdl_class: Optional[str] = None
    cdl_state: Optional[str] = None
    endorsements: Optional[List[str]] = None

    specialties: Optional[List[str]] = None
    looking_for: Optional[List[str]] = None
    preferred_haul: Optional[List[str]] = None

    completion_percentage: int = 0

    class Config:
        from_attributes = True


class OpenToWorkListItem(BaseModel):
    """Item in the open-to-work driver listing"""
    driver_id: UUID
    handle: Optional[str] = None
    avatar_id: Optional[str] = None
    profile_photo_url: Optional[str] = None

    years_experience: Optional[int] = None
    haul_type: Optional[str] = None
    equipment_type: Optional[str] = None
    estimated_miles: Optional[int] = None
    estimated_miles_display: Optional[str] = None

    cdl_class: Optional[str] = None
    endorsements: Optional[List[str]] = None

    looking_for: Optional[List[str]] = None
    preferred_haul: Optional[List[str]] = None

    bio: Optional[str] = None
    badges: Optional[List[Any]] = []
    completion_percentage: int = 0

    class Config:
        from_attributes = True
