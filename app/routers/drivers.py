"""
Driver Router
Endpoints for driver profile management
"""

from fastapi import APIRouter, HTTPException, status, Depends
from supabase import Client
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.database import get_db_admin
from app.models.driver import (
    DriverCreateRequest,
    DriverCreate,
    DriverUpdate,
    Driver,
    DriverPublic,
    StatusUpdate
)
from app.models.follow_up import StatusUpdateWithFollowUp
from app.services.follow_up_engine import determine_follow_up
from app.utils.location import calculate_distance
from app.dependencies import get_current_user, get_current_driver
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drivers", tags=["Drivers"])


def parse_timestamp(timestamp_str: str) -> datetime:
    """
    Safely parse timestamp from Supabase, handling various formats.
    Supabase may return timestamps with varying microsecond precision.
    """
    try:
        # Remove 'Z' and replace with +00:00
        timestamp_str = timestamp_str.replace("Z", "+00:00")

        # Try parsing directly first
        try:
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            # If it fails, it might be due to microsecond precision
            # Parse manually and truncate microseconds if needed
            from dateutil import parser
            return parser.isoparse(timestamp_str)
    except Exception as e:
        logger.error(f"Failed to parse timestamp '{timestamp_str}': {e}")
        # Fallback to current time
        return datetime.utcnow()


@router.post("", response_model=Driver, status_code=status.HTTP_201_CREATED)
async def create_driver_profile(
    driver_data: DriverCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db_admin)
):
    """
    Create driver profile for current user.
    This is the onboarding step after authentication.
    Frontend sends: { handle, avatar_id, status }
    Backend adds: user_id from authenticated user
    """
    try:
        # Check if driver profile already exists
        existing = db.from_("drivers").select("id").eq(
            "user_id", current_user.id
        ).execute()

        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Driver profile already exists"
            )

        # Check if handle is unique
        handle_check = db.from_("drivers").select("id").eq(
            "handle", driver_data.handle
        ).execute()

        if handle_check.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Handle '{driver_data.handle}' is already taken"
            )

        # Create driver profile - add user_id from authenticated user
        driver_dict = driver_data.model_dump()
        driver_dict["user_id"] = str(current_user.id)  # Convert to string for Supabase

        response = db.from_("drivers").insert(driver_dict).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create driver profile"
            )

        logger.info(f"Driver profile created for user {current_user.id}")

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create driver profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create driver profile: {str(e)}"
        )


@router.get("/me", response_model=Driver)
async def get_my_profile(
    driver: dict = Depends(get_current_driver)
):
    """
    Get current driver's full profile.
    """
    return driver


