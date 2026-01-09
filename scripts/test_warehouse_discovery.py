"""
Test warehouse/shipper/distribution center discovery
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.facility_discovery import find_nearby_facility, discover_facilities, query_osm_nearby
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

db = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def test_warehouse_area():
    """Test discovery in an area known to have warehouses"""

    # Ontario, CA - major warehouse district (Inland Empire)
    lat, lng = 34.0633, -117.6509

    logger.info("="*80)
    logger.info("Testing: Ontario, CA Warehouse District (Inland Empire)")
    logger.info(f"Location: ({lat}, {lng})")
    logger.info("="*80)

    # First, clear cache for this area to force fresh query
    logger.info("\nStep 1: Query OSM directly to see what types of facilities exist...")

    elements = query_osm_nearby(lat, lng, radius_miles=2.0)  # Smaller radius for testing

    logger.info(f"\nOSM returned {len(elements)} elements")

    if elements:
        logger.info("\nBreakdown by type:")
        types_count = {}
        sample_by_type = {}

        for element in elements:
            tags = element.get("tags", {})
            building = tags.get("building", "")
            amenity = tags.get("amenity", "")
            highway = tags.get("highway", "")
            industrial = tags.get("industrial", "")

            # Categorize
            if building in ["warehouse", "industrial"]:
                category = f"building={building}"
            elif industrial:
                category = f"industrial={industrial}"
            elif amenity == "fuel":
                category = "fuel"
            elif highway:
                category = f"highway={highway}"
            else:
                category = "other"

            types_count[category] = types_count.get(category, 0) + 1

            # Save sample
            if category not in sample_by_type:
                sample_by_type[category] = {
                    "name": tags.get("name", "Unnamed"),
                    "tags": dict(tags)
                }

        for cat, count in sorted(types_count.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {cat}: {count}")
            sample = sample_by_type.get(cat, {})
            logger.info(f"    Example: {sample.get('name', 'N/A')}")

    # Test full discovery
    logger.info("\n" + "="*80)
    logger.info("Step 2: Test facility discovery with new query...")
    logger.info("="*80)

    facility_id, facility_name = find_nearby_facility(
        db=db,
        latitude=lat,
        longitude=lng,
        max_distance_miles=0.5,  # Wider search for warehouses
        discover_if_missing=True
    )

    if facility_name:
        logger.info(f"\n✅ FOUND FACILITY: {facility_name}")
    else:
        logger.info(f"\n❌ No facility found within 0.5 miles")

    # Show all facilities discovered
    logger.info("\n" + "="*80)
    logger.info("All facilities in database (recent discoveries):")
    logger.info("="*80)

    result = db.from_("facilities") \
        .select("name,type,latitude,longitude,data_source") \
        .eq("data_source", "openstreetmap") \
        .order("created_at", desc=True) \
        .limit(15) \
        .execute()

    if result.data:
        logger.info(f"\nFound {len(result.data)} facilities from OSM:")
        for i, fac in enumerate(result.data, 1):
            logger.info(f"{i}. {fac['name']}")
            logger.info(f"   Type: {fac['type']}")
            logger.info(f"   Location: ({fac['latitude']:.4f}, {fac['longitude']:.4f})")

        # Count by type
        type_counts = {}
        for fac in result.data:
            t = fac["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        logger.info("\nFacility types discovered:")
        for t, count in type_counts.items():
            logger.info(f"  {t}: {count}")


if __name__ == "__main__":
    logger.info("="*80)
    logger.info("WAREHOUSE DISCOVERY TEST")
    logger.info("="*80)

    response = input("\nThis will query OSM for warehouses/distribution centers. Continue? (y/n): ")
    if response.lower() != 'y':
        logger.info("Test cancelled")
        sys.exit(0)

    test_warehouse_area()

    logger.info("\n" + "="*80)
    logger.info("Test complete!")
    logger.info("="*80)
