"""
Driver Router
Endpoints for driver profile management
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
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
    StatusUpdate,
    ProfileStats,
    DriverProfileUpdate,
    AccountDeletionRequest,
    CBHandleCheck,
    VALID_ROLES
)
from app.models.follow_up import StatusUpdateWithFollowUp
from app.services.follow_up_engine import determine_follow_up
from app.services.facility_discovery import find_nearby_facility
from app.utils.location import calculate_distance
from app.dependencies import get_current_user, get_current_driver
from app.services.cb_handle_generator import generate_cb_handle, generate_cb_handle_suggestions
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

        # Auto-generate CB handle if not provided
        if not driver_data.cb_handle:
            # Get existing CB handles to avoid collisions
            existing_response = db.from_("drivers").select("cb_handle").not_.is_("cb_handle", "null").execute()
            existing_handles = {d["cb_handle"] for d in existing_response.data} if existing_response.data else set()
            driver_data.cb_handle = generate_cb_handle(existing_handles)
        else:
            # Check CB handle uniqueness if user provided one
            cb_check = db.from_("drivers").select("id").eq(
                "cb_handle", driver_data.cb_handle
            ).execute()
            if cb_check.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"CB Handle '{driver_data.cb_handle}' is already taken"
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


@router.get("/cb-handle/suggestions")
async def get_cb_handle_suggestions(
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db_admin)
):
    """
    Get CB Handle suggestions for the current user.
    Returns 5 unique, trucker-themed handle suggestions.
    """
    try:
        # Get existing CB handles to avoid collisions
        existing_response = db.from_("drivers").select("cb_handle").not_.is_("cb_handle", "null").execute()
        existing_handles = {d["cb_handle"] for d in existing_response.data} if existing_response.data else set()

        suggestions = generate_cb_handle_suggestions(count=5, existing_handles=existing_handles)

        return {"suggestions": suggestions}

    except Exception as e:
        logger.error(f"Failed to generate CB handle suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate suggestions"
        )


@router.post("/cb-handle/check")
async def check_cb_handle_availability(
    check_data: CBHandleCheck,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db_admin)
):
    """
    Check if a CB Handle is available.
    Returns whether the handle is already taken.
    """
    try:
        result = db.from_("drivers").select("id").eq(
            "cb_handle", check_data.cb_handle
        ).execute()

        available = not result.data

        return {
            "cb_handle": check_data.cb_handle,
            "available": available
        }

    except Exception as e:
        logger.error(f"Failed to check CB handle availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check handle availability"
        )


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


@router.get("/seekers")
async def list_job_seekers(
    cdl_class: Optional[str] = Query(None),
    equipment: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Client = Depends(get_db_admin)
):
    """
    List drivers who are open to work and visible on the job board.
    Public endpoint for recruiters/companies to discover drivers.
    Respects privacy settings from professional_profiles.
    """
    try:
        query = db.from_("professional_profiles") \
            .select(
                "driver_id, cdl_class, endorsements, "
                "equipment_type, years_experience, "
                "preferred_haul, haul_type, "
                "drivers!inner(id, handle, cb_handle, role, avatar_id)",
                count="exact"
            ) \
            .eq("open_to_work", True) \
            .eq("is_public", True)

        if cdl_class:
            query = query.eq("cdl_class", cdl_class)
        if equipment:
            query = query.eq("equipment_type", equipment)
        if region:
            query = query.contains("preferred_haul", [region])

        query = query.order("updated_at", desc=True) \
            .range(offset, offset + limit - 1)

        response = query.execute()

        seekers = []
        for row in (response.data or []):
            driver_data = row.get("drivers", {})
            seekers.append({
                "driver_id": row["driver_id"],
                "handle": driver_data.get("handle"),
                "cb_handle": driver_data.get("cb_handle"),
                "role": driver_data.get("role"),
                "avatar_id": driver_data.get("avatar_id"),
                "cdl_class": row.get("cdl_class"),
                "endorsements": row.get("endorsements", []),
                "equipment_type": row.get("equipment_type"),
                "years_experience": row.get("years_experience"),
                "preferred_haul": row.get("preferred_haul", []),
                "haul_type": row.get("haul_type"),
            })

        return seekers

    except Exception as e:
        logger.error(f"Failed to list job seekers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list job seekers"
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

        # Location is REQUIRED for status updates
        # This ensures drivers appear on map and get location-based features
        current_latitude = status_update.latitude
        current_longitude = status_update.longitude

        if current_latitude is None or current_longitude is None:
            # Try to get from driver_locations as fallback
            location_query = db.from_("driver_locations") \
                .select("latitude, longitude") \
                .eq("driver_id", driver["id"]) \
                .single() \
                .execute()

            if location_query.data:
                current_latitude = location_query.data["latitude"]
                current_longitude = location_query.data["longitude"]
            else:
                # No location available - reject the request
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Location is required for status updates. Please enable location permissions and try again."
                )

        # Initialize context and question
        context = None
        question = None
        facility_id = None
        facility_name = None

        # Only calculate context if we have location data
        if current_latitude is not None and current_longitude is not None:
            # Find facility using smart discovery (queries OSM if needed)
            facility_id, facility_name = find_nearby_facility(
                db=db,
                latitude=current_latitude,
                longitude=current_longitude,
                max_distance_miles=0.3,
                discover_if_missing=True  # Trigger OSM query for unmapped areas
            )

            # Determine follow-up question based on context
            context, question, weather_info = determine_follow_up(
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
            weather_info=weather_info,
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


@router.get("/me/stats", response_model=ProfileStats)
async def get_my_stats(
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Get current driver's profile statistics.
    Returns total status updates, days active, breakdown by status, etc.
    """
    try:
        # Get total status updates count
        updates_response = db.from_("status_updates") \
            .select("id", count="exact") \
            .eq("driver_id", driver["id"]) \
            .execute()

        total_updates = updates_response.count or 0

        # Get status breakdown
        status_breakdown = db.from_("status_updates") \
            .select("status") \
            .eq("driver_id", driver["id"]) \
            .execute()

        rolling_count = sum(1 for s in status_breakdown.data if s["status"] == "rolling")
        waiting_count = sum(1 for s in status_breakdown.data if s["status"] == "waiting")
        parked_count = sum(1 for s in status_breakdown.data if s["status"] == "parked")

        # Calculate days active (days since account creation)
        created_at = parse_timestamp(driver["created_at"])
        # Make utcnow() timezone-aware to match parsed timestamps
        now_utc = datetime.utcnow().replace(tzinfo=created_at.tzinfo) if created_at.tzinfo else datetime.utcnow()
        days_active = (now_utc - created_at).days

        last_active = parse_timestamp(driver["last_active"])

        return ProfileStats(
            total_status_updates=total_updates,
            days_active=days_active,
            rolling_count=rolling_count,
            waiting_count=waiting_count,
            parked_count=parked_count,
            member_since=created_at,
            last_active=last_active
        )

    except Exception as e:
        logger.error(f"Failed to fetch driver stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch stats"
        )


