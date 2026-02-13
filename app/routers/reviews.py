"""
Reviews Router
Endpoints for facility ratings & reviews: search, CRUD, Google Places fallback
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from supabase import Client
from typing import Optional
from uuid import UUID
from datetime import date
from app.database import get_db_admin
from app.dependencies import get_current_driver
from app.models.review import (
    FacilityType,
    CATEGORY_RATINGS_BY_TYPE,
    CATEGORY_LABELS,
    ReviewedFacilityCreate,
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewedFacilityResponse,
    ReviewedFacilityDetailResponse,
    FacilitySearchResponse,
    FacilityListResponse,
    MyReviewsResponse,
    CategoryInfo,
)
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ── Google type auto-detection ──────────────────────────────────────

GOOGLE_TYPE_MAP = {
    # High confidence
    "gas_station": "truck_stop",
    "car_repair": "mechanic",
    "car_wash": "mechanic",
    # Medium confidence
    "parking": "rest_area",
    "storage": "warehouse",
    "moving_company": "warehouse",
    "lodging": "truck_stop",
}


def _detect_facility_type(google_types: list) -> str:
    """Auto-detect facility type from Google Places types array."""
    if not google_types:
        return "other"
    for gtype in google_types:
        if gtype in GOOGLE_TYPE_MAP:
            return GOOGLE_TYPE_MAP[gtype]
    return "other"


# ── Helpers ──────────────────────────────────────────────────────────

def _validate_category_ratings(facility_type: str, category_ratings: dict):
    """Validate that category rating keys are valid for the facility type."""
    valid_keys = CATEGORY_RATINGS_BY_TYPE.get(facility_type, [])
    for key in category_ratings:
        if key not in valid_keys:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid category '{key}' for facility type '{facility_type}'. "
                    f"Valid categories: {valid_keys}"
                )
            )


def _row_to_facility_response(row: dict, source: str = "local") -> ReviewedFacilityResponse:
    """Convert a Supabase row to a ReviewedFacilityResponse."""
    return ReviewedFacilityResponse(
        id=row["id"],
        facility_id=row.get("facility_id"),
        name=row["name"],
        facility_type=row["facility_type"],
        address=row.get("address"),
        city=row.get("city"),
        state=row.get("state"),
        zip_code=row.get("zip_code"),
        latitude=row.get("latitude"),
        longitude=row.get("longitude"),
        phone=row.get("phone"),
        website=row.get("website"),
        google_place_id=row.get("google_place_id"),
        google_rating=row.get("google_rating"),
        google_review_count=row.get("google_review_count"),
        auto_detected_type=row.get("auto_detected_type"),
        type_confirmed=row.get("type_confirmed", False),
        type_correction_count=row.get("type_correction_count", 0),
        avg_overall_rating=float(row.get("avg_overall_rating", 0) or 0),
        total_reviews=row.get("total_reviews", 0),
        category_averages=row.get("category_averages") or {},
        location_source=row.get("location_source"),
        created_at=row["created_at"],
        updated_at=row.get("updated_at", row["created_at"]),
        source=source,
    )


def _row_to_review_response(row: dict) -> ReviewResponse:
    """Convert a Supabase row to a ReviewResponse."""
    return ReviewResponse(
        id=row["id"],
        reviewed_facility_id=row["reviewed_facility_id"],
        reviewer_id=row["reviewer_id"],
        overall_rating=row["overall_rating"],
        category_ratings=row.get("category_ratings") or {},
        comment=row.get("comment"),
        visit_date=row.get("visit_date"),
        would_return=row.get("would_return"),
        visit_count=row.get("visit_count", "first_visit"),
        revision_number=row.get("revision_number", 0),
        created_at=row["created_at"],
        updated_at=row.get("updated_at", row["created_at"]),
        reviewer_handle=row.get("reviewer_handle"),
        reviewer_avatar_id=row.get("reviewer_avatar_id"),
    )


def _archive_review(db: Client, review_row: dict):
    """Archive the current version of a review before it gets updated."""
    try:
        db.from_("facility_review_history").insert({
            "review_id": review_row["id"],
            "reviewed_facility_id": review_row["reviewed_facility_id"],
            "reviewer_id": review_row["reviewer_id"],
            "overall_rating": review_row["overall_rating"],
            "category_ratings": review_row.get("category_ratings") or {},
            "comment": review_row.get("comment"),
            "visit_date": review_row.get("visit_date"),
            "would_return": review_row.get("would_return"),
            "visit_count": review_row.get("visit_count"),
            "revision_number": review_row.get("revision_number", 0),
            "original_created_at": review_row["created_at"],
            "original_updated_at": review_row.get("updated_at", review_row["created_at"]),
        }).execute()
    except Exception as e:
        logger.error(f"Failed to archive review {review_row['id']}: {e}")


def _recalculate_category_averages(db: Client, facility_id: str):
    """Recalculate category_averages JSONB from all reviews for a facility."""
    try:
        reviews_resp = db.from_("facility_reviews") \
            .select("category_ratings") \
            .eq("reviewed_facility_id", facility_id) \
            .execute()

        if not reviews_resp.data:
            db.from_("reviewed_facilities") \
                .update({"category_averages": {}}) \
                .eq("id", facility_id) \
                .execute()
            return

        # Aggregate all category ratings
        totals: dict = {}
        counts: dict = {}
        for review in reviews_resp.data:
            ratings = review.get("category_ratings") or {}
            for key, val in ratings.items():
                if isinstance(val, (int, float)):
                    totals[key] = totals.get(key, 0) + val
                    counts[key] = counts.get(key, 0) + 1

        averages = {
            key: round(totals[key] / counts[key], 1)
            for key in totals
        }

        db.from_("reviewed_facilities") \
            .update({"category_averages": averages}) \
            .eq("id", facility_id) \
            .execute()

    except Exception as e:
        logger.error(f"Failed to recalculate category averages for {facility_id}: {e}")


# ── GET /api/v1/reviews/categories/{facility_type} ─────────────────

@router.get("/categories/{facility_type}", response_model=list)
async def get_categories_for_type(facility_type: str):
    """Get the valid category ratings for a facility type."""
    categories = CATEGORY_RATINGS_BY_TYPE.get(facility_type)
    if categories is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown facility type: {facility_type}"
        )
    return [
        CategoryInfo(key=key, label=CATEGORY_LABELS.get(key, key))
        for key in categories
    ]


# ── GET /api/v1/reviews/facilities/search ──────────────────────────

@router.get("/facilities/search", response_model=FacilitySearchResponse)
async def search_facilities(
    q: Optional[str] = Query(None, description="Search by name or address"),
    type: Optional[str] = Query(None, description="Filter by facility type"),
    lat: Optional[float] = Query(None, description="Latitude for nearby search"),
    lng: Optional[float] = Query(None, description="Longitude for nearby search"),
    limit: int = Query(20, ge=1, le=100),
    db: Client = Depends(get_db_admin)
):
    """
    Search facilities — checks local DB first, falls back to Google Places API.
    Google results are auto-saved to our DB on first search.
    """
    try:
        # 1. Search local DB
        query = db.from_("reviewed_facilities").select("*", count="exact")

        if q:
            query = query.or_(
                f"name.ilike.%{q}%,"
                f"address.ilike.%{q}%,"
                f"city.ilike.%{q}%"
            )

        if type:
            query = query.eq("facility_type", type)

        query = query.order("avg_overall_rating", desc=True).limit(limit)
        response = query.execute()

        local_results = response.data or []
        facilities = [_row_to_facility_response(r, "local") for r in local_results]

        # 2. If fewer than 5 local results and we have a query, try Google Places
        if len(local_results) < 5 and (q or (lat and lng)):
            try:
                from app.services.google_places_api import search_places
                from app.config import settings

                google_api_key = getattr(settings, "google_places_api_key", None) or \
                                 getattr(settings, "google_api_key", None)

                if google_api_key:
                    location_str = None
                    if lat and lng:
                        location_str = f"{lat},{lng}"

                    search_query = q or "truck stop"
                    google_results = search_places(
                        query=search_query,
                        api_key=google_api_key,
                        location=location_str,
                        limit=10
                    )

                    # Existing google_place_ids in our results
                    existing_ids = {
                        r.get("google_place_id")
                        for r in local_results
                        if r.get("google_place_id")
                    }

                    for place in google_results:
                        if place.place_id and place.place_id not in existing_ids:
                            # Check if already in DB
                            existing = db.from_("reviewed_facilities") \
                                .select("id") \
                                .eq("google_place_id", place.place_id) \
                                .execute()

                            if existing.data:
                                # Already saved, fetch full record
                                full = db.from_("reviewed_facilities") \
                                    .select("*") \
                                    .eq("google_place_id", place.place_id) \
                                    .execute()
                                if full.data:
                                    facilities.append(
                                        _row_to_facility_response(full.data[0], "local")
                                    )
                                continue

                            # Auto-detect facility type from Google types
                            detected_type = _detect_facility_type(place.types or [])

                            # Save to our DB
                            insert_data = {
                                "name": place.name or "Unknown",
                                "facility_type": detected_type,
                                "address": place.address,
                                "city": place.city,
                                "state": place.state,
                                "zip_code": place.zip_code,
                                "latitude": place.latitude,
                                "longitude": place.longitude,
                                "phone": place.phone,
                                "website": place.website,
                                "google_place_id": place.place_id,
                                "google_data": place.to_dict(),
                                "google_rating": place.rating,
                                "google_review_count": place.review_count,
                                "auto_detected_type": detected_type,
                                "type_confirmed": False,
                                "location_source": "google",
                            }

                            try:
                                insert_resp = db.from_("reviewed_facilities") \
                                    .insert(insert_data) \
                                    .execute()

                                if insert_resp.data:
                                    facilities.append(
                                        _row_to_facility_response(
                                            insert_resp.data[0], "google"
                                        )
                                    )
                                    existing_ids.add(place.place_id)
                            except Exception as insert_err:
                                logger.warning(
                                    f"Failed to save Google place {place.place_id}: {insert_err}"
                                )

            except ImportError:
                logger.warning("Google Places service not available")
            except Exception as google_err:
                logger.error(f"Google Places search failed: {google_err}")

        return FacilitySearchResponse(
            facilities=facilities[:limit],
            total=len(facilities)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search facilities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search facilities"
        )


# ── GET /api/v1/reviews/facilities/nearby ──────────────────────────

@router.get("/facilities/nearby", response_model=FacilityListResponse)
async def get_nearby_facilities(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: float = Query(25.0, description="Radius in miles"),
    type: Optional[str] = Query(None, description="Filter by facility type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Client = Depends(get_db_admin)
):
    """Get facilities near a location, sorted by distance."""
    try:
        # Approximate degree-to-miles conversion
        lat_range = radius / 69.0
        lng_range = radius / 54.6

        query = db.from_("reviewed_facilities") \
            .select("*", count="exact") \
            .gte("latitude", lat - lat_range) \
            .lte("latitude", lat + lat_range) \
            .gte("longitude", lng - lng_range) \
            .lte("longitude", lng + lng_range)

        if type:
            query = query.eq("facility_type", type)

        query = query.order("avg_overall_rating", desc=True) \
            .range(offset, offset + limit - 1)

        response = query.execute()

        facilities = [
            _row_to_facility_response(r) for r in (response.data or [])
        ]

        return FacilityListResponse(
            facilities=facilities,
            total=response.count or 0,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to get nearby facilities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get nearby facilities"
        )


# ── GET /api/v1/reviews/facilities/top-rated ───────────────────────

@router.get("/facilities/top-rated", response_model=FacilityListResponse)
async def get_top_rated_facilities(
    type: Optional[str] = Query(None, description="Filter by facility type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Client = Depends(get_db_admin)
):
    """Get top-rated facilities, optionally filtered by type."""
    try:
        query = db.from_("reviewed_facilities") \
            .select("*", count="exact") \
            .gt("total_reviews", 0)

        if type:
            query = query.eq("facility_type", type)

        query = query.order("avg_overall_rating", desc=True) \
            .range(offset, offset + limit - 1)

        response = query.execute()

        facilities = [
            _row_to_facility_response(r) for r in (response.data or [])
        ]

        return FacilityListResponse(
            facilities=facilities,
            total=response.count or 0,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to get top-rated facilities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get top-rated facilities"
        )


# ── GET /api/v1/reviews/me ─────────────────────────────────────────

@router.get("/me", response_model=MyReviewsResponse)
async def get_my_reviews(
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Get all reviews by the current user."""
    try:
        response = db.from_("facility_reviews") \
            .select("*") \
            .eq("reviewer_id", driver["id"]) \
            .order("created_at", desc=True) \
            .execute()

        reviews = []
        for row in (response.data or []):
            review = _row_to_review_response(row)
            review.reviewer_handle = driver.get("handle")
            review.reviewer_avatar_id = driver.get("avatar_id")
            reviews.append(review)

        return MyReviewsResponse(
            reviews=reviews,
            total=len(reviews)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get my reviews: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get your reviews"
        )


