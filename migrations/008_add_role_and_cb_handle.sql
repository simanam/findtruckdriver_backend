-- Migration: 008_add_role_and_cb_handle
-- Description: Add role, CB Handle, profile photo, and map display preference to drivers table
-- Date: 2026-02-12

-- Add role column (what they do in the trucking industry)
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS role VARCHAR(30) NOT NULL DEFAULT 'company_driver';

-- Add CB Handle (anonymous map display name)
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS cb_handle VARCHAR(50);

-- Add profile photo URL (separate from avatar_id which is the cartoon)
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS profile_photo_url TEXT;

-- What name to show on the map
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS show_on_map_as VARCHAR(20) DEFAULT 'cb_handle';

-- Index for role lookups
CREATE INDEX IF NOT EXISTS idx_drivers_role ON drivers(role);

-- Ensure CB handle uniqueness (only for non-null values)
CREATE UNIQUE INDEX IF NOT EXISTS idx_drivers_cb_handle ON drivers(cb_handle) WHERE cb_handle IS NOT NULL;

-- Track migration
INSERT INTO migration_history (migration_name, description)
VALUES ('008_add_role_and_cb_handle', 'Add role, CB Handle, profile photo, and map display preference to drivers table')
ON CONFLICT (migration_name) DO NOTHING;
