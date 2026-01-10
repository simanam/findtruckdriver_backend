"""
Location & Check-in Router
Endpoints for location updates and manual check-ins
"""

from fastapi import APIRouter, HTTPException, status, Depends
from supabase import Client
from datetime import datetime, timedelta
from typing import Optional
from app.database import get_db_admin
from app.models.location import (
    LocationUpdate,
    LocationResponse,
    MyLocationResponse,
    CheckInRequest,
    CheckInResponse,
    StatusChangeRequest,
    StatusChangeResponse,
    AppOpenRequest,
    AppOpenResponse
)
from app.services.follow_up_engine import determine_follow_up
from app.services.facility_discovery import find_nearby_facility
from app.dependencies import get_current_driver
from app.utils.location import fuzz_location, calculate_distance
from app.config import settings
import logging
import geohash as gh

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locations", tags=["Locations"])


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


@router.post("/check-in", response_model=CheckInResponse)
async def check_in(
    request: CheckInRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Manual check-in. Refreshes location, keeps same status.
    Resets the 12-hour stale timer.
    """
    try:
        # Get driver's current status
        current_status = driver["status"]

        # Apply location fuzzing based on status
        fuzz_distance = {
            "rolling": settings.location_fuzz_rolling_miles,
            "waiting": settings.location_fuzz_waiting_miles,
            "parked": settings.location_fuzz_parked_miles
        }.get(current_status, 0.5)

        fuzzed_lat, fuzzed_lng = fuzz_location(
            request.latitude,
            request.longitude,
            fuzz_distance
        )

        # Calculate geohash for clustering
        geohash = gh.encode(fuzzed_lat, fuzzed_lng, precision=settings.geohash_precision_local)

        # Update or insert location
        location_data = {
            "driver_id": driver["id"],
            "latitude": request.latitude,
            "longitude": request.longitude,
            "fuzzed_latitude": fuzzed_lat,
            "fuzzed_longitude": fuzzed_lng,
            "accuracy": request.accuracy,
            "heading": request.heading,
            "speed": request.speed,
            "geohash": geohash,
            "recorded_at": datetime.utcnow().isoformat()
        }

        # Upsert location (update if exists, insert if not)
        location_response = db.from_("driver_locations").upsert(
            location_data,
            on_conflict="driver_id"
        ).execute()

        # Update driver's last_active timestamp
        db.from_("drivers").update({
            "last_active": datetime.utcnow().isoformat()
        }).eq("id", driver["id"]).execute()

        # Try to find facility at this location (if available)
        facility_name = None
        if request.latitude and request.longitude:
            # Query facilities within ~0.1 miles
            facilities = db.from_("facilities").select("*").execute()

            if facilities.data:
                for facility in facilities.data:
                    distance = calculate_distance(
                        request.latitude,
                        request.longitude,
                        facility["latitude"],
                        facility["longitude"]
                    )
                    if distance <= 0.1:  # Within 0.1 miles
                        facility_name = facility["name"]
                        break

        logger.info(f"Driver {driver['id']} checked in at ({fuzzed_lat}, {fuzzed_lng})")

        return CheckInResponse(
            success=True,
            status=current_status,
            location=LocationResponse(
                latitude=fuzzed_lat,
                longitude=fuzzed_lng,
                facility_name=facility_name,
                updated_at=datetime.utcnow()
            ),
            message=f"You're on the map! {current_status.title()}" + (
                f" at {facility_name}" if facility_name else ""
            )
        )

    except Exception as e:
        logger.error(f"Check-in failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Check-in failed: {str(e)}"
        )


@router.post("/app-open", response_model=AppOpenResponse)
async def on_app_open(
    request: AppOpenRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Called when user opens app or tab regains focus.
    Detects if movement or staleness requires status prompt.

    This implements the web-first "check on app open" logic:
    - If 12+ hours since last update → prompt "Welcome back!"
    - If location changed significantly → prompt status update
    - Otherwise → silent location refresh
    """
    try:
        current_status = driver["status"]

        # Get last location
        last_location_response = db.from_("driver_locations") \
            .select("*") \
            .eq("driver_id", driver["id"]) \
            .execute()

        last_location = last_location_response.data[0] if last_location_response.data else None

        # Calculate time since last update
        last_active = parse_timestamp(driver["last_active"])
        hours_since_update = (datetime.utcnow() - last_active.replace(tzinfo=None)).total_seconds() / 3600

        # Calculate distance moved (if we have previous location)
        distance_moved = 0.0
        if last_location:
            distance_moved = calculate_distance(
                last_location["latitude"],
                last_location["longitude"],
                request.latitude,
                request.longitude
            )

        # Get facility name at last location (if exists)
        last_facility_name = None
        if last_location:
            try:
                facilities = db.from_("facilities").select("*").execute()
                if facilities.data:
                    for facility in facilities.data:
                        dist = calculate_distance(
                            last_location["latitude"],
                            last_location["longitude"],
                            facility["latitude"],
                            facility["longitude"]
                        )
                        if dist <= 0.1:
                            last_facility_name = facility["name"]
                            break
            except Exception as e:
                # Facilities table doesn't exist yet - that's OK
                logger.debug(f"Could not query facilities (table may not exist): {e}")
                pass

        # CASE 1: Driver was stale (12+ hours)
        if hours_since_update >= 12:
            logger.info(f"Driver {driver['id']} app open: stale (>{hours_since_update:.1f}h)")
            return AppOpenResponse(
                action="prompt_status",
                reason="welcome_back",
                message="Welcome back! What's your status?",
                current_status=current_status,
                last_status=current_status,
                last_location_name=last_facility_name,
                distance_moved=round(distance_moved, 1) if distance_moved else None,
                hours_since_update=round(hours_since_update, 1),
                suggested_status=None
            )

        # CASE 2: Significant movement detected (>0.5 miles)
        if distance_moved > 0.5:
            # They were parked/waiting but clearly moved
            if current_status in ["parked", "waiting"]:
                logger.info(f"Driver {driver['id']} app open: moved {distance_moved:.1f} miles while {current_status}")
                return AppOpenResponse(
                    action="prompt_status",
                    reason="location_changed",
                    message="Looks like you've moved. What's your status now?",
                    current_status=current_status,
                    last_status=current_status,
                    last_location_name=last_facility_name,
                    distance_moved=round(distance_moved, 1),
                    hours_since_update=round(hours_since_update, 1),
                    suggested_status="rolling"
                )

            # They were rolling - just update location silently
            elif current_status == "rolling":
                logger.info(f"Driver {driver['id']} app open: moved {distance_moved:.1f} miles while rolling (silent update)")
                # Update location silently
                await _update_location_silently(driver["id"], request, db)
                return AppOpenResponse(
                    action="none",
                    reason=None,
                    message=None,
                    current_status=current_status,
                    last_status=current_status,
                    last_location_name=last_facility_name,
                    distance_moved=round(distance_moved, 1),
                    hours_since_update=round(hours_since_update, 1),
                    suggested_status=None
                )

        # CASE 3: Same location, not stale - just refresh timestamp
        logger.info(f"Driver {driver['id']} app open: no change (silent refresh)")
        await _update_location_silently(driver["id"], request, db)
        return AppOpenResponse(
            action="none",
            reason=None,
            message=None,
            current_status=current_status,
            last_status=current_status,
            last_location_name=last_facility_name,
            distance_moved=round(distance_moved, 1) if distance_moved else None,
            hours_since_update=round(hours_since_update, 1),
            suggested_status=None
        )

    except Exception as e:
        logger.error(f"App open detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"App open detection failed: {str(e)}"
        )


async def _update_location_silently(driver_id: str, request: AppOpenRequest, db: Client):
    """
    Helper function to silently update driver location and timestamp.
    Used when no status prompt is needed.
    """
    try:
        # Get driver status for fuzzing
        driver_response = db.from_("drivers").select("status").eq("id", driver_id).execute()
        if not driver_response.data:
            return

        driver_status = driver_response.data[0]["status"]

        # Apply fuzzing
        fuzz_distance = {
            "rolling": settings.location_fuzz_rolling_miles,
            "waiting": settings.location_fuzz_waiting_miles,
            "parked": settings.location_fuzz_parked_miles
        }.get(driver_status, 0.5)

        fuzzed_lat, fuzzed_lng = fuzz_location(
            request.latitude,
            request.longitude,
            fuzz_distance
        )

        # Calculate geohash
        geohash = gh.encode(fuzzed_lat, fuzzed_lng, precision=settings.geohash_precision_local)

        # Update location
        location_data = {
            "driver_id": driver_id,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "fuzzed_latitude": fuzzed_lat,
            "fuzzed_longitude": fuzzed_lng,
            "accuracy": request.accuracy,
            "heading": request.heading,
            "speed": request.speed,
            "geohash": geohash,
            "recorded_at": datetime.utcnow().isoformat()
        }

        db.from_("driver_locations").upsert(
            location_data,
            on_conflict="driver_id"
        ).execute()

        # Update last_active timestamp
        db.from_("drivers").update({
            "last_active": datetime.utcnow().isoformat()
        }).eq("id", driver_id).execute()

        logger.debug(f"Silently updated location for driver {driver_id}")

    except Exception as e:
        logger.error(f"Silent location update failed: {e}")
        # Don't raise - this is a background operation


@router.post("/status/update", response_model=StatusChangeResponse)
async def update_status_with_location(
    request: StatusChangeRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Change status with location update + intelligent follow-up questions.

    Updates status, location, closes old status history, opens new.

    NEW: Returns contextual follow-up questions based on status transitions:
    - WAITING → ROLLING: Detention time and payment tracking
    - PARKED → ROLLING: Parking safety and vibe feedback
    """
    try:
        old_status = driver["status"]
        new_status = request.status

        # Validate status
        valid_statuses = ["rolling", "waiting", "parked"]
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )

        # Get previous status from status_updates table for follow-up context
        prev_query = db.from_("status_updates") \
            .select("*") \
            .eq("driver_id", driver["id"]) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        prev = prev_query.data[0] if prev_query.data else None

        # Apply location fuzzing based on NEW status
        fuzz_distance = {
            "rolling": settings.location_fuzz_rolling_miles,
            "waiting": settings.location_fuzz_waiting_miles,
            "parked": settings.location_fuzz_parked_miles
        }.get(new_status, 0.5)

        fuzzed_lat, fuzzed_lng = fuzz_location(
            request.latitude,
            request.longitude,
            fuzz_distance
        )

        # Calculate geohash
        geohash = gh.encode(fuzzed_lat, fuzzed_lng, precision=settings.geohash_precision_local)

        # Update location
        location_data = {
            "driver_id": driver["id"],
            "latitude": request.latitude,
            "longitude": request.longitude,
            "fuzzed_latitude": fuzzed_lat,
            "fuzzed_longitude": fuzzed_lng,
            "accuracy": request.accuracy,
            "heading": request.heading,
            "speed": request.speed,
            "geohash": geohash,
            "recorded_at": datetime.utcnow().isoformat()
        }

        db.from_("driver_locations").upsert(
            location_data,
            on_conflict="driver_id"
        ).execute()

        # Update driver status and last_active
        db.from_("drivers").update({
            "status": new_status,
            "last_active": datetime.utcnow().isoformat()
        }).eq("id", driver["id"]).execute()

        # Close old status history entry (if exists and different status)
        if old_status != new_status:
            db.from_("status_history").update({
                "ended_at": datetime.utcnow().isoformat()
            }).eq("driver_id", driver["id"]).is_("ended_at", "null").execute()

            # Create new status history entry
            db.from_("status_history").insert({
                "driver_id": driver["id"],
                "status": new_status,
                "started_at": datetime.utcnow().isoformat(),
                "latitude": fuzzed_lat,
                "longitude": fuzzed_lng
            }).execute()

        # Find facility using smart discovery (queries OSM if needed)
        facility_id, facility_name = find_nearby_facility(
            db=db,
            latitude=request.latitude,
            longitude=request.longitude,
            max_distance_miles=0.3,
            discover_if_missing=True  # Trigger OSM query for unmapped areas
        )

        # Calculate follow-up question context
        context = None
        question = None

        if old_status != new_status:  # Only for status changes
            context, question, weather_info = determine_follow_up(
                prev_status=prev["status"] if prev else None,
                prev_latitude=prev["latitude"] if prev else None,
                prev_longitude=prev["longitude"] if prev else None,
                prev_updated_at=parse_timestamp(prev["created_at"]) if prev else None,
                new_status=new_status,
                new_latitude=request.latitude,
                new_longitude=request.longitude,
                facility_name=facility_name
            )

        # Save status_update record with context
        status_record = {
            "driver_id": driver["id"],
            "status": new_status,
            "latitude": request.latitude,
            "longitude": request.longitude,
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
        status_update_id = result.data[0]["id"] if result.data else None

        # Get wait context if status is "waiting" and at a facility
        wait_context = None
        if new_status == "waiting" and facility_name:
            # Count other drivers waiting at this location
            waiting_drivers = db.from_("driver_locations") \
                .select("driver_id") \
                .eq("geohash", geohash[:6]) \
                .execute()

            # Get waiting drivers' statuses
            if waiting_drivers.data:
                driver_ids = [d["driver_id"] for d in waiting_drivers.data]
                active_waiting = db.from_("drivers") \
                    .select("id") \
                    .eq("status", "waiting") \
                    .in_("id", driver_ids) \
                    .execute()

                others_waiting = len(active_waiting.data) - 1  # Exclude current driver

                # Calculate average wait time (simplified - would need more logic)
                wait_context = {
                    "others_waiting": max(0, others_waiting),
                    "avg_wait_hours": 2.5  # TODO: Calculate from status_history
                }

        logger.info(
            f"Driver {driver['id']} changed status from {old_status} to {new_status}" +
            (f" with follow-up question: {question.question_type}" if question else "")
        )

        return StatusChangeResponse(
            success=True,
            old_status=old_status,
            new_status=new_status,
            location=LocationResponse(
                latitude=fuzzed_lat,
                longitude=fuzzed_lng,
                facility_name=facility_name,
                updated_at=datetime.utcnow()
            ),
            wait_context=wait_context,
            follow_up_question=question,
                weather_info=weather_info,
            status_update_id=status_update_id,
            message=f"Status updated to {new_status.title()}" + (
                f" at {facility_name}" if facility_name else ""
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status update failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status update failed: {str(e)}"
        )


@router.get("/me", response_model=MyLocationResponse)
async def get_my_location(
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Get my current location (fuzzed) with driver info.
    Use this to show "YOU" marker on the map.
    """
    try:
        location = db.from_("driver_locations") \
            .select("*") \
            .eq("driver_id", driver["id"]) \
            .single() \
            .execute()

        if not location.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No location data found. Please check in first."
            )

        # Try to find nearby facility
        facility_name = None
        try:
            facilities = db.from_("facilities").select("*").execute()
            if facilities.data:
                for facility in facilities.data:
                    distance = calculate_distance(
                        location.data["fuzzed_latitude"],
                        location.data["fuzzed_longitude"],
                        facility["latitude"],
                        facility["longitude"]
                    )
                    if distance <= 0.1:  # Within 0.1 miles
                        facility_name = facility["name"]
                        break
        except Exception as e:
            logger.debug(f"Could not query facilities: {e}")

        return MyLocationResponse(
            driver_id=driver["id"],
            handle=driver["handle"],
            status=driver["status"],
            latitude=location.data["fuzzed_latitude"],
            longitude=location.data["fuzzed_longitude"],
            facility_name=facility_name,
            updated_at=location.data["recorded_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get location: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get location"
        )


@router.get("/nearby")
async def get_nearby_drivers(
    latitude: float,
    longitude: float,
    radius_miles: float = 10.0,
    status_filter: Optional[str] = None,
    db: Client = Depends(get_db_admin)
):
    """
    Get drivers near a location (public endpoint).
    Returns fuzzed locations only.
    """
    try:
        # Calculate geohash for the search area
        center_geohash = gh.encode(latitude, longitude, precision=settings.geohash_precision_cluster)

        # Get all drivers in nearby geohash cells
        # This is approximate - would need PostGIS for exact distance
        locations = db.from_("driver_locations") \
            .select("*, drivers!inner(id, handle, status, last_active)") \
            .execute()

        nearby = []
        for loc in locations.data if locations.data else []:
            # Calculate distance
            distance = calculate_distance(
                latitude,
                longitude,
                loc["fuzzed_latitude"],
                loc["fuzzed_longitude"]
            )

            if distance <= radius_miles:
                driver = loc["drivers"]

                # Apply status filter if provided
                if status_filter and driver["status"] != status_filter:
                    continue

                # Check if location is stale (>12 hours)
                recorded_at = parse_timestamp(loc["recorded_at"])
                if datetime.utcnow() - recorded_at.replace(tzinfo=None) > timedelta(hours=12):
                    continue  # Skip stale locations

                nearby.append({
                    "driver_id": driver["id"],
                    "handle": driver["handle"],
                    "status": driver["status"],
                    "latitude": loc["fuzzed_latitude"],
                    "longitude": loc["fuzzed_longitude"],
                    "distance_miles": round(distance, 2),
                    "last_active": driver["last_active"]
                })

        # Sort by distance
        nearby.sort(key=lambda x: x["distance_miles"])

        return {
            "count": len(nearby),
            "drivers": nearby
        }

    except Exception as e:
        logger.error(f"Failed to get nearby drivers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get nearby drivers"
        )
