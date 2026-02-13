-- Migration: 013_add_job_postings
-- Description: Job board - job_postings table
-- Date: 2026-02-12
-- Dependencies: Phase 2 (professional_profiles), Phase 3 (FMCSA)

-- ============================================================================
-- JOB POSTINGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS job_postings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Who posted it (FK to drivers, since all users are drivers-table entries)
    posted_by UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,

    -- Core job info
    title VARCHAR(200) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    description TEXT,
    how_to_apply TEXT NOT NULL,

    -- FMCSA identifiers (optional, verified if provided)
    mc_number VARCHAR(20),
    dot_number VARCHAR(20),
    fmcsa_verified BOOLEAN DEFAULT false,

    -- Job classification
    haul_type VARCHAR(30) NOT NULL CHECK (haul_type IN (
        'otr', 'regional', 'local', 'dedicated', 'team'
    )),
    equipment VARCHAR(30) NOT NULL CHECK (equipment IN (
        'dry_van', 'reefer', 'flatbed', 'tanker', 'car_hauler',
        'intermodal', 'hazmat', 'oversized', 'ltl', 'other'
    )),

    -- Compensation and requirements
    pay_info TEXT,
    requirements JSONB DEFAULT '[]'::jsonb,
    regions JSONB DEFAULT '[]'::jsonb,

    -- Lifecycle
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================
-- Primary listing query: active jobs, newest first
CREATE INDEX IF NOT EXISTS idx_job_postings_active
    ON job_postings(is_active, created_at DESC)
    WHERE is_active = true;

-- My posted jobs
CREATE INDEX IF NOT EXISTS idx_job_postings_posted_by
    ON job_postings(posted_by, created_at DESC);

-- Filter by haul type
CREATE INDEX IF NOT EXISTS idx_job_postings_haul_type
    ON job_postings(haul_type)
    WHERE is_active = true;

-- Filter by equipment
CREATE INDEX IF NOT EXISTS idx_job_postings_equipment
    ON job_postings(equipment)
    WHERE is_active = true;

-- GIN index for JSONB requirements/regions filtering
CREATE INDEX IF NOT EXISTS idx_job_postings_requirements
    ON job_postings USING GIN (requirements);

CREATE INDEX IF NOT EXISTS idx_job_postings_regions
    ON job_postings USING GIN (regions);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================
ALTER TABLE job_postings ENABLE ROW LEVEL SECURITY;

-- Anyone can read active, non-expired jobs
DROP POLICY IF EXISTS "Public read active jobs" ON job_postings;
CREATE POLICY "Public read active jobs" ON job_postings
    FOR SELECT
    USING (is_active = true AND expires_at > NOW());

-- Poster can read ALL their own jobs (including inactive/expired)
DROP POLICY IF EXISTS "Poster read own jobs" ON job_postings;
CREATE POLICY "Poster read own jobs" ON job_postings
    FOR SELECT
    USING (
        posted_by IN (
            SELECT id FROM drivers WHERE user_id = auth.uid()
        )
    );

-- Only authenticated users can insert (role check done in API layer)
DROP POLICY IF EXISTS "Authenticated insert jobs" ON job_postings;
CREATE POLICY "Authenticated insert jobs" ON job_postings
    FOR INSERT
    WITH CHECK (
        posted_by IN (
            SELECT id FROM drivers WHERE user_id = auth.uid()
        )
    );

-- Only poster can update their own jobs
DROP POLICY IF EXISTS "Poster update own jobs" ON job_postings;
CREATE POLICY "Poster update own jobs" ON job_postings
    FOR UPDATE
    USING (
        posted_by IN (
            SELECT id FROM drivers WHERE user_id = auth.uid()
        )
    );

-- Only poster can delete their own jobs
DROP POLICY IF EXISTS "Poster delete own jobs" ON job_postings;
CREATE POLICY "Poster delete own jobs" ON job_postings
    FOR DELETE
    USING (
        posted_by IN (
            SELECT id FROM drivers WHERE user_id = auth.uid()
        )
    );

-- ============================================================================
-- UPDATED_AT TRIGGER
-- ============================================================================
CREATE OR REPLACE FUNCTION update_job_postings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_job_postings_updated_at ON job_postings;
CREATE TRIGGER trigger_job_postings_updated_at
    BEFORE UPDATE ON job_postings
    FOR EACH ROW
    EXECUTE FUNCTION update_job_postings_updated_at();

-- ============================================================================
-- MIGRATION TRACKING
-- ============================================================================
INSERT INTO migration_history (migration_name, description)
VALUES ('013_add_job_postings', 'Job board - job_postings table with RLS')
ON CONFLICT (migration_name) DO NOTHING;