# ── GET /api/v1/reviews/facilities/{id} ────────────────────────────

@router.get("/facilities/{facility_id}", response_model=ReviewedFacilityDetailResponse)
async def get_facility_detail(
    facility_id: UUID,
    db: Client = Depends(get_db_admin)
):
    """Get full facility detail with all reviews."""
    try:
        # Fetch facility
        fac_resp = db.from_("reviewed_facilities") \
            .select("*") \
            .eq("id", str(facility_id)) \
            .execute()

        if not fac_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facility not found"
            )

        facility = _row_to_facility_response(fac_resp.data[0])

        # Fetch all reviews for this facility
        reviews_resp = db.from_("facility_reviews") \
            .select("*") \
            .eq("reviewed_facility_id", str(facility_id)) \
            .order("created_at", desc=True) \
            .execute()

        reviews = []
        reviewer_ids = set()
        for row in (reviews_resp.data or []):
            reviews.append(_row_to_review_response(row))
            reviewer_ids.add(row["reviewer_id"])

        # Fetch reviewer info
        if reviewer_ids:
            drivers_resp = db.from_("drivers") \
                .select("id, handle, avatar_id") \
                .in_("id", list(reviewer_ids)) \
                .execute()

            driver_map = {
                d["id"]: d for d in (drivers_resp.data or [])
            }

            for review in reviews:
                driver_info = driver_map.get(str(review.reviewer_id))
                if driver_info:
                    review.reviewer_handle = driver_info.get("handle")
                    review.reviewer_avatar_id = driver_info.get("avatar_id")

        return ReviewedFacilityDetailResponse(
            facility=facility,
            reviews=reviews,
            my_review=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get facility {facility_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get facility details"
        )


# ── POST /api/v1/reviews/facilities ────────────────────────────────

@router.post("/facilities", response_model=ReviewedFacilityResponse,
             status_code=status.HTTP_201_CREATED)
async def add_facility(
    data: ReviewedFacilityCreate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Add a facility manually. Requires location (facility coords or driver GPS)."""
    try:
        # Check for duplicate google_place_id
        if data.google_place_id:
            existing = db.from_("reviewed_facilities") \
                .select("id") \
                .eq("google_place_id", data.google_place_id) \
                .execute()

            if existing.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This facility already exists in our database"
                )

        # Determine final coordinates + source
        final_lat = data.latitude
        final_lng = data.longitude
        location_source = "unknown"

        if data.google_place_id:
            location_source = "google"
        elif final_lat is not None and final_lng is not None:
            location_source = "manual"
        elif data.reviewer_latitude is not None and data.reviewer_longitude is not None:
            # Use driver's GPS as facility coordinates
            final_lat = data.reviewer_latitude
            final_lng = data.reviewer_longitude
            location_source = "driver_gps"

        # Manual adds (no google_place_id) require some form of coordinates
        if not data.google_place_id and (final_lat is None or final_lng is None):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Location required. Use 'I'm here now' with GPS enabled, or enter an address and verify it on the map."
            )

        # Duplicate detection: check for nearby facilities with similar names
        if final_lat is not None and final_lng is not None:
            lat_range = 0.15 / 69.0  # ~0.15 miles
            lng_range = 0.15 / 54.6
            nearby = db.from_("reviewed_facilities") \
                .select("id, name, facility_type, address, city, state, avg_overall_rating, total_reviews") \
                .gte("latitude", final_lat - lat_range) \
                .lte("latitude", final_lat + lat_range) \
                .gte("longitude", final_lng - lng_range) \
                .lte("longitude", final_lng + lng_range) \
                .execute()

            if nearby.data:
                # Check for similar names (case-insensitive prefix match)
                name_lower = data.name.lower().strip()
                for candidate in nearby.data:
                    candidate_name = (candidate.get("name") or "").lower().strip()
                    # Match if names share first 5+ chars or one contains the other
                    if (len(name_lower) >= 5 and candidate_name.startswith(name_lower[:5])) or \
                       name_lower in candidate_name or candidate_name in name_lower:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail={
                                "message": "A similar facility already exists nearby",
                                "existing_facility": {
                                    "id": str(candidate["id"]),
                                    "name": candidate["name"],
                                    "facility_type": candidate.get("facility_type"),
                                    "address": candidate.get("address"),
                                    "city": candidate.get("city"),
                                    "state": candidate.get("state"),
                                    "avg_overall_rating": float(candidate.get("avg_overall_rating", 0) or 0),
                                    "total_reviews": candidate.get("total_reviews", 0),
                                }
                            }
                        )

        insert_data = data.model_dump(
            exclude_unset=True,
            exclude={"reviewer_latitude", "reviewer_longitude"}
        )
        insert_data["facility_type"] = data.facility_type.value
        insert_data["latitude"] = final_lat
        insert_data["longitude"] = final_lng
        insert_data["location_source"] = location_source
        insert_data["added_by"] = driver.get("user_id") or str(driver["id"])

        response = db.from_("reviewed_facilities") \
            .insert(insert_data) \
            .execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add facility"
            )

        logger.info(f"Facility added by driver {driver['id']}: {data.name} (source: {location_source})")
        return _row_to_facility_response(response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add facility: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add facility: {str(e)}"
        )


# ── POST /api/v1/reviews/facilities/{id}/reviews ──────────────────

@router.post("/facilities/{facility_id}/reviews",
             response_model=ReviewResponse,
             status_code=status.HTTP_201_CREATED)
async def submit_review(
    facility_id: UUID,
    data: ReviewCreate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Submit a review for a facility. One review per user per facility.
    Includes optional type confirmation for the first reviewer.
    """
    try:
        # Verify facility exists
        fac_resp = db.from_("reviewed_facilities") \
            .select("*") \
            .eq("id", str(facility_id)) \
            .execute()

        if not fac_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facility not found"
            )

        facility = fac_resp.data[0]
        facility_type = facility["facility_type"]

        # Handle type confirmation
        if data.confirm_type and not facility.get("type_confirmed", False):
            facility_type = data.confirm_type
            db.from_("reviewed_facilities") \
                .update({
                    "facility_type": data.confirm_type,
                    "type_confirmed": True,
                    "type_confirmed_by": driver["id"],
                }) \
                .eq("id", str(facility_id)) \
                .execute()

        # Validate category ratings against facility type
        if data.category_ratings:
            _validate_category_ratings(facility_type, data.category_ratings)

        # Check for existing review
        existing = db.from_("facility_reviews") \
            .select("id") \
            .eq("reviewed_facility_id", str(facility_id)) \
            .eq("reviewer_id", driver["id"]) \
            .execute()

        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already reviewed this facility. Use PATCH to update."
            )

        # Insert review
        insert_data = {
            "reviewed_facility_id": str(facility_id),
            "reviewer_id": driver["id"],
            "overall_rating": data.overall_rating,
            "category_ratings": data.category_ratings,
            "comment": data.comment,
            "would_return": data.would_return,
            "visit_count": data.visit_count or "first_visit",
            "revision_number": 0,
        }

        if data.visit_date:
            insert_data["visit_date"] = data.visit_date.isoformat()

        response = db.from_("facility_reviews") \
            .insert(insert_data) \
            .execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit review"
            )

        # Recalculate category averages (application layer)
        _recalculate_category_averages(db, str(facility_id))

        logger.info(
            f"Review submitted by driver {driver['id']} for facility {facility_id}"
        )

        review = _row_to_review_response(response.data[0])
        review.reviewer_handle = driver.get("handle")
        review.reviewer_avatar_id = driver.get("avatar_id")
        return review

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit review: {str(e)}"
        )


