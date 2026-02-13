-- Migration 011: Add company_start_date to professional_profiles
-- Tracks when the driver started at their current company

ALTER TABLE professional_profiles
ADD COLUMN IF NOT EXISTS company_start_date TEXT DEFAULT NULL;

-- Track migration
INSERT INTO migration_history (migration_name, description)
VALUES ('011_add_company_start_date', 'Add company_start_date column to professional_profiles')
ON CONFLICT DO NOTHING;
