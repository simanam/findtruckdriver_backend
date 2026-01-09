"""
Facility Discovery Service
On-demand facility lookup with OSM fallback for unmapped areas
"""

import requests
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from supabase import Client

from app.utils.location import calculate_distance

logger = logging.getLogger(__name__)

# Geohash precision levels
# 6 chars ≈ 0.6km x 1.2km (good for "have we queried this area?")
GEOHASH_PRECISION = 6
QUERY_RADIUS_MILES = 5.0  # Query 5 mile radius from driver location
CACHE_REFRESH_DAYS = 30  # Re-query areas after 30 days


def encode_geohash(latitude: float, longitude: float, precision: int = 6) -> str:
    """
    Encode coordinates to geohash string.

    Simple implementation - for production consider using python-geohash library.
    """
    try:
        import geohash as gh
        return gh.encode(latitude, longitude, precision=precision)
    except ImportError:
        # Fallback: simple grid-based hash
        lat_cell = int((latitude + 90) * 100)
        lng_cell = int((longitude + 180) * 100)
        return f"{lat_cell:05d}{lng_cell:06d}"[:precision]


def should_query_osm(db: Client, latitude: float, longitude: float) -> bool:
    """
    Check if we should query OSM for this location.

    Returns True if:
    - Area has never been queried
    - Area was last queried > 30 days ago
    """

    geohash = encode_geohash(latitude, longitude, precision=GEOHASH_PRECISION)

    try:
        result = db.from_("osm_query_cache") \
            .select("last_queried_at") \
            .eq("geohash_prefix", geohash) \
            .single() \
            .execute()

        if not result.data:
            # Never queried
            return True

        # Check if stale
        last_queried = datetime.fromisoformat(result.data["last_queried_at"].replace("Z", "+00:00"))
        age = datetime.utcnow().replace(tzinfo=last_queried.tzinfo) - last_queried

        if age > timedelta(days=CACHE_REFRESH_DAYS):
            logger.info(f"OSM cache for {geohash} is stale ({age.days} days old)")
            return True

        logger.debug(f"OSM cache hit for {geohash}, last queried {age.days} days ago")
        return False

    except Exception as e:
        logger.warning(f"Error checking OSM cache: {e}")
        # On error, default to querying (better to have data)
        return True


def query_osm_nearby(latitude: float, longitude: float, radius_miles: float = 5.0) -> List[Dict]:
    """
    Query OpenStreetMap for truck facilities within radius of coordinates.

    Uses small bounding box for fast queries (<5 seconds typically).
    """

    # Convert radius to degrees (approximate)
    import math
    radius_lat = radius_miles / 69.0
    radius_lng = radius_miles / (69.0 * math.cos(math.radians(latitude)))

    # Create bounding box
    south = latitude - radius_lat
    north = latitude + radius_lat
    west = longitude - radius_lng
    east = longitude + radius_lng

    overpass_url = "https://overpass-api.de/api/interpreter"

    # Query for truck-related facilities AND business locations
    query = f"""
    [out:json][timeout:30];
    (
      // Truck stops and fuel
      node["amenity"="fuel"]["hgv"="yes"]({south},{west},{north},{east});
      way["amenity"="fuel"]["hgv"="yes"]({south},{west},{north},{east});
      node["amenity"="fuel"]["name"~"(Love|Pilot|Flying J|TA|Petro)",i]({south},{west},{north},{east});
      way["amenity"="fuel"]["name"~"(Love|Pilot|Flying J|TA|Petro)",i]({south},{west},{north},{east});

      // Rest areas and service plazas
      node["highway"="rest_area"]({south},{west},{north},{east});
      way["highway"="rest_area"]({south},{west},{north},{east});
      node["highway"="services"]({south},{west},{north},{east});
      way["highway"="services"]({south},{west},{north},{east});

      // Warehouses and distribution centers
      node["building"="warehouse"]({south},{west},{north},{east});
      way["building"="warehouse"]({south},{west},{north},{east});
      node["building"="industrial"]({south},{west},{north},{east});
      way["building"="industrial"]({south},{west},{north},{east});
      node["industrial"="distribution"]({south},{west},{north},{east});
      way["industrial"="distribution"]({south},{west},{north},{east});

      // Commercial/retail buildings with names (like Walmart DC, Target DC, etc.)
      node["building"="retail"]["name"]({south},{west},{north},{east});
      way["building"="retail"]["name"]({south},{west},{north},{east});
      node["building"="commercial"]["name"]({south},{west},{north},{east});
      way["building"="commercial"]["name"]({south},{west},{north},{east});
    );
    out center tags;
    """

    logger.info(f"Querying OSM for facilities near ({latitude:.4f}, {longitude:.4f}) r={radius_miles}mi")

    try:
        response = requests.post(
            overpass_url,
            data={"data": query},
            timeout=35  # Slightly longer than query timeout
        )
        response.raise_for_status()
        data = response.json()

        elements = data.get("elements", [])
        logger.info(f"Found {len(elements)} facilities from OSM")

        return elements

    except requests.exceptions.Timeout:
        logger.error(f"OSM query timeout for ({latitude:.4f}, {longitude:.4f})")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"OSM query failed: {e}")
        return []


