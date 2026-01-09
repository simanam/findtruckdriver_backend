# Database Tables - Current State

## Current Tables in Database

### 1. drivers ✅ REQUIRED
**Status:** EXISTS
**Purpose:** Core user profile table
**Contains:**
- id (UUID) - Primary key
- user_id (UUID) - Links to auth.users
- handle (VARCHAR) - Username (unique)
- avatar_id (TEXT) - Avatar identifier
- status (VARCHAR) - Current status: 'rolling', 'waiting', 'parked'
- last_active (TIMESTAMPTZ) - Last activity timestamp
- created_at (TIMESTAMPTZ) - Account creation time

**Used By:**
- Authentication system
- Profile endpoints
- Map display
- All driver-related operations

**RLS Policies:**
- Public read access
- Users can update their own profile
- Users can insert their own profile

---

### 2. driver_locations ✅ REQUIRED
**Status:** EXISTS
**Purpose:** Track current location for each driver
**Contains:**
- id (UUID) - Primary key
- driver_id (UUID) - References drivers(id)
- latitude (FLOAT) - Actual GPS latitude
- longitude (FLOAT) - Actual GPS longitude
- fuzzed_latitude (FLOAT) - Privacy-protected latitude
- fuzzed_longitude (FLOAT) - Privacy-protected longitude
- accuracy (FLOAT) - Location accuracy in meters
- heading (FLOAT) - Direction of travel (0-360°)
- speed (FLOAT) - Speed in mph
- geohash (VARCHAR) - Spatial index for clustering
- recorded_at (TIMESTAMPTZ) - Timestamp of location

**Used By:**
- Location update endpoint: POST /api/v1/locations
- App-open detection: POST /api/v1/locations/app-open
- Map clustering: GET /api/v1/map/clusters
- Privacy fuzzing system

**RLS Policies:**
- Public read access (returns fuzzed coordinates only)
- Drivers can insert/update own location

**Indexes:**
- idx_driver_locations_driver_id (fast lookups by driver)
- idx_driver_locations_geohash (spatial clustering)
- idx_driver_locations_recorded (time-based queries)

---

### 3. spatial_ref_sys ⚙️ SYSTEM TABLE
**Status:** EXISTS (PostGIS extension)
**Purpose:** PostGIS spatial reference system definitions
**Contains:** Coordinate system definitions (EPSG codes, projections)

**Used By:**
- PostGIS extension automatically
- Not directly queried by our application

**Action Required:** None - leave as is

---

## Missing Tables (From Migrations)

### 4. migration_history ❌ MISSING (BUT NEEDED)
**Status:** SHOULD EXIST
**Purpose:** Track which migrations have been applied
**Should Contain:**
- id (SERIAL) - Primary key
- migration_name (VARCHAR) - e.g., '001_initial_schema'
- applied_at (TIMESTAMPTZ) - When migration ran
- description (TEXT) - What the migration does

**Why Missing:**
The migrations haven't been run via the migration script yet. You manually ran the SQL to create tables, but didn't create migration_history.

**Action Required:** Run the migration script:
```bash
cd /Users/amansingh/Documents/findtruckdriver/finddriverapp/finddriverbackend
./migrations/run_migrations.sh
```

This will create migration_history and record what's been applied.

---

### 5. status_history ❌ MISSING (BUT NEEDED)
**Status:** SHOULD EXIST
**Purpose:** Track driver status changes over time
**Should Contain:**
- id (UUID) - Primary key
- driver_id (UUID) - References drivers(id)
- status (VARCHAR) - Status during this period: 'rolling', 'waiting', 'parked'
- latitude (FLOAT) - Location when status changed
- longitude (FLOAT) - Location when status changed
- started_at (TIMESTAMPTZ) - When status began
- ended_at (TIMESTAMPTZ) - When status ended (NULL if current)
- duration_mins (INT) - Auto-calculated duration

**Used By:**
- Status update endpoint: POST /api/v1/drivers/status (should create history records)
- Analytics and reporting (future)
- Understanding driver behavior patterns

**Why Missing:**
The migration script hasn't been run. This table is created by [002_add_driver_locations.sql](../migrations/002_add_driver_locations.sql).

**Action Required:** Run the migration script.

---

