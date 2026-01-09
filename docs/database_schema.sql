-- Find a Truck Driver - Complete Database Schema
-- Run this in Supabase SQL Editor

-- Enable PostGIS for location features
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================================
-- DRIVERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    handle VARCHAR(30) UNIQUE NOT NULL,
    avatar_id TEXT NOT NULL,  -- Changed from VARCHAR(50) to support full URLs
    status VARCHAR(20) DEFAULT 'parked' CHECK (status IN ('rolling', 'waiting', 'parked')),  -- Fixed: was 'white'
    last_active TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- If table already exists, fix the status column
-- ALTER TABLE drivers ALTER COLUMN avatar_id TYPE TEXT;
-- ALTER TABLE drivers ALTER COLUMN status SET DEFAULT 'parked';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_drivers_user_id ON drivers(user_id);
CREATE INDEX IF NOT EXISTS idx_drivers_handle ON drivers(handle);
CREATE INDEX IF NOT EXISTS idx_drivers_status ON drivers(status) WHERE last_active > NOW() - INTERVAL '30 minutes';
CREATE INDEX IF NOT EXISTS idx_drivers_last_active ON drivers(last_active DESC);

-- Enable RLS
ALTER TABLE drivers ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Public read access" ON drivers;
CREATE POLICY "Public read access" ON drivers
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "User update own" ON drivers;
CREATE POLICY "User update own" ON drivers
    FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "User insert own" ON drivers;
