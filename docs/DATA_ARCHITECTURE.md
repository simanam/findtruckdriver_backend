# Data Architecture: Live vs Historical Data

## Overview

The Find a Truck Driver backend uses a **hybrid approach** combining:
1. **Live Data** - Recent driver locations and status (< 12 hours old)
2. **Historical Data** - Status transitions, follow-up responses, facility metrics
3. **Cumulative Data** - Aggregated statistics and trends

---

## Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Frontend Client                          │
│  (React Native / Next.js with Polling & Real-time Updates)      │
└─────────────────┬────────────────────────────────────────────────┘
                  │
                  │ HTTP Requests (every 15-30 seconds)
                  │
┌─────────────────▼────────────────────────────────────────────────┐
│                      Backend API (FastAPI)                        │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Live Data Endpoints (Always Fresh)                         ││
│  │  • GET /api/v1/map/stats/global                             ││
│  │  • GET /api/v1/map/drivers?bbox=...                         ││
│  │  • GET /api/v1/locations/me                                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Historical Data Endpoints (Trends & Analysis)              ││
│  │  • GET /api/v1/follow-ups/history                           ││
│  │  • GET /api/v1/facilities/{id}/metrics                      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────┬────────────────────────────────────────────────┘
                  │
                  │ SQL Queries
                  │
┌─────────────────▼────────────────────────────────────────────────┐
│                      Database (Supabase/PostgreSQL)              │
│                                                                   │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐ │
│  │   Live Data Tables   │  │   Historical Data Tables         │ │
│  │  (Updated Realtime)  │  │   (Append-Only Logs)            │ │
│  ├──────────────────────┤  ├──────────────────────────────────┤ │
│  │ • driver_locations   │  │ • status_updates                │ │
│  │   (UPSERT on        │  │   (new row per status change)   │ │
│  │    driver_id)       │  │                                  │ │
│  │                     │  │ • follow_up_responses           │ │
│  │ • drivers           │  │   (driver feedback)             │ │
│  │   (current status)  │  │                                  │ │
│  │                     │  │                                  │ │
│  └──────────────────────┘  └──────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │   Aggregated Data Tables (Pre-computed)                     ││
│  │  • facility_metrics (detention rates, safety scores)        ││
│  │  • Computed from status_updates + follow_up_responses       ││
│  └──────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────┘
```

---

## 1. Live Data (Real-Time Driver Status)

### Tables
- **`driver_locations`** - Current location of each driver
- **`drivers`** - Current status, last_active timestamp

### Characteristics
- **Update Pattern**: UPSERT (one row per driver)
- **Data Freshness**: < 30 seconds (via polling)
- **Retention**: Show only active drivers (last_active < 12 hours)
- **Privacy**: Uses fuzzed_latitude/fuzzed_longitude for public display

### Frontend Polling Strategy

```typescript
// Example: Stats Bar Component
const StatsBar = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    // Initial fetch
    fetchStats();

    // Poll every 15 seconds
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    const response = await fetch('/api/v1/map/stats/global');
    const data = await response.json();
    setStats(data);
  };

  return (
    <div>
      <span>📍 {stats?.rolling || 0} Rolling</span>
      <span>⏸️ {stats?.waiting || 0} Waiting</span>
      <span>🅿️ {stats?.parked || 0} Parked</span>
    </div>
  );
};
```

### Key Endpoints

#### GET /api/v1/map/stats/global
**Returns**: Total network statistics
```json
{
  "total_drivers": 47,
  "rolling": 23,
  "waiting": 12,
  "parked": 12,
  "recently_active": 35,
  "activity_percentage": 74.5,
  "timestamp": "2026-01-09T19:30:00Z"
}
```

**How it works**:
```python
# Queries driver_locations joined with drivers table
# Filters: recorded_at >= (now - 12 hours)
cutoff_time = (datetime.utcnow() - timedelta(hours=12)).isoformat()

