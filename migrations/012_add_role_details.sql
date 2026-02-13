-- Migration 012: Add role_details JSONB column to professional_profiles
-- Stores role-specific verified data (FMCSA, Google Places, mechanic specialties, etc.)

ALTER TABLE professional_profiles
ADD COLUMN IF NOT EXISTS role_details JSONB DEFAULT '{}'::jsonb;

-- Add a comment for documentation
COMMENT ON COLUMN professional_profiles.role_details IS 'Role-specific data: FMCSA verification, Google Places verification, mechanic specialties, dispatcher info, broker details';
