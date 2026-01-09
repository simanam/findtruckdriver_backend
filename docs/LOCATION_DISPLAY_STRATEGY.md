# Location Display Strategy: Facility Names vs Coordinates

## TL;DR

**We show BOTH - facility names when available, fuzzed coordinates always:**

```
✅ "Love's Truck Stop" (36.77°, -119.41°)  ← Best UX
✅ (36.77°, -119.41°)                     ← Fallback when no facility nearby
❌ Exact coordinates                       ← Never (privacy violation)
```

---

## The Strategy

### 1. Privacy-First Coordinates

**ALL locations shown publicly use fuzzed coordinates:**

```python
# When driver updates location, we store TWO sets of coordinates:

# PRIVATE (never exposed)
latitude = 36.77832        # Exact location
longitude = -119.41794     # Exact location

# PUBLIC (always shown)
fuzzed_latitude = 36.78    # Rounded to ~0.01 degrees (~1 mile)
fuzzed_longitude = -119.42 # Rounded to ~0.01 degrees (~1 mile)
```

**Fuzzing Logic:**
- Round to 2 decimal places (~1 mile radius)
- Prevents exact tracking of individual drivers
- Still accurate enough for map display

```python
# From app/routers/locations.py
def fuzz_coordinate(coord: float) -> float:
    """Round coordinate to 2 decimal places for privacy"""
    return round(coord, 2)

fuzzed_lat = fuzz_coordinate(request.latitude)
fuzzed_lng = fuzz_coordinate(request.longitude)
```

### 2. Facility Name Lookup

**When driver is near a known facility, we show the name:**

```python
# Check if driver is within 0.3 miles of any facility
facilities = db.from_("facilities").select("*").execute()

for facility in facilities.data:
    distance = calculate_distance(
        driver_lat, driver_lng,
        facility["latitude"], facility["longitude"]
    )
    if distance <= 0.3:  # Within 0.3 miles
        facility_name = facility["name"]
        break
```

**Detection Thresholds:**
- **Check-in**: 0.1 miles (very close, high confidence)
- **Status update**: 0.3 miles (moderate confidence)
- **Hotspot detection**: 0.3 miles (for clustering)

---

## Database Schema

### facilities Table

