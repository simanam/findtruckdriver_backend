-- Migration: 015_add_detention_sessions
-- Description: Add detention tracking sessions table + facility detention aggregates
-- Date: 2026-02-13
-- Dependencies: Phase 1 (auth), drivers table (001), reviewed_facilities table (014)

-- ============================================================================
-- DETENTION SESSIONS TABLE
-- ============================================================================
-- Tracks driver check-in/check-out at facilities for detention time tracking.
-- Links to reviewed_facilities (which has Google Places integration).

CREATE TABLE IF NOT EXISTS detention_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,

    -- Facility reference (from reviewed_facilities - has Google Places data, reviews, etc.)
    reviewed_facility_id UUID NOT NULL REFERENCES reviewed_facilities(id) ON DELETE SET NULL,

    -- Session timing
    checked_in_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checked_out_at TIMESTAMPTZ,

    -- Location at check-in (exact, for proximity verification)
    checkin_latitude DOUBLE PRECISION NOT NULL,
    checkin_longitude DOUBLE PRECISION NOT NULL,

    -- Location at check-out (to detect if they left vs checked out in place)
    checkout_latitude DOUBLE PRECISION,
    checkout_longitude DOUBLE PRECISION,

    -- Detention calculation
    free_time_minutes INT NOT NULL DEFAULT 120,  -- User's configured free time at time of session
    total_time_minutes INT,                       -- Calculated on checkout: (checked_out_at - checked_in_at) in minutes
    detention_time_minutes INT,                   -- max(0, total_time - free_time)

    -- Checkout method
    checkout_type VARCHAR(20) CHECK (checkout_type IN (
        'manual',         -- User tapped "Check Out" while at facility
        'auto_detected',  -- System detected user left facility, user confirmed
        'manual_entry',   -- User entered departure time manually (forgot to check out)
        'expired'         -- Session auto-expired after 24h with no activity
    )),

    -- Session state
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN (
        'active',       -- Currently checked in at facility
        'completed',    -- Checked out (any method)
        'cancelled'     -- User cancelled without completing
    )),

    -- Optional notes from driver
    notes TEXT,

    -- PDF proof tracking
    proof_generated_at TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_detention_sessions_driver
    ON detention_sessions(driver_id, checked_in_at DESC);

CREATE INDEX IF NOT EXISTS idx_detention_sessions_facility
    ON detention_sessions(reviewed_facility_id, checked_in_at DESC);

CREATE INDEX IF NOT EXISTS idx_detention_sessions_active
    ON detention_sessions(driver_id) WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_detention_sessions_completed
    ON detention_sessions(status, checked_in_at DESC) WHERE status = 'completed';

CREATE INDEX IF NOT EXISTS idx_detention_sessions_detention
    ON detention_sessions(reviewed_facility_id, detention_time_minutes DESC)
    WHERE status = 'completed' AND detention_time_minutes > 0;

-- Enable RLS
ALTER TABLE detention_sessions ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Drivers can read own sessions" ON detention_sessions;
CREATE POLICY "Drivers can read own sessions" ON detention_sessions
    FOR SELECT
    USING (driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS "Drivers can insert own sessions" ON detention_sessions;
CREATE POLICY "Drivers can insert own sessions" ON detention_sessions
    FOR INSERT
    WITH CHECK (driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS "Drivers can update own sessions" ON detention_sessions;
CREATE POLICY "Drivers can update own sessions" ON detention_sessions
    FOR UPDATE
    USING (driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid()));

-- ============================================================================
-- ADD DETENTION PREFERENCE TO DRIVERS TABLE
-- ============================================================================
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS detention_free_time_minutes INT DEFAULT 120;

-- ============================================================================
-- ADD DETENTION AGGREGATES TO REVIEWED_FACILITIES TABLE
-- ============================================================================
ALTER TABLE reviewed_facilities
    ADD COLUMN IF NOT EXISTS avg_detention_minutes NUMERIC(6,1) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_detention_sessions INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS detention_percentage NUMERIC(4,1) DEFAULT 0;

-- ============================================================================
-- TRIGGER: Auto-recalculate facility detention aggregates
-- ============================================================================
CREATE OR REPLACE FUNCTION recalculate_facility_detention()
RETURNS TRIGGER AS $$
DECLARE
    fac_id UUID;
BEGIN
    IF TG_OP = 'DELETE' THEN
        fac_id := OLD.reviewed_facility_id;
    ELSE
        fac_id := NEW.reviewed_facility_id;
    END IF;

    -- Skip if facility id is null
    IF fac_id IS NULL THEN
        RETURN COALESCE(NEW, OLD);
    END IF;

    UPDATE reviewed_facilities SET
        avg_detention_minutes = COALESCE(
            (SELECT ROUND(AVG(detention_time_minutes)::numeric, 1)
             FROM detention_sessions
             WHERE reviewed_facility_id = fac_id
             AND status = 'completed'
             AND detention_time_minutes > 0),
            0
        ),
        total_detention_sessions = (
            SELECT COUNT(*) FROM detention_sessions
            WHERE reviewed_facility_id = fac_id AND status = 'completed'
        ),
        detention_percentage = COALESCE(
            (SELECT ROUND(
                (COUNT(*) FILTER (WHERE detention_time_minutes > 0)::numeric /
                 NULLIF(COUNT(*)::numeric, 0)) * 100, 1
            ) FROM detention_sessions
            WHERE reviewed_facility_id = fac_id AND status = 'completed'),
            0
        ),
        updated_at = NOW()
    WHERE id = fac_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_recalculate_detention ON detention_sessions;
CREATE TRIGGER trigger_recalculate_detention
    AFTER INSERT OR UPDATE OR DELETE ON detention_sessions
    FOR EACH ROW EXECUTE FUNCTION recalculate_facility_detention();

-- ============================================================================
-- TRIGGER: Auto-update updated_at on detention_sessions
-- ============================================================================
CREATE OR REPLACE FUNCTION update_detention_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_detention_sessions_updated_at ON detention_sessions;
CREATE TRIGGER trigger_detention_sessions_updated_at
    BEFORE UPDATE ON detention_sessions
    FOR EACH ROW EXECUTE FUNCTION update_detention_sessions_updated_at();

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO migration_history (migration_name, description)
VALUES ('015_add_detention_sessions', 'Add detention tracking sessions table + facility detention aggregates')
ON CONFLICT (migration_name) DO NOTHING;
