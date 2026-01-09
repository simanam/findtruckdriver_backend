# Warehouse & Shipper Support

## Overview

The facility discovery system now supports **warehouses, distribution centers, and shippers** in addition to truck stops and rest areas.

## What Changed

### 1. Expanded OSM Query

**Added warehouse-related tags:**
```overpass
// Warehouses and distribution centers
node["building"="warehouse"]
way["building"="warehouse"]
node["building"="industrial"]
way["building"="industrial"]
node["industrial"="distribution"]
way["industrial"="distribution"]

// Commercial/retail buildings with names (Walmart DC, Target DC, etc.)
node["building"="retail"]["name"]
way["building"="retail"]["name"]
node["building"="commercial"]["name"]
way["building"="commercial"]["name"]
```

### 2. New Facility Type: `warehouse`

**Database migration applied:**
- Migration 006 adds `warehouse` to valid facility types
- Facilities table now supports: `truck_stop`, `rest_area`, `parking`, `service_plaza`, `weigh_station`, `warehouse`

### 3. Updated Parsing Logic

**Facility type detection:**
```python
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
```

## How It Works

**When a driver reports their location at a warehouse:**

```
1. Driver at (34.0633, -117.6509) - Inland Empire warehouse district
   ↓
2. System checks local DB → No facility found
   ↓
3. Triggers OSM discovery (5-mile radius)
   ↓
4. OSM query includes:
   - Truck stops (Love's, Pilot, TA, etc.)
   - Rest areas
   - Warehouses (building=warehouse)
   - Distribution centers (industrial=distribution)
   - Named commercial buildings (Walmart DC, Target DC, etc.)
   ↓
5. Imports all discovered facilities
   ↓
6. Returns facility name to driver
```

## Example Use Cases

### Use Case 1: Driver at Walmart Distribution Center

```json
POST /api/v1/locations/status/update
{
  "status": "waiting",
  "latitude": 34.063,
  "longitude": -117.651
}

Response:
{
  "status": "waiting",
  "location": {
    "facility_name": "Walmart Distribution Center"  ← Discovered from OSM!
  },
  "follow_up_question": {
    "text": "How's it looking?",
    "subtext": "Walmart Distribution Center",
    ...
  }
}
```

### Use Case 2: Driver at Industrial Warehouse

```json
{
  "status": "waiting",
  "facility_name": "Industrial Warehouse (34.0630, -117.6510)"  ← Generic name if no OSM name
}
```

## OSM Data Quality

### Challenges

**Issue:** OSM warehouse data is often **unnamed or poorly tagged**

**Example:**
- ✅ Good: `name="Walmart Distribution Center #6345"`
- ❌ Poor: `building=warehouse` (no name)
- ❌ Missing: Many warehouses not mapped at all

### Solution: User Submissions

Drivers can report facility names for unmapped/unnamed locations:

```python
@router.post("/facilities/submit")
async def submit_facility_name(
    facility_name: str,
    latitude: float,
    longitude: float,
    driver: dict = Depends(get_current_driver)
):
    """Allow drivers to report facility names"""

    # Create user-submitted facility
    db.from_("facilities").insert({
        "name": facility_name,
        "type": "warehouse",
        "latitude": latitude,
        "longitude": longitude,
        "data_source": "user_submitted",
        "submitted_by": driver["id"],
        "verified": False  # Requires verification
    }).execute()
```

## Performance Considerations

### Query Complexity

**Concern:** Expanded query (truck stops + warehouses) is more complex and may timeout more often

**Impact:**
- Truck stops only: ~10-20 results per 5-mile radius
- With warehouses: ~50-100 results per 5-mile radius (in industrial areas)
- Query time: 2-4 seconds → 5-8 seconds
- Timeout risk: Low → Medium

**Mitigation:**
1. **Reduce query radius** in warehouse-heavy areas (5 miles → 2 miles)
2. **Background processing** - make discovery async
3. **Selective queries** - only query warehouses if driver status is "waiting" (not "rolling")

### Database Growth

**Expected growth:**
- Without warehouses: ~2,000-3,000 facilities in first month
- With warehouses: ~5,000-8,000 facilities in first month

**Storage impact:** Minimal (each facility ~1KB = 8MB total)

## Configuration

### Query Modes

You can configure discovery behavior based on driver status:

```python
# In app/services/facility_discovery.py

def find_nearby_facility(
    db: Client,
    latitude: float,
    longitude: float,
    max_distance_miles: float = 0.3,
    discover_if_missing: bool = True,
    include_warehouses: bool = True  # ← New parameter
):
    """
    include_warehouses: Set to False for faster queries (truck stops only)
    """
    # ... discovery logic
```

**Usage:**
```python
# When driver is rolling (fast query needed)
facility_id, facility_name = find_nearby_facility(
    db, lat, lng,
    include_warehouses=False  # Skip warehouses for speed
)

# When driver is waiting/parked (comprehensive search)
facility_id, facility_name = find_nearby_facility(
    db, lat, lng,
    include_warehouses=True  # Include warehouses
)
```

## Testing

### Test Script: `scripts/test_warehouse_discovery.py`

```bash
source venv/bin/activate
python scripts/test_warehouse_discovery.py

# Tests warehouse discovery in Ontario, CA (Inland Empire)
# Expected: Discover warehouses, distribution centers, truck stops
```

### Known Test Locations

| Location | Expected Facilities |
|----------|---------------------|
| Ontario, CA (Inland Empire) | Many warehouses, 1-2 truck stops |
| Tracy, CA (I-580 & I-205) | Warehouses + truck stops |
| Dallas, TX (I-35 corridor) | Distribution centers + truck stops |

## Limitations

1. **OSM Data Gaps**
   - Many warehouses not mapped
   - Unnamed warehouses ("Warehouse (lat, lng)")
   - No shipper/receiver distinction

2. **Query Timeouts**
   - Complex queries may timeout in warehouse-heavy areas
   - Fallback: graceful handling, retry on next driver

3. **False Positives**
   - Some commercial buildings may not be relevant to truckers
   - Can filter by adding exclusion list

## Future Enhancements

### Phase 1: User Submissions ✅ (Planned)
Allow drivers to name facilities

### Phase 2: Crowd-Sourced Ratings
- "How's the wait?" for warehouses
- Detention pay tracking per facility
- Dock door count, parking availability

### Phase 3: External Data Sources
- Import from:
  - CargoNet (theft-prone locations)
  - FMCSA (registered motor carriers)
  - State DOT (weigh stations, inspection sites)

### Phase 4: Facility Verification
- Admin dashboard to verify user submissions
- Merge duplicate facilities
- Flag inactive/closed locations

## Summary

**Status: ✅ WAREHOUSE SUPPORT ENABLED**

**Capabilities:**
- ✅ Discovers warehouses from OSM
- ✅ Discovers distribution centers
- ✅ Discovers named commercial buildings
- ✅ Falls back to truck stops if no warehouse found
- ✅ Supports "warehouse" facility type in database

**Next Steps:**
1. Monitor query timeout rates
2. Implement user facility submissions
3. Add warehouse-specific follow-up questions ("Getting loaded?", "At the dock?")

**Impact:**
Drivers waiting at shippers/receivers will now see facility names in their status updates and follow-up questions, making the app more useful for tracking detention time and facility performance.
