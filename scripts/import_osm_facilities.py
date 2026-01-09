"""
Import truck stops, rest areas, and parking facilities from OpenStreetMap.

Usage:
    python scripts/import_osm_facilities.py --state California
    python scripts/import_osm_facilities.py --state Texas --dry-run
    python scripts/import_osm_facilities.py --all-states
"""

import os
import sys
import json
import requests
import argparse
from typing import List, Dict, Optional
from datetime import datetime
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client
from app.utils.location import calculate_distance
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY environment variables")

db: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

# Major trucking states (prioritized by truck traffic volume)
MAJOR_STATES = [
    "California", "Texas", "Florida", "Pennsylvania", "Ohio",
    "Illinois", "Georgia", "North Carolina", "Tennessee", "Indiana"
]

# Bounding boxes for major trucking regions (south, west, north, east)
REGION_BBOXES = {
    # Test with small area first
    "fresno_area": (36.6, -119.9, 36.9, -119.6),  # Fresno, CA - small test area

    # California regions
    "california_central_valley": (35.0, -121.5, 40.0, -118.0),  # Fresno to Redding
    "california_la_area": (33.5, -119.0, 34.5, -117.0),  # LA metro
    "california_bay_area": (37.0, -123.0, 38.5, -121.5),  # SF Bay Area

    # Texas regions
    "texas_i35_corridor": (29.0, -98.0, 33.5, -96.5),  # San Antonio to Dallas
    "texas_houston_area": (29.0, -96.0, 30.5, -94.5),  # Houston metro
}

# Try alternative Overpass API instances if main one is slow
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def query_osm_facilities_bbox(bbox: tuple, region_name: str, timeout: int = 180) -> List[Dict]:
    """
    Query OpenStreetMap Overpass API for truck-related facilities in a bounding box.

    Args:
        bbox: (south, west, north, east) coordinates
        region_name: Name for logging
        timeout: Query timeout in seconds

    Returns list of facilities
    """

    overpass_url = "http://overpass-api.de/api/interpreter"

    south, west, north, east = bbox

    # Overpass QL query with bounding box
    query = f"""
    [out:json][timeout:{timeout}];
    (
      // Truck stops (fuel stations that accept trucks)
      node["amenity"="fuel"]["hgv"="yes"]({south},{west},{north},{east});
      way["amenity"="fuel"]["hgv"="yes"]({south},{west},{north},{east});

      // Rest areas
      node["highway"="rest_area"]({south},{west},{north},{east});
      way["highway"="rest_area"]({south},{west},{north},{east});

      // Truck parking
      node["amenity"="parking"]["hgv"="yes"]({south},{west},{north},{east});
      way["amenity"="parking"]["hgv"="yes"]({south},{west},{north},{east});

      // Service areas
      node["highway"="services"]({south},{west},{north},{east});
      way["highway"="services"]({south},{west},{north},{east});
    );
    out center tags;
    """

    logger.info(f"Querying OpenStreetMap for facilities in {region_name}...")

    try:
        response = requests.post(
            overpass_url,
            data={"data": query},
            timeout=timeout + 10
        )
        response.raise_for_status()
        data = response.json()

        logger.info(f"Found {len(data.get('elements', []))} facilities in {region_name}")
        return data.get("elements", [])

    except requests.exceptions.Timeout:
        logger.error(f"Query timeout for {region_name} - try smaller bbox or increase timeout")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to query OSM for {region_name}: {e}")
        return []


def query_osm_facilities(state: str, timeout: int = 180) -> List[Dict]:
    """
    Query OpenStreetMap Overpass API for truck-related facilities in a state.

    Returns list of facilities with:
    - Truck stops (amenity=fuel + hgv=yes)
    - Rest areas (highway=rest_area)
    - Truck parking (amenity=parking + hgv=yes)
    - Service areas (highway=services)
    """

    overpass_url = "http://overpass-api.de/api/interpreter"

    # Overpass QL query
    query = f"""
    [out:json][timeout:{timeout}];
    area["ISO3166-1"="US"]["name"="{state}"]->.searchArea;
    (
      // Truck stops (fuel stations that accept trucks)
      node["amenity"="fuel"]["hgv"="yes"](area.searchArea);
      way["amenity"="fuel"]["hgv"="yes"](area.searchArea);

      // Rest areas
      node["highway"="rest_area"](area.searchArea);
      way["highway"="rest_area"](area.searchArea);

      // Truck parking
      node["amenity"="parking"]["hgv"="yes"](area.searchArea);
      way["amenity"="parking"]["hgv"="yes"](area.searchArea);

      // Service areas (often have truck facilities)
      node["highway"="services"](area.searchArea);
      way["highway"="services"](area.searchArea);
    );
    out center tags;
    """

    logger.info(f"Querying OpenStreetMap for facilities in {state}...")

    try:
        response = requests.post(
            overpass_url,
            data={"data": query},
            timeout=timeout + 10
        )
        response.raise_for_status()
        data = response.json()

        logger.info(f"Found {len(data.get('elements', []))} facilities in {state}")
        return data.get("elements", [])

    except requests.exceptions.Timeout:
        logger.error(f"Query timeout for {state} - try increasing timeout value")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to query OSM for {state}: {e}")
        return []


