-- Migration: 014_add_facility_reviews
-- Description: Facility reviews with category ratings, reviewed_facilities lookup, review history
-- Date: 2026-02-12
-- Dependencies: Phase 1 (auth), facilities table (003)

-- ============================================================================
-- REVIEWED FACILITIES TABLE
-- ============================================================================
-- Stores facilities that users have searched for and reviewed.
-- Seeded from Google Places API on first search, then cached locally.
-- Also links to existing facilities table entries when applicable.

CREATE TABLE IF NOT EXISTS reviewed_facilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to existing facilities table (if this is a known truck stop, rest area, etc.)
    facility_id UUID REFERENCES facilities(id) ON DELETE SET NULL,

    -- Facility identity
    name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(50) NOT NULL CHECK (facility_type IN (
        'shipper', 'receiver', 'warehouse', 'mechanic', 'truck_stop',
        'rest_area', 'broker', 'weigh_station', 'service_plaza', 'other'
    )),

    -- Location
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(10),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geohash VARCHAR(12),

    -- Contact
    phone VARCHAR(20),
    website TEXT,

    -- Google Places data (cached to avoid re-fetching)
    google_place_id VARCHAR(255) UNIQUE,
    google_data JSONB,
    google_rating NUMERIC(2,1),
    google_review_count INT,

    -- Type detection (auto-detect from Google + quick-confirm by first reviewer)
    auto_detected_type VARCHAR(50),
    type_confirmed BOOLEAN DEFAULT false,
    type_confirmed_by UUID REFERENCES drivers(id) ON DELETE SET NULL,
    type_correction_count INT DEFAULT 0,

    -- Our aggregated ratings
    avg_overall_rating NUMERIC(2,1) DEFAULT 0,
    total_reviews INT DEFAULT 0,
    category_averages JSONB DEFAULT '{}',
    -- e.g. {"dock_wait_time": 3.5, "parking": 4.2, "safety": 4.8}

    -- How coordinates were obtained
    location_source VARCHAR(20) DEFAULT 'unknown' CHECK (location_source IN (
        'google', 'driver_gps', 'manual', 'unknown'
    )),

    -- Metadata
    added_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_reviewed_facilities_type ON reviewed_facilities(facility_type);
