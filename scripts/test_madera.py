"""
Test facility discovery for Madera, CA
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.facility_discovery import find_nearby_facility, query_osm_nearby, parse_osm_element
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise ValueError("Missing SUPABASE credentials")

db = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def test_madera():
    """Test Madera, CA specifically"""

    # Madera, CA coordinates (near CA-99)
    lat, lng = 36.9613, -120.0607

    logger.info("="*80)
    logger.info(f"Testing: Madera, CA")
    logger.info(f"Location: ({lat}, {lng})")
    logger.info("="*80)

    # First, let's see what OSM returns for this area
    logger.info("\nStep 1: Query OSM directly for Madera area...")

    elements = query_osm_nearby(lat, lng, radius_miles=5.0)

    logger.info(f"OSM returned {len(elements)} elements")

    if elements:
        logger.info("\nFacilities found in OSM:")
        for i, element in enumerate(elements[:10], 1):  # Show first 10
            tags = element.get("tags", {})
            name = tags.get("name", "Unnamed")
            amenity = tags.get("amenity", "")
            highway = tags.get("highway", "")
            hgv = tags.get("hgv", "")
            brand = tags.get("brand", "")

            # Get coordinates
            if element["type"] == "node":
                lat_elem = element.get("lat")
                lon_elem = element.get("lon")
            elif "center" in element:
                lat_elem = element["center"].get("lat")
                lon_elem = element["center"].get("lon")
            else:
                lat_elem, lon_elem = None, None

            logger.info(f"\n  {i}. {name}")
            logger.info(f"     OSM ID: {element.get('id')}")
            logger.info(f"     Type: {element.get('type')}")
            logger.info(f"     Tags: amenity={amenity}, highway={highway}, hgv={hgv}, brand={brand}")
            if lat_elem and lon_elem:
                logger.info(f"     Location: ({lat_elem:.4f}, {lon_elem:.4f})")

            # Try to parse it
            parsed = parse_osm_element(element)
            if parsed:
                logger.info(f"     ✅ Parsed as: {parsed['type']} - {parsed['name']}")
            else:
                logger.info(f"     ❌ Could not parse")
    else:
        logger.info("\n❌ No facilities found in OSM for Madera area")
        logger.info("This suggests:")
        logger.info("  1. OSM has no truck facilities tagged in this area")
        logger.info("  2. Or our query filters are too restrictive")

    # Now test the full discovery process
    logger.info("\n" + "="*80)
    logger.info("Step 2: Test full discovery process...")
    logger.info("="*80)

    facility_id, facility_name = find_nearby_facility(
        db=db,
        latitude=lat,
        longitude=lng,
        max_distance_miles=0.3,
        discover_if_missing=True
    )

    if facility_name:
        logger.info(f"\n✅ SUCCESS! Found facility: {facility_name} (ID: {facility_id})")
    else:
        logger.info(f"\n❌ No facility found within 0.3 miles of Madera")

    # Check what's now in the database
    logger.info("\n" + "="*80)
    logger.info("Step 3: Check database...")
    logger.info("="*80)

    # Count facilities from openstreetmap
    result = db.from_("facilities") \
        .select("*") \
        .eq("data_source", "openstreetmap") \
        .execute()

    logger.info(f"\nFacilities from OSM in database: {len(result.data)}")

    if result.data:
        logger.info("\nRecently imported from OSM:")
        for i, fac in enumerate(result.data[:5], 1):
            logger.info(f"  {i}. {fac['name']} ({fac['type']})")
            logger.info(f"     Location: ({fac['latitude']:.4f}, {fac['longitude']:.4f})")
            logger.info(f"     OSM ID: {fac.get('osm_id')}")


if __name__ == "__main__":
    logger.info("="*80)
    logger.info("MADERA, CA FACILITY DISCOVERY TEST")
    logger.info("="*80)

    test_madera()

    logger.info("\n" + "="*80)
    logger.info("Test complete!")
    logger.info("="*80)
