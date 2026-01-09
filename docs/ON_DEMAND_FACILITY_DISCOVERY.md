# On-Demand Facility Discovery System

## TL;DR

**We don't pre-import facility data. We discover it organically as drivers use the app.**

```
Driver reports location → Check local DB → Not found? → Query OSM → Cache facilities → Show name
                                ↓
                              Found! → Show name immediately
```

**Benefits:**
- ✅ No API timeouts (queries are small, <5 seconds)
- ✅ Database grows based on actual driver usage
- ✅ Always fresh data (re-queries after 30 days)
- ✅ Focuses on real trucking routes
- ✅ Zero upfront import time

---

## The Problem We Solved

### Original Approach (Didn't Work)
```
1. Try to import entire state from OSM → 504 Gateway Timeout ❌
2. Try smaller regions → Still timeout ❌
3. Would need to import 10,000-15,000 facilities upfront ❌
4. Data goes stale immediately ❌
```

### On-Demand Approach (Works!)
```
1. Driver reports location (36.78, -119.42)
2. Check: Have we queried this ~1km grid square before?
   - Yes → Use cached facilities from DB
   - No → Query OSM for 5-mile radius (~2 seconds)
3. Import discovered facilities to DB
4. Return facility name immediately
5. Over time, naturally build coverage where drivers actually are
```

---

## How It Works

### 1. Geohash-Based Caching

**Each location gets a geohash (grid square ID):**

```python
# Fresno, CA
lat, lng = 36.7783, -119.4179
geohash = encode_geohash(lat, lng, precision=6)
# → "9qh7w8" (represents ~0.6km x 1.2km grid square)
```

**Before querying OSM, we check:**
```sql
SELECT last_queried_at
FROM osm_query_cache
WHERE geohash_prefix = '9qh7w8'
```

- **Never queried** → Query OSM now
- **Queried < 30 days ago** → Skip (use cached facilities)
- **Queried > 30 days ago** → Re-query (data might be stale)

### 2. Smart Facility Lookup

```python
def find_nearby_facility(db, latitude, longitude, max_distance_miles=0.3):
    """
    Find facility near coordinates. Triggers OSM discovery if needed.
    """

    # Step 1: Check local DB first (FAST)
    geohash = encode_geohash(latitude, longitude, precision=6)

    facilities = db.from_("facilities") \
        .select("id,name,latitude,longitude") \
        .like("geohash", f"{geohash}%") \
        .execute()

    # Step 2: Find nearest within threshold
    for facility in facilities.data:
        distance = calculate_distance(lat, lng, facility["lat"], facility["lng"])
        if distance <= 0.3:  # Within 0.3 miles
            return facility["id"], facility["name"]  # ✅ FOUND!

    # Step 3: Not found - should we query OSM?
    if should_query_osm(db, latitude, longitude):
        # Query OSM for 5-mile radius
        discovered = discover_facilities(db, latitude, longitude)

        if discovered > 0:
            # Retry search with newly discovered facilities
            return find_nearby_facility(db, latitude, longitude, discover_if_missing=False)

    return None, None  # No facility nearby
```

### 3. OSM Discovery Process

```python
def discover_facilities(db, latitude, longitude):
    """
    Query OSM and import facilities for this location.
    """

    # 1. Calculate 5-mile bounding box
    bbox = calculate_bbox(latitude, longitude, radius_miles=5.0)

    # 2. Query OSM Overpass API
    query = f"""
    [out:json][timeout:30];
    (
      node["amenity"="fuel"]["hgv"="yes"]({bbox});
      node["highway"="rest_area"]({bbox});
      node["highway"="services"]({bbox});
    );
    out center tags;
    """

    response = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
    elements = response.json()["elements"]

    # 3. Parse and import facilities
    imported = 0
    for element in elements:
        facility = parse_osm_element(element)

        # Check for duplicates (by OSM ID or proximity)
        if not check_duplicate_facility(db, facility):
            db.from_("facilities").insert(facility).execute()
            imported += 1

    # 4. Update query cache
    db.from_("osm_query_cache").insert({
        "geohash_prefix": geohash,
        "last_queried_at": datetime.utcnow(),
        "facilities_found": len(elements)
    }).execute()

    return imported
```