locations = db.from_("driver_locations") \
    .select("*, drivers!inner(id, status, last_active)") \
    .gte("recorded_at", cutoff_time) \
    .execute()

# Counts by status in real-time
for loc in locations.data:
    status_counts[loc["drivers"]["status"]] += 1
```

#### GET /api/v1/map/drivers
**Returns**: All drivers in map viewport (bounding box)
```json
{
  "count": 15,
  "drivers": [
    {
      "driver_id": "uuid",
      "handle": "TruckerJoe",
      "status": "rolling",
      "latitude": 36.7783,  // fuzzed
      "longitude": -119.4179,  // fuzzed
      "last_active": "2026-01-09T19:28:00Z",
      "distance_from_center": 5.2
    }
  ]
}
```

**Polling**: Frontend polls this endpoint every 15-30 seconds when map is visible

---

## 2. Historical Data (Status Transitions)

### Tables
- **`status_updates`** - Complete log of every status change
- **`follow_up_responses`** - Driver answers to follow-up questions

### Characteristics
- **Update Pattern**: INSERT (append-only log)
- **Data Retention**: Indefinite (for trend analysis)
- **Use Cases**:
  - Show driver's history
  - Calculate wait times
  - Track detention patterns
  - Build facility reputations

### Example: Status Updates Log

```sql
-- status_updates table structure
CREATE TABLE status_updates (
  id UUID PRIMARY KEY,
  driver_id UUID REFERENCES drivers(id),
  status TEXT NOT NULL,  -- new status
  latitude DECIMAL,
  longitude DECIMAL,
  facility_id UUID REFERENCES facilities(id),

  -- Previous status context
  prev_status TEXT,
  prev_latitude DECIMAL,
  prev_longitude DECIMAL,
  prev_facility_id UUID,
  prev_updated_at TIMESTAMP,

  -- Calculated context
  time_since_last_seconds INTEGER,
  distance_from_last_miles DECIMAL,

  -- Follow-up question asked
  follow_up_question_type TEXT,
  follow_up_question_text TEXT,
  follow_up_options JSONB,

  -- Driver's response (if answered)
  follow_up_response TEXT,
  follow_up_answered_at TIMESTAMP,

  created_at TIMESTAMP DEFAULT NOW()
);
```

### Example: Tracking Detention Time

**Scenario**: Driver enters WAITING at facility, then leaves 3 hours later

```
1. Driver changes status: ROLLING → WAITING
   ├─ Record in status_updates:
   │  ├─ status: "waiting"
   │  ├─ facility_id: "Sysco Houston"
   │  ├─ prev_status: "rolling"
   │  └─ created_at: 2026-01-09 10:00:00
   └─ Frontend shows follow-up: "How's it looking?"
      └─ Driver answers: "🐢 Slow"

2. [3 hours pass...]

3. Driver changes status: WAITING → ROLLING
   ├─ Record in status_updates:
   │  ├─ status: "rolling"
   │  ├─ prev_status: "waiting"
   │  ├─ time_since_last_seconds: 10800  (3 hours)
   │  ├─ facility_id: "Sysco Houston"
   │  └─ created_at: 2026-01-09 13:00:00
   └─ Frontend shows follow-up: "3 hrs. Getting paid?"
      └─ Driver answers: "😤 Nope"
