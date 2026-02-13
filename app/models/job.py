"""
Job Posting Models
Pydantic models for job board data validation and serialization
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class HaulType(str, Enum):
    OTR = "otr"
    REGIONAL = "regional"
    LOCAL = "local"
    DEDICATED = "dedicated"
    TEAM = "team"


class EquipmentType(str, Enum):
    DRY_VAN = "dry_van"
    REEFER = "reefer"
    FLATBED = "flatbed"
    TANKER = "tanker"
    CAR_HAULER = "car_hauler"
    INTERMODAL = "intermodal"
    HAZMAT = "hazmat"
    OVERSIZED = "oversized"
    LTL = "ltl"
    OTHER = "other"


# Roles allowed to post jobs
POSTER_ROLES = [
    "recruiter", "fleet_manager", "dispatcher",
    "owner_operator", "freight_broker"
]

VALID_REQUIREMENTS = [
    "cdl_a", "cdl_b", "hazmat", "tanker", "doubles_triples",
    "twic", "1yr_exp", "2yr_exp", "5yr_exp",
    "clean_record", "no_sap", "team_willing"
]

VALID_REGIONS = [
    "northeast", "southeast", "midwest", "southwest",
    "west", "northwest", "national"
]


class JobCreateRequest(BaseModel):
    """Request model for creating a job posting."""
    title: str = Field(..., min_length=5, max_length=200)
    company_name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    how_to_apply: str = Field(..., min_length=5, max_length=1000)

    mc_number: Optional[str] = Field(None, max_length=20)
    dot_number: Optional[str] = Field(None, max_length=20)

    haul_type: HaulType
    equipment: EquipmentType
    pay_info: Optional[str] = Field(None, max_length=500)
    requirements: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)

    @field_validator("requirements")
    @classmethod
    def validate_requirements(cls, v):
        for item in v:
            if item not in VALID_REQUIREMENTS:
                raise ValueError(
                    f"Invalid requirement '{item}'. Must be one of: {VALID_REQUIREMENTS}"
                )
        return v

    @field_validator("regions")
    @classmethod
    def validate_regions(cls, v):
        for item in v:
            if item not in VALID_REGIONS:
                raise ValueError(
                    f"Invalid region '{item}'. Must be one of: {VALID_REGIONS}"
                )
        return v

    @field_validator("mc_number")
    @classmethod
    def validate_mc_number(cls, v):
        if v is not None:
            cleaned = v.replace("MC-", "").replace("MC", "").strip()
            if not cleaned.isdigit():
                raise ValueError("MC number must be numeric (e.g. '123456')")
            return cleaned
        return v

    @field_validator("dot_number")
    @classmethod
    def validate_dot_number(cls, v):
        if v is not None:
            cleaned = v.replace("DOT-", "").replace("DOT", "").strip()
            if not cleaned.isdigit():
                raise ValueError("DOT number must be numeric")
            return cleaned
        return v


class JobUpdateRequest(BaseModel):
    """Request model for updating a job posting (all fields optional)."""
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    company_name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    how_to_apply: Optional[str] = Field(None, min_length=5, max_length=1000)
    mc_number: Optional[str] = Field(None, max_length=20)
    dot_number: Optional[str] = Field(None, max_length=20)
    haul_type: Optional[HaulType] = None
    equipment: Optional[EquipmentType] = None
    pay_info: Optional[str] = Field(None, max_length=500)
    requirements: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class JobResponse(BaseModel):
    """Response model for a single job posting."""
    id: UUID
    posted_by: UUID
    title: str
    company_name: str
    description: Optional[str] = None
    how_to_apply: str

    mc_number: Optional[str] = None
    dot_number: Optional[str] = None
    fmcsa_verified: bool = False

    haul_type: str
    equipment: str
    pay_info: Optional[str] = None
    requirements: List[str] = []
    regions: List[str] = []

    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    poster_handle: Optional[str] = None
    poster_cb_handle: Optional[str] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Paginated list of job postings."""
    jobs: List[JobResponse]
    total: int
    limit: int
    offset: int


class JobMatchResponse(BaseModel):
    """A job posting with a match score for the current driver."""
    job: JobResponse
    match_score: int = 0
    match_reasons: List[str] = []

    class Config:
        from_attributes = True


class JobMatchListResponse(BaseModel):
    """Paginated list of matched jobs."""
    matches: List[JobMatchResponse]
    total: int
    limit: int
    offset: int
