# Truck Parking Public Data Integration

## Overview

The U.S. Department of Transportation provides **free, public truck parking data** through the National Transportation Atlas Database (NTAD). This can supplement our OpenStreetMap facility discovery with official government parking data.

---

## Data Source

### U.S. DOT - Truck Stop Parking Dataset

**Official Page:** https://catalog.data.gov/dataset/truck-stop-parking1

**Provider:** Federal Highway Administration (FHWA) / Bureau of Transportation Statistics (BTS)

**Authority:** Jason's Law Truck Parking Survey (MAP-21 requirement)

**Purpose:** "National priority on addressing the shortage of long-term parking for commercial motor vehicles"

---

## Dataset Details

### Available Formats

1. **ESRI Geodatabase** - GIS format
2. **ESRI Shapefile** - GIS format
3. **Spreadsheet** (CSV/Excel) - Easiest to import
4. **WFS (Web Feature Service)** - OGC-compliant API for real-time queries

### API Access

**ArcGIS REST Services Directory:**
- Complies with OGC WFS Map Service standard
- Allows programmatic queries for truck parking locations
- Geospatial filtering by bounding box, coordinates, etc.

### Data Freshness

- **Created:** July 1, 2017
- **Compiled:** April 9, 2019
- **Last Updated:** July 17, 2025 (metadata update)
- **Update Frequency:** As needed (not on fixed schedule)

