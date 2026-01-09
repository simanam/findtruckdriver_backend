"""
Import U.S. DOT truck parking data from NTAD dataset

This script downloads and imports truck parking facilities from the
U.S. Department of Transportation's National Transportation Atlas Database.

Data Source: https://catalog.data.gov/dataset/truck-stop-parking1
Provider: Federal Highway Administration (FHWA) / BTS
"""

import os
import sys
import requests
import csv
import json
from io import StringIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.utils.location import calculate_distance
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

db = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

# ArcGIS Feature Server endpoint for truck parking data
DOT_PARKING_API = "https://geo.dot.gov/server/rest/services/Hosted/Truck_Stop_Parking/FeatureServer/0/query"

def download_dot_parking_data():
    """
    Download truck parking data from U.S. DOT ArcGIS Feature Server

    Returns:
        List of parking facility dictionaries
    """
    logger.info("Downloading truck parking data from U.S. DOT...")

    params = {
        'where': '1=1',  # Get all records
        'outFields': '*',  # Get all fields
        'f': 'json',  # JSON format
        'returnGeometry': 'true'
    }

    try:
        response = requests.get(DOT_PARKING_API, params=params, timeout=60)
        response.raise_for_status()

        data = response.json()

        if 'features' not in data:
            logger.error("No features found in response")
            return []

        logger.info(f"Downloaded {len(data['features'])} parking facilities")
        return data['features']

    except Exception as e:
        logger.error(f"Error downloading DOT data: {e}")
        return []


def parse_dot_facility(feature):
    """
    Parse DOT parking facility from ArcGIS feature

    Args:
        feature: ArcGIS feature object

    Returns:
        Dictionary with facility data, or None if invalid
    """
    try:
        attrs = feature.get('attributes', {})
        geom = feature.get('geometry', {})

        # Extract coordinates (ArcGIS uses x/y for lng/lat)
        longitude = geom.get('x')
        latitude = geom.get('y')

        if not longitude or not latitude:
            return None

        # Extract facility information
        # Field names may vary - check actual dataset for correct names
        name = attrs.get('NAME') or attrs.get('FACILITY_NAME') or attrs.get('SITE_NAME')
        if not name:
            name = f"Truck Parking ({latitude:.4f}, {longitude:.4f})"

        # Determine facility type
        facility_type = "parking"  # Default to parking

        # Some DOT data may have type indicators
        dot_type = attrs.get('FACILITY_TYPE', '').lower()
        if 'rest area' in dot_type or 'rest stop' in dot_type:
            facility_type = "rest_area"
        elif 'truck stop' in dot_type or 'travel center' in dot_type:
            facility_type = "truck_stop"
        elif 'service plaza' in dot_type:
            facility_type = "service_plaza"

        # Extract parking spaces
        parking_spaces = attrs.get('PARKING_SPACES') or attrs.get('TRUCK_SPACES') or attrs.get('SPACES')
        if parking_spaces:
            try:
                parking_spaces = int(parking_spaces)
            except (ValueError, TypeError):
                parking_spaces = None

        # Build metadata
        metadata = {}

        # Store original DOT attributes that might be useful
        for key in ['FACILITY_ID', 'STATE', 'COUNTY', 'ROUTE', 'MILE_POST', 'AMENITIES']:
            if attrs.get(key):
                metadata[key.lower()] = attrs[key]

        return {
            'name': name,
            'type': facility_type,
            'latitude': float(latitude),
            'longitude': float(longitude),
            'parking_spaces': parking_spaces,
            'data_source': 'usdot_ntad',
            'data_sources': ['usdot_ntad'],
            'metadata': metadata if metadata else None,
            'dot_attributes': attrs  # Keep for duplicate detection
        }

    except Exception as e:
        logger.warning(f"Error parsing facility: {e}")
        return None


def find_duplicate(new_facility, existing_facilities):
    """
    Check if facility already exists in database

    A duplicate is defined as:
    - Within 0.1 miles (528 feet) of existing facility
    - Same or very similar name

    Args:
        new_facility: Facility dict to check
        existing_facilities: List of existing facilities from DB

    Returns:
        Existing facility dict if duplicate found, None otherwise
    """
    for existing in existing_facilities:
        distance = calculate_distance(
            new_facility['latitude'],
            new_facility['longitude'],
            existing['latitude'],
            existing['longitude']
        )

        # Within 0.1 miles = likely same facility
        if distance <= 0.1:
            # Simple name similarity check
            new_name = new_facility['name'].lower()
            existing_name = existing['name'].lower()

            # Check if names overlap significantly
            words_new = set(new_name.split())
            words_existing = set(existing_name.split())

            # If 50%+ of words match, it's likely the same facility
            if words_new and words_existing:
                overlap = len(words_new & words_existing)
                similarity = overlap / min(len(words_new), len(words_existing))

                if similarity > 0.5:
                    logger.info(f"Duplicate found: '{new_facility['name']}' matches '{existing['name']}' ({distance:.3f} miles)")
                    return existing

    return None


