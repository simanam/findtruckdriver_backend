-- Migration: 009_create_professional_profiles
-- Description: Create professional_profiles table for driver career info
-- Date: 2026-02-12

CREATE TABLE IF NOT EXISTS professional_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    driver_id UUID NOT NULL UNIQUE REFERENCES drivers(id) ON DELETE CASCADE,

    -- Basic professional info
    years_experience INTEGER,
    haul_type VARCHAR(30),  -- 'long_haul', 'regional', 'local', 'otr', 'dedicated'
    equipment_type VARCHAR(50),  -- 'dry_van', 'flatbed', 'reefer', 'tanker', 'hazmat', 'auto_carrier'

    -- License info
    cdl_class VARCHAR(5),  -- 'A', 'B', 'C'
    cdl_state VARCHAR(2),
    endorsements TEXT[],  -- Array: ['H', 'N', 'P', 'S', 'T', 'X']

    -- Professional details
    company_name VARCHAR(100),
    mc_number VARCHAR(20),
    dot_number VARCHAR(20),
    bio TEXT,
    specialties TEXT[],

    -- Calculated fields
    estimated_miles INTEGER,  -- Auto-calculated from years + haul_type

    -- Privacy settings
    is_public BOOLEAN DEFAULT true,
    show_experience BOOLEAN DEFAULT true,
    show_equipment BOOLEAN DEFAULT true,
    show_company BOOLEAN DEFAULT true,
    show_cdl BOOLEAN DEFAULT true,

    -- Open to work
    open_to_work BOOLEAN DEFAULT false,
    looking_for TEXT[],  -- Array: ['company_driver', 'owner_operator', 'team_driver']
    preferred_haul TEXT[],  -- Array: ['long_haul', 'regional', 'local']

    -- Badges (JSON array of badge objects)
    badges JSONB DEFAULT '[]'::jsonb,

    -- Completion tracking
    completion_percentage INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_professional_profiles_driver_id ON professional_profiles(driver_id);
CREATE INDEX IF NOT EXISTS idx_professional_profiles_open_to_work ON professional_profiles(open_to_work) WHERE open_to_work = true;
CREATE INDEX IF NOT EXISTS idx_professional_profiles_is_public ON professional_profiles(is_public) WHERE is_public = true;

-- RLS
ALTER TABLE professional_profiles ENABLE ROW LEVEL SECURITY;

-- Owner can do everything with their own profile
CREATE POLICY IF NOT EXISTS "Users can manage own profile"
    ON professional_profiles FOR ALL
    USING (driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid()))
    WITH CHECK (driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid()));

-- Anyone can read public profiles
CREATE POLICY IF NOT EXISTS "Public profiles are readable"
    ON professional_profiles FOR SELECT
    USING (is_public = true);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_professional_profile_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_professional_profile_updated_at ON professional_profiles;
CREATE TRIGGER trigger_update_professional_profile_updated_at
    BEFORE UPDATE ON professional_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_professional_profile_updated_at();

-- Track migration
INSERT INTO migration_history (migration_name, description)
VALUES ('009_create_professional_profiles', 'Create professional_profiles table for driver career info')
ON CONFLICT (migration_name) DO NOTHING;