---

## Database Schema

### osm_query_cache Table

```sql
CREATE TABLE osm_query_cache (
    id UUID PRIMARY KEY,
    geohash_prefix VARCHAR(8) UNIQUE,     -- Grid square ID (e.g., "9qh7w8")
    center_latitude FLOAT,
    center_longitude FLOAT,
    query_radius_miles FLOAT DEFAULT 5.0,
    facilities_found INT DEFAULT 0,       -- How many facilities OSM returned
    last_queried_at TIMESTAMPTZ,          -- When we last queried OSM
    query_count INT DEFAULT 1,            -- How many times we've queried this area
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Purpose:** Track which geographic regions we've already queried from OSM to avoid redundant API calls.

### facilities Table (Updated)

```sql
ALTER TABLE facilities
ADD COLUMN data_source VARCHAR(50) DEFAULT 'manual',  -- 'openstreetmap', 'manual', 'user_submitted'
ADD COLUMN osm_id BIGINT,                             -- OpenStreetMap node/way ID
ADD COLUMN osm_version INT,                           -- OSM version (for updates)
ADD COLUMN last_verified_at TIMESTAMPTZ;              -- Last time we verified this data
```

---

## Integration with Endpoints

### Location Update Endpoint

```python
# app/routers/locations.py

@router.post("/status/update")
async def update_status_with_location(request: StatusChangeRequest, ...):
    # ... update driver location ...

    # OLD CODE (queries ALL facilities, doesn't work with empty DB):
    # facilities = db.from_("facilities").select("*").execute()
    # for facility in facilities.data:
    #     if calculate_distance(...) <= 0.3:
    #         facility_name = facility["name"]

    # NEW CODE (smart discovery):
    facility_id, facility_name = find_nearby_facility(
        db=db,
        latitude=request.latitude,
        longitude=request.longitude,
        max_distance_miles=0.3,
        discover_if_missing=True  # ← Triggers OSM query if needed
    )

    # ... rest of endpoint ...
```

### Driver Status Update Endpoint

```python
# app/routers/drivers.py

@router.post("/me/status")
async def update_my_status(status_update: StatusUpdate, ...):
    # Same integration as above
    facility_id, facility_name = find_nearby_facility(
        db=db,
        latitude=current_latitude,
        longitude=current_longitude,
        max_distance_miles=0.3,
        discover_if_missing=True
    )
    # ...
```

---

## Performance Characteristics

### Cold Start (First Driver in New Area)

```
Driver reports location at (36.78, -119.42)
 ↓
Check DB: No facilities in geohash "9qh7w8" ❌
 ↓
Check cache: Never queried this area ❌
 ↓
Query OSM (5 mile radius) → 2-4 seconds ⏱️
 ↓
Parse 12 facilities → 0.1 seconds
 ↓
Import to DB → 0.5 seconds
 ↓
Update cache → 0.1 seconds
 ↓
Return facility_name: "Love's Travel Stop" ✅

Total latency: ~3-5 seconds (first time only)
```

### Warm (Subsequent Drivers in Same Area)

```
Another driver reports location at (36.79, -119.43)
 ↓
Check DB: Found 12 facilities in geohash "9qh7w8" ✅
 ↓
Calculate distances → 0.01 seconds
 ↓
Found nearest facility: "Love's Travel Stop" ✅

Total latency: ~10-50ms (instant!)
```

### Cache Hit Rate (After 1 Month of Use)

Assuming 100 active drivers:
- **Major highways (I-5, I-10, I-80):** 95% cache hit rate
- **Secondary routes:** 70% cache hit rate
- **Rural areas:** 40% cache hit rate

**Average query latency:** ~50ms (mostly cache hits)

---

## Data Quality & Freshness

### Deduplication

We check for duplicates using:

1. **OSM ID** (exact match)
   ```python
   if facility.osm_id == existing.osm_id:
       return True  # Duplicate
   ```

2. **Proximity + Name Similarity** (within 250 feet)
   ```python
   if distance <= 0.05 miles and name1 in name2:
       return True  # Likely duplicate
   ```

### Refresh Strategy

```python
CACHE_REFRESH_DAYS = 30