# ── PATCH /api/v1/reviews/facilities/{id}/reviews/mine ─────────────

@router.patch("/facilities/{facility_id}/reviews/mine",
              response_model=ReviewResponse)
async def update_my_review(
    facility_id: UUID,
    data: ReviewUpdate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Update the current user's review for a facility. Archives old version first."""
    try:
        # Fetch existing review
        existing = db.from_("facility_reviews") \
            .select("*") \
            .eq("reviewed_facility_id", str(facility_id)) \
            .eq("reviewer_id", driver["id"]) \
            .execute()

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You haven't reviewed this facility yet"
            )

        old_review = existing.data[0]

        # Get facility type for validation
        fac_resp = db.from_("reviewed_facilities") \
            .select("facility_type") \
            .eq("id", str(facility_id)) \
            .execute()

        facility_type = fac_resp.data[0]["facility_type"] if fac_resp.data else "other"

        update_dict = data.model_dump(exclude_unset=True)

        # Validate category ratings
        if "category_ratings" in update_dict and update_dict["category_ratings"]:
            _validate_category_ratings(facility_type, update_dict["category_ratings"])

        if "visit_date" in update_dict and update_dict["visit_date"]:
            update_dict["visit_date"] = update_dict["visit_date"].isoformat()

        if not update_dict:
            return _row_to_review_response(old_review)

        # Archive the old version before overwriting
        _archive_review(db, old_review)

        # Increment revision number
        update_dict["revision_number"] = (old_review.get("revision_number", 0) or 0) + 1

        response = db.from_("facility_reviews") \
            .update(update_dict) \
            .eq("reviewed_facility_id", str(facility_id)) \
            .eq("reviewer_id", driver["id"]) \
            .execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update review"
            )

        # Recalculate category averages
        _recalculate_category_averages(db, str(facility_id))

        logger.info(
            f"Review updated by driver {driver['id']} for facility {facility_id}"
        )

        review = _row_to_review_response(response.data[0])
        review.reviewer_handle = driver.get("handle")
        review.reviewer_avatar_id = driver.get("avatar_id")
        return review

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update review: {str(e)}"
        )