**Note:** Data is ~8 years old for actual parking locations, but metadata was recently updated. This is **static infrastructure data** (parking lot locations don't change often).

---

## State TPIMS (Truck Parking Information Management Systems)

### Real-Time Parking Availability

Several states provide **live parking availability data** through TPIMS:

**States with TPIMS:**
- Iowa (41 facilities: rest areas, truck stops)
- Washington (I-5 corridor, expanding 2026)
- Minnesota (study in progress, 2026)
- Regional systems in development

**API Access:**
- GET requests with API token authentication
- Dynamic public feed (updates every 1-5 minutes)
- Static public feed (location data)
- Archive feed (historical data)

**Data Fields:**
- Facility location
- Total parking spaces
- Available spaces (real-time)
- Timestamp
- Facility type

**Documentation:** https://transportal.cee.wisc.edu/tpims/TPIMS_TruckParking_Data_Interface_V2.2.pdf

---

## Integration Plan

### Phase 1: Import Static U.S. DOT Parking Data ✅ (Recommended First)

**Goal:** Import ~2,000-5,000 truck parking locations from official government data

**Steps:**

1. **Download Dataset**
   ```bash
   # Download CSV/Shapefile from data.gov
   wget https://data-usdot.opendata.arcgis.com/datasets/truck-stop-parking.csv
   ```

2. **Parse and Import**
   ```python
   # scripts/import_dot_truck_parking.py
   import csv
   from supabase import create_client

   # Read CSV
   with open('truck-stop-parking.csv', 'r') as f:
       reader = csv.DictReader(f)
       for row in reader:
           # Insert into facilities table
           db.from_("facilities").insert({
               "name": row["NAME"],
               "type": "parking",  # New type for truck parking lots
               "latitude": float(row["LATITUDE"]),
               "longitude": float(row["LONGITUDE"]),
               "data_source": "usdot_ntad",
               "osm_id": None,
               "metadata": {
                   "parking_spaces": row.get("SPACES"),
                   "facility_type": row.get("FACILITY_TYPE"),
                   "amenities": row.get("AMENITIES")
               }
           }).execute()
   ```

3. **Add 'parking' Facility Type**
   ```sql
   -- Migration 007: Add 'parking' type
   ALTER TABLE facilities DROP CONSTRAINT IF EXISTS facilities_type_check;

   ALTER TABLE facilities ADD CONSTRAINT facilities_type_check
       CHECK (type IN ('truck_stop', 'rest_area', 'parking', 'service_plaza', 'weigh_station', 'warehouse'));
   ```

**Benefits:**
- ✅ Free, official government data
- ✅ One-time import, works offline
- ✅ Covers nationwide truck parking
- ✅ Complements OSM data (fills gaps)

**Limitations:**
- ❌ Static data (no real-time availability)
- ❌ May be outdated (2017 data)
- ❌ No duplicate detection with OSM (need to handle)

---

### Phase 2: State TPIMS Real-Time Availability (Future)

**Goal:** Show real-time parking availability for rest areas

**Implementation:**

```python
# app/services/tpims_api.py

import requests
from typing import Optional, Dict

TPIMS_API_BASE = "https://transportal.cee.wisc.edu/tpims/api/v1"
TPIMS_API_KEY = os.getenv("TPIMS_API_KEY")

def get_parking_availability(facility_id: str) -> Optional[Dict]:
    """
    Get real-time parking availability from state TPIMS

    Returns:
        {
            "total_spaces": 50,
            "available_spaces": 12,
            "last_updated": "2026-01-09T10:30:00Z",
            "status": "filling_up"  # available, filling_up, full
        }
    """
    try:
        response = requests.get(
            f"{TPIMS_API_BASE}/facilities/{facility_id}/availability",
            headers={"Authorization": f"Bearer {TPIMS_API_KEY}"},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "total_spaces": data["total_spaces"],
                "available_spaces": data["available_spaces"],
                "last_updated": data["timestamp"],
                "status": calculate_status(data["available_spaces"], data["total_spaces"])
            }
    except Exception as e:
        logger.warning(f"TPIMS API error: {e}")
        return None

def calculate_status(available: int, total: int) -> str:
    """Calculate parking status based on availability"""
    pct = (available / total) * 100
    if pct >= 50:
        return "available"
    elif pct >= 20:
        return "filling_up"
    else:
        return "full"
```

**Integration with Status Update:**

```python
# In app/routers/locations.py

facility_id, facility_name = find_nearby_facility(...)

# If facility supports real-time data, fetch availability
availability = None
if facility_id:
    facility = db.from_("facilities").select("*").eq("id", facility_id).single().execute()
    if facility.data.get("has_tpims"):
        availability = get_parking_availability(facility_id)

# Return in response
return {
    "location": {
        "facility_name": facility_name,
        "facility_id": facility_id,
        "parking_availability": availability  # NEW!
    }
}
```

**Frontend Display:**

```typescript
// Show parking availability if available
{location.parking_availability && (
  <View>
    <Text>
      {location.parking_availability.available_spaces} / {location.parking_availability.total_spaces} spaces available
    </Text>
    <ProgressBar
      value={location.parking_availability.available_spaces}
      max={location.parking_availability.total_spaces}
    />
  </View>
)}
```

---

### Phase 3: Duplicate Detection & Merging

**Problem:** DOT parking data may overlap with OSM truck stops

**Solution:** Detect and merge duplicates

```python
def is_duplicate(new_facility: Dict, existing_facilities: List[Dict]) -> Optional[str]:
    """
    Check if facility already exists (within 0.1 miles with similar name)

    Returns:
        facility_id if duplicate found, None otherwise
    """
    for existing in existing_facilities:
        distance = calculate_distance(
            new_facility["latitude"],
            new_facility["longitude"],
            existing["latitude"],
            existing["longitude"]
        )

        # Within 0.1 miles and similar name = duplicate
        if distance <= 0.1:
            name_similarity = difflib.SequenceMatcher(
                None,
                new_facility["name"].lower(),
                existing["name"].lower()
            ).ratio()

            if name_similarity > 0.7:
                return existing["id"]

    return None

# During import:
existing_facilities = db.from_("facilities").select("*").execute().data

for dot_facility in dot_data:
    duplicate_id = is_duplicate(dot_facility, existing_facilities)

    if duplicate_id:
        # Merge: Add DOT metadata to existing facility
        db.from_("facilities").update({
            "metadata": {
                **existing_metadata,
                "dot_parking_spaces": dot_facility["spaces"],
                "dot_facility_id": dot_facility["id"]
            },
            "data_sources": ["openstreetmap", "usdot_ntad"]  # Track both sources
        }).eq("id", duplicate_id).execute()
    else:
        # New facility: Insert
        db.from_("facilities").insert(dot_facility).execute()
```

---

## Data Quality Comparison

| Source | Coverage | Freshness | Real-Time | Quality |
|--------|----------|-----------|-----------|---------|
| **OpenStreetMap** | Excellent (truck stops, warehouses) | Variable | No | Good (community-maintained) |
| **U.S. DOT NTAD** | Good (official parking lots) | Static (2017) | No | High (government data) |
| **State TPIMS** | Limited (participating states) | Real-time | Yes | High (sensor data) |

**Best Approach:** Use all three sources
- OSM for discovery and general facilities
- DOT for official truck parking lots
- TPIMS for real-time availability (where available)

---

## Migration: Add Parking Type

```sql
-- migrations/007_add_parking_spaces.sql

-- Add 'parking' to facility types (if not already present)
ALTER TABLE facilities DROP CONSTRAINT IF EXISTS facilities_type_check;

ALTER TABLE facilities ADD CONSTRAINT facilities_type_check
    CHECK (type IN ('truck_stop', 'rest_area', 'parking', 'service_plaza', 'weigh_station', 'warehouse'));

-- Add parking metadata fields
ALTER TABLE facilities
ADD COLUMN IF NOT EXISTS parking_spaces INT,
ADD COLUMN IF NOT EXISTS has_tpims BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS tpims_facility_id VARCHAR(100);

-- Add composite index for location-based queries
CREATE INDEX IF NOT EXISTS idx_facilities_location
ON facilities (latitude, longitude);

-- Record migration
INSERT INTO migration_history (migration_name, description)
VALUES ('007_add_parking_spaces', 'Add truck parking spaces and TPIMS support')
ON CONFLICT (migration_name) DO NOTHING;
```

---

## Implementation Checklist

### Phase 1: Static DOT Data (1-2 hours)

- [ ] Download U.S. DOT truck parking CSV from data.gov
- [ ] Create migration 007 for parking type and metadata fields
- [ ] Apply migration to database
- [ ] Write import script (`scripts/import_dot_truck_parking.py`)
- [ ] Implement duplicate detection logic
- [ ] Run import script
- [ ] Verify data in database (check facility count, sample locations)
- [ ] Test facility discovery with new parking locations
- [ ] Update documentation

### Phase 2: TPIMS Real-Time (Future - 4-6 hours)

- [ ] Research TPIMS API authentication (need API key)
- [ ] Create `app/services/tpims_api.py`
- [ ] Add `has_tpims` flag to relevant facilities
- [ ] Integrate availability checks into status updates
- [ ] Update API responses to include parking availability
- [ ] Add frontend UI for parking availability display
- [ ] Monitor API rate limits and error rates

---

## Expected Results

### Before (Current State)
```json
{
  "facility_name": "Love's Travel Stop",
  "facility_type": "truck_stop"
}
```

### After Phase 1 (DOT Data)
```json
{
  "facility_name": "I-5 Northbound Rest Area Mile 245",
  "facility_type": "parking",
  "parking_spaces": 50,
  "data_source": "usdot_ntad"
}
```

### After Phase 2 (TPIMS)
```json
{
  "facility_name": "I-5 Northbound Rest Area Mile 245",
  "facility_type": "parking",
  "parking_availability": {
    "total_spaces": 50,
    "available_spaces": 12,
    "status": "filling_up",
    "last_updated": "2026-01-09T10:30:00Z"
  }
}
```

---

## Cost & Performance

### U.S. DOT NTAD Data
- **Cost:** FREE ✅
- **One-time import:** ~2,000-5,000 facilities
- **Database size:** ~5MB additional
- **Query performance:** No impact (same as OSM data)

### TPIMS API
- **Cost:** FREE for approved users (need API key)
- **Rate limits:** Unknown (need to contact state DOTs)
- **API latency:** ~200-500ms per facility
- **Recommended:** Cache availability for 5 minutes

---

## Sources

1. [U.S. DOT Truck Stop Parking Dataset](https://catalog.data.gov/dataset/truck-stop-parking1) - Official government parking data
2. [TPIMS Data Interface Documentation](https://transportal.cee.wisc.edu/tpims/TPIMS_TruckParking_Data_Interface_V2.2.pdf) - Real-time API specs
3. [Washington State TPIMS Launch](https://washingtonstatestandard.com/briefs/new-tools-will-help-truckers-find-rest-area-parking-on-i-5-in-washington/) - State implementation
4. [FHWA Truck Parking Technology](https://ops.fhwa.dot.gov/Freight/infrastructure/truck_parking/coalition/technology_data/product/best_practices.htm) - Best practices
5. [FMCSA API Access](https://mobile.fmcsa.dot.gov/QCDevsite/docs/apiAccess) - Federal API documentation

---

## Current Status (January 2026)

### DOT Data Portal Update

**Issue**: The U.S. DOT data portal URLs have changed or are temporarily unavailable
- Previous ArcGIS endpoints are returning 404 errors
- Direct CSV/GeoJSON downloads not accessible
- Data portal may be undergoing migration or restructuring

**Alternative Approaches**:

1. **Manual Download** (If needed)
   - Visit https://geodata.bts.gov/datasets/truck-stop-parking
   - Download dataset manually as CSV/Shapefile when available
   - Run import script with local file

2. **OpenStreetMap** (Already Implemented ✅)
   - Our existing OSM discovery already captures rest areas and truck stops
   - OSM tags include: `highway=rest_area`, `highway=services`, `amenity=fuel`
   - On-demand discovery works nationwide with no API dependency
   - Migration 007 completed - supports parking type

3. **State DOT APIs** (Future Enhancement)
   - Contact state DOTs directly for TPIMS API access
   - Participating states provide real-time availability data
   - Requires individual partnerships and API keys

---

## Recommendation (Updated)

**Current Approach: OSM Discovery is Sufficient ✅**
- Already implemented and working
- Covers truck stops, rest areas, warehouses nationwide
- No external API dependencies or data portals
- Automatic discovery as drivers use the app
- Free, no rate limits, no maintenance overhead

**Future: Add DOT Data as Enhancement**
- Monitor https://geodata.bts.gov for portal restoration
- Can bulk import thousands of official parking facilities
- Complements OSM with government-verified data
- Not critical for MVP launch

**Conclusion**: The current OSM-based facility discovery provides excellent coverage. DOT parking data integration remains available as a Phase 2 enhancement once the data portal becomes accessible.
