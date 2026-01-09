-- Migration Fix for Existing Database
-- Run this to fix the issues in your current Supabase database

-- ============================================================================
-- FIX 1: Fix drivers table status default
-- ============================================================================

-- Change default from 'white' to 'parked' (one of the valid enum values)
ALTER TABLE drivers ALTER COLUMN status SET DEFAULT 'parked';

-- Optional: Update any existing 'white' statuses to 'parked'
-- (Only run if there are existing drivers with invalid status)
-- UPDATE drivers SET status = 'parked' WHERE status = 'white';

-- ============================================================================
-- FIX 2: Change avatar_id from VARCHAR(50) to TEXT
-- ============================================================================

-- This allows for full avatar URLs instead of just IDs
ALTER TABLE drivers ALTER COLUMN avatar_id TYPE TEXT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check the changes
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'drivers'
  AND column_name IN ('status', 'avatar_id');

-- Should show:
-- status    | character varying | 'parked'::character varying
-- avatar_id | text             | (no default)