# ── DELETE /api/v1/reviews/facilities/{id}/reviews/mine ────────────

@router.delete("/facilities/{facility_id}/reviews/mine",
               status_code=status.HTTP_200_OK)
async def delete_my_review(
    facility_id: UUID,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Delete the current user's review for a facility."""
    try:
        existing = db.from_("facility_reviews") \
            .select("id") \
            .eq("reviewed_facility_id", str(facility_id)) \
            .eq("reviewer_id", driver["id"]) \
            .execute()

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You haven't reviewed this facility"
            )

        db.from_("facility_reviews") \
            .delete() \
            .eq("reviewed_facility_id", str(facility_id)) \
            .eq("reviewer_id", driver["id"]) \
            .execute()

        # Recalculate category averages
        _recalculate_category_averages(db, str(facility_id))

        logger.info(
            f"Review deleted by driver {driver['id']} for facility {facility_id}"
        )

        return {
            "success": True,
            "message": "Review deleted",
            "facility_id": str(facility_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete review"
        )


# ── POST /api/v1/reviews/facilities/{id}/flag-type ─────────────────

@router.post("/facilities/{facility_id}/flag-type",
             status_code=status.HTTP_200_OK)
async def flag_facility_type(
    facility_id: UUID,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Flag a facility as having the wrong type.
    After 3 flags, type_confirmed resets so the next reviewer can re-classify.
    """
    try:
        fac_resp = db.from_("reviewed_facilities") \
            .select("id, type_confirmed, type_correction_count") \
            .eq("id", str(facility_id)) \
            .execute()

        if not fac_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facility not found"
            )

        facility = fac_resp.data[0]
        new_count = (facility.get("type_correction_count", 0) or 0) + 1

        update_data = {"type_correction_count": new_count}

        # At 3 flags, reset type_confirmed
        if new_count >= 3:
            update_data["type_confirmed"] = False
            update_data["type_correction_count"] = 0

        db.from_("reviewed_facilities") \
            .update(update_data) \
            .eq("id", str(facility_id)) \
            .execute()

        logger.info(
            f"Facility {facility_id} type flagged by driver {driver['id']} "
            f"(count: {new_count})"
        )

        return {
            "success": True,
            "message": "Type flagged" if new_count < 3 else "Type reset for re-classification",
            "correction_count": new_count if new_count < 3 else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to flag facility type: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to flag facility type"
        )
