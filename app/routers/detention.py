"""
Detention Tracking Router
Endpoints for facility check-in/check-out, detention time tracking, heatmap data, and proof generation
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from supabase import Client
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from app.database import get_db_admin
from app.dependencies import get_current_driver
from app.utils.location import calculate_distance
from app.models.detention import (
    DetentionCheckInRequest,
    DetentionCheckOutRequest,
    DetentionManualCheckoutRequest,
    DetentionSettingsRequest,
    DetentionSessionResponse,
    DetentionSessionListResponse,
    DetentionSettingsResponse,
    DetentionFacilityStatsResponse,
    DetentionHeatmapPoint,
    DetentionHeatmapResponse,
    DetentionProofResponse,
)
import logging
import math

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detention", tags=["Detention Tracking"])

# Proximity threshold for check-in (miles)
CHECKIN_PROXIMITY_MILES = 1.0


# ── Helpers ──────────────────────────────────────────────────────────

def _build_session_response(session: dict, facility: dict) -> DetentionSessionResponse:
    """Build a DetentionSessionResponse from DB rows."""
    return DetentionSessionResponse(
        id=session["id"],
        driver_id=session["driver_id"],
        reviewed_facility_id=session["reviewed_facility_id"],
        facility_name=facility.get("name", "Unknown Facility"),
        facility_type=facility.get("facility_type", "other"),
        facility_address=facility.get("address"),
        facility_latitude=facility.get("latitude"),
        facility_longitude=facility.get("longitude"),
        checked_in_at=session["checked_in_at"],
        checked_out_at=session.get("checked_out_at"),
        checkin_latitude=session["checkin_latitude"],
        checkin_longitude=session["checkin_longitude"],
        checkout_latitude=session.get("checkout_latitude"),
        checkout_longitude=session.get("checkout_longitude"),
        free_time_minutes=session["free_time_minutes"],
        total_time_minutes=session.get("total_time_minutes"),
        detention_time_minutes=session.get("detention_time_minutes"),
        checkout_type=session.get("checkout_type"),
        load_type=session.get("load_type"),
        status=session["status"],
        notes=session.get("notes"),
        proof_generated_at=session.get("proof_generated_at"),
        created_at=session["created_at"],
        updated_at=session.get("updated_at"),
    )


def _calculate_detention(checked_in_at_str: str, checked_out_at: datetime, free_time_minutes: int):
    """Calculate total time and detention time."""
    checked_in = datetime.fromisoformat(checked_in_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
    checkout = checked_out_at.replace(tzinfo=None) if checked_out_at.tzinfo else checked_out_at

    total_seconds = (checkout - checked_in).total_seconds()
    total_minutes = max(0, int(total_seconds / 60))
    detention_minutes = max(0, total_minutes - free_time_minutes)

    return total_minutes, detention_minutes


# ── Check-In ──────────────────────────────────────────────────────────

@router.post("/check-in")
async def check_in(
    request: DetentionCheckInRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Start a detention tracking session at a facility.

    Validates:
    - No existing active session for this driver
    - Driver is within proximity of the facility (<=1 mile)
    - Facility exists in reviewed_facilities
    """
    try:
        # 1. Check for existing active session
        active_check = db.from_("detention_sessions") \
            .select("id, reviewed_facility_id") \
            .eq("driver_id", driver["id"]) \
            .eq("status", "active") \
            .limit(1) \
            .execute()

        if active_check.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active detention session. Check out first."
            )

        # 2. Get facility
        facility_response = db.from_("reviewed_facilities") \
            .select("id, name, facility_type, address, latitude, longitude") \
            .eq("id", str(request.reviewed_facility_id)) \
            .limit(1) \
            .execute()

        if not facility_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facility not found"
            )

        facility = facility_response.data[0]

        # 3. Proximity check
        if facility.get("latitude") and facility.get("longitude"):
            distance = calculate_distance(
                request.latitude, request.longitude,
                facility["latitude"], facility["longitude"]
            )
            if distance > CHECKIN_PROXIMITY_MILES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"You are {distance:.1f} miles from this facility. "
                           f"You must be within {CHECKIN_PROXIMITY_MILES} mile to check in."
                )

        # 4. Get driver's free time preference
        free_time = driver.get("detention_free_time_minutes", 120)

        # 5. Create session
        session_data = {
            "driver_id": driver["id"],
            "reviewed_facility_id": str(request.reviewed_facility_id),
            "checked_in_at": datetime.utcnow().isoformat(),
            "checkin_latitude": request.latitude,
            "checkin_longitude": request.longitude,
            "free_time_minutes": free_time,
            "status": "active",
        }
        if request.load_type:
            session_data["load_type"] = request.load_type

        result = db.from_("detention_sessions").insert(session_data).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create detention session"
            )

        session = result.data[0]

        logger.info(f"Driver {driver['id']} checked in at {facility['name']} (session {session['id']})")

        return _build_session_response(session, facility)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Check-in failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Check-in failed: {str(e)}"
        )


