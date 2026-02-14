"""
Detention Monitor Service
Detects when a driver has left a facility without checking out from an active detention session.
Called during background location check-ins.
"""

from typing import Optional, Dict
from supabase import Client
from app.utils.location import calculate_distance
import logging

logger = logging.getLogger(__name__)

# Distance threshold: if driver is more than this many miles from facility, they likely left
CHECKOUT_DISTANCE_THRESHOLD_MILES = 1.0


async def check_auto_checkout(
    db: Client,
    driver_id: str,
    current_lat: float,
    current_lng: float
) -> Optional[Dict]:
    """
    Check if the driver has an active detention session and has moved away from the facility.

    Called during background location check-ins (/locations/check-in).

    Returns:
        Dict with alert data if driver appears to have left, None otherwise.
        {
            "session_id": str,
            "facility_name": str,
            "facility_type": str,
            "checked_in_at": str,
            "distance_from_facility_miles": float
        }
    """
    try:
        # Check for active detention session
        session_response = db.from_("detention_sessions") \
            .select("id, reviewed_facility_id, checked_in_at, checkin_latitude, checkin_longitude") \
            .eq("driver_id", driver_id) \
            .eq("status", "active") \
            .order("checked_in_at", desc=True) \
            .limit(1) \
            .execute()

        if not session_response.data:
            return None

        session = session_response.data[0]

        # Get facility location from reviewed_facilities
        facility_response = db.from_("reviewed_facilities") \
            .select("id, name, facility_type, latitude, longitude") \
            .eq("id", session["reviewed_facility_id"]) \
            .limit(1) \
            .execute()

        if not facility_response.data:
            return None

        facility = facility_response.data[0]

        # Use facility coordinates if available, otherwise use check-in coordinates
        facility_lat = facility.get("latitude") or session["checkin_latitude"]
        facility_lng = facility.get("longitude") or session["checkin_longitude"]

        # Calculate distance from facility
        distance = calculate_distance(
            current_lat, current_lng,
            facility_lat, facility_lng
        )

        if distance > CHECKOUT_DISTANCE_THRESHOLD_MILES:
            logger.info(
                f"Auto-checkout detected: Driver {driver_id} is {distance:.1f} miles "
                f"from {facility['name']} (session {session['id']})"
            )
            return {
                "session_id": session["id"],
                "facility_name": facility["name"],
                "facility_type": facility["facility_type"],
                "checked_in_at": session["checked_in_at"],
                "distance_from_facility_miles": round(distance, 1)
            }

        return None

    except Exception as e:
        logger.error(f"Auto-checkout check failed for driver {driver_id}: {e}")
        return None
