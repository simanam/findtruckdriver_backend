-- Migration: 005_add_osm_query_cache
-- Description: Track which geographic regions have been queried from OSM
-- Date: 2026-01-09
-- Author: Backend Team

-- ============================================================================
-- OSM QUERY CACHE TABLE
-- ============================================================================
-- This table tracks which geographic regions we've already queried from OSM
-- to avoid redundant API calls and build facilities database organically

CREATE TABLE IF NOT EXISTS osm_query_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    geohash_prefix VARCHAR(8) NOT NULL UNIQUE,  -- 8-char geohash ≈ 0.6km x 1.2km cell
    center_latitude FLOAT NOT NULL,
    center_longitude FLOAT NOT NULL,
    query_radius_miles FLOAT NOT NULL DEFAULT 5.0,
    facilities_found INT NOT NULL DEFAULT 0,
    last_queried_at TIMESTAMPTZ DEFAULT NOW(),
    query_count INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_osm_cache_geohash ON osm_query_cache(geohash_prefix);
CREATE INDEX IF NOT EXISTS idx_osm_cache_last_queried ON osm_query_cache(last_queried_at);

-- Enable RLS (admin/service role only)
ALTER TABLE osm_query_cache ENABLE ROW LEVEL SECURITY;

-- Public read access (so we can check if area has been queried)
DROP POLICY IF EXISTS "Public read query cache" ON osm_query_cache;
CREATE POLICY "Public read query cache" ON osm_query_cache
    FOR SELECT
    USING (true);

-- Only service role can insert/update (via backend)
-- RLS will prevent direct inserts from authenticated users


-- ============================================================================
-- ADD DATA SOURCE TRACKING TO FACILITIES
-- ============================================================================
-- Track where each facility came from for data quality

ALTER TABLE facilities
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'manual',
ADD COLUMN IF NOT EXISTS osm_id BIGINT,
ADD COLUMN IF NOT EXISTS osm_version INT,
ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_facilities_data_source ON facilities(data_source);
CREATE INDEX IF NOT EXISTS idx_facilities_osm_id ON facilities(osm_id);

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO migration_history (migration_name, description)
VALUES ('005_add_osm_query_cache', 'Add OSM query cache for on-demand facility discovery')
ON CONFLICT (migration_name) DO NOTHING;
