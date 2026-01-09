"""
Test if driver near Love's Madera can find it
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.facility_discovery import find_nearby_facility
from app.utils.location import calculate_distance
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

db = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def test_near_facility():
    """Test if we can find Love's when driver is close by"""

    # Love's location from previous discovery: (36.9960, -120.0968)
    loves_lat, loves_lng = 36.9960, -120.0968

    # Simulate driver 0.2 miles away (within threshold)
    driver_lat = loves_lat + 0.002  # About 0.14 miles north
    driver_lng = loves_lng

    distance = calculate_distance(driver_lat, driver_lng, loves_lat, loves_lng)

    logger.info("="*80)
    logger.info("Testing: Driver near Love's Madera")
    logger.info("="*80)
    logger.info(f"Love's location: ({loves_lat}, {loves_lng})")
    logger.info(f"Driver location: ({driver_lat:.4f}, {driver_lng:.4f})")
    logger.info(f"Distance: {distance:.2f} miles")
    logger.info("="*80)

    # Test find_nearby_facility
    facility_id, facility_name = find_nearby_facility(
        db=db,
        latitude=driver_lat,
        longitude=driver_lng,
        max_distance_miles=0.3,
        discover_if_missing=False  # Don't trigger discovery, use cached data
    )

    if facility_name:
        logger.info(f"\n✅ SUCCESS! Driver found: {facility_name}")
        logger.info(f"   Facility ID: {facility_id}")
        logger.info(f"\nThis is what the driver would see in the app!")
    else:
        logger.info(f"\n❌ No facility found")

    # Test at exact Love's location
    logger.info("\n" + "="*80)
    logger.info("Testing: Driver at exact Love's location")
    logger.info("="*80)

    facility_id, facility_name = find_nearby_facility(
        db=db,
        latitude=loves_lat,
        longitude=loves_lng,
        max_distance_miles=0.3,
        discover_if_missing=False
    )

    if facility_name:
        logger.info(f"✅ SUCCESS! Driver at: {facility_name}")
    else:
        logger.info(f"❌ No facility found")

    # Show all facilities in Madera area
    logger.info("\n" + "="*80)
    logger.info("All facilities in Madera area:")
    logger.info("="*80)

    result = db.from_("facilities") \
        .select("name,type,latitude,longitude,data_source") \
        .eq("data_source", "openstreetmap") \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()

    for i, fac in enumerate(result.data, 1):
        dist = calculate_distance(36.9613, -120.0607, fac["latitude"], fac["longitude"])
        logger.info(f"{i}. {fac['name']} ({fac['type']})")
        logger.info(f"   Location: ({fac['latitude']:.4f}, {fac['longitude']:.4f})")
        logger.info(f"   Distance from Madera center: {dist:.2f} miles")


if __name__ == "__main__":
    test_near_facility()