CREATE POLICY "User insert own" ON drivers
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- DRIVER LOCATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS driver_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID REFERENCES drivers(id) ON DELETE CASCADE,
    location GEOGRAPHY(POINT, 4326) NOT NULL,          -- Raw location (never exposed)
    fuzzed_location GEOGRAPHY(POINT, 4326) NOT NULL,   -- Display location (fuzzed)
    accuracy FLOAT,
    heading FLOAT,                                      -- Direction of travel (0-360)
    speed FLOAT,                                        -- Speed in mph
    geohash VARCHAR(12),                                -- For spatial queries
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_driver_locations_driver_id ON driver_locations(driver_id);
CREATE INDEX IF NOT EXISTS idx_driver_locations_geohash ON driver_locations(geohash);
CREATE INDEX IF NOT EXISTS idx_driver_locations_recorded ON driver_locations(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_driver_locations_spatial ON driver_locations USING GIST(fuzzed_location);

-- Keep only last 100 locations per driver (optional cleanup)
-- Can be done via background job

-- Enable RLS
ALTER TABLE driver_locations ENABLE ROW LEVEL SECURITY;

-- RLS Policies - Only return fuzzed locations
DROP POLICY IF EXISTS "Public read fuzzed locations" ON driver_locations;
CREATE POLICY "Public read fuzzed locations" ON driver_locations
    FOR SELECT
    USING (true);

-- ============================================================================
-- STATUS HISTORY TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID REFERENCES drivers(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('rolling', 'waiting', 'parked')),
    location_id UUID REFERENCES driver_locations(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    duration_mins INT GENERATED ALWAYS AS (
        CASE
            WHEN ended_at IS NOT NULL THEN EXTRACT(EPOCH FROM (ended_at - started_at)) / 60
            ELSE NULL
        END
    ) STORED
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_status_history_driver_id ON status_history(driver_id);
CREATE INDEX IF NOT EXISTS idx_status_history_started ON status_history(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_status_history_status ON status_history(status);

-- Enable RLS
ALTER TABLE status_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Public read status history" ON status_history;
CREATE POLICY "Public read status history" ON status_history
    FOR SELECT
    USING (true);

-- ============================================================================
-- FACILITIES TABLE (Truck Stops, Warehouses, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS facilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) CHECK (type IN ('truck_stop', 'warehouse', 'rest_area', 'distribution_center', 'other')),
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    address TEXT,
    geohash VARCHAR(12),
    amenities JSONB,  -- { "showers": true, "restaurant": true, "parking_spots": 120 }
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_facilities_geohash ON facilities(geohash);
CREATE INDEX IF NOT EXISTS idx_facilities_type ON facilities(type);
CREATE INDEX IF NOT EXISTS idx_facilities_spatial ON facilities USING GIST(location);

-- Enable RLS
ALTER TABLE facilities ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Public read facilities" ON facilities;
CREATE POLICY "Public read facilities" ON facilities
    FOR SELECT
    USING (true);

-- ============================================================================
-- HOTSPOTS TABLE (Auto-detected detention areas)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hotspots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    type VARCHAR(50),
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    geohash VARCHAR(12),
    avg_wait_mins INT DEFAULT 0,
    drivers_waiting INT DEFAULT 0,
    facility_id UUID REFERENCES facilities(id),  -- Link to facility if known
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_hotspots_geohash ON hotspots(geohash);
CREATE INDEX IF NOT EXISTS idx_hotspots_spatial ON hotspots USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_hotspots_facility ON hotspots(facility_id);

-- Enable RLS
ALTER TABLE hotspots ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Public read hotspots" ON hotspots;
CREATE POLICY "Public read hotspots" ON hotspots
    FOR SELECT
    USING (true);

-- ============================================================================
-- OTP VERIFICATION TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS otp_verification (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_hash VARCHAR(255) NOT NULL,
    code_hash VARCHAR(255) NOT NULL,  -- Store hashed OTP
    expires_at TIMESTAMPTZ NOT NULL,
    attempts INT DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_otp_phone_hash ON otp_verification(phone_hash);
CREATE INDEX IF NOT EXISTS idx_otp_expires ON otp_verification(expires_at);

-- Cleanup expired OTPs (run via cron)
-- DELETE FROM otp_verification WHERE expires_at < NOW() - INTERVAL '1 day';

-- ============================================================================
-- FACILITY STATS TABLE (Pre-aggregated for performance)
-- ============================================================================
CREATE TABLE IF NOT EXISTS facility_stats (
    facility_id UUID PRIMARY KEY REFERENCES facilities(id) ON DELETE CASCADE,
    rolling_count INT DEFAULT 0,
    waiting_count INT DEFAULT 0,
    parked_count INT DEFAULT 0,
    total_count INT DEFAULT 0,
    avg_wait_mins INT,
    wait_count_24h INT DEFAULT 0,
    wait_total_mins_24h INT DEFAULT 0,
    hero_driver_id UUID REFERENCES drivers(id),
    ring_driver_ids UUID[],  -- Array of up to 6 driver IDs for avatar ring
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_facility_stats_total ON facility_stats(total_count DESC);
CREATE INDEX IF NOT EXISTS idx_facility_stats_waiting ON facility_stats(waiting_count DESC);

-- ============================================================================
-- CLUSTER STATS TABLE (Pre-aggregated by geohash)
-- ============================================================================
CREATE TABLE IF NOT EXISTS cluster_stats (
    geohash VARCHAR(8) PRIMARY KEY,
    precision INT NOT NULL,  -- 2 = region, 4 = cluster, 6 = metro
    rolling_count INT DEFAULT 0,
    waiting_count INT DEFAULT 0,
    parked_count INT DEFAULT 0,
    total_count INT DEFAULT 0,
    hero_driver_id UUID REFERENCES drivers(id),
    hero_avatar_id TEXT,
    hero_handle VARCHAR(30),
    hero_updated_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_cluster_stats_precision ON cluster_stats(precision);
CREATE INDEX IF NOT EXISTS idx_cluster_stats_geohash_prefix ON cluster_stats(LEFT(geohash, 2));
CREATE INDEX IF NOT EXISTS idx_cluster_stats_total ON cluster_stats(total_count DESC);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to update driver's last_active timestamp
CREATE OR REPLACE FUNCTION update_driver_last_active()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE drivers
    SET last_active = NEW.recorded_at
    WHERE id = NEW.driver_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update last_active on location insert
DROP TRIGGER IF EXISTS trigger_update_last_active ON driver_locations;
CREATE TRIGGER trigger_update_last_active
    AFTER INSERT ON driver_locations
    FOR EACH ROW
    EXECUTE FUNCTION update_driver_last_active();

-- Function to calculate distance between two points in miles
CREATE OR REPLACE FUNCTION distance_miles(
    lat1 FLOAT,
    lon1 FLOAT,
    lat2 FLOAT,
    lon2 FLOAT
)
RETURNS FLOAT AS $$
BEGIN
    RETURN ST_Distance(
        ST_MakePoint(lon1, lat1)::geography,
        ST_MakePoint(lon2, lat2)::geography
    ) * 0.000621371;  -- Convert meters to miles
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- VIEWS (Optional - for convenient querying)
-- ============================================================================

-- View: Active drivers with their latest location
CREATE OR REPLACE VIEW active_drivers_with_location AS
SELECT
    d.id,
    d.user_id,
    d.handle,
    d.avatar_id,
    d.status,
    d.last_active,
    dl.fuzzed_location,
    dl.geohash,
    dl.speed,
    dl.heading,
    dl.recorded_at as location_updated_at
FROM drivers d
LEFT JOIN LATERAL (
    SELECT * FROM driver_locations
    WHERE driver_id = d.id
    ORDER BY recorded_at DESC
    LIMIT 1
) dl ON true
WHERE d.last_active > NOW() - INTERVAL '30 minutes';

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Uncomment to insert sample facility data
/*
INSERT INTO facilities (name, type, location, address, geohash, amenities) VALUES
    ('Loves Travel Stop #247', 'truck_stop',
     ST_SetSRID(ST_MakePoint(-96.0, 36.0), 4326)::geography,
     'I-40 Exit 238, Tulsa, OK',
     '9y4p',
     '{"showers": true, "restaurant": true, "parking_spots": 120}'::jsonb),
    ('Pilot Flying J #892', 'truck_stop',
     ST_SetSRID(ST_MakePoint(-119.7, 36.7), 4326)::geography,
     'Highway 99, Fresno, CA',
     '9q5cs',
     '{"showers": true, "restaurant": true, "fuel": true, "parking_spots": 85}'::jsonb);
*/

-- ============================================================================
-- MAINTENANCE
-- ============================================================================

-- Cleanup old locations (keep last 100 per driver)
-- Run this via cron job
/*
DELETE FROM driver_locations
WHERE id IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY driver_id ORDER BY recorded_at DESC) as rn
        FROM driver_locations
    ) t WHERE rn > 100
);
*/

-- Cleanup expired OTPs
/*
DELETE FROM otp_verification WHERE expires_at < NOW() - INTERVAL '1 day';
*/

-- Remove inactive drivers from active views
/*
UPDATE drivers SET last_active = last_active
WHERE last_active < NOW() - INTERVAL '30 minutes';
*/