```sql
CREATE TABLE facilities (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,        -- "Love's Travel Stop #234"
  type VARCHAR(50) NOT NULL,         -- "truck_stop", "rest_area", "parking"
  latitude FLOAT NOT NULL,           -- Exact facility location
  longitude FLOAT NOT NULL,          -- Exact facility location

  -- Address info
  address TEXT,
  city VARCHAR(100),
  state VARCHAR(2),
  zip_code VARCHAR(10),

  -- Metadata
  brand VARCHAR(100),                -- "Love's", "Pilot", "TA"
  amenities JSONB,                   -- {"showers": true, "food": true}
  parking_spaces INT,
  is_open_24h BOOLEAN,

  -- Geospatial
  geohash VARCHAR(12),               -- For fast proximity queries

  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

### driver_locations Table

```sql
CREATE TABLE driver_locations (
  driver_id UUID PRIMARY KEY,

  -- Exact coordinates (PRIVATE - never exposed in API)
  latitude FLOAT NOT NULL,
  longitude FLOAT NOT NULL,

  -- Fuzzed coordinates (PUBLIC - always shown)
  fuzzed_latitude FLOAT NOT NULL,
  fuzzed_longitude FLOAT NOT NULL,

  -- Geospatial
  geohash VARCHAR(12),

  recorded_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Response Examples

### Example 1: Driver at Known Facility

**Request:**
```bash
GET /api/v1/locations/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "driver_id": "uuid",
  "handle": "TruckerJoe",
  "status": "waiting",
  "latitude": 36.78,              // Fuzzed
  "longitude": -119.42,           // Fuzzed
  "facility_name": "Love's Travel Stop #234",  // ✅ Shown!
  "updated_at": "2026-01-09T19:30:00Z"
}
```

### Example 2: Driver in Middle of Nowhere

**Request:**
```bash
GET /api/v1/map/drivers?bbox=...
```

**Response:**
```json
{
  "drivers": [
    {
      "driver_id": "uuid",
      "handle": "HighwayHank",
      "status": "rolling",
      "latitude": 37.12,          // Fuzzed
      "longitude": -120.85,       // Fuzzed
      "facility_name": null,      // ❌ No facility nearby
      "updated_at": "2026-01-09T19:28:00Z"
    }
  ]
}
```

### Example 3: Follow-Up Question with Facility

**Request:**
```bash
POST /api/v1/drivers/me/status
{
  "status": "parked",
  "latitude": 36.77832,
  "longitude": -119.41794
}
```

**Response:**
```json
{
  "success": true,
  "old_status": "rolling",
  "new_status": "parked",
  "location": {
    "latitude": 36.78,            // Fuzzed
    "longitude": -119.42,         // Fuzzed
    "facility_name": "Love's Travel Stop #234"
  },
  "follow_up_question": {
    "question_type": "parking_spot_entry",
    "text": "How's the spot?",
    "subtext": "Love's Travel Stop #234",  // ✅ Facility name in question!
    "options": [
      {"emoji": "😴", "label": "Solid", "value": "solid"},
      {"emoji": "😐", "label": "Meh", "value": "meh"},
      {"emoji": "😬", "label": "Sketch", "value": "sketch"}
    ]
  }
}
```

---

## Frontend Display Logic

### Map Pin with Facility Name

```typescript
interface DriverMarker {
  driver_id: string;
  handle: string;
  status: "rolling" | "waiting" | "parked";
  latitude: number;      // Already fuzzed by backend
  longitude: number;     // Already fuzzed by backend
  facility_name?: string;
}

const DriverPin = ({ driver }: { driver: DriverMarker }) => {
  return (
    <Marker
      latitude={driver.latitude}
      longitude={driver.longitude}
      onClick={() => showDriverInfo(driver)}
    >
      <DriverPinIcon status={driver.status} />
      {driver.facility_name && (
        <Tooltip>
          {driver.handle} - {driver.facility_name}
        </Tooltip>
      )}
    </Marker>
  );
};
```

### Driver Info Modal

```typescript
const DriverInfoModal = ({ driver }: { driver: DriverMarker }) => {
  return (
    <div>
      <h2>{driver.handle}</h2>
      <StatusBadge status={driver.status} />

      {/* Show facility name if available */}
      {driver.facility_name ? (
        <div>
          <LocationIcon />
          <span>{driver.facility_name}</span>
        </div>
      ) : (
        <div>
          <LocationIcon />
          <span>
            {driver.latitude.toFixed(2)}°, {driver.longitude.toFixed(2)}°
          </span>
        </div>
      )}
    </div>
  );
};
```

### Follow-Up Question with Context

```typescript
const FollowUpModal = ({ question }) => {
  return (
    <div>
      <h3>{question.text}</h3>

      {/* Show facility name as context */}
      {question.subtext && (
        <p className="subtext">
          📍 {question.subtext}  {/* "Love's Travel Stop #234" */}
        </p>
      )}

      <div className="options">
        {question.options.map(option => (
          <button key={option.value}>
            <span>{option.emoji}</span>
            <span>{option.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
```

---

## When Facility Names Are Shown

| Context | Facility Name Shown? | Example |
|---------|---------------------|---------|
| **Map pins** | ✅ Yes (if within 0.3 mi) | "TruckerJoe at Love's" |
| **Driver profile** | ✅ Yes (if within 0.1 mi) | "Last seen at Pilot Flying J" |
| **Follow-up questions** | ✅ Yes (in subtext) | "How's the spot? Love's Travel Stop" |
| **Status history** | ✅ Yes (from status_updates) | "Waited 3 hrs at Sysco Houston" |
| **Hotspots** | ✅ Yes (clustered locations) | "12 drivers waiting at Walmart DC" |
| **Facility metrics** | ✅ Yes (primary identifier) | "Sysco Houston: 67% detention pay" |

---

## Privacy Considerations

### What We DO Show:
- ✅ Fuzzed coordinates (rounded to ~1 mile)
- ✅ Facility names (public places only)
- ✅ Approximate location ("near I-80 exit 142")
- ✅ Status (rolling, waiting, parked)

### What We DON'T Show:
- ❌ Exact coordinates (privacy violation)
- ❌ Street addresses (too specific)
- ❌ Real-time tracking of individuals
- ❌ Movement patterns without consent

### Fuzzing Details:

```python
# Coordinate fuzzing reduces precision from:
Original:  36.778324, -119.417942  (±11 meters)
Fuzzed:    36.78,     -119.42      (±1 mile)

# This means:
✅ Can show driver on map in general area
✅ Can match to nearby facilities
❌ Cannot pinpoint exact truck location
❌ Cannot track individual movements precisely
```

---

## Facility Data Sources

### Current: Manual Import
```sql
-- Sample facility data (migrations/sample_facilities.sql)
INSERT INTO facilities (name, type, latitude, longitude, city, state, brand)
VALUES
  ('Love''s Travel Stop #234', 'truck_stop', 36.7783, -119.4179, 'Fresno', 'CA', 'Love''s'),
  ('Pilot Flying J #456', 'truck_stop', 36.8523, -119.7462, 'Madera', 'CA', 'Pilot'),
  ('I-5 Rest Area', 'rest_area', 36.9234, -119.8456, 'Madera', 'CA', null);
```

### Future: Third-Party APIs
- **Truck Stop Chains**: Love's, Pilot, TA/Petro APIs
- **DOT Data**: Rest areas, weigh stations
- **OpenStreetMap**: Community-maintained truck parking
- **User Submissions**: Drivers can add missing facilities

---

## Advanced: Reverse Geocoding

### For Enhanced Location Display

**Instead of:** `(36.78°, -119.42°)`
**Show:** `Near I-5, Fresno County, CA`

```typescript
// Using Mapbox Geocoding API
const getReverseGeocode = async (lat: number, lng: number) => {
  const response = await fetch(
    `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?access_token=${MAPBOX_TOKEN}`
  );
  const data = await response.json();

  // Extract highway/city info
  const feature = data.features[0];
  return {
    highway: feature.context.find(c => c.id.startsWith('road')),
    city: feature.context.find(c => c.id.startsWith('place')),
    county: feature.context.find(c => c.id.startsWith('county'))
  };
};

// Display: "Near I-5, Fresno County"
```

**Note:** This is optional and would add external API dependency.

---

## Summary Table

| Data Type | Precision | Shown to Public? | Example |
|-----------|-----------|------------------|---------|
| **Exact coords** | ±11 meters | ❌ No (private) | 36.778324, -119.417942 |
| **Fuzzed coords** | ±1 mile | ✅ Yes | 36.78, -119.42 |
| **Facility name** | Exact building | ✅ Yes | "Love's Travel Stop #234" |
| **Facility address** | Street address | 🔶 Optional | "1234 Highway 99, Fresno CA" |
| **City/State** | General area | ✅ Yes | "Fresno, CA" |
| **Reverse geocode** | Highway/area | ✅ Yes | "Near I-5, Fresno County" |

---

## Implementation Checklist

### Backend ✅ Complete
- [x] Store exact + fuzzed coordinates
- [x] Facility lookup within 0.3 miles
- [x] Return facility_name in all location responses
- [x] Include facility_name in follow-up questions
- [x] Store facility_id in status_updates

### Frontend 🚧 To Do
- [ ] Display facility names on map pins
- [ ] Show facility names in driver modals
- [ ] Render facility names in follow-up questions
- [ ] Fallback to coordinates when no facility
- [ ] Add facility search/filter
- [ ] Display facility metrics (ratings, detention)

---

## Best Practices

### 1. Always Prefer Facility Names
```typescript
// Good
const displayLocation = (driver) => {
  return driver.facility_name || `${driver.lat.toFixed(2)}°, ${driver.lng.toFixed(2)}°`;
};

// Bad
const displayLocation = (driver) => {
  return `${driver.lat}, ${driver.lng}`;  // No fallback, no facility name
};
```

### 2. Never Show Exact Coordinates
```typescript
// Good - Backend already fuzzed
<span>{driver.latitude}°, {driver.longitude}°</span>

// Bad - Would need manual fuzzing (but backend handles it)
<span>{driver.latitude.toFixed(2)}°, {driver.longitude.toFixed(2)}°</span>
```

### 3. Show Facility Names in Context
```typescript
// Good - Provides context
<div>
  <h3>Status: Waiting</h3>
  {driver.facility_name && <p>at {driver.facility_name}</p>}
  <small>3 other drivers waiting here</small>
</div>

// Bad - Missing valuable context
<div>
  <h3>Status: Waiting</h3>
  <small>(36.78, -119.42)</small>
</div>
```

---

## Future Enhancements

### Phase 2: Facility Pages
Each facility gets its own page with:
- Real-time driver count
- Historical wait times
- Detention pay statistics
- Parking safety ratings
- Amenities and services
- Reviews and comments

```
/facilities/love-s-travel-stop-234
  → "Love's Travel Stop #234"
  → "Current: 12 drivers waiting"
  → "Avg wait: 45 min"
  → "Detention paid: 89%"
  → "Safety: 94/100 (😴 Solid)"
```

### Phase 3: User-Submitted Facilities
Allow drivers to add missing truck stops:
```typescript
<AddFacilityButton
  onSubmit={(data) => {
    POST('/api/v1/facilities', {
      name: data.name,
      latitude: currentLocation.lat,
      longitude: currentLocation.lng,
      type: 'parking',
      amenities: data.amenities
    });
  }}
/>
```
