"""
Live test of facility discovery with actual driver location
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.facility_discovery import find_nearby_facility, discover_facilities
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise ValueError("Missing SUPABASE credentials")

db = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def test_location(name: str, lat: float, lng: float):
    """Test facility discovery at a specific location"""

    logger.info("="*80)
    logger.info(f"Testing: {name}")
    logger.info(f"Location: ({lat}, {lng})")
    logger.info("="*80)

    # Check current state of facilities table
    result = db.from_("facilities").select("id", count="exact").execute()
    logger.info(f"Current facilities in DB: {result.count}")

    # Check cache state
    cache_result = db.from_("osm_query_cache").select("*", count="exact").execute()
    logger.info(f"Cached regions: {cache_result.count}")

    # Test find_nearby_facility with discovery
    logger.info("\nCalling find_nearby_facility() with discovery enabled...")

    facility_id, facility_name = find_nearby_facility(
        db=db,
        latitude=lat,
        longitude=lng,
        max_distance_miles=0.3,
        discover_if_missing=True
    )

    if facility_name:
        logger.info(f"✅ FOUND FACILITY: {facility_name} (ID: {facility_id})")
    else:
        logger.info(f"❌ No facility found within 0.3 miles")

    # Check facilities again
    result = db.from_("facilities").select("id", count="exact").execute()
    logger.info(f"Facilities in DB after discovery: {result.count}")

    # Check cache again
    cache_result = db.from_("osm_query_cache").select("*", count="exact").execute()
    logger.info(f"Cached regions after discovery: {cache_result.count}")

    # Show nearby facilities
    logger.info("\nNearby facilities discovered:")
    nearby = db.from_("facilities") \
        .select("name,type,latitude,longitude,data_source") \
        .order("created_at", desc=True) \
        .limit(5) \
        .execute()

    if nearby.data:
        for i, fac in enumerate(nearby.data, 1):
            logger.info(f"  {i}. {fac['name']} ({fac['type']}) - {fac['data_source']}")
            logger.info(f"     ({fac['latitude']:.4f}, {fac['longitude']:.4f})")
    else:
        logger.info("  No facilities found")

    return facility_name is not None


def main():
    logger.info("="*80)
    logger.info("LIVE FACILITY DISCOVERY TEST")
    logger.info("="*80)

    # Test locations (known to have truck stops nearby)
    test_locations = [
        ("Fresno, CA (I-5 & CA-99)", 36.7783, -119.4179),
        ("Ontario, CA (I-10 & I-15)", 34.0633, -117.6509),
        ("Barstow, CA (I-15 & I-40)", 34.8958, -117.0228),
    ]

    logger.info(f"\nWill test {len(test_locations)} locations")
    logger.info("This will query OpenStreetMap and may take 1-2 minutes\n")

    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        logger.info("Test cancelled")
        sys.exit(0)

    results = []

    for name, lat, lng in test_locations:
        found = test_location(name, lat, lng)
        results.append((name, found))

        logger.info("\n" + "-"*80 + "\n")

        # Small delay between locations
        import time
        time.sleep(2)

    # Summary
    logger.info("="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)

    for name, found in results:
        status = "✅ FOUND" if found else "❌ NOT FOUND"
        logger.info(f"{status} - {name}")

    success_rate = sum(1 for _, found in results if found) / len(results) * 100
    logger.info(f"\nSuccess rate: {success_rate:.0f}%")

    # Final stats
    result = db.from_("facilities").select("id", count="exact").execute()
    logger.info(f"Total facilities in database: {result.count}")

    cache_result = db.from_("osm_query_cache").select("*", count="exact").execute()
    logger.info(f"Total cached regions: {cache_result.count}")

    logger.info("\n✅ Live testing complete!")


if __name__ == "__main__":
    main()