def parse_osm_element(element: Dict) -> Optional[Dict]:
    """
    Parse OSM element into facility record.
    """

    tags = element.get("tags", {})

    # Get coordinates
    if element["type"] == "node":
        lat = element.get("lat")
        lon = element.get("lon")
    elif "center" in element:
        lat = element["center"].get("lat")
        lon = element["center"].get("lon")
    else:
        return None

    if not lat or not lon:
        return None

    # Determine facility type
    amenity = tags.get("amenity")
    highway = tags.get("highway")
    building = tags.get("building")
    industrial = tags.get("industrial")

    # Truck stops and rest areas
    if amenity == "fuel" and tags.get("hgv") == "yes":
        facility_type = "truck_stop"
    elif amenity == "fuel":
        # Major truck stop chains even without hgv tag
        facility_type = "truck_stop"
    elif highway == "rest_area":
        facility_type = "rest_area"
    elif amenity == "parking" and tags.get("hgv") == "yes":
        facility_type = "parking"
    elif highway == "services":
        facility_type = "service_plaza"

    # Warehouses and distribution centers
    elif building == "warehouse":
        facility_type = "warehouse"
    elif building == "industrial":
        facility_type = "warehouse"
    elif industrial == "distribution":
        facility_type = "warehouse"

    # Commercial/retail (Walmart DC, Target DC, etc.)
    elif building in ["retail", "commercial"]:
        facility_type = "warehouse"

    else:
        facility_type = "truck_stop"  # Default

    # Extract name
    name = (
        tags.get("name") or
        tags.get("operator") or
        tags.get("brand") or
        f"{facility_type.replace('_', ' ').title()} ({lat:.4f}, {lon:.4f})"
    )

    # Build amenities JSON
    amenities = {}
    if tags.get("fuel:diesel") == "yes":
        amenities["diesel"] = True
    if tags.get("shop") == "convenience":
        amenities["convenience_store"] = True
    if tags.get("amenity") in ["restaurant", "food"]:
        amenities["food"] = True
    if tags.get("shower") == "yes":
        amenities["showers"] = True
    if tags.get("toilets") == "yes":
        amenities["restrooms"] = True
    if tags.get("wifi") == "yes":
        amenities["wifi"] = True

    # Geohash for indexing
    geohash = encode_geohash(lat, lon, precision=12)

    return {
        "name": name,
        "type": facility_type,
        "latitude": lat,
        "longitude": lon,
        "address": tags.get("addr:street"),
        "city": tags.get("addr:city"),
        "state": tags.get("addr:state"),
        "zip_code": tags.get("addr:postcode"),
        "brand": tags.get("brand") or tags.get("operator"),
        "amenities": amenities if amenities else None,
        "parking_spaces": int(tags.get("capacity")) if tags.get("capacity", "").isdigit() else None,
        "is_open_24h": tags.get("opening_hours") == "24/7",
        "geohash": geohash,
        "data_source": "openstreetmap",
        "osm_id": element.get("id"),
        "last_verified_at": datetime.utcnow().isoformat(),
    }


def check_duplicate_facility(db: Client, facility: Dict, threshold_miles: float = 0.05) -> bool:
    """
    Check if facility already exists in database.

    Checks by:
    1. OSM ID (exact match)
    2. Proximity + name similarity (within 0.05 miles ≈ 250 feet)
    """

    # Check by OSM ID first (fastest)
    if facility.get("osm_id"):
        result = db.from_("facilities") \
            .select("id") \
            .eq("osm_id", facility["osm_id"]) \
            .execute()

        if result.data:
            logger.debug(f"Facility duplicate found by OSM ID: {facility['osm_id']}")
            return True

    # Check by proximity (get facilities in same geohash cell)
    geohash_prefix = facility["geohash"][:6]  # ≈ 1km cell

    nearby = db.from_("facilities") \
        .select("id,name,latitude,longitude") \
        .like("geohash", f"{geohash_prefix}%") \
        .execute()

    if not nearby.data:
        return False

    # Check distance and name similarity
    for existing in nearby.data:
        distance = calculate_distance(
            facility["latitude"],
            facility["longitude"],
            existing["latitude"],
            existing["longitude"]
        )

        if distance <= threshold_miles:
            # Close proximity - check name similarity
            name1 = facility["name"].lower()
            name2 = existing["name"].lower()

            if name1 == name2 or name1 in name2 or name2 in name1:
                logger.debug(f"Facility duplicate found by proximity: {facility['name']}")
                return True

    return False