CREATE INDEX IF NOT EXISTS idx_reviewed_facilities_geohash ON reviewed_facilities(geohash);
CREATE INDEX IF NOT EXISTS idx_reviewed_facilities_location ON reviewed_facilities(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_reviewed_facilities_state ON reviewed_facilities(state);
CREATE INDEX IF NOT EXISTS idx_reviewed_facilities_google_place ON reviewed_facilities(google_place_id);
CREATE INDEX IF NOT EXISTS idx_reviewed_facilities_facility ON reviewed_facilities(facility_id);
CREATE INDEX IF NOT EXISTS idx_reviewed_facilities_avg_rating ON reviewed_facilities(avg_overall_rating DESC);

-- Enable RLS
ALTER TABLE reviewed_facilities ENABLE ROW LEVEL SECURITY;

-- Public read
DROP POLICY IF EXISTS "Public read reviewed_facilities" ON reviewed_facilities;
CREATE POLICY "Public read reviewed_facilities" ON reviewed_facilities
    FOR SELECT USING (true);

-- Authenticated users can add facilities
DROP POLICY IF EXISTS "Authenticated insert reviewed_facilities" ON reviewed_facilities;
CREATE POLICY "Authenticated insert reviewed_facilities" ON reviewed_facilities
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- ============================================================================
-- FACILITY REVIEWS TABLE
-- ============================================================================
-- One active review per user per facility (Google model).
-- When a user updates their review, the old version is archived to review_history.
-- visit_count tracks how many times the reviewer has been there.

CREATE TABLE IF NOT EXISTS facility_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reviewed_facility_id UUID NOT NULL REFERENCES reviewed_facilities(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,

    -- Overall rating
    overall_rating SMALLINT NOT NULL CHECK (overall_rating BETWEEN 1 AND 5),

    -- Category ratings (type-specific, stored as JSONB)
    -- e.g. {"dock_wait_time": 4, "parking": 3, "safety": 5}
    category_ratings JSONB NOT NULL DEFAULT '{}',

    -- Optional text review
    comment TEXT,

    -- Review metadata
    visit_date DATE,
    would_return BOOLEAN,

    -- Visit frequency: how many times the reviewer has been here
    -- Gives readers context ("regular visitor rates it 4 stars" vs "first-timer")
    visit_count VARCHAR(20) DEFAULT 'first_visit' CHECK (visit_count IN (
        'first_visit', '2_to_5', '6_to_10', 'regular'
    )),

    -- How many times this review has been updated (0 = original, 1+ = edited)
    revision_number INT DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- One active review per user per facility (Google model)
    UNIQUE(reviewed_facility_id, reviewer_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_facility_reviews_facility ON facility_reviews(reviewed_facility_id);
CREATE INDEX IF NOT EXISTS idx_facility_reviews_reviewer ON facility_reviews(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_facility_reviews_rating ON facility_reviews(overall_rating);
CREATE INDEX IF NOT EXISTS idx_facility_reviews_created ON facility_reviews(created_at DESC);

-- Enable RLS
ALTER TABLE facility_reviews ENABLE ROW LEVEL SECURITY;

-- Public read
DROP POLICY IF EXISTS "Public read facility_reviews" ON facility_reviews;
CREATE POLICY "Public read facility_reviews" ON facility_reviews
    FOR SELECT USING (true);

-- Users can create their own reviews
DROP POLICY IF EXISTS "Users insert own reviews" ON facility_reviews;
CREATE POLICY "Users insert own reviews" ON facility_reviews
    FOR INSERT WITH CHECK (
        reviewer_id IN (SELECT id FROM drivers WHERE user_id = auth.uid())
    );

-- Users can update their own reviews
DROP POLICY IF EXISTS "Users update own reviews" ON facility_reviews;
CREATE POLICY "Users update own reviews" ON facility_reviews
    FOR UPDATE USING (
        reviewer_id IN (SELECT id FROM drivers WHERE user_id = auth.uid())
    );

-- Users can delete their own reviews
DROP POLICY IF EXISTS "Users delete own reviews" ON facility_reviews;
CREATE POLICY "Users delete own reviews" ON facility_reviews
    FOR DELETE USING (
        reviewer_id IN (SELECT id FROM drivers WHERE user_id = auth.uid())
    );

-- ============================================================================
-- REVIEW HISTORY TABLE
-- ============================================================================
-- Archives previous versions of reviews when a user updates their review.
-- Preserves the full history: what they originally said, what changed, when.
-- Read-only — users don't interact with this table directly.

CREATE TABLE IF NOT EXISTS facility_review_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Which active review this is a snapshot of
    review_id UUID NOT NULL REFERENCES facility_reviews(id) ON DELETE CASCADE,
    reviewed_facility_id UUID NOT NULL,
    reviewer_id UUID NOT NULL,

    -- Snapshot of the old review data
    overall_rating SMALLINT NOT NULL,
    category_ratings JSONB NOT NULL DEFAULT '{}',
    comment TEXT,
    visit_date DATE,
    would_return BOOLEAN,
    visit_count VARCHAR(20),
    revision_number INT NOT NULL,

    -- When this version was active
    original_created_at TIMESTAMPTZ NOT NULL,
    original_updated_at TIMESTAMPTZ NOT NULL,
    archived_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_history_review ON facility_review_history(review_id);
CREATE INDEX IF NOT EXISTS idx_review_history_facility ON facility_review_history(reviewed_facility_id);
CREATE INDEX IF NOT EXISTS idx_review_history_reviewer ON facility_review_history(reviewer_id);

-- Enable RLS
ALTER TABLE facility_review_history ENABLE ROW LEVEL SECURITY;

-- Public read (history is transparent)
DROP POLICY IF EXISTS "Public read review_history" ON facility_review_history;
CREATE POLICY "Public read review_history" ON facility_review_history
    FOR SELECT USING (true);

-- Only system (admin client) inserts into history — no direct user writes
-- (Archival happens in the application layer via admin client)

-- ============================================================================
-- TRIGGERS: Auto-update updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_reviewed_facilities_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_reviewed_facilities_updated_at
    BEFORE UPDATE ON reviewed_facilities
    FOR EACH ROW EXECUTE FUNCTION update_reviewed_facilities_updated_at();

CREATE OR REPLACE FUNCTION update_facility_reviews_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_facility_reviews_updated_at
    BEFORE UPDATE ON facility_reviews
    FOR EACH ROW EXECUTE FUNCTION update_facility_reviews_updated_at();

-- ============================================================================
-- TRIGGER: Auto-recalculate facility averages on review insert/update/delete
-- ============================================================================
CREATE OR REPLACE FUNCTION recalculate_facility_ratings()
RETURNS TRIGGER AS $$
DECLARE
    fac_id UUID;
BEGIN
    -- Get the facility ID (handle INSERT, UPDATE, DELETE)
    IF TG_OP = 'DELETE' THEN
        fac_id := OLD.reviewed_facility_id;
    ELSE
        fac_id := NEW.reviewed_facility_id;
    END IF;

    -- Recalculate averages
    UPDATE reviewed_facilities SET
        avg_overall_rating = COALESCE(
            (SELECT ROUND(AVG(overall_rating)::numeric, 1) FROM facility_reviews WHERE reviewed_facility_id = fac_id),
            0
        ),
        total_reviews = (SELECT COUNT(*) FROM facility_reviews WHERE reviewed_facility_id = fac_id),
        updated_at = NOW()
    WHERE id = fac_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_recalculate_ratings
    AFTER INSERT OR UPDATE OR DELETE ON facility_reviews
    FOR EACH ROW EXECUTE FUNCTION recalculate_facility_ratings();

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO migration_history (migration_name, description)
VALUES ('014_add_facility_reviews', 'Facility reviews with category ratings, reviewed_facilities lookup, and review history')
ON CONFLICT (migration_name) DO NOTHING;