@router.put("/me", response_model=Driver)
async def update_my_profile(
    updates: DriverUpdate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Update current driver's profile.
    """
    try:
        # If handle is being changed, check uniqueness
        if updates.handle and updates.handle != driver["handle"]:
            handle_check = db.from_("drivers").select("id").eq(
                "handle", updates.handle
            ).execute()

            if handle_check.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Handle '{updates.handle}' is already taken"
                )

        # Update profile
        update_dict = updates.model_dump(exclude_unset=True)

        response = db.from_("drivers").update(update_dict).eq(
            "id", driver["id"]
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )

        logger.info(f"Driver profile updated: {driver['id']}")

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update driver profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.get("/{driver_id}", response_model=DriverPublic)
async def get_driver_by_id(
    driver_id: UUID,
    db: Client = Depends(get_db_admin)
):
    """
    Get public driver profile by ID.
    Returns limited public information.
    """
    try:
        response = db.from_("drivers").select(
            "id,handle,first_name,status,created_at"
        ).eq("id", driver_id).single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Driver not found"
            )

        return response.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch driver: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch driver"
        )


@router.get("/handle/{handle}", response_model=DriverPublic)
async def get_driver_by_handle(
    handle: str,
    db: Client = Depends(get_db_admin)
):
    """
    Get public driver profile by handle.
    Returns limited public information.
    """
    try:
        response = db.from_("drivers").select(
            "id,handle,first_name,status,created_at"
        ).eq("handle", handle).single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Driver with handle '{handle}' not found"
            )

        return response.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch driver by handle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch driver"
        )


@router.post("/me/status", response_model=StatusUpdateWithFollowUp)
async def update_my_status(
    status_update: StatusUpdate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Update current driver's status with intelligent follow-up questions.

    Valid statuses: rolling, waiting, parked.

    If location (latitude, longitude) is provided, the system will:
    1. Calculate context from previous status (time elapsed, distance moved)
    2. Determine if a follow-up question is appropriate
    3. Return the question for the frontend to display

    Phase 1 MVP covers:
    - WAITING → ROLLING: Detention time and payment tracking
    - PARKED → ROLLING: Parking safety/vibe feedback
    """
    try:
        # Get previous status from status_updates table
        prev_query = db.from_("status_updates") \
            .select("*") \
            .eq("driver_id", driver["id"]) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        prev = prev_query.data[0] if prev_query.data else None

        # Use location from request, or fall back to driver_locations table
        current_latitude = status_update.latitude
        current_longitude = status_update.longitude

        if current_latitude is None or current_longitude is None:
            # Try to get from driver_locations
            location_query = db.from_("driver_locations") \
                .select("latitude, longitude") \
                .eq("driver_id", driver["id"]) \
                .single() \
                .execute()

            if location_query.data:
                current_latitude = location_query.data["latitude"]
                current_longitude = location_query.data["longitude"]

        # Initialize context and question
        context = None
        question = None
        facility_id = None
        facility_name = None

        # Only calculate context if we have location data
        if current_latitude is not None and current_longitude is not None:
            # Try to find facility at current location
            facilities = db.from_("facilities").select("*").execute()

            if facilities.data:
                for facility in facilities.data:
                    distance = calculate_distance(
                        current_latitude,
                        current_longitude,
                        facility["latitude"],
                        facility["longitude"]
                    )
                    if distance <= 0.3:  # Within 0.3 miles
                        facility_id = facility["id"]
                        facility_name = facility["name"]
                        break

            # Determine follow-up question based on context
            context, question = determine_follow_up(
                prev_status=prev["status"] if prev else None,
                prev_latitude=prev["latitude"] if prev else None,
                prev_longitude=prev["longitude"] if prev else None,
                prev_updated_at=parse_timestamp(prev["created_at"]) if prev else None,
                new_status=status_update.status,
                new_latitude=current_latitude,
                new_longitude=current_longitude,
                facility_name=facility_name
            )

        # Save status_update record with context
        status_record = {
            "driver_id": driver["id"],
            "status": status_update.status,
            "latitude": current_latitude,
            "longitude": current_longitude,
            "facility_id": facility_id,
            # Previous context
            "prev_status": prev["status"] if prev else None,
            "prev_latitude": prev["latitude"] if prev else None,
            "prev_longitude": prev["longitude"] if prev else None,
            "prev_facility_id": prev["facility_id"] if prev else None,
            "prev_updated_at": prev["created_at"] if prev else None,
        }

        # Add calculated context if available
        if context:
            status_record.update({
                "time_since_last_seconds": context.time_since_seconds,
                "distance_from_last_miles": context.distance_miles,
            })

        # Add follow-up question if present
        if question:
            status_record.update({
                "follow_up_question_type": question.question_type,
                "follow_up_question_text": question.text,
                "follow_up_options": [opt.model_dump() for opt in question.options],
                "follow_up_skippable": question.skippable,
                "follow_up_auto_dismiss_seconds": question.auto_dismiss_seconds,
            })

        # Insert status update record
        result = db.from_("status_updates").insert(status_record).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record status update"
            )

        status_update_id = result.data[0]["id"]

        # Update driver's current status and last_active
        db.from_("drivers").update({
            "status": status_update.status,
            "last_active": datetime.utcnow().isoformat()
        }).eq("id", driver["id"]).execute()

        logger.info(
            f"Driver {driver['id']} status updated to {status_update.status}" +
            (f" with follow-up question: {question.question_type}" if question else "")
        )

        # Return response with follow-up question
        return StatusUpdateWithFollowUp(
            status_update_id=status_update_id,
            status=status_update.status,
            prev_status=prev["status"] if prev else None,
            context=context,
            follow_up_question=question,
            message="Status updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update driver status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update status: {str(e)}"
        )