### 6. facilities ✅ EXISTS (OPTIONAL BUT READY)
**Status:** EXISTS with sample data
**Purpose:** Truck stops, rest areas, parking locations
**Contains:**
- id (UUID) - Primary key
- name (VARCHAR) - Facility name (e.g., "Pilot Travel Center")
- type (VARCHAR) - Type: 'truck_stop', 'rest_area', 'parking', 'service_plaza', 'weigh_station'
- latitude (FLOAT) - GPS latitude
- longitude (FLOAT) - GPS longitude
- address (TEXT) - Street address
- city (VARCHAR) - City name
- state (VARCHAR) - Two-letter state code
- zip_code (VARCHAR) - Postal code
- country (VARCHAR) - Country code (default 'US')
- phone (VARCHAR) - Contact phone
- website (TEXT) - Website URL
- amenities (JSONB) - Available services (showers, fuel, food, etc.)
- parking_spaces (INT) - Number of truck parking spots
- is_open_24h (BOOLEAN) - Open 24 hours
- brand (VARCHAR) - Brand name (e.g., "Pilot Flying J", "Love's")
- geohash (VARCHAR) - Spatial clustering hash
- created_at (TIMESTAMPTZ) - Creation timestamp
- updated_at (TIMESTAMPTZ) - Last update timestamp

**Used By:**
- App-open detection (shows location name like "You were last at Pilot Travel Center #456")
- Map markers (future feature)
- Facility search (future feature)

**Current Data:**
- 5 sample facilities loaded (Pilot, Love's, TA Petro, rest area, parking)
- See [FACILITIES_IMPORT.md](FACILITIES_IMPORT.md) for how to add more data

**RLS Policies:**
- Public read access (facilities are public data)

**Indexes:**
- idx_facilities_geohash (spatial clustering)
- idx_facilities_type (filter by type)
- idx_facilities_state (search by state)
- idx_facilities_brand (search by brand)
- idx_facilities_location (lat/lon queries)
- idx_facilities_amenities (JSON amenity search)

**Action Required:**
- Optionally import more facilities (see [FACILITIES_IMPORT.md](FACILITIES_IMPORT.md))
- Choose data source: OpenStreetMap (free), TruckMaster API (paid), or manual entry

---

## Summary

### ✅ Tables That Exist and Are Working
1. **drivers** - Core profiles ✅
2. **driver_locations** - Current locations ✅
3. **migration_history** - Migration tracking ✅
4. **status_history** - Status change tracking ✅
5. **facilities** - Truck stops and rest areas (5 sample records) ✅
6. **spatial_ref_sys** - PostGIS system table ✅

### 🎉 All Tables Created!

All required and optional tables have been created via migrations. The database is **production-ready**.

---

## Recommended Actions

### ✅ Completed
- ✅ Migration system set up
- ✅ All migrations applied
- ✅ Core tables created (drivers, driver_locations)
- ✅ History tables created (migration_history, status_history)
- ✅ Facilities table created with sample data

### Optional Next Steps
1. **Import more facilities** - See [FACILITIES_IMPORT.md](FACILITIES_IMPORT.md)
   - Options: OpenStreetMap (free), TruckMaster API (paid), manual entry
   - Current: 5 sample facilities for testing

2. **Test the app-open endpoint** - Should now show facility names:
   ```bash
   curl -X POST https://your-api.com/api/v1/locations/app-open \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"latitude": 34.0522, "longitude": -118.2437}'
   ```

3. **Deploy to production** - See [DEPLOYMENT.md](../DEPLOYMENT.md)

---

## Table Dependency Graph

```
auth.users (Supabase managed)
    ↓
drivers (exists)
    ↓
    ├─→ driver_locations (exists)
    └─→ status_history (missing - should exist)

facilities (optional, future)
```

---

## Why Some Tables Exist But Others Don't

**What Happened:**
1. You manually ran SQL to create `drivers` and `driver_locations` tables when backend was throwing errors
2. This got the app working quickly
3. But the migration system wasn't used, so `migration_history` and `status_history` weren't created

**Solution:**
Running `./migrations/run_migrations.sh` will:
- Detect that `drivers` and `driver_locations` already exist
- Skip recreating them (uses `IF NOT EXISTS`)
- Create the missing `migration_history` and `status_history` tables
- Record everything properly for production

---

## For Production Deployment

When deploying to production:
1. Set DATABASE_URL environment variable
2. Run `./migrations/run_migrations.sh`
3. All 4 required tables will be created in correct order
4. Migration history will track everything

See [DEPLOYMENT.md](../DEPLOYMENT.md) for full production checklist.
