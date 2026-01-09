-- Migration: 006_add_warehouse_type
-- Description: Add 'warehouse' facility type for shippers and distribution centers
-- Date: 2026-01-09
-- Author: Backend Team

-- ============================================================================
-- UPDATE FACILITY TYPE CHECK CONSTRAINT
-- ============================================================================
-- Add 'warehouse' to the list of valid facility types

-- Drop old constraint
ALTER TABLE facilities DROP CONSTRAINT IF EXISTS facilities_type_check;

-- Add new constraint with 'warehouse' included
ALTER TABLE facilities ADD CONSTRAINT facilities_type_check
    CHECK (type IN ('truck_stop', 'rest_area', 'parking', 'service_plaza', 'weigh_station', 'warehouse'));

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO migration_history (migration_name, description)
VALUES ('006_add_warehouse_type', 'Add warehouse facility type for shippers and distribution centers')
ON CONFLICT (migration_name) DO NOTHING;
