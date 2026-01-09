"""
Map & Search Router
Endpoints for map view, driver clusters, and hotspot detection
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from supabase import Client
from datetime import datetime, timedelta
from typing import Optional, List
from collections import defaultdict
from app.database import get_db_admin
from app.utils.location import calculate_distance
from app.config import settings
import logging
import geohash as gh

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/map", tags=["Map & Search"])


@router.get("/drivers")
async def get_drivers_in_area(
    latitude: float = Query(..., ge=-90, le=90, description="Center latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Center longitude"),
    radius_miles: float = Query(25.0, ge=1, le=100, description="Search radius in miles"),
    status_filter: Optional[str] = Query(None, description="Filter by status: rolling, waiting, parked"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of drivers to return"),
    db: Client = Depends(get_db_admin)
):
    """
    Get all drivers visible in the map area.
    Returns fuzzed locations for privacy.
    """
    try:
        # Calculate geohash for the search area
        center_geohash = gh.encode(latitude, longitude, precision=settings.geohash_precision_cluster)

        # Get all active drivers (not stale)
        cutoff_time = (datetime.utcnow() - timedelta(hours=12)).isoformat()

        # Query locations with driver info
        query = db.from_("driver_locations") \
            .select("*, drivers!inner(id, handle, status, last_active)") \
            .gte("recorded_at", cutoff_time)

        locations_response = query.execute()

        drivers_in_area = []

        for loc in locations_response.data if locations_response.data else []:
            driver = loc["drivers"]

            # Apply status filter if provided
            if status_filter and driver["status"] != status_filter:
                continue

            # Calculate distance from center
            distance = calculate_distance(
                latitude,
                longitude,
                loc["fuzzed_latitude"],
                loc["fuzzed_longitude"]
            )

            if distance <= radius_miles:
                drivers_in_area.append({
                    "driver_id": driver["id"],
                    "handle": driver["handle"],
                    "status": driver["status"],
                    "latitude": loc["fuzzed_latitude"],
                    "longitude": loc["fuzzed_longitude"],
                    "geohash": loc["geohash"][:settings.geohash_precision_cluster],
                    "distance_miles": round(distance, 2),
                    "last_active": driver["last_active"]
                })

        # Sort by distance and limit
        drivers_in_area.sort(key=lambda x: x["distance_miles"])
        drivers_in_area = drivers_in_area[:limit]

        logger.info(f"Found {len(drivers_in_area)} drivers in {radius_miles}mi radius")

        return {
            "center": {
                "latitude": latitude,
                "longitude": longitude
            },
            "radius_miles": radius_miles,
            "count": len(drivers_in_area),
            "drivers": drivers_in_area
        }

    except Exception as e:
        logger.error(f"Failed to get drivers in area: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get drivers in area: {str(e)}"
        )


@router.get("/clusters")
async def get_driver_clusters(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_miles: float = Query(50.0, ge=1, le=200),
    min_drivers: int = Query(3, ge=2, le=20, description="Minimum drivers to form a cluster"),
    db: Client = Depends(get_db_admin)
):
    """
    Get driver clusters (groups of drivers in close proximity).
    Useful for showing aggregated driver counts on map.
    """
    try:
        # Get all active drivers in area
        cutoff_time = (datetime.utcnow() - timedelta(hours=12)).isoformat()

        locations_response = db.from_("driver_locations") \
            .select("*, drivers!inner(id, status, last_active)") \
            .gte("recorded_at", cutoff_time) \
            .execute()

        # Group by geohash (precision for metro area clustering)
        geohash_groups = defaultdict(list)

        for loc in locations_response.data if locations_response.data else []:
            driver = loc["drivers"]

            # Calculate distance from center
            distance = calculate_distance(
                latitude,
                longitude,
                loc["fuzzed_latitude"],
                loc["fuzzed_longitude"]
            )

            if distance <= radius_miles:
                cluster_hash = loc["geohash"][:settings.geohash_precision_metro]
                geohash_groups[cluster_hash].append({
                    "driver_id": driver["id"],
                    "status": driver["status"],
                    "latitude": loc["fuzzed_latitude"],
                    "longitude": loc["fuzzed_longitude"]
                })

        # Build clusters
        clusters = []
        for geohash_key, drivers in geohash_groups.items():
            if len(drivers) >= min_drivers:
                # Calculate cluster center (average of driver locations)
                avg_lat = sum(d["latitude"] for d in drivers) / len(drivers)
                avg_lng = sum(d["longitude"] for d in drivers) / len(drivers)

                # Count by status
                status_counts = defaultdict(int)
                for d in drivers:
                    status_counts[d["status"]] += 1

                clusters.append({
                    "geohash": geohash_key,
                    "center": {
                        "latitude": avg_lat,
                        "longitude": avg_lng
                    },
                    "total_drivers": len(drivers),
                    "status_breakdown": dict(status_counts),
                    "distance_from_search": round(
                        calculate_distance(latitude, longitude, avg_lat, avg_lng), 2
                    )
                })

        # Sort by distance from search center
        clusters.sort(key=lambda x: x["distance_from_search"])

        logger.info(f"Found {len(clusters)} clusters with {min_drivers}+ drivers")

        return {
            "center": {
                "latitude": latitude,
                "longitude": longitude
            },
            "radius_miles": radius_miles,
            "min_drivers_per_cluster": min_drivers,
            "cluster_count": len(clusters),
            "clusters": clusters
        }

    except Exception as e:
        logger.error(f"Failed to get clusters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get clusters: {str(e)}"
        )


@router.get("/hotspots")
async def get_hotspots(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_miles: float = Query(100.0, ge=1, le=300),
    min_waiting_drivers: Optional[int] = Query(
        None,
        description=f"Minimum waiting drivers (default from config: {settings.hotspot_min_waiting_drivers})"
    ),
    db: Client = Depends(get_db_admin)
):
    """
    Get hotspot locations where many drivers are waiting.
    Helps identify busy facilities and loading/unloading areas.
    """
    try:
        min_drivers = min_waiting_drivers or settings.hotspot_min_waiting_drivers

        # Get all waiting drivers
        cutoff_time = (datetime.utcnow() - timedelta(hours=12)).isoformat()

        locations_response = db.from_("driver_locations") \
            .select("*, drivers!inner(id, status, last_active)") \
            .eq("drivers.status", "waiting") \
            .gte("recorded_at", cutoff_time) \
            .execute()

        # Group by geohash (local precision for facility-level grouping)
        hotspot_groups = defaultdict(list)

        for loc in locations_response.data if locations_response.data else []:
            # Calculate distance from center
            distance = calculate_distance(
                latitude,
                longitude,
                loc["fuzzed_latitude"],
                loc["fuzzed_longitude"]
            )

            if distance <= radius_miles:
                hotspot_hash = loc["geohash"][:settings.geohash_precision_local]
                hotspot_groups[hotspot_hash].append({
                    "driver_id": loc["drivers"]["id"],
                    "latitude": loc["fuzzed_latitude"],
                    "longitude": loc["fuzzed_longitude"],
                    "recorded_at": loc["recorded_at"]
                })

        # Build hotspots
        hotspots = []
        for geohash_key, waiting_drivers in hotspot_groups.items():
            if len(waiting_drivers) >= min_drivers:
                # Calculate hotspot center
                avg_lat = sum(d["latitude"] for d in waiting_drivers) / len(waiting_drivers)
                avg_lng = sum(d["longitude"] for d in waiting_drivers) / len(waiting_drivers)

                # Try to find facility at this location
                facility_name = None
                facilities = db.from_("facilities").select("*").execute()

                if facilities.data:
                    for facility in facilities.data:
                        fac_distance = calculate_distance(
                            avg_lat,
                            avg_lng,
                            facility["latitude"],
                            facility["longitude"]
                        )
                        if fac_distance <= 0.3:  # Within 0.3 miles
                            facility_name = facility["name"]
                            break

                # Calculate average wait time (simplified)
                # TODO: Query status_history for actual wait times
                avg_wait_hours = 2.5  # Placeholder

                hotspots.append({
                    "geohash": geohash_key,
                    "location": {
                        "latitude": avg_lat,
                        "longitude": avg_lng
                    },
                    "facility_name": facility_name,
                    "waiting_drivers": len(waiting_drivers),
                    "avg_wait_hours": avg_wait_hours,
                    "distance_from_search": round(
                        calculate_distance(latitude, longitude, avg_lat, avg_lng), 2
                    )
                })

        # Sort by number of waiting drivers (most congested first)
        hotspots.sort(key=lambda x: x["waiting_drivers"], reverse=True)

        logger.info(f"Found {len(hotspots)} hotspots with {min_drivers}+ waiting drivers")

        return {
            "center": {
                "latitude": latitude,
                "longitude": longitude
            },
            "radius_miles": radius_miles,
            "min_waiting_drivers": min_drivers,
            "hotspot_count": len(hotspots),
            "hotspots": hotspots
        }

    except Exception as e:
        logger.error(f"Failed to get hotspots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hotspots: {str(e)}"
        )


@router.get("/stats")
async def get_map_stats(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_miles: float = Query(50.0, ge=1, le=200),
    db: Client = Depends(get_db_admin)
):
    """
    Get aggregated statistics for a map area.
    Shows total drivers, status breakdown, and activity metrics.
    """
    try:
        # Get all active drivers in area
        cutoff_time = (datetime.utcnow() - timedelta(hours=12)).isoformat()

        locations_response = db.from_("driver_locations") \
            .select("*, drivers!inner(id, status, last_active)") \
            .gte("recorded_at", cutoff_time) \
            .execute()

        total_drivers = 0
        status_counts = defaultdict(int)
        recent_activity = 0  # Active in last hour

        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        for loc in locations_response.data if locations_response.data else []:
            driver = loc["drivers"]

            # Calculate distance from center
            distance = calculate_distance(
                latitude,
                longitude,
                loc["fuzzed_latitude"],
                loc["fuzzed_longitude"]
            )

            if distance <= radius_miles:
                total_drivers += 1
                status_counts[driver["status"]] += 1

                # Check if recently active
                if driver["last_active"] >= one_hour_ago:
                    recent_activity += 1

        return {
            "center": {
                "latitude": latitude,
                "longitude": longitude
            },
            "radius_miles": radius_miles,
            "total_drivers": total_drivers,
            "status_breakdown": dict(status_counts),
            "recently_active": recent_activity,
            "activity_percentage": round(
                (recent_activity / total_drivers * 100) if total_drivers > 0 else 0, 1
            )
        }

    except Exception as e:
        logger.error(f"Failed to get map stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get map stats: {str(e)}"
        )