# ── Check-Out ──────────────────────────────────────────────────────────

@router.post("/check-out")
async def check_out(
    request: DetentionCheckOutRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    End a detention tracking session.
    Calculates total time and detention time.
    """
    try:
        # 1. Get the session
        session_response = db.from_("detention_sessions") \
            .select("*") \
            .eq("id", str(request.session_id)) \
            .eq("driver_id", driver["id"]) \
            .eq("status", "active") \
            .limit(1) \
            .execute()

        if not session_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active session not found"
            )

        session = session_response.data[0]

        # 2. Calculate times
        checkout_time = datetime.utcnow()
        total_minutes, detention_minutes = _calculate_detention(
            session["checked_in_at"], checkout_time, session["free_time_minutes"]
        )

        # 3. Update session
        update_data = {
            "checked_out_at": checkout_time.isoformat(),
            "checkout_latitude": request.latitude,
            "checkout_longitude": request.longitude,
            "total_time_minutes": total_minutes,
            "detention_time_minutes": detention_minutes,
            "checkout_type": "manual",
            "status": "completed",
            "notes": request.notes,
        }

        result = db.from_("detention_sessions") \
            .update(update_data) \
            .eq("id", str(request.session_id)) \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update session"
            )

        updated_session = result.data[0]

        # 4. Get facility info
        facility_response = db.from_("reviewed_facilities") \
            .select("id, name, facility_type, address, latitude, longitude") \
            .eq("id", session["reviewed_facility_id"]) \
            .limit(1) \
            .execute()

        facility = facility_response.data[0] if facility_response.data else {}

        logger.info(
            f"Driver {driver['id']} checked out from {facility.get('name', 'unknown')} "
            f"(total: {total_minutes}min, detention: {detention_minutes}min)"
        )

        return _build_session_response(updated_session, facility)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Check-out failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Check-out failed: {str(e)}"
        )


# ── Manual Checkout ──────────────────────────────────────────────────

@router.post("/manual-checkout")
async def manual_checkout(
    request: DetentionManualCheckoutRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Manual checkout for when driver forgot to check out.
    Driver enters their actual departure time.
    Marked as 'manual_entry' checkout type.
    """
    try:
        # 1. Get the session
        session_response = db.from_("detention_sessions") \
            .select("*") \
            .eq("id", str(request.session_id)) \
            .eq("driver_id", driver["id"]) \
            .eq("status", "active") \
            .limit(1) \
            .execute()

        if not session_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active session not found"
            )

        session = session_response.data[0]

        # 2. Validate checkout time is after check-in
        checked_in = datetime.fromisoformat(
            session["checked_in_at"].replace("Z", "+00:00")
        ).replace(tzinfo=None)
        checkout_time = request.actual_checkout_time.replace(tzinfo=None)

        if checkout_time <= checked_in:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Checkout time must be after check-in time"
            )

        # 3. Calculate times
        total_minutes, detention_minutes = _calculate_detention(
            session["checked_in_at"], request.actual_checkout_time, session["free_time_minutes"]
        )

        # 4. Update session
        update_data = {
            "checked_out_at": request.actual_checkout_time.isoformat(),
            "total_time_minutes": total_minutes,
            "detention_time_minutes": detention_minutes,
            "checkout_type": "manual_entry",
            "status": "completed",
            "notes": request.notes,
        }

        result = db.from_("detention_sessions") \
            .update(update_data) \
            .eq("id", str(request.session_id)) \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update session"
            )

        updated_session = result.data[0]

        # Get facility info
        facility_response = db.from_("reviewed_facilities") \
            .select("id, name, facility_type, address, latitude, longitude") \
            .eq("id", session["reviewed_facility_id"]) \
            .limit(1) \
            .execute()

        facility = facility_response.data[0] if facility_response.data else {}

        logger.info(
            f"Driver {driver['id']} manual checkout from {facility.get('name', 'unknown')} "
            f"(total: {total_minutes}min, detention: {detention_minutes}min, type: manual_entry)"
        )

        return _build_session_response(updated_session, facility)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual checkout failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual checkout failed: {str(e)}"
        )