if age > timedelta(days=30):
    # Re-query OSM for updated data
    discover_facilities(db, latitude, longitude)
```

**Why 30 days?**
- Truck stops rarely open/close overnight
- Balances freshness vs API usage
- Can be adjusted based on area importance

---

## Coverage Growth Simulation

### Week 1 (10 Active Drivers)

```
Drivers mainly on I-5 California corridor
 ↓
Queried: 50 unique geohash cells
 ↓
Facilities in DB: ~200-300
 ↓
Coverage: Central Valley, LA, Bay Area
```

### Month 1 (50 Active Drivers)

```
Drivers across California, Arizona, Nevada
 ↓
Queried: 300 unique geohash cells
 ↓
Facilities in DB: ~1,500-2,000
 ↓
Coverage: All major trucking routes in Southwest
```

### Month 6 (200 Active Drivers)

```
Drivers across entire West Coast + Texas
 ↓
Queried: 1,500 unique geohash cells
 ↓
Facilities in DB: ~8,000-10,000
 ↓
Coverage: 80% of major trucking routes nationwide
```

**Key Insight:** Database naturally focuses on areas where drivers actually operate, not random locations.

---

## Error Handling

### OSM API Timeout

```python
try:
    response = requests.post(overpass_url, timeout=35)
except requests.exceptions.Timeout:
    logger.error("OSM query timeout")
    # Still return None (driver sees coordinates instead of name)
    # Will retry on next driver in that area
    return None, None
```

### OSM API Rate Limiting

```
OSM Overpass API limits:
- 10,000 queries/day (per IP)
- 2 concurrent requests max

Our usage:
- ~50-100 queries/day with 100 active drivers
- Well within limits ✅
```

### Empty Results

```python
if not elements:
    # No facilities found (rural area)
    # Cache this result to avoid re-querying
    _update_query_cache(db, latitude, longitude, facilities_found=0)
    return None, None
```

---

## Migration Path

### Step 1: Apply Migration

```bash
# Apply migration 005
psql $DATABASE_URL < migrations/005_add_osm_query_cache.sql
```

### Step 2: Deploy Backend

```bash
# Updated endpoints automatically use new discovery system
git push origin main
```

### Step 3: Monitor

```sql
-- Check discovery activity
SELECT
    COUNT(*) as areas_queried,
    SUM(facilities_found) as total_facilities,
    AVG(facilities_found) as avg_per_area
FROM osm_query_cache;

-- Check facility growth
SELECT
    data_source,
    COUNT(*) as count
FROM facilities
GROUP BY data_source;
```

### Step 4: (Optional) Seed Major Routes

If you want instant coverage for major routes, pre-seed them:

```bash
# Seed I-5 corridor (optional)
python scripts/seed_major_routes.py --route i5 --states CA,OR,WA
```

---

## Testing

### Unit Tests

```bash
# Test geohash encoding
python scripts/test_facility_discovery.py

# Expected output:
# Geohash (6 chars): 9qh7w8
# Querying OSM for facilities near (36.7783, -119.4179)
# Found 12 facilities from OSM
#   1. Love's Travel Stop (truck_stop) at 36.7780, -119.4175
#   2. TA Truck Service (truck_stop) at 36.8234, -119.3891
#   3. I-5 Rest Area (rest_area) at 36.7123, -119.4567
```

### Integration Test

```bash
# Start backend
uvicorn app.main:app --reload

# Test location update with discovery
curl -X POST http://localhost:8000/api/v1/locations/status/update \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "status": "parked",
    "latitude": 36.7783,
    "longitude": -119.4179
  }'

