"""
Test facility discovery system
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.facility_discovery import (
    encode_geohash,
    query_osm_nearby,
    parse_osm_element,
    find_nearby_facility
)
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY")

db = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def test_geohash():
    """Test geohash encoding"""
    logger.info("Testing geohash encoding...")

    lat, lng = 36.7783, -119.4179  # Fresno, CA
    geohash = encode_geohash(lat, lng, precision=6)

    logger.info(f"Coordinates: ({lat}, {lng})")
    logger.info(f"Geohash (6 chars): {geohash}")

    return geohash


def test_osm_query():
    """Test OSM query for small area"""
    logger.info("\nTesting OSM query...")

    # Fresno, CA - should have truck stops
    lat, lng = 36.7783, -119.4179

    logger.info(f"Querying OSM for facilities near ({lat}, {lng})")

    elements = query_osm_nearby(lat, lng, radius_miles=2.0)  # Small radius for testing

    logger.info(f"Found {len(elements)} facilities from OSM")

    if elements:
        logger.info("\nFirst 3 facilities:")
        for i, element in enumerate(elements[:3], 1):
            parsed = parse_osm_element(element)
            if parsed:
                logger.info(f"  {i}. {parsed['name']} ({parsed['type']}) at {parsed['latitude']:.4f}, {parsed['longitude']:.4f}")

    return elements


def test_facility_lookup():
    """Test facility lookup (won't work until migration is applied)"""
    logger.info("\nTesting facility lookup...")

    lat, lng = 36.7783, -119.4179

    try:
        facility_id, facility_name = find_nearby_facility(
            db=db,
            latitude=lat,
            longitude=lng,
            max_distance_miles=0.3,
            discover_if_missing=False  # Don't trigger discovery yet
        )

        if facility_name:
            logger.info(f"Found facility: {facility_name} (ID: {facility_id})")
        else:
            logger.info("No facility found in database (expected if DB is empty)")

    except Exception as e:
        logger.error(f"Error during lookup: {e}")
        logger.info("This is expected if migration 005 hasn't been applied yet")


def main():
    logger.info("="*80)
    logger.info("FACILITY DISCOVERY SYSTEM TEST")
    logger.info("="*80)

    # Test 1: Geohash
    geohash = test_geohash()

    # Test 2: OSM Query (this will actually query OpenStreetMap)
    logger.info("\nTest 2: OSM Query")
    logger.info("WARNING: This will make a real API call to OpenStreetMap")

    response = input("Continue with OSM query? (y/n): ")
    if response.lower() == 'y':
        elements = test_osm_query()
    else:
        logger.info("Skipping OSM query")

    # Test 3: Database lookup
    logger.info("\nTest 3: Database Lookup")
    test_facility_lookup()

    logger.info("\n" + "="*80)
    logger.info("Tests complete!")
    logger.info("="*80)


if __name__ == "__main__":
    main()