def merge_facility_data(existing, new_data):
    """
    Merge DOT data into existing facility

    Args:
        existing: Existing facility dict from DB
        new_data: New facility data from DOT

    Returns:
        Updated facility dict
    """
    updates = {}

    # Add DOT to data sources if not already present
    data_sources = existing.get('data_sources', [existing.get('data_source', 'manual')])
    if 'usdot_ntad' not in data_sources:
        data_sources.append('usdot_ntad')
        updates['data_sources'] = data_sources

    # Add parking spaces if not already set
    if new_data.get('parking_spaces') and not existing.get('parking_spaces'):
        updates['parking_spaces'] = new_data['parking_spaces']

    # Merge metadata
    existing_metadata = existing.get('metadata', {}) or {}
    new_metadata = new_data.get('metadata', {}) or {}

    if new_metadata:
        merged_metadata = {**existing_metadata, **new_metadata}
        updates['metadata'] = merged_metadata

    return updates


def import_parking_data():
    """
    Main import function

    Downloads DOT parking data and imports into database,
    handling duplicates intelligently.
    """
    logger.info("="*80)
    logger.info("U.S. DOT TRUCK PARKING DATA IMPORT")
    logger.info("="*80)

    # Download data
    features = download_dot_parking_data()

    if not features:
        logger.error("No data to import")
        return

    # Parse facilities
    logger.info("Parsing facilities...")
    parsed_facilities = []

    for feature in features:
        facility = parse_dot_facility(feature)
        if facility:
            parsed_facilities.append(facility)

    logger.info(f"Successfully parsed {len(parsed_facilities)} facilities")

    # Get existing facilities from database
    logger.info("Loading existing facilities from database...")
    try:
        result = db.from_("facilities").select("*").execute()
        existing_facilities = result.data
        logger.info(f"Found {len(existing_facilities)} existing facilities")
    except Exception as e:
        logger.error(f"Error loading existing facilities: {e}")
        return

    # Import with duplicate detection
    logger.info("Importing facilities...")

    stats = {
        'new': 0,
        'duplicate': 0,
        'merged': 0,
        'error': 0
    }

    for i, facility in enumerate(parsed_facilities, 1):
        if i % 100 == 0:
            logger.info(f"Progress: {i}/{len(parsed_facilities)}")

        try:
            # Check for duplicates
            duplicate = find_duplicate(facility, existing_facilities)

            if duplicate:
                # Merge data into existing facility
                updates = merge_facility_data(duplicate, facility)

                if updates:
                    db.from_("facilities").update(updates).eq("id", duplicate["id"]).execute()
                    stats['merged'] += 1
                else:
                    stats['duplicate'] += 1
            else:
                # Insert new facility
                # Remove temporary fields before insert
                facility_clean = {k: v for k, v in facility.items() if k != 'dot_attributes'}

                db.from_("facilities").insert(facility_clean).execute()
                stats['new'] += 1

        except Exception as e:
            logger.error(f"Error importing facility '{facility['name']}': {e}")
            stats['error'] += 1

    # Print summary
    logger.info("="*80)
    logger.info("IMPORT COMPLETE")
    logger.info("="*80)
    logger.info(f"New facilities added:     {stats['new']}")
    logger.info(f"Merged with existing:     {stats['merged']}")
    logger.info(f"Duplicates skipped:       {stats['duplicate']}")
    logger.info(f"Errors:                   {stats['error']}")
    logger.info(f"Total processed:          {len(parsed_facilities)}")

    # Verify database
    logger.info("\nVerifying database...")
    result = db.from_("facilities").select("*").eq("data_source", "usdot_ntad").execute()
    logger.info(f"Facilities from DOT in database: {len(result.data)}")

    # Sample facilities
    if result.data:
        logger.info("\nSample imported facilities:")
        for i, fac in enumerate(result.data[:5], 1):
            logger.info(f"{i}. {fac['name']} ({fac['type']})")
            logger.info(f"   Location: ({fac['latitude']:.4f}, {fac['longitude']:.4f})")
            if fac.get('parking_spaces'):
                logger.info(f"   Spaces: {fac['parking_spaces']}")


if __name__ == "__main__":
    logger.info("Starting DOT truck parking import...")
    logger.info("This will download data from catalog.data.gov and import into Supabase")

    response = input("\nContinue? (y/n): ")
    if response.lower() != 'y':
        logger.info("Import cancelled")
        sys.exit(0)

    import_parking_data()

    logger.info("\n" + "="*80)
    logger.info("Import script complete!")
    logger.info("="*80)
