"""
Facility Review Models
Pydantic models for facility ratings & reviews with category ratings per facility type
"""

from datetime import date, datetime
from typing import Optional, List, Dict
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class FacilityType(str, Enum):
    SHIPPER = "shipper"
    RECEIVER = "receiver"
    WAREHOUSE = "warehouse"
    MECHANIC = "mechanic"
    TRUCK_STOP = "truck_stop"
    REST_AREA = "rest_area"
    BROKER = "broker"
    WEIGH_STATION = "weigh_station"
    SERVICE_PLAZA = "service_plaza"
    OTHER = "other"


# Category ratings valid for each facility type
CATEGORY_RATINGS_BY_TYPE: Dict[str, List[str]] = {
    "shipper": [
        "dock_wait_time", "check_in_process", "dock_staff",
        "parking", "restroom_access", "safety"
    ],
    "receiver": [
        "dock_wait_time", "check_in_process", "dock_staff",
        "parking", "restroom_access", "safety"
    ],
    "warehouse": [
        "dock_wait_time", "organization", "dock_equipment",
        "parking", "lumper_fees", "safety"
    ],
    "mechanic": [
        "turnaround_time", "quality_of_work", "pricing",
        "communication", "parts_availability", "truck_parking"
    ],
    "truck_stop": [
        "fuel_price", "parking", "showers",
        "food", "restrooms", "wifi", "safety"
    ],
    "rest_area": [
        "parking", "restrooms", "safety", "truck_friendly"
    ],
    "broker": [
        "pay_speed", "rate_fairness", "communication",
        "load_accuracy", "detention_pay"
    ],
    "weigh_station": [
        "wait_time", "staff", "safety"
    ],
    "service_plaza": [
        "fuel_price", "parking", "food",
        "restrooms", "safety"
    ],
    "other": [],
}

# Human-readable labels for categories
CATEGORY_LABELS: Dict[str, str] = {
    "dock_wait_time": "Dock Wait Time",
    "check_in_process": "Check-in Process",
    "dock_staff": "Dock Staff",
    "parking": "Parking",
    "restroom_access": "Restroom Access",
    "safety": "Safety",
    "organization": "Organization",
    "dock_equipment": "Dock Equipment",
    "lumper_fees": "Lumper Fees",
    "turnaround_time": "Turnaround Time",
    "quality_of_work": "Quality of Work",
    "pricing": "Pricing",
    "communication": "Communication",
    "parts_availability": "Parts Availability",
    "truck_parking": "Truck Parking",
    "fuel_price": "Fuel Price",
    "showers": "Showers",
    "food": "Food",
    "restrooms": "Restrooms",
    "wifi": "WiFi",
    "truck_friendly": "Truck Friendly",
    "pay_speed": "Pay Speed",
    "rate_fairness": "Rate Fairness",
    "load_accuracy": "Load Accuracy",
    "detention_pay": "Detention Pay",
    "wait_time": "Wait Time",
    "staff": "Staff",
}


# ── Request Models ──────────────────────────────────────────────────

class ReviewedFacilityCreate(BaseModel):
    """Create a reviewed facility (manual add or from Google Places)."""
    name: str = Field(..., min_length=1, max_length=255)
    facility_type: FacilityType
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=10)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = None
    google_place_id: Optional[str] = Field(None, max_length=255)
    google_data: Optional[dict] = None
    google_rating: Optional[float] = None
    google_review_count: Optional[int] = None
    auto_detected_type: Optional[str] = None
    # Driver's GPS when adding manually — used as fallback coords + trust signal
    reviewer_latitude: Optional[float] = None
    reviewer_longitude: Optional[float] = None


VALID_VISIT_COUNTS = ["first_visit", "2_to_5", "6_to_10", "regular"]


