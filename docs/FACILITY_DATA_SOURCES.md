# Building the Facility Database: Free Data Sources

## The Problem

**We need a comprehensive database of:**
- Truck stops (Love's, Pilot, TA, etc.)
- Rest areas (state/federal DOT)
- Truck parking areas
- Distribution centers & warehouses
- Weigh stations

**Without this data, we can only show coordinates, which is poor UX.**

---

## Strategy Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   Multi-Source Data Strategy                     │
└─────────────────────────────────────────────────────────────────┘

1. OpenStreetMap (OSM)        ← Best free source, comprehensive
2. DOT/Government Data         ← Official rest areas, weigh stations
3. Truck Stop Chain APIs       ← Direct from brands (Love's, Pilot)
4. User Submissions            ← Crowd-sourced additions
5. Manual Curation             ← Fill gaps with research

                    ↓
            ┌──────────────┐
            │  PostgreSQL  │
            │  facilities  │
            │    table     │
            └──────────────┘
```

---

## 1. OpenStreetMap (OSM) - FREE & COMPREHENSIVE

**Best source for truck-related POIs**

### What OSM Has:
- ✅ Truck stops (tagged as `amenity=fuel` + `hgv=yes`)
- ✅ Rest areas (`highway=rest_area`)
- ✅ Parking areas (`amenity=parking` + `hgv=yes`)
- ✅ Service plazas (`highway=services`)
- ✅ Exact coordinates, names, addresses
- ✅ Amenities (showers, restaurants, etc.)

### How to Get OSM Data

#### Option A: Overpass API (Query on Demand)

```python
# Example: Get all truck stops in California
import requests

overpass_url = "http://overpass-api.de/api/interpreter"
overpass_query = """
[out:json][timeout:60];
area["ISO3166-1"="US"]["name"="California"]->.searchArea;
(
  // Truck stops
  node["amenity"="fuel"]["hgv"="yes"](area.searchArea);
  way["amenity"="fuel"]["hgv"="yes"](area.searchArea);

  // Rest areas
  node["highway"="rest_area"](area.searchArea);
  way["highway"="rest_area"](area.searchArea);

  // Truck parking
  node["amenity"="parking"]["hgv"="yes"](area.searchArea);
  way["amenity"="parking"]["hgv"="yes"](area.searchArea);

  // Service plazas
  node["highway"="services"](area.searchArea);
  way["highway"="services"](area.searchArea);
);
out center;
"""

response = requests.post(overpass_url, data={"data": overpass_query})
data = response.json()

# Process results
for element in data["elements"]:
    if element["type"] == "node":
        lat = element["lat"]
        lon = element["lon"]
    else:  # way
        lat = element["center"]["lat"]
        lon = element["center"]["lon"]

    name = element.get("tags", {}).get("name", "Unknown")
    amenities = element.get("tags", {})

    print(f"{name}: {lat}, {lon}")
```

#### Option B: Download Regional Extract (Faster)

```bash
# Download California extract from Geofabrik
wget https://download.geofabrik.de/north-america/us/california-latest.osm.pbf

# Use osmosis or osm2pgsql to filter truck-related features
osmosis --read-pbf california-latest.osm.pbf \
  --tf accept-nodes amenity=fuel,parking \
  --tf accept-ways amenity=fuel,parking \
  --tf accept-relations amenity=fuel,parking \
  --write-xml california-truck-stops.osm
```

#### Option C: Use Existing Python Library

```bash
pip install osmnx overpy
```

```python
import overpy

api = overpy.Overpass()

# Query truck stops in a bounding box
result = api.query("""
    [out:json];
    (
      node["amenity"="fuel"]["hgv"="yes"](36.0,-121.0,37.0,-119.0);
      way["amenity"="fuel"]["hgv"="yes"](36.0,-121.0,37.0,-119.0);
    );
    out center;
""")

for node in result.nodes:
    print(f"{node.tags.get('name', 'Unknown')}: {node.lat}, {node.lon}")
```

### Import Script for OSM Data

```python
# scripts/import_osm_facilities.py
import requests
from app.database import get_db_admin
import geohash as gh

def import_truck_stops_from_osm(state="California"):
    """Import truck stops from OpenStreetMap"""

    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:180];
    area["ISO3166-1"="US"]["name"="{state}"]->.searchArea;
    (
      node["amenity"="fuel"]["hgv"="yes"](area.searchArea);
      way["amenity"="fuel"]["hgv"="yes"](area.searchArea);
      node["highway"="rest_area"](area.searchArea);
      way["highway"="rest_area"](area.searchArea);
    );
    out center;
    """

    response = requests.post(overpass_url, data={"data": query})
    data = response.json()

    db = get_db_admin()
    facilities = []

    for element in data["elements"]:
        tags = element.get("tags", {})

        # Get coordinates
        if element["type"] == "node":
            lat, lon = element["lat"], element["lon"]
        else:
            lat = element["center"]["lat"]
            lon = element["center"]["lon"]

        # Determine facility type
        if tags.get("highway") == "rest_area":
            fac_type = "rest_area"
        elif tags.get("amenity") == "fuel":
            fac_type = "truck_stop"
        else:
            fac_type = "parking"

        # Extract name and details
        name = tags.get("name") or tags.get("operator") or "Unnamed Facility"
        brand = tags.get("brand") or tags.get("operator")

        # Parse amenities
        amenities = {}
        if tags.get("toilets") == "yes":
            amenities["restrooms"] = True
        if tags.get("shower") == "yes" or "shower" in tags.get("description", "").lower():
            amenities["showers"] = True
        if tags.get("restaurant") == "yes":
            amenities["restaurant"] = True

        facility = {
            "name": name,
            "type": fac_type,
            "latitude": lat,
            "longitude": lon,
            "address": tags.get("addr:full") or tags.get("addr:street"),
            "city": tags.get("addr:city"),
            "state": tags.get("addr:state"),
            "zip_code": tags.get("addr:postcode"),
            "brand": brand,
            "amenities": amenities,
            "is_open_24h": tags.get("opening_hours") == "24/7",
            "geohash": gh.encode(lat, lon, precision=12)
        }

        facilities.append(facility)

    # Bulk insert
    if facilities:
        db.from_("facilities").insert(facilities).execute()
        print(f"Imported {len(facilities)} facilities from OSM")

    return facilities

# Run it
if __name__ == "__main__":
    import_truck_stops_from_osm("California")
```

---

## 2. Government/DOT Data - OFFICIAL & FREE

### Federal Highway Administration (FHWA)

**Rest Areas Dataset:**
- URL: https://data.transportation.gov/
- Search: "Rest Areas", "Truck Parking"
- Format: CSV, JSON
- Coverage: All US states

**Example:**
```bash
# Download National Rest Areas dataset
wget https://www.fhwa.dot.gov/pressroom/fhwa2015/trucking_parking_facilities.csv

# Import CSV
python scripts/import_csv_facilities.py trucking_parking_facilities.csv
```

### State DOT Websites

**California DOT:**
- Rest areas: https://dot.ca.gov/travel/rest-areas
- Truck parking: https://dot.ca.gov/programs/traffic-operations/trucks

**Texas DOT:**
- https://www.txdot.gov/driver/share-road/trucks.html

**Florida DOT:**
- https://www.fdot.gov/traffic/its/projects-deploy/truckparkingavailabilitysystem.shtm

### Import Script for CSV Data

```python
# scripts/import_csv_facilities.py
import csv
import sys
from app.database import get_db_admin
import geohash as gh

def import_from_csv(csv_file):
    """Import facilities from CSV"""
    db = get_db_admin()
    facilities = []

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Adapt field names to match your CSV
            facility = {
                "name": row.get("Name") or row.get("Facility_Name"),
                "type": "rest_area",  # Adjust based on data
                "latitude": float(row["Latitude"]),
                "longitude": float(row["Longitude"]),
                "address": row.get("Address"),
                "city": row.get("City"),
                "state": row.get("State"),
                "zip_code": row.get("ZIP"),
                "parking_spaces": int(row["Parking_Spaces"]) if row.get("Parking_Spaces") else None,
                "geohash": gh.encode(float(row["Latitude"]), float(row["Longitude"]), precision=12)
            }
            facilities.append(facility)

    if facilities:
        db.from_("facilities").insert(facilities).execute()
        print(f"Imported {len(facilities)} facilities from CSV")

if __name__ == "__main__":
    import_from_csv(sys.argv[1])
```

---

## 3. Truck Stop Chain APIs/Websites

### Love's Travel Stops
- **Store Locator API**: https://www.loves.com/locations (might have API)
- **Scraping Alternative**: Use their store locator page
- **~500 locations nationwide**

### Pilot Flying J
- **Store Locator**: https://pilotflyingj.com/store-locator
- **~750 locations nationwide**

### TA/Petro
- **Store Locator**: https://www.ta-petro.com/location-finder
- **~270 locations nationwide**

### Web Scraping Example

```python
# scripts/scrape_loves_locations.py
import requests
from bs4 import BeautifulSoup
from app.database import get_db_admin
import geohash as gh

def scrape_loves_locations():
    """Scrape Love's Travel Stops locations"""
    # Note: Respect robots.txt and rate limits

    url = "https://www.loves.com/locations"
    # This is example code - actual implementation depends on their site structure

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    facilities = []
    # Parse store location data from page
    # ... (implementation depends on site structure)

    return facilities
```

**Better Approach:** Contact chains directly for partnership/data access

---

## 4. Commercial APIs (Some Free Tiers)

### Google Places API
- **Pros**: Comprehensive, regularly updated
- **Cons**: $$ after free tier (200 requests/day)
- **Good for**: Filling gaps, validating data

```python
import googlemaps

gmaps = googlemaps.Client(key='YOUR_API_KEY')

# Search for truck stops near a location
places = gmaps.places_nearby(
    location=(36.7783, -119.4179),
    radius=50000,  # 50km
    keyword='truck stop',
    type='gas_station'
)

for place in places['results']:
    print(place['name'], place['geometry']['location'])
```

### Yelp Fusion API
- **Free tier**: 5000 requests/day
- **Good for**: Truck stops, rest areas
- **Has**: Reviews, ratings, photos

```python
import requests

headers = {'Authorization': 'Bearer YOUR_API_KEY'}
params = {
    'term': 'truck stop',
    'latitude': 36.7783,
    'longitude': -119.4179,
    'radius': 40000,  # meters
    'limit': 50
}

response = requests.get(
    'https://api.yelp.com/v3/businesses/search',
    headers=headers,
    params=params
)

for business in response.json()['businesses']:
    print(business['name'], business['location'])
```

---

## 5. User Submissions (Crowd-Sourcing)

**Allow drivers to add missing facilities:**

```typescript
// Frontend component
const AddFacilityForm = () => {
  const [name, setName] = useState('');
  const currentLocation = useCurrentLocation();

  const handleSubmit = async () => {
    await fetch('/api/v1/facilities', {
      method: 'POST',
      body: JSON.stringify({
        name,
        type: 'truck_stop',
        latitude: currentLocation.lat,
        longitude: currentLocation.lng,
        submitted_by_driver: true
      })
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        placeholder="Facility name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <select name="type">
        <option value="truck_stop">Truck Stop</option>
        <option value="parking">Parking Area</option>
        <option value="rest_area">Rest Area</option>
      </select>
      <button type="submit">Add Facility</button>
    </form>
  );
};
```

**Backend endpoint:**
```python
# app/routers/facilities.py
@router.post("/facilities")
async def submit_facility(
    facility: FacilityCreate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Allow drivers to submit new facilities"""
    facility_data = facility.model_dump()
    facility_data["submitted_by"] = driver["id"]
    facility_data["verified"] = False  # Requires admin approval

    result = db.from_("facilities").insert(facility_data).execute()
    return {"success": True, "id": result.data[0]["id"]}
```

---

## 6. Recommended Implementation Plan

### Phase 1: Initial Import (Week 1)
```bash
# 1. Import California OSM data
python scripts/import_osm_facilities.py California

# 2. Import federal rest areas CSV
python scripts/import_csv_facilities.py rest_areas_national.csv

# Expected result: ~2,000-3,000 facilities in California
```

### Phase 2: Expand Coverage (Week 2)
```bash
# Import all major states
for state in Texas Florida Arizona Nevada Oregon Washington; do
    python scripts/import_osm_facilities.py $state
done

# Expected result: ~10,000-15,000 facilities nationwide
```

### Phase 3: Add Chain Data (Week 3)
- Contact Love's, Pilot, TA for partnership
- Or use their public locators (with permission)
- Expected: +2,000 major truck stops

### Phase 4: Enable User Submissions (Ongoing)
- Launch "Add Missing Facility" feature
- Review and approve submissions
- Expected: +50-100/month from drivers

---

## 7. Complete Import Script

```python
# scripts/import_all_facilities.py
"""
Master script to import facilities from all sources
"""

import logging
from typing import List, Dict
import requests
import csv
import geohash as gh
from app.database import get_db_admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FacilityImporter:
    def __init__(self):
        self.db = get_db_admin()
        self.imported_count = 0

    def import_from_osm(self, state: str):
        """Import from OpenStreetMap"""
        logger.info(f"Importing OSM data for {state}...")

        overpass_url = "http://overpass-api.de/api/interpreter"
        query = f"""
        [out:json][timeout:180];
        area["ISO3166-1"="US"]["name"="{state}"]->.searchArea;
        (
          node["amenity"="fuel"]["hgv"="yes"](area.searchArea);
          way["amenity"="fuel"]["hgv"="yes"](area.searchArea);
          node["highway"="rest_area"](area.searchArea);
          way["highway"="rest_area"](area.searchArea);
          node["amenity"="parking"]["hgv"="yes"](area.searchArea);
          way["amenity"="parking"]["hgv"="yes"](area.searchArea);
        );
        out center;
        """

        try:
            response = requests.post(overpass_url, data={"data": query}, timeout=300)
            data = response.json()

            facilities = []
            for element in data["elements"]:
                facility = self._parse_osm_element(element)
                if facility:
                    facilities.append(facility)

            if facilities:
                # Check for duplicates before inserting
                unique_facilities = self._deduplicate(facilities)
                self.db.from_("facilities").insert(unique_facilities).execute()
                self.imported_count += len(unique_facilities)
                logger.info(f"Imported {len(unique_facilities)} facilities from OSM ({state})")

        except Exception as e:
            logger.error(f"Error importing OSM data: {e}")

    def import_from_csv(self, csv_path: str, field_mapping: Dict[str, str]):
        """Import from CSV with custom field mapping"""
        logger.info(f"Importing from CSV: {csv_path}")

        facilities = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                facility = {
                    "name": row[field_mapping["name"]],
                    "type": field_mapping.get("type", "rest_area"),
                    "latitude": float(row[field_mapping["latitude"]]),
                    "longitude": float(row[field_mapping["longitude"]]),
                    "address": row.get(field_mapping.get("address")),
                    "city": row.get(field_mapping.get("city")),
                    "state": row.get(field_mapping.get("state")),
                    "geohash": gh.encode(
                        float(row[field_mapping["latitude"]]),
                        float(row[field_mapping["longitude"]]),
                        precision=12
                    )
                }
                facilities.append(facility)

        if facilities:
            unique_facilities = self._deduplicate(facilities)
            self.db.from_("facilities").insert(unique_facilities).execute()
            self.imported_count += len(unique_facilities)
            logger.info(f"Imported {len(unique_facilities)} facilities from CSV")

    def _parse_osm_element(self, element: Dict) -> Dict:
        """Parse OSM element into facility dict"""
        tags = element.get("tags", {})

        if element["type"] == "node":
            lat, lon = element["lat"], element["lon"]
        else:
            lat = element["center"]["lat"]
            lon = element["center"]["lon"]

        # Determine type
        if tags.get("highway") == "rest_area":
            fac_type = "rest_area"
        elif tags.get("amenity") == "fuel":
            fac_type = "truck_stop"
        elif tags.get("amenity") == "parking":
            fac_type = "parking"
        else:
            return None

        return {
            "name": tags.get("name") or tags.get("operator") or f"Unnamed {fac_type}",
            "type": fac_type,
            "latitude": lat,
            "longitude": lon,
            "address": tags.get("addr:street"),
            "city": tags.get("addr:city"),
            "state": tags.get("addr:state"),
            "zip_code": tags.get("addr:postcode"),
            "brand": tags.get("brand") or tags.get("operator"),
            "amenities": {
                "restrooms": tags.get("toilets") == "yes",
                "showers": tags.get("shower") == "yes",
                "restaurant": tags.get("restaurant") == "yes"
            },
            "is_open_24h": tags.get("opening_hours") == "24/7",
            "geohash": gh.encode(lat, lon, precision=12)
        }

    def _deduplicate(self, facilities: List[Dict]) -> List[Dict]:
        """Remove duplicates based on proximity"""
        unique = []
        for facility in facilities:
            # Check if facility already exists within 100 meters
            existing = self.db.from_("facilities") \
                .select("id") \
                .gte("latitude", facility["latitude"] - 0.001) \
                .lte("latitude", facility["latitude"] + 0.001) \
                .gte("longitude", facility["longitude"] - 0.001) \
                .lte("longitude", facility["longitude"] + 0.001) \
                .execute()

            if not existing.data:
                unique.append(facility)

        return unique

# Main execution
if __name__ == "__main__":
    importer = FacilityImporter()

    # Import from OSM for major trucking states
    states = ["California", "Texas", "Florida", "Arizona", "Nevada",
              "Oregon", "Washington", "Georgia", "Tennessee", "Ohio"]

    for state in states:
        importer.import_from_osm(state)

    # Import from CSV if available
    # importer.import_from_csv(
    #     "data/rest_areas.csv",
    #     field_mapping={
    #         "name": "Name",
    #         "latitude": "Latitude",
    #         "longitude": "Longitude",
    #         "city": "City",
    #         "state": "State"
    #     }
    # )

    logger.info(f"Total imported: {importer.imported_count} facilities")
```

---

## 8. Running the Import

```bash
# Setup
cd finddriverbackend
source venv/bin/activate
pip install overpy geohash2

# Run import
python scripts/import_all_facilities.py

# Expected output:
# INFO: Importing OSM data for California...
# INFO: Imported 2,347 facilities from OSM (California)
# INFO: Importing OSM data for Texas...
# INFO: Imported 1,892 facilities from OSM (Texas)
# ...
# INFO: Total imported: 12,451 facilities
```

---

## Summary

### Best Free Sources (Ranked):
1. **OpenStreetMap** - Most comprehensive, free, regularly updated
2. **Federal DOT Data** - Official rest areas, reliable
3. **State DOT Websites** - Local truck parking data
4. **User Submissions** - Fill gaps, keep data fresh

### Implementation Cost:
- **Time**: 1-2 weeks for initial import
- **Money**: $0 (all free sources)
- **Maintenance**: Periodic re-imports (monthly/quarterly)

### Expected Coverage:
- **After Phase 1**: 2,000-3,000 facilities (California)
- **After Phase 2**: 10,000-15,000 facilities (nationwide)
- **After Phase 3**: 12,000-17,000 facilities (with chains)
- **After 6 months**: 15,000-20,000 (with user submissions)

**Start with OpenStreetMap - it's the best free source and covers most of what you need!**
