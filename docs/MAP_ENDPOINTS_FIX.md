# Map Endpoints - Frontend Integration Fix

## Issue

User reported: "i cannot see my self on map"

## Root Cause

The frontend is calling `/api/v1/map/clusters` which requires **minimum 2 drivers** to form a cluster. Since you're the only driver in the system, no clusters are formed and the map appears empty.

## Solution

The frontend needs to use `/api/v1/map/drivers` instead of (or in addition to) `/api/v1/map/clusters`.

## Available Map Endpoints

### 1. `/api/v1/map/drivers` ✅ Use This for Individual Drivers

**Purpose:** Show all individual drivers on the map

**Example Request:**
```bash
GET /api/v1/map/drivers?latitude=36.83&longitude=-119.91&radius_miles=50
```

**Response:**
```json
{
  "center": {"latitude": 36.83, "longitude": -119.91},
  "radius_miles": 50.0,
  "count": 1,
  "drivers": [
    {
      "driver_id": "104eabd9-5e56-4d30-a468-24b380607e37",
      "handle": "steel_hawk",
      "status": "waiting",
      "latitude": 36.8339727596223,
      "longitude": -119.908968599149,
      "geohash": "9qd9",
      "distance_miles": 0.28,
      "last_active": "2026-01-09T15:29:39.74833+00:00"
    }
  ]
}
```

**Use Case:** Default map view showing all active drivers

---

### 2. `/api/v1/map/clusters` ⚠️ Requires 2+ Drivers

**Purpose:** Show driver clusters (aggregated groups)

**Limitation:** Requires `min_drivers >= 2` per cluster

**Example Request:**
```bash
GET /api/v1/map/clusters?latitude=36.83&longitude=-119.91&radius_miles=50&min_drivers=2
```

**When to Use:** When you have many drivers and want to show grouped markers instead of individual ones

**Response (when enough drivers exist):**
```json
{
  "cluster_count": 3,
  "clusters": [
    {
      "geohash": "9q9p",
      "center": {"latitude": 37.77, "longitude": -122.41},
      "total_drivers": 5,
      "status_breakdown": {"rolling": 2, "waiting": 2, "parked": 1}
    }
  ]
}
```

---

### 3. `/api/v1/map/hotspots` 🔥 Waiting Driver Aggregation

**Purpose:** Show where many drivers are waiting (busy facilities)

**Example:**
```bash
GET /api/v1/map/hotspots?latitude=36.83&longitude=-119.91&radius_miles=100&min_waiting_drivers=3
```

**Use Case:** Show congestion areas where drivers are waiting for loads

---

### 4. `/api/v1/map/stats` 📊 Area Statistics

**Purpose:** Get counts and breakdown for a map area

**Example:**
```bash
GET /api/v1/map/stats?latitude=36.83&longitude=-119.91&radius_miles=50
```

**Response:**
```json
{
  "total_drivers": 12,
  "status_breakdown": {"rolling": 5, "waiting": 4, "parked": 3},
  "recently_active": 8,
  "activity_percentage": 66.7
}
```

**Use Case:** Dashboard statistics, heat maps

---

## Frontend Fix Needed

### Current Code (Broken):
```typescript
// ❌ This won't work with only 1 driver
const response = await fetch(`/api/v1/map/clusters?...&min_drivers=3`);
```

### Fixed Code (Option 1 - Show Individual Drivers):
```typescript
// ✅ Show individual driver markers
const response = await fetch(
  `/api/v1/map/drivers?latitude=${lat}&longitude=${lng}&radius_miles=${radius}`
);
const data = await response.json();

// Place markers for each driver
data.drivers.forEach(driver => {
  addMarkerToMap(driver.latitude, driver.longitude, driver.handle, driver.status);
});
```

### Fixed Code (Option 2 - Clusters with Fallback):
```typescript
// ✅ Try clusters first, fallback to individual drivers
async function loadMapDrivers(lat, lng, radius) {
  // Try clusters (only works if 2+ drivers exist)
  const clustersResponse = await fetch(
    `/api/v1/map/clusters?latitude=${lat}&longitude=${lng}&radius_miles=${radius}&min_drivers=2`
  );
  const clusters = await clustersResponse.json();

  if (clusters.cluster_count > 0) {
    // Show cluster markers
    clusters.clusters.forEach(cluster => {
      addClusterMarker(cluster.center.latitude, cluster.center.longitude, cluster.total_drivers);
    });
  } else {
    // Fallback to individual drivers
    const driversResponse = await fetch(
      `/api/v1/map/drivers?latitude=${lat}&longitude=${lng}&radius_miles=${radius}`
    );
    const drivers = await driversResponse.json();

    drivers.drivers.forEach(driver => {
      addMarkerToMap(driver.latitude, driver.longitude, driver.handle, driver.status);
    });
  }
}
```

### Fixed Code (Option 3 - Smart Clustering):
```typescript
// ✅ Cluster only when many drivers exist
async function loadMapDrivers(lat, lng, radius) {
  // Always get individual drivers first
  const driversResponse = await fetch(
    `/api/v1/map/drivers?latitude=${lat}&longitude=${lng}&radius_miles=${radius}&limit=100`
  );
  const data = await driversResponse.json();

  if (data.count < 10) {
    // Show individual markers for < 10 drivers
    data.drivers.forEach(driver => {
      addMarkerToMap(driver.latitude, driver.longitude, driver.handle, driver.status);
    });
  } else {
    // Use clustering for 10+ drivers
    const clustersResponse = await fetch(
      `/api/v1/map/clusters?latitude=${lat}&longitude=${lng}&radius_miles=${radius}&min_drivers=2`
    );
    const clusters = await clustersResponse.json();

    clusters.clusters.forEach(cluster => {
      addClusterMarker(cluster.center.latitude, cluster.center.longitude, cluster.total_drivers);
    });
  }
}
```

---

## Testing

### Test with your current data (1 driver):
```bash
# This works ✅
curl "http://localhost:8000/api/v1/map/drivers?latitude=36.83&longitude=-119.91&radius_miles=50"

# This returns empty ❌ (needs 2+ drivers)
curl "http://localhost:8000/api/v1/map/clusters?latitude=36.83&longitude=-119.91&radius_miles=50&min_drivers=2"
```

### Add a test driver to verify clustering:
```sql
-- Create a second test driver near you
INSERT INTO drivers (handle, avatar_id, status, user_id)
VALUES ('test_driver_2', 'bear', 'rolling', (SELECT id FROM auth.users LIMIT 1 OFFSET 1));

-- Add their location
INSERT INTO driver_locations (driver_id, latitude, longitude, fuzzed_latitude, fuzzed_longitude, geohash, recorded_at)
VALUES (
  (SELECT id FROM drivers WHERE handle = 'test_driver_2'),
  36.84, -119.92,  -- Real coords
  36.835, -119.915,  -- Fuzzed coords
  '9qd9',
  NOW()
);
```

Now clusters endpoint will work because you have 2+ drivers.

---

## Summary

**Backend is working correctly.** The issue is the frontend calling the wrong endpoint.

**Quick Fix:** Change frontend to use `/api/v1/map/drivers` instead of `/api/v1/map/clusters`.

**Better Fix:** Use the smart clustering approach (Option 3 above) that shows individual drivers when count is low and clusters when many drivers exist.

---

## Related Files

- [app/routers/map.py](../app/routers/map.py) - Map endpoints implementation
- [docs/API_URLS_REFERENCE.md](API_URLS_REFERENCE.md) - All available endpoints
- [docs/FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) - Frontend integration guide