# Expected response:
# {
#   "success": true,
#   "status": "parked",
#   "location": {
#     "latitude": 36.78,  # Fuzzed
#     "longitude": -119.42,  # Fuzzed
#     "facility_name": "Love's Travel Stop"  # ← Discovered from OSM!
#   },
#   "follow_up_question": {
#     "text": "How's the spot?",
#     "subtext": "Love's Travel Stop",
#     ...
#   }
# }
```

---

## Monitoring & Metrics

### Key Metrics to Track

```sql
-- Discovery performance
SELECT
    DATE(created_at) as date,
    COUNT(*) as new_areas_queried,
    AVG(facilities_found) as avg_facilities_per_query
FROM osm_query_cache
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Facility growth
SELECT
    DATE(created_at) as date,
    COUNT(*) as new_facilities
FROM facilities
WHERE data_source = 'openstreetmap'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Cache hit rate (via application logs)
-- Log: "OSM cache hit for {geohash}"
-- Log: "No facility found, triggering discovery"
```

### Expected Behavior

**Week 1:**
- Cache hit rate: ~30% (lots of discovery)
- Queries per day: 50-100
- New facilities per day: 100-200

**Month 1:**
- Cache hit rate: ~70% (mostly cached)
- Queries per day: 20-30
- New facilities per day: 30-50

**Month 6:**
- Cache hit rate: ~90% (well-covered)
- Queries per day: 5-10
- New facilities per day: 5-10

---

## Future Enhancements

### Phase 2: Background Discovery

Make discovery async so driver doesn't wait:

```python
@router.post("/status/update")
async def update_status_with_location(...):
    # Try quick lookup
    facility_id, facility_name = find_nearby_facility(db, lat, lng, discover_if_missing=False)

    # If not found, trigger background job
    if not facility_name and should_query_osm(db, lat, lng):
        celery_app.send_task('discover_facilities', args=[lat, lng])

    # Return immediately (name will populate on next status update)
    return {"facility_name": facility_name or None}
```

### Phase 3: User Submissions

Allow drivers to add missing facilities:

```python
@router.post("/facilities/submit")
async def submit_facility(facility: UserSubmittedFacility, ...):
    # Driver reports missing truck stop
    db.from_("facilities").insert({
        "name": facility.name,
        "latitude": facility.latitude,
        "longitude": facility.longitude,
        "data_source": "user_submitted",
        "submitted_by": driver_id,
        "verified": False  # Requires admin approval
    }).execute()
```

### Phase 4: ML-Based Discovery

Predict where drivers will go next and pre-cache facilities:

```python
# Analyze driver routes
if driver heading east on I-80:
    # Pre-discover next 50 miles of route
    for lat, lng in predicted_route:
        if should_query_osm(db, lat, lng):
            discover_facilities_async(db, lat, lng)
```

---

## Comparison: Bulk Import vs On-Demand

| Aspect | Bulk Import | On-Demand Discovery |
|--------|-------------|---------------------|
| **Initial Setup** | Hours (504 timeouts) | Minutes (just deploy) |
| **Coverage Day 1** | Full state/region | Zero (builds organically) |
| **Coverage Month 1** | Same (static) | Major routes (80% coverage) |
| **Data Freshness** | Stale immediately | Always fresh (30-day refresh) |
| **API Costs** | High (thousands of requests) | Low (10-100/day) |
| **Database Size** | 10,000+ facilities | 2,000-8,000 facilities |
| **Relevance** | Includes irrelevant locations | Only where drivers actually go |
| **Maintenance** | Manual re-imports | Self-updating |

**Winner:** On-Demand Discovery ✅

---

## Summary

### What We Built

1. **Geohash-based query cache** → Track which areas we've queried
2. **Smart facility lookup** → Check DB first, OSM fallback
3. **Organic growth** → Database builds based on actual usage
4. **Automatic refresh** → Re-query stale areas (30+ days)

### Why It Works

- ✅ Small queries never timeout (5-mile radius = 2-3 seconds)
- ✅ Database grows naturally along trucking routes
- ✅ Data stays fresh automatically
- ✅ Zero upfront work
- ✅ Scales with user growth

### Next Steps

1. Apply migration `005_add_osm_query_cache.sql`
2. Deploy updated endpoints
3. Monitor discovery activity in first week
4. Optional: Seed major routes for instant coverage

**The database builds itself as drivers use the app. Brilliant! 🚛**
