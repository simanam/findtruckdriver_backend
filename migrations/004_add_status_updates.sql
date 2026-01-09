-- Migration: 004_add_status_updates
-- Description: Add status updates table with context tracking and follow-up questions
-- Date: 2026-01-09
-- Author: Backend Team

-- ============================================================================
-- STATUS UPDATES TABLE (Enhanced tracking with context)
-- ============================================================================
CREATE TABLE IF NOT EXISTS status_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,

    -- Current status info
    status VARCHAR(20) NOT NULL CHECK (status IN ('rolling', 'waiting', 'parked')),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    facility_id UUID REFERENCES facilities(id),

    -- Previous status context (captured at write time)
    prev_status VARCHAR(20),
    prev_latitude FLOAT,
    prev_longitude FLOAT,
    prev_facility_id UUID REFERENCES facilities(id),
    prev_updated_at TIMESTAMPTZ,

    -- Calculated context fields
    time_since_last_seconds INT,  -- Seconds since last update
    distance_from_last_miles FLOAT,  -- Miles from previous location

    -- Follow-up question (if shown)
    follow_up_question_type VARCHAR(100),  -- e.g., 'detention_payment', 'parking_safety'
    follow_up_question_text TEXT,
    follow_up_options JSONB,  -- Array of options shown
    follow_up_skippable BOOLEAN DEFAULT true,
    follow_up_auto_dismiss_seconds INT,

    -- Follow-up response (if answered)
    follow_up_response VARCHAR(50),
    follow_up_response_text TEXT,
    follow_up_answered_at TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_status_updates_driver ON status_updates(driver_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_status_updates_facility ON status_updates(facility_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_status_updates_transition ON status_updates(prev_status, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_status_updates_question_type ON status_updates(follow_up_question_type) WHERE follow_up_question_type IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_status_updates_unanswered ON status_updates(driver_id, follow_up_answered_at) WHERE follow_up_question_type IS NOT NULL AND follow_up_answered_at IS NULL;

-- Enable RLS
ALTER TABLE status_updates ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Drivers can read own updates" ON status_updates;
CREATE POLICY "Drivers can read own updates" ON status_updates
    FOR SELECT
    USING (driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS "Drivers can insert own updates" ON status_updates;
CREATE POLICY "Drivers can insert own updates" ON status_updates
    FOR INSERT
    WITH CHECK (driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS "Drivers can update own updates" ON status_updates;
CREATE POLICY "Drivers can update own updates" ON status_updates
    FOR UPDATE
    USING (driver_id IN (SELECT id FROM drivers WHERE user_id = auth.uid()));

-- Public read access for aggregated analytics (future)
DROP POLICY IF EXISTS "Public read aggregated data" ON status_updates;
CREATE POLICY "Public read aggregated data" ON status_updates
    FOR SELECT
    USING (
        -- Allow reading for analytics, but hide personal details
        -- We'll handle this at application level for now
        false
    );

-- ============================================================================
-- FACILITY METRICS TABLE (Aggregated data from status updates)
-- ============================================================================
CREATE TABLE IF NOT EXISTS facility_metrics (
    facility_id UUID PRIMARY KEY REFERENCES facilities(id) ON DELETE CASCADE,

    -- Wait time statistics
    avg_wait_minutes INT DEFAULT 0,
    median_wait_minutes INT DEFAULT 0,
    min_wait_minutes INT DEFAULT 0,
    max_wait_minutes INT DEFAULT 0,
    wait_reports_count INT DEFAULT 0,
    wait_last_updated TIMESTAMPTZ,

    -- Detention payment statistics
    detention_paid_count INT DEFAULT 0,
    detention_unpaid_count INT DEFAULT 0,
    detention_unknown_count INT DEFAULT 0,
    detention_paid_percentage FLOAT DEFAULT 0,
    detention_last_updated TIMESTAMPTZ,

    -- Current facility flow (real-time)
    current_flow VARCHAR(20),  -- steady, slow, frozen, null
    flow_updated_at TIMESTAMPTZ,
    drivers_waiting_now INT DEFAULT 0,

    -- Parking safety (for truck stops)
    safety_positive_count INT DEFAULT 0,
    safety_negative_count INT DEFAULT 0,
    safety_percentage FLOAT DEFAULT 0,
    safety_last_updated TIMESTAMPTZ,

    -- Metadata
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_facility_metrics_wait_time ON facility_metrics(avg_wait_minutes DESC) WHERE wait_reports_count > 0;
CREATE INDEX IF NOT EXISTS idx_facility_metrics_detention ON facility_metrics(detention_paid_percentage) WHERE detention_paid_count + detention_unpaid_count > 0;
CREATE INDEX IF NOT EXISTS idx_facility_metrics_flow ON facility_metrics(current_flow, flow_updated_at DESC) WHERE current_flow IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_facility_metrics_safety ON facility_metrics(safety_percentage DESC) WHERE safety_positive_count + safety_negative_count > 0;

-- Enable RLS (public read)
ALTER TABLE facility_metrics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read facility metrics" ON facility_metrics;
CREATE POLICY "Public read facility metrics" ON facility_metrics
    FOR SELECT
    USING (true);

-- ============================================================================
-- HELPER FUNCTION: Get previous status for a driver
-- ============================================================================
CREATE OR REPLACE FUNCTION get_previous_status(p_driver_id UUID)
RETURNS TABLE (
    status VARCHAR(20),
    latitude FLOAT,
    longitude FLOAT,
    facility_id UUID,
    updated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        su.status,
        su.latitude,
        su.longitude,
        su.facility_id,
        su.created_at
    FROM status_updates su
    WHERE su.driver_id = p_driver_id
    ORDER BY su.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO migration_history (migration_name, description)
VALUES ('004_add_status_updates', 'Add status updates table with context tracking and follow-up questions')
ON CONFLICT (migration_name) DO NOTHING;
