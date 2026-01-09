-- Migration: 003_add_facilities
-- Description: Add truck stops, rest areas, and parking facilities
-- Date: 2026-01-09
-- Author: Backend Team

-- ============================================================================
-- FACILITIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS facilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('truck_stop', 'rest_area', 'parking', 'service_plaza', 'weigh_station')),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    country VARCHAR(2) DEFAULT 'US',
    phone VARCHAR(20),
    website TEXT,
    amenities JSONB DEFAULT '{}',
    parking_spaces INT,
    is_open_24h BOOLEAN DEFAULT false,
    brand VARCHAR(100),
    geohash VARCHAR(12),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_facilities_geohash ON facilities(geohash);
CREATE INDEX IF NOT EXISTS idx_facilities_type ON facilities(type);
CREATE INDEX IF NOT EXISTS idx_facilities_state ON facilities(state);
CREATE INDEX IF NOT EXISTS idx_facilities_brand ON facilities(brand);
CREATE INDEX IF NOT EXISTS idx_facilities_location ON facilities(latitude, longitude);

-- GIN index for JSONB amenities search
CREATE INDEX IF NOT EXISTS idx_facilities_amenities ON facilities USING GIN (amenities);

-- Enable RLS
ALTER TABLE facilities ENABLE ROW LEVEL SECURITY;

-- RLS Policies - Public read access (facilities are public data)
DROP POLICY IF EXISTS "Public read facilities" ON facilities;
CREATE POLICY "Public read facilities" ON facilities
    FOR SELECT
    USING (true);

-- Only admins can modify facilities (we'll add admin role later if needed)
-- For now, use service role key for data imports

-- ============================================================================
-- HELPER FUNCTION: Calculate geohash for facilities
-- ============================================================================
-- Note: This is a simple geohash implementation
-- For production, consider using PostGIS ST_GeoHash or a proper geohash library

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO migration_history (migration_name, description)
VALUES ('003_add_facilities', 'Add truck stops, rest areas, and parking facilities')
ON CONFLICT (migration_name) DO NOTHING;
