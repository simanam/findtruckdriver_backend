-- Migration: 001_initial_schema
-- Description: Initial database setup with drivers table
-- Date: 2026-01-09
-- Author: Backend Team

-- ============================================================================
-- DRIVERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    handle VARCHAR(30) UNIQUE NOT NULL,
    avatar_id TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'parked' CHECK (status IN ('rolling', 'waiting', 'parked')),
    last_active TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_id UNIQUE (user_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_drivers_user_id ON drivers(user_id);
CREATE INDEX IF NOT EXISTS idx_drivers_handle ON drivers(handle);
CREATE INDEX IF NOT EXISTS idx_drivers_status ON drivers(status) WHERE last_active > NOW() - INTERVAL '30 minutes';
CREATE INDEX IF NOT EXISTS idx_drivers_last_active ON drivers(last_active DESC);

-- Enable RLS
ALTER TABLE drivers ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Public read access" ON drivers;
CREATE POLICY "Public read access" ON drivers
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "User update own" ON drivers;
CREATE POLICY "User update own" ON drivers
    FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "User insert own" ON drivers;
CREATE POLICY "User insert own" ON drivers
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- MIGRATION TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    description TEXT
);

-- Record this migration
INSERT INTO migration_history (migration_name, description)
VALUES ('001_initial_schema', 'Initial database setup with drivers table')
ON CONFLICT (migration_name) DO NOTHING;