# ── Cancel Session ──────────────────────────────────────────────────

@router.post("/{session_id}/cancel")
async def cancel_session(
    session_id: UUID,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Cancel an active detention session without completing it."""
    try:
        result = db.from_("detention_sessions") \
            .update({"status": "cancelled"}) \
            .eq("id", str(session_id)) \
            .eq("driver_id", driver["id"]) \
            .eq("status", "active") \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active session not found"
            )

        return {"success": True, "message": "Session cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel session failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cancel failed: {str(e)}"
        )


# ── Get Active Session ──────────────────────────────────────────────

@router.get("/active")
async def get_active_session(
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Get the driver's current active detention session, if any."""
    try:
        session_response = db.from_("detention_sessions") \
            .select("*") \
            .eq("driver_id", driver["id"]) \
            .eq("status", "active") \
            .order("checked_in_at", desc=True) \
            .limit(1) \
            .execute()

        if not session_response.data:
            return {"active": False, "session": None}

        session = session_response.data[0]

        # Get facility info
        facility_response = db.from_("reviewed_facilities") \
            .select("id, name, facility_type, address, latitude, longitude") \
            .eq("id", session["reviewed_facility_id"]) \
            .limit(1) \
            .execute()

        facility = facility_response.data[0] if facility_response.data else {}

        return {
            "active": True,
            "session": _build_session_response(session, facility)
        }

    except Exception as e:
        logger.error(f"Get active session failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active session"
        )


# ── Session History ──────────────────────────────────────────────────

@router.get("/history")
async def get_session_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Get the driver's detention session history (completed sessions)."""
    try:
        # Get total count
        count_response = db.from_("detention_sessions") \
            .select("id", count="exact") \
            .eq("driver_id", driver["id"]) \
            .eq("status", "completed") \
            .execute()

        total = count_response.count or 0

        # Get paginated sessions
        sessions_response = db.from_("detention_sessions") \
            .select("*") \
            .eq("driver_id", driver["id"]) \
            .eq("status", "completed") \
            .order("checked_in_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        sessions = []
        for session in sessions_response.data or []:
            # Get facility info for each session
            facility_response = db.from_("reviewed_facilities") \
                .select("id, name, facility_type, address, latitude, longitude") \
                .eq("id", session["reviewed_facility_id"]) \
                .limit(1) \
                .execute()

            facility = facility_response.data[0] if facility_response.data else {}
            sessions.append(_build_session_response(session, facility))

        return DetentionSessionListResponse(
            sessions=sessions,
            total=total,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Get history failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session history"
        )


# ── Single Session ──────────────────────────────────────────────────

@router.get("/{session_id}/proof")
async def get_session_proof(
    session_id: UUID,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Get detention proof data for PDF generation."""
    try:
        session_response = db.from_("detention_sessions") \
            .select("*") \
            .eq("id", str(session_id)) \
            .eq("driver_id", driver["id"]) \
            .limit(1) \
            .execute()

        if not session_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        session = session_response.data[0]

        # Get facility info
        facility_response = db.from_("reviewed_facilities") \
            .select("*") \
            .eq("id", session["reviewed_facility_id"]) \
            .limit(1) \
            .execute()

        facility = facility_response.data[0] if facility_response.data else {}

        # Mark proof as generated
        db.from_("detention_sessions") \
            .update({"proof_generated_at": datetime.utcnow().isoformat()}) \
            .eq("id", str(session_id)) \
            .execute()

        return DetentionProofResponse(
            session=_build_session_response(session, facility),
            driver_name=driver.get("handle", "Driver"),
            driver_handle=driver.get("cb_handle") or driver.get("handle", ""),
            generated_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get proof failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get proof data"
        )


# ── Heatmap Data ──────────────────────────────────────────────────

@router.get("/heatmap")
async def get_heatmap_data(
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    radius_miles: float = Query(200, ge=1, le=1000),
    db: Client = Depends(get_db_admin)
):
    """
    Get detention heatmap data for map rendering.
    Returns facilities with detention data, weighted by severity.
    Public endpoint - no auth required.
    """
    try:
        # Get facilities with detention data
        query = db.from_("reviewed_facilities") \
            .select("id, name, facility_type, latitude, longitude, avg_detention_minutes, total_detention_sessions, detention_percentage") \
            .gt("total_detention_sessions", 0) \
            .not_.is_("latitude", "null") \
            .not_.is_("longitude", "null")

        result = query.execute()

        facilities = []
        max_detention = 1  # Avoid division by zero

        # First pass: find max detention for normalization
        for row in result.data or []:
            avg_det = float(row.get("avg_detention_minutes") or 0)
            if avg_det > max_detention:
                max_detention = avg_det

        # Second pass: build response with distance filtering
        for row in result.data or []:
            fac_lat = row.get("latitude")
            fac_lng = row.get("longitude")

            if not fac_lat or not fac_lng:
                continue

            # Distance filter if center provided
            if latitude is not None and longitude is not None:
                distance = calculate_distance(latitude, longitude, fac_lat, fac_lng)
                if distance > radius_miles:
                    continue

            avg_det = float(row.get("avg_detention_minutes") or 0)
            # Normalize weight to 0-1 range
            weight = min(1.0, avg_det / max_detention) if max_detention > 0 else 0

            facilities.append(DetentionHeatmapPoint(
                latitude=fac_lat,
                longitude=fac_lng,
                weight=round(weight, 3),
                facility_name=row["name"],
                facility_type=row["facility_type"],
                avg_detention_minutes=avg_det,
                total_sessions=row.get("total_detention_sessions") or 0,
            ))

        return DetentionHeatmapResponse(
            facilities=facilities,
            total=len(facilities)
        )

    except Exception as e:
        logger.error(f"Heatmap data failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get heatmap data"
        )


# ── Facility Stats ──────────────────────────────────────────────────

@router.get("/facility/{facility_id}/stats")
async def get_facility_detention_stats(
    facility_id: UUID,
    db: Client = Depends(get_db_admin)
):
    """Get detention statistics for a specific facility. Public endpoint."""
    try:
        # Get facility info
        facility_response = db.from_("reviewed_facilities") \
            .select("id, name, facility_type, avg_detention_minutes, total_detention_sessions, detention_percentage") \
            .eq("id", str(facility_id)) \
            .limit(1) \
            .execute()

        if not facility_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facility not found"
            )

        facility = facility_response.data[0]

        # Get average total time from completed sessions
        sessions_response = db.from_("detention_sessions") \
            .select("total_time_minutes") \
            .eq("reviewed_facility_id", str(facility_id)) \
            .eq("status", "completed") \
            .not_.is_("total_time_minutes", "null") \
            .execute()

        avg_total = 0
        recent_count = 0
        if sessions_response.data:
            times = [s["total_time_minutes"] for s in sessions_response.data]
            avg_total = sum(times) / len(times) if times else 0

        # Count recent sessions (last 30 days)
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        recent_response = db.from_("detention_sessions") \
            .select("id", count="exact") \
            .eq("reviewed_facility_id", str(facility_id)) \
            .eq("status", "completed") \
            .gte("checked_in_at", thirty_days_ago) \
            .execute()

        recent_count = recent_response.count or 0

        return DetentionFacilityStatsResponse(
            reviewed_facility_id=facility["id"],
            facility_name=facility["name"],
            facility_type=facility["facility_type"],
            avg_total_time_minutes=round(avg_total, 1),
            avg_detention_minutes=float(facility.get("avg_detention_minutes") or 0),
            total_sessions=facility.get("total_detention_sessions") or 0,
            detention_percentage=float(facility.get("detention_percentage") or 0),
            recent_sessions=recent_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Facility stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get facility stats"
        )


# ── Settings ──────────────────────────────────────────────────────────

@router.get("/settings")
async def get_detention_settings(
    driver: dict = Depends(get_current_driver),
):
    """Get driver's detention settings."""
    return DetentionSettingsResponse(
        free_time_minutes=driver.get("detention_free_time_minutes", 120)
    )


@router.patch("/settings")
async def update_detention_settings(
    request: DetentionSettingsRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Update driver's detention free time preference."""
    try:
        db.from_("drivers") \
            .update({"detention_free_time_minutes": request.free_time_minutes}) \
            .eq("id", driver["id"]) \
            .execute()

        logger.info(f"Driver {driver['id']} updated detention free time to {request.free_time_minutes} minutes")

        return DetentionSettingsResponse(
            free_time_minutes=request.free_time_minutes
        )

    except Exception as e:
        logger.error(f"Update settings failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings"
        )