```

### Frontend Display

```typescript
// GET /api/v1/follow-ups/history
const DriverHistory = () => {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetchHistory();
  }, []);

  return (
    <div>
      {history.map(update => (
        <div key={update.id}>
          <span>{update.facility_name}</span>
          <span>{formatDuration(update.time_since_last_seconds)}</span>
          {update.follow_up_response && (
            <span>Response: {update.follow_up_response}</span>
          )}
        </div>
      ))}
    </div>
  );
};
```

---

## 3. Cumulative/Aggregated Data (Facility Metrics)

### Table
- **`facility_metrics`** - Pre-computed statistics per facility

### Characteristics
- **Update Pattern**: Computed from historical data
- **Update Frequency**: Daily batch job or on-demand
- **Use Cases**:
  - Facility reputation scores
  - Detention payment rates
  - Parking safety ratings
  - Average wait times

### Example: Facility Metrics

```sql
CREATE TABLE facility_metrics (
  id UUID PRIMARY KEY,
  facility_id UUID REFERENCES facilities(id),

  -- Detention tracking
  total_visits INTEGER,
  avg_wait_time_minutes DECIMAL,
  median_wait_time_minutes DECIMAL,
  detention_pay_rate DECIMAL,  -- % of times detention was paid

  -- Parking safety (from follow-up responses)
  parking_safety_score DECIMAL,  -- 0-100
  total_parking_ratings INTEGER,
  solid_ratings INTEGER,
  meh_ratings INTEGER,
  sketch_ratings INTEGER,

  -- Facility flow (from follow-up responses)
  total_flow_ratings INTEGER,
  moving_ratings INTEGER,
  slow_ratings INTEGER,
  dead_ratings INTEGER,

  -- Metadata
  last_computed_at TIMESTAMP,
  data_freshness TEXT  -- "realtime", "1 hour", "1 day"
);
```

### Computing Metrics

```python
# Background job (runs daily or on-demand)
def compute_facility_metrics(facility_id: UUID):
    # Get all status updates for this facility
    updates = db.from_("status_updates") \
        .select("*") \
        .eq("facility_id", facility_id) \
        .eq("prev_status", "waiting") \
        .eq("status", "rolling") \
        .execute()

    # Calculate detention metrics
    total_visits = len(updates.data)
    wait_times = [u["time_since_last_seconds"] for u in updates.data]
    avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0

    # Calculate detention pay rate
    paid_count = sum(1 for u in updates.data
                     if u["follow_up_response"] == "paid")
    pay_rate = (paid_count / total_visits * 100) if total_visits > 0 else 0

    # Get parking ratings
    parking_updates = db.from_("status_updates") \
        .select("follow_up_response") \
        .eq("facility_id", facility_id) \
        .eq("follow_up_question_type", "parking_spot_entry") \
        .execute()

    solid_count = sum(1 for u in parking_updates.data
                      if u["follow_up_response"] == "solid")
    total_parking = len(parking_updates.data)
    safety_score = (solid_count / total_parking * 100) if total_parking > 0 else None

    # Save to facility_metrics
    db.from_("facility_metrics").upsert({
        "facility_id": facility_id,
        "total_visits": total_visits,
        "avg_wait_time_minutes": avg_wait / 60,
        "detention_pay_rate": pay_rate,
        "parking_safety_score": safety_score,
        "total_parking_ratings": total_parking,
        "solid_ratings": solid_count,
        "last_computed_at": datetime.utcnow().isoformat()
    }).execute()
```

### Frontend Display

```typescript
// Facility detail page
const FacilityDetails = ({ facilityId }) => {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    fetch(`/api/v1/facilities/${facilityId}/metrics`)
      .then(res => res.json())
      .then(setMetrics);
  }, [facilityId]);

  return (
    <div>
      <h2>Sysco Houston Distribution Center</h2>

      <div>
        <h3>Detention Performance</h3>
        <p>Average Wait: {metrics?.avg_wait_time_minutes} min</p>
        <p>Detention Paid: {metrics?.detention_pay_rate}%</p>
        <small>Based on {metrics?.total_visits} driver reports</small>
      </div>

      <div>
        <h3>Parking Safety</h3>
        <p>Safety Score: {metrics?.parking_safety_score}/100</p>
        <p>😴 Solid: {metrics?.solid_ratings}</p>
        <p>😬 Sketch: {metrics?.sketch_ratings}</p>
        <small>Based on {metrics?.total_parking_ratings} ratings</small>
      </div>
    </div>
  );
};
```

---

## 4. Data Freshness Strategy

### Real-Time Data (< 1 minute stale)
- **driver_locations** (current position)
- **drivers.status** (current status)
- **drivers.last_active** (last seen)

**Polling**: Every 15-30 seconds

### Near Real-Time (< 5 minutes stale)
- **status_updates** (recent transitions)
- **follow_up_responses** (just answered)

**Polling**: Every 1-2 minutes for personal history

### Cached/Aggregated (< 1 day stale)
- **facility_metrics** (reputation scores)
- Can be updated in background jobs

**Polling**: Once per session or on-demand

---

## 5. Frontend Caching & Optimization

### React Query / SWR Pattern

```typescript
// Using React Query for smart caching
import { useQuery } from '@tanstack/react-query';

