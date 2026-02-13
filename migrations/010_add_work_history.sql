-- Migration 010: Add work_history column to professional_profiles
-- Stores past work experience as a JSONB array
-- Each entry: { company_name, role, start_date (YYYY-MM), end_date (YYYY-MM or null) }

ALTER TABLE professional_profiles
ADD COLUMN IF NOT EXISTS work_history JSONB DEFAULT '[]'::jsonb;

-- Track migration
INSERT INTO migration_history (migration_name, description)
VALUES ('010_add_work_history', 'Add work_history JSONB column to professional_profiles')
ON CONFLICT DO NOTHING;