class ReviewCreate(BaseModel):
    """Create a review for a facility."""
    overall_rating: int = Field(..., ge=1, le=5)
    category_ratings: Dict[str, int] = Field(default_factory=dict)
    comment: Optional[str] = Field(None, max_length=2000)
    visit_date: Optional[date] = None
    would_return: Optional[bool] = None
    visit_count: Optional[str] = "first_visit"
    confirm_type: Optional[str] = None

    @field_validator("visit_count")
    @classmethod
    def validate_visit_count(cls, v):
        if v is not None and v not in VALID_VISIT_COUNTS:
            raise ValueError(
                f"Invalid visit_count '{v}'. Must be one of: {VALID_VISIT_COUNTS}"
            )
        return v

    @field_validator("category_ratings")
    @classmethod
    def validate_category_values(cls, v):
        for key, val in v.items():
            if not isinstance(val, int) or val < 1 or val > 5:
                raise ValueError(
                    f"Category rating '{key}' must be an integer between 1 and 5"
                )
        return v

    @field_validator("visit_date")
    @classmethod
    def validate_visit_date(cls, v):
        if v is not None and v > date.today():
            raise ValueError("Visit date cannot be in the future")
        return v

    @field_validator("confirm_type")
    @classmethod
    def validate_confirm_type(cls, v):
        if v is not None:
            valid = [t.value for t in FacilityType]
            if v not in valid:
                raise ValueError(
                    f"Invalid facility type '{v}'. Must be one of: {valid}"
                )
        return v


class ReviewUpdate(BaseModel):
    """Update an existing review (all fields optional). Old version is archived."""
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    category_ratings: Optional[Dict[str, int]] = None
    comment: Optional[str] = Field(None, max_length=2000)
    visit_date: Optional[date] = None
    would_return: Optional[bool] = None
    visit_count: Optional[str] = None

    @field_validator("visit_count")
    @classmethod
    def validate_visit_count(cls, v):
        if v is not None and v not in VALID_VISIT_COUNTS:
            raise ValueError(
                f"Invalid visit_count '{v}'. Must be one of: {VALID_VISIT_COUNTS}"
            )
        return v

    @field_validator("category_ratings")
    @classmethod
    def validate_category_values(cls, v):
        if v is not None:
            for key, val in v.items():
                if not isinstance(val, int) or val < 1 or val > 5:
                    raise ValueError(
                        f"Category rating '{key}' must be an integer between 1 and 5"
                    )
        return v

    @field_validator("visit_date")
    @classmethod
    def validate_visit_date(cls, v):
        if v is not None and v > date.today():
            raise ValueError("Visit date cannot be in the future")
        return v


# ── Response Models ──────────────────────────────────────────────────

class ReviewResponse(BaseModel):
    """Single review response with reviewer info."""
    id: UUID
    reviewed_facility_id: UUID
    reviewer_id: UUID
    overall_rating: int
    category_ratings: Dict[str, int] = {}
    comment: Optional[str] = None
    visit_date: Optional[date] = None
    would_return: Optional[bool] = None
    visit_count: Optional[str] = "first_visit"
    revision_number: int = 0
    created_at: datetime
    updated_at: datetime

    # Joined reviewer info
    reviewer_handle: Optional[str] = None
    reviewer_avatar_id: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewedFacilityResponse(BaseModel):
    """Full facility data with aggregated ratings."""
    id: UUID
    facility_id: Optional[UUID] = None
    name: str
    facility_type: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    google_place_id: Optional[str] = None
    google_rating: Optional[float] = None
    google_review_count: Optional[int] = None
    auto_detected_type: Optional[str] = None
    type_confirmed: bool = False
    type_correction_count: int = 0
    avg_overall_rating: float = 0
    total_reviews: int = 0
    category_averages: Dict[str, float] = {}
    location_source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Source indicator for search results
    source: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewedFacilityDetailResponse(BaseModel):
    """Facility detail with reviews list."""
    facility: ReviewedFacilityResponse
    reviews: List[ReviewResponse] = []
    my_review: Optional[ReviewResponse] = None


class FacilitySearchResponse(BaseModel):
    """Search results combining local DB + Google Places."""
    facilities: List[ReviewedFacilityResponse]
    total: int


class FacilityListResponse(BaseModel):
    """Paginated facility list."""
    facilities: List[ReviewedFacilityResponse]
    total: int
    limit: int
    offset: int


class MyReviewsResponse(BaseModel):
    """List of all reviews by current user."""
    reviews: List[ReviewResponse]
    total: int


class CategoryInfo(BaseModel):
    """Category rating metadata for a facility type."""
    key: str
    label: str