def discover_facilities(db: Client, latitude: float, longitude: float) -> int:
    """
    Discover and import facilities for a location if not already cached.

    Returns number of new facilities added.
    """

    # Check if we should query OSM
    if not should_query_osm(db, latitude, longitude):
        logger.debug("Skipping OSM query - area recently queried")
        return 0

    # Query OSM
    osm_elements = query_osm_nearby(latitude, longitude, radius_miles=QUERY_RADIUS_MILES)

    if not osm_elements:
        logger.info("No facilities found from OSM")
        # Still cache the query to avoid re-querying empty areas
        _update_query_cache(db, latitude, longitude, 0)
        return 0

    # Parse and import facilities
    imported = 0
    for element in osm_elements:
        facility = parse_osm_element(element)

        if not facility:
            continue

        # Check for duplicates
        if check_duplicate_facility(db, facility):
            continue

        # Insert facility
        try:
            result = db.from_("facilities").insert(facility).execute()
            if result.data:
                imported += 1
                logger.debug(f"Imported facility: {facility['name']}")
        except Exception as e:
            logger.error(f"Failed to import facility {facility['name']}: {e}")
            continue

    logger.info(f"Imported {imported} new facilities from {len(osm_elements)} OSM elements")

    # Update query cache
    _update_query_cache(db, latitude, longitude, len(osm_elements))

    return imported


def _update_query_cache(db: Client, latitude: float, longitude: float, facilities_found: int):
    """
    Update OSM query cache for this location.
    """

    geohash = encode_geohash(latitude, longitude, precision=GEOHASH_PRECISION)

    try:
        # Try to update existing record
        result = db.from_("osm_query_cache") \
            .select("id,query_count") \
            .eq("geohash_prefix", geohash) \
            .execute()

        if result.data:
            # Update existing
            db.from_("osm_query_cache").update({
                "last_queried_at": datetime.utcnow().isoformat(),
                "facilities_found": facilities_found,
                "query_count": result.data[0]["query_count"] + 1
            }).eq("geohash_prefix", geohash).execute()
        else:
            # Insert new
            db.from_("osm_query_cache").insert({
                "geohash_prefix": geohash,
                "center_latitude": latitude,
                "center_longitude": longitude,
                "query_radius_miles": QUERY_RADIUS_MILES,
                "facilities_found": facilities_found,
                "last_queried_at": datetime.utcnow().isoformat(),
                "query_count": 1
            }).execute()

        logger.debug(f"Updated OSM query cache for {geohash}")

    except Exception as e:
        logger.error(f"Failed to update query cache: {e}")


def find_nearby_facility(
    db: Client,
    latitude: float,
    longitude: float,
    max_distance_miles: float = 0.3,
    discover_if_missing: bool = True
) -> Tuple[Optional[str], Optional[str]]:
    """
    Find facility near coordinates. Optionally triggers discovery if none found.

    Returns (facility_id, facility_name) or (None, None)

    Args:
        db: Supabase client
        latitude: Driver latitude
        longitude: Driver longitude
        max_distance_miles: Maximum distance to consider "at facility"
        discover_if_missing: If True, trigger OSM discovery when no facilities found

    Returns:
        Tuple of (facility_id, facility_name) or (None, None)
    """

    # Calculate bounding box for search (search slightly wider to catch nearby cells)
    # 0.3 miles ≈ 0.0044 degrees latitude, 0.0045 degrees longitude (at ~37° latitude)
    search_radius_deg = max_distance_miles / 69.0 * 1.5  # 1.5x wider for safety

    lat_min = latitude - search_radius_deg
    lat_max = latitude + search_radius_deg
    lng_min = longitude - search_radius_deg
    lng_max = longitude + search_radius_deg

    # Query facilities within bounding box
    facilities = db.from_("facilities") \
        .select("id,name,latitude,longitude") \
        .gte("latitude", lat_min) \
        .lte("latitude", lat_max) \
        .gte("longitude", lng_min) \
        .lte("longitude", lng_max) \
        .execute()

    # Find nearest facility within threshold
    nearest_facility = None
    nearest_distance = float('inf')

    if facilities.data:
        for facility in facilities.data:
            distance = calculate_distance(
                latitude, longitude,
                facility["latitude"], facility["longitude"]
            )

            if distance <= max_distance_miles and distance < nearest_distance:
                nearest_facility = facility
                nearest_distance = distance

    if nearest_facility:
        logger.debug(f"Found facility {nearest_facility['name']} at {nearest_distance:.2f} miles")
        return nearest_facility["id"], nearest_facility["name"]

    # No facility found - trigger discovery if enabled
    if discover_if_missing:
        logger.info(f"No facility found near ({latitude:.4f}, {longitude:.4f}), triggering discovery")

        # Discover facilities (synchronous for now, can be made async later)
        discovered = discover_facilities(db, latitude, longitude)

        if discovered > 0:
            # Retry the search
            return find_nearby_facility(db, latitude, longitude, max_distance_miles, discover_if_missing=False)

    logger.debug(f"No facility within {max_distance_miles} miles of ({latitude:.4f}, {longitude:.4f})")
    return None, None