@router.patch("/me/profile", response_model=Driver)
async def update_my_profile_info(
    updates: DriverProfileUpdate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Update driver profile information.
    Supports: handle, avatar_id, role, cb_handle, show_on_map_as, profile_photo_url.
    Status updates should use POST /me/status endpoint.
    """
    try:
        # Build update dict from provided fields only
        update_dict = {}

        # Handle update with uniqueness check
        if updates.handle is not None:
            if updates.handle != driver["handle"]:
                # Check if new handle is unique
                handle_check = db.from_("drivers").select("id").eq(
                    "handle", updates.handle
                ).execute()

                if handle_check.data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Handle '{updates.handle}' is already taken"
                    )

            update_dict["handle"] = updates.handle

        # Avatar update (no validation needed)
        if updates.avatar_id is not None:
            update_dict["avatar_id"] = updates.avatar_id

        # Role update (validated by model)
        if updates.role is not None:
            update_dict["role"] = updates.role

        # CB Handle update with uniqueness check
        if updates.cb_handle is not None:
            current_cb = driver.get("cb_handle")
            if updates.cb_handle != current_cb:
                cb_check = db.from_("drivers").select("id").eq(
                    "cb_handle", updates.cb_handle
                ).execute()

                if cb_check.data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"CB Handle '{updates.cb_handle}' is already taken"
                    )

            update_dict["cb_handle"] = updates.cb_handle

        # Show on map as update (validated by model)
        if updates.show_on_map_as is not None:
            update_dict["show_on_map_as"] = updates.show_on_map_as

        # Profile photo URL update
        if updates.profile_photo_url is not None:
            update_dict["profile_photo_url"] = updates.profile_photo_url

        # Return current profile if no changes
        if not update_dict:
            return driver

        # Update profile
        response = db.from_("drivers").update(update_dict).eq(
            "id", driver["id"]
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )

        logger.info(f"Driver profile updated: {driver['id']} - {list(update_dict.keys())}")

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update driver profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_my_account(
    deletion_request: AccountDeletionRequest,
    driver: dict = Depends(get_current_driver),
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db_admin)
):
    """
    Delete driver account and all associated data.

    This is a destructive operation that:
    1. Deletes driver profile
    2. Deletes all status updates
    3. Deletes location data
    4. Deletes authentication account (via Supabase Auth)

    Requires confirmation field to be "DELETE".
    """
    try:
        driver_id = driver["id"]
        user_id = str(current_user.id)

        logger.warning(
            f"Account deletion initiated for driver {driver_id} (user {user_id}). "
            f"Reason: {deletion_request.reason or 'Not provided'}"
        )

        # Step 1: Delete status updates (cascade will handle follow-up responses)
        db.from_("status_updates").delete().eq("driver_id", driver_id).execute()
        logger.info(f"Deleted status updates for driver {driver_id}")

        # Step 2: Delete location data
        db.from_("driver_locations").delete().eq("driver_id", driver_id).execute()
        logger.info(f"Deleted location data for driver {driver_id}")

        # Step 3: Delete driver profile
        db.from_("drivers").delete().eq("id", driver_id).execute()
        logger.info(f"Deleted driver profile {driver_id}")

        # Step 4: Delete authentication account (Supabase Auth)
        try:
            # Sign out current session first
            db.auth.sign_out()

            # Delete user from Supabase Auth
            # Note: This requires admin privileges
            from app.database import get_db_client
            admin_db = get_db_client()
            admin_db.auth.admin.delete_user(user_id)
            logger.info(f"Deleted auth account for user {user_id}")
        except Exception as auth_error:
            logger.error(f"Failed to delete auth account: {auth_error}")
            # Continue anyway - driver data is already deleted
            # Frontend should handle by clearing local tokens

        logger.warning(f"Account deletion completed for driver {driver_id}")

        return {
            "success": True,
            "message": "Account successfully deleted",
            "deleted_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deletion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )
