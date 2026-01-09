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
    CheckInRequest,
    CheckInResponse,
    StatusChangeRequest,
    StatusChangeResponse
)
from app.dependencies import get_current_driver
from app.utils.location import fuzz_location, calculate_distance
from app.config import settings
import logging
import geohash as gh

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locations", tags=["Locations"])


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


@router.post("/status/update", response_model=StatusChangeResponse)
async def update_status_with_location(
    request: StatusChangeRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Change status with location update.
    Updates status, location, closes old status history, opens new.
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

        # Find facility
        facility_name = None
        facilities = db.from_("facilities").select("*").execute()

        if facilities.data:
            for facility in facilities.data:
                distance = calculate_distance(
                    request.latitude,
                    request.longitude,
                    facility["latitude"],
                    facility["longitude"]
                )
                if distance <= 0.1:
                    facility_name = facility["name"]
                    break

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

        logger.info(f"Driver {driver['id']} changed status from {old_status} to {new_status}")

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
            message=f"Status updated to {new_status.title()}" + (
                f" at {facility_name}" if facility_name else ""
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status update failed: {str(e)}"
        )


@router.get("/me", response_model=LocationResponse)
async def get_my_location(
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Get my current location (fuzzed).
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

        return LocationResponse(
            latitude=location.data["fuzzed_latitude"],
            longitude=location.data["fuzzed_longitude"],
            facility_name=None,  # TODO: Look up facility
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
                recorded_at = datetime.fromisoformat(loc["recorded_at"].replace("Z", "+00:00"))
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
