-- Migration: 007_add_parking_type
-- Description: Add truck parking support and metadata fields
-- Date: 2026-01-09
-- Author: Backend Team

-- ============================================================================
-- UPDATE FACILITY TYPE CHECK CONSTRAINT
-- ============================================================================
-- Ensure 'parking' is in the list of valid facility types

-- Drop old constraint
ALTER TABLE facilities DROP CONSTRAINT IF EXISTS facilities_type_check;

-- Add new constraint with 'parking' included
ALTER TABLE facilities ADD CONSTRAINT facilities_type_check
    CHECK (type IN ('truck_stop', 'rest_area', 'parking', 'service_plaza', 'weigh_station', 'warehouse'));

-- ============================================================================
-- ADD PARKING METADATA FIELDS
-- ============================================================================

-- Number of parking spaces
ALTER TABLE facilities
ADD COLUMN IF NOT EXISTS parking_spaces INT;

-- TPIMS (Truck Parking Information Management System) support
ALTER TABLE facilities
ADD COLUMN IF NOT EXISTS has_tpims BOOLEAN DEFAULT FALSE;

ALTER TABLE facilities
ADD COLUMN IF NOT EXISTS tpims_facility_id VARCHAR(100);

-- Support multiple data sources (e.g., ["openstreetmap", "usdot_ntad"])
ALTER TABLE facilities
ADD COLUMN IF NOT EXISTS data_sources TEXT[] DEFAULT ARRAY['manual'];

-- ============================================================================
-- ADD INDEXES FOR PERFORMANCE
-- ============================================================================

-- Composite index for location-based queries (bounding box searches)
CREATE INDEX IF NOT EXISTS idx_facilities_location
ON facilities (latitude, longitude);

-- Index for data source queries
CREATE INDEX IF NOT EXISTS idx_facilities_data_source
ON facilities (data_source);

-- Index for facility type queries
CREATE INDEX IF NOT EXISTS idx_facilities_type
ON facilities (type);

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO migration_history (migration_name, description)
VALUES ('007_add_parking_type', 'Add truck parking type and metadata fields for DOT data integration')
ON CONFLICT (migration_name) DO NOTHING;