def parse_osm_element(element: Dict, state: str) -> Optional[Dict]:
    """
    Parse OSM element into facility data structure.

    Returns None if element doesn't have required fields.
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

    if amenity == "fuel" and tags.get("hgv") == "yes":
        facility_type = "truck_stop"
    elif highway == "rest_area":
        facility_type = "rest_area"
    elif amenity == "parking" and tags.get("hgv") == "yes":
        facility_type = "truck_parking"
    elif highway == "services":
        facility_type = "service_area"
    else:
        facility_type = "truck_stop"  # Default

    # Extract name
    name = (
        tags.get("name") or
        tags.get("operator") or
        tags.get("brand") or
        f"{facility_type.replace('_', ' ').title()} ({lat:.4f}, {lon:.4f})"
    )

    # Extract brand
    brand = tags.get("brand") or tags.get("operator")

    # Extract address info
    address = tags.get("addr:street")
    if address and tags.get("addr:housenumber"):
        address = f"{tags['addr:housenumber']} {address}"

    city = tags.get("addr:city")
    state_abbr = tags.get("addr:state")
    zip_code = tags.get("addr:postcode")

    # Extract amenities
    amenities = {}

    if tags.get("fuel:diesel") == "yes":
        amenities["diesel"] = True
    if tags.get("shop") == "convenience":
        amenities["convenience_store"] = True
    if tags.get("amenity") == "restaurant" or "restaurant" in tags:
        amenities["food"] = True
    if tags.get("shower") == "yes":
        amenities["showers"] = True
    if tags.get("toilets") == "yes":
        amenities["restrooms"] = True
    if tags.get("wifi") == "yes":
        amenities["wifi"] = True

    # Parking info
    parking_spaces = None
    capacity = tags.get("capacity")
    if capacity and capacity.isdigit():
        parking_spaces = int(capacity)

    # Operating hours
    is_open_24h = tags.get("opening_hours") == "24/7"

    # Build geohash (simplified - first 8 chars of lat/lon)
    geohash = f"{int(lat * 10000):08x}{int(lon * 10000):08x}"[:12]

    return {
        "name": name,
        "type": facility_type,
        "latitude": lat,
        "longitude": lon,
        "address": address,
        "city": city,
        "state": state_abbr or state,
        "zip_code": zip_code,
        "brand": brand,
        "amenities": amenities if amenities else None,
        "parking_spaces": parking_spaces,
        "is_open_24h": is_open_24h,
        "geohash": geohash,
        "data_source": "openstreetmap",
        "osm_id": element.get("id"),
    }


def check_duplicate(facility: Dict, existing_facilities: List[Dict], threshold_miles: float = 0.1) -> bool:
    """
    Check if facility is duplicate of existing facility.

    Two facilities are considered duplicates if they are within threshold_miles
    and have similar names.
    """

    for existing in existing_facilities:
        distance = calculate_distance(
            facility["latitude"],
            facility["longitude"],
            existing["latitude"],
            existing["longitude"]
        )

        if distance <= threshold_miles:
            # Check name similarity
            name1 = facility["name"].lower()
            name2 = existing["name"].lower()

            # Simple similarity check
            if name1 == name2 or name1 in name2 or name2 in name1:
                logger.debug(f"Duplicate found: {facility['name']} matches {existing['name']}")
                return True

    return False


def import_facilities(facilities: List[Dict], dry_run: bool = False) -> int:
    """
    Import facilities into database.

    Returns number of facilities imported.
    """

    if dry_run:
        logger.info(f"DRY RUN: Would import {len(facilities)} facilities")
        for i, facility in enumerate(facilities[:5], 1):
            logger.info(f"  {i}. {facility['name']} ({facility['type']}) at {facility['latitude']}, {facility['longitude']}")
        if len(facilities) > 5:
            logger.info(f"  ... and {len(facilities) - 5} more")
        return 0

    # Get existing facilities for duplicate checking
    logger.info("Fetching existing facilities for duplicate checking...")
    existing_response = db.from_("facilities").select("name,latitude,longitude").execute()
    existing_facilities = existing_response.data if existing_response.data else []

    logger.info(f"Found {len(existing_facilities)} existing facilities")

    # Filter out duplicates
    unique_facilities = []
    duplicates = 0

    for facility in facilities:
        if not check_duplicate(facility, existing_facilities, threshold_miles=0.1):
            unique_facilities.append(facility)
        else:
            duplicates += 1

    logger.info(f"Filtered out {duplicates} duplicates, importing {len(unique_facilities)} unique facilities")

    if not unique_facilities:
        logger.info("No new facilities to import")
        return 0

    # Import in batches of 100
    batch_size = 100
    imported = 0

    for i in range(0, len(unique_facilities), batch_size):
        batch = unique_facilities[i:i + batch_size]

        try:
            response = db.from_("facilities").insert(batch).execute()

            if response.data:
                imported += len(response.data)
                logger.info(f"Imported batch {i // batch_size + 1}: {len(response.data)} facilities")
            else:
                logger.warning(f"Batch {i // batch_size + 1} returned no data")

        except Exception as e:
            logger.error(f"Failed to import batch {i // batch_size + 1}: {e}")
            continue

        # Rate limiting - avoid hammering database
        time.sleep(0.5)

    logger.info(f"Successfully imported {imported} facilities")
    return imported


def import_region(region_name: str, bbox: tuple, dry_run: bool = False) -> int:
    """
    Import all facilities for a given region (bounding box).
    """

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting import for region {region_name}")

    # Query OSM
    elements = query_osm_facilities_bbox(bbox, region_name)

    if not elements:
        logger.warning(f"No facilities found for {region_name}")
        return 0

    # Parse elements
    facilities = []
    for element in elements:
        # Extract state from tags or use region name
        tags = element.get("tags", {})
        state = tags.get("addr:state", region_name.split("_")[0].title())

        parsed = parse_osm_element(element, state)
        if parsed:
            facilities.append(parsed)

    logger.info(f"Parsed {len(facilities)} valid facilities from {len(elements)} OSM elements")

    # Import
    imported = import_facilities(facilities, dry_run=dry_run)

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Completed import for {region_name}: {imported} facilities")

    return imported


def import_state(state: str, dry_run: bool = False) -> int:
    """
    Import all facilities for a given state.
    """

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting import for {state}")

    # Query OSM
    elements = query_osm_facilities(state)

    if not elements:
        logger.warning(f"No facilities found for {state}")
        return 0

    # Parse elements
    facilities = []
    for element in elements:
        parsed = parse_osm_element(element, state)
        if parsed:
            facilities.append(parsed)

    logger.info(f"Parsed {len(facilities)} valid facilities from {len(elements)} OSM elements")

    # Import
    imported = import_facilities(facilities, dry_run=dry_run)

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Completed import for {state}: {imported} facilities")

    return imported


def import_all_states(dry_run: bool = False):
    """
    Import facilities for all major trucking states.
    """

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting import for {len(MAJOR_STATES)} states")

    total_imported = 0

    for state in MAJOR_STATES:
        try:
            imported = import_state(state, dry_run=dry_run)
            total_imported += imported

            # Rate limiting between states
            if state != MAJOR_STATES[-1]:
                logger.info("Waiting 10 seconds before next state...")
                time.sleep(10)

        except Exception as e:
            logger.error(f"Failed to import {state}: {e}")
            continue

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Total imported across all states: {total_imported}")


def main():
    parser = argparse.ArgumentParser(description="Import truck facilities from OpenStreetMap")
    parser.add_argument("--state", type=str, help="State name (e.g., 'California')")
    parser.add_argument("--region", type=str, help="Region name from REGION_BBOXES")
    parser.add_argument("--all-states", action="store_true", help="Import all major trucking states")
    parser.add_argument("--all-regions", action="store_true", help="Import all defined regions")
    parser.add_argument("--dry-run", action="store_true", help="Preview without importing")

    args = parser.parse_args()

    if args.all_states:
        import_all_states(dry_run=args.dry_run)
    elif args.all_regions:
        logger.info(f"{'[DRY RUN] ' if args.dry_run else ''}Importing all regions")
        total = 0
        for region_name, bbox in REGION_BBOXES.items():
            imported = import_region(region_name, bbox, dry_run=args.dry_run)
            total += imported
            if region_name != list(REGION_BBOXES.keys())[-1]:
                logger.info("Waiting 5 seconds before next region...")
                time.sleep(5)
        logger.info(f"{'[DRY RUN] ' if args.dry_run else ''}Total imported: {total} facilities")
    elif args.region:
        if args.region not in REGION_BBOXES:
            logger.error(f"Unknown region: {args.region}")
            logger.info(f"Available regions: {', '.join(REGION_BBOXES.keys())}")
            sys.exit(1)
        import_region(args.region, REGION_BBOXES[args.region], dry_run=args.dry_run)
    elif args.state:
        import_state(args.state, dry_run=args.dry_run)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