// Global stats - refresh every 15 seconds, keep stale data
const useGlobalStats = () => {
  return useQuery({
    queryKey: ['stats', 'global'],
    queryFn: () => fetch('/api/v1/map/stats/global').then(r => r.json()),
    refetchInterval: 15000,  // Poll every 15s
    staleTime: 10000,        // Consider fresh for 10s
    cacheTime: 300000,       // Keep in cache for 5 min
  });
};

// Map drivers - refresh only when map moves or every 30s
const useMapDrivers = (bounds) => {
  return useQuery({
    queryKey: ['drivers', 'map', bounds],
    queryFn: () => fetch(`/api/v1/map/drivers?...`).then(r => r.json()),
    refetchInterval: 30000,
    enabled: !!bounds,  // Only fetch when bounds are set
  });
};

// Facility metrics - refresh rarely, heavy cache
const useFacilityMetrics = (facilityId) => {
  return useQuery({
    queryKey: ['facility', facilityId, 'metrics'],
    queryFn: () => fetch(`/api/v1/facilities/${facilityId}/metrics`).then(r => r.json()),
    staleTime: 3600000,  // 1 hour stale time
    cacheTime: 86400000, // 24 hour cache
  });
};
```

---

## 6. Data Consistency

### Write Pattern
```
User Action (Frontend)
    ↓
POST /api/v1/drivers/me/status
    ↓
Backend writes to 3 tables:
    1. drivers.status = "parked" (UPSERT current)
    2. driver_locations.recorded_at = NOW() (UPSERT current)
    3. status_updates (INSERT new row, append-only log)
    ↓
Background job (async):
    4. Update facility_metrics (daily aggregation)
```

### Read Pattern
```
Frontend Component Mounts
    ↓
Fetch live data: /map/stats/global (every 15s)
Fetch live data: /map/drivers (every 30s)
Fetch cached data: /facilities/{id}/metrics (once per session)
    ↓
Display to user with smart caching
```

---

## 7. Summary

| Data Type | Freshness | Update Pattern | Use Case | Polling Interval |
|-----------|-----------|----------------|----------|------------------|
| **Live Status** | < 30s | UPSERT | Map pins, stats bar | 15-30s |
| **Historical Logs** | Real-time | INSERT | Driver history, trends | 1-2 min |
| **Aggregated Metrics** | < 1 day | Batch compute | Facility reputation | Once per session |

### Key Principles
1. **Separation of Concerns**: Live data (current state) vs Historical data (event log)
2. **Smart Polling**: Different refresh rates for different data types
3. **Progressive Enhancement**: Show stale data while fetching fresh data
4. **Privacy First**: Always use fuzzed coordinates for public display
5. **Scalability**: Pre-compute heavy aggregations, cache aggressively

---

## Next Steps

### Phase 2: Real-Time Subscriptions (Future)
Replace HTTP polling with WebSocket subscriptions for truly real-time updates:
```typescript
// Instead of polling every 15s, subscribe to changes
const subscription = supabase
  .channel('driver_locations')
  .on('postgres_changes',
    { event: 'UPDATE', schema: 'public', table: 'driver_locations' },
    (payload) => updateMapPin(payload.new)
  )
  .subscribe();
```

This would provide sub-second updates without polling overhead.
