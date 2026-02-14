-- Migration: 016_add_load_type_to_detention
-- Description: Add load_type column to detention_sessions (pickup/dropoff/both/none)
-- Date: 2026-02-13

ALTER TABLE detention_sessions
ADD COLUMN IF NOT EXISTS load_type VARCHAR(20) CHECK (load_type IN (
    'pickup',     -- Picking up a load (at shipper)
    'dropoff',    -- Dropping off a load (at receiver)
    'both',       -- Both pickup and dropoff
    'none'        -- Not load-related (truck stop, mechanic, etc.)
));
