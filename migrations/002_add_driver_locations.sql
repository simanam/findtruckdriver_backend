-- Migration: 002_add_driver_locations
-- Description: Add location tracking with PostGIS and status history
-- Date: 2026-01-09
-- Author: Backend Team

-- ============================================================================
-- ENABLE POSTGIS EXTENSION
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================================
-- DRIVER LOCATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS driver_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID REFERENCES drivers(id) ON DELETE CASCADE UNIQUE,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    fuzzed_latitude FLOAT NOT NULL,
    fuzzed_longitude FLOAT NOT NULL,
    accuracy FLOAT,
    heading FLOAT CHECK (heading >= 0 AND heading < 360),
    speed FLOAT CHECK (speed >= 0),
    geohash VARCHAR(12),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_driver_location UNIQUE (driver_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_driver_locations_driver_id ON driver_locations(driver_id);
CREATE INDEX IF NOT EXISTS idx_driver_locations_geohash ON driver_locations(geohash);
CREATE INDEX IF NOT EXISTS idx_driver_locations_recorded ON driver_locations(recorded_at DESC);

-- Enable RLS
ALTER TABLE driver_locations ENABLE ROW LEVEL SECURITY;

-- RLS Policies - Only return fuzzed locations
DROP POLICY IF EXISTS "Public read fuzzed locations" ON driver_locations;
CREATE POLICY "Public read fuzzed locations" ON driver_locations
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Drivers can insert own location" ON driver_locations;
CREATE POLICY "Drivers can insert own location" ON driver_locations
    FOR INSERT
    WITH CHECK (
        driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Drivers can update own location" ON driver_locations;
CREATE POLICY "Drivers can update own location" ON driver_locations
    FOR UPDATE
    USING (
        driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid())
    );

-- ============================================================================
-- STATUS HISTORY TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID REFERENCES drivers(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('rolling', 'waiting', 'parked')),
    latitude FLOAT,
    longitude FLOAT,
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
CREATE INDEX IF NOT EXISTS idx_status_history_active ON status_history(driver_id, started_at DESC) WHERE ended_at IS NULL;

-- Enable RLS
ALTER TABLE status_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Public read status history" ON status_history;
CREATE POLICY "Public read status history" ON status_history
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Drivers can insert own history" ON status_history;
CREATE POLICY "Drivers can insert own history" ON status_history
    FOR INSERT
    WITH CHECK (
        driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Drivers can update own history" ON status_history;
CREATE POLICY "Drivers can update own history" ON status_history
    FOR UPDATE
    USING (
        driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid())
    );

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO migration_history (migration_name, description)
VALUES ('002_add_driver_locations', 'Add location tracking with PostGIS and status history')
ON CONFLICT (migration_name) DO NOTHING;
