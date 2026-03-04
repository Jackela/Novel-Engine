-- Migration: V007__add_events_rumors_tables.sql
-- Description: Create history_events and rumors tables for world context persistence
-- Author: Novel Engine Team
-- Date: 2026-03-04

-- =====================================================
-- history_events table
-- =====================================================
CREATE TABLE IF NOT EXISTS history_events (
    id UUID PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    description TEXT,
    event_type VARCHAR(50) NOT NULL,
    significance VARCHAR(50) NOT NULL,
    outcome VARCHAR(50) DEFAULT 'neutral',
    date_description VARCHAR(200) NOT NULL,
    duration_description VARCHAR(200),
    location_ids UUID[] DEFAULT '{}',
    faction_ids UUID[] DEFAULT '{}',
    key_figures TEXT[] DEFAULT '{}',
    causes TEXT[] DEFAULT '{}',
    consequences TEXT[] DEFAULT '{}',
    preceding_event_ids UUID[] DEFAULT '{}',
    following_event_ids UUID[] DEFAULT '{}',
    related_event_ids UUID[] DEFAULT '{}',
    is_secret BOOLEAN DEFAULT FALSE,
    sources TEXT[] DEFAULT '{}',
    narrative_importance INTEGER DEFAULT 50 CHECK (narrative_importance >= 0 AND narrative_importance <= 100),
    impact_scope VARCHAR(50),
    affected_faction_ids UUID[] DEFAULT '{}',
    affected_location_ids UUID[] DEFAULT '{}',
    structured_date JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for history_events
CREATE INDEX IF NOT EXISTS idx_history_events_type ON history_events(event_type);
CREATE INDEX IF NOT EXISTS idx_history_events_significance ON history_events(significance);
CREATE INDEX IF NOT EXISTS idx_history_events_location_ids ON history_events USING GIN(location_ids);
CREATE INDEX IF NOT EXISTS idx_history_events_faction_ids ON history_events USING GIN(faction_ids);
CREATE INDEX IF NOT EXISTS idx_history_events_narrative_importance ON history_events(narrative_importance DESC);
CREATE INDEX IF NOT EXISTS idx_history_events_is_secret ON history_events(is_secret) WHERE is_secret = TRUE;
CREATE INDEX IF NOT EXISTS idx_history_events_created_at ON history_events(created_at DESC);

-- Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_history_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_history_events_updated_at ON history_events;
CREATE TRIGGER trigger_history_events_updated_at
    BEFORE UPDATE ON history_events
    FOR EACH ROW
    EXECUTE FUNCTION update_history_events_updated_at();

-- =====================================================
-- rumors table
-- =====================================================
CREATE TABLE IF NOT EXISTS rumors (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    truth_value INTEGER NOT NULL CHECK (truth_value >= 0 AND truth_value <= 100),
    origin_type VARCHAR(50) NOT NULL,
    source_event_id UUID REFERENCES history_events(id) ON DELETE SET NULL,
    origin_location_id UUID NOT NULL,
    current_locations UUID[] NOT NULL DEFAULT '{}',
    created_date JSONB,
    spread_count INTEGER DEFAULT 0 CHECK (spread_count >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for rumors
CREATE INDEX IF NOT EXISTS idx_rumors_origin_location ON rumors(origin_location_id);
CREATE INDEX IF NOT EXISTS idx_rumors_truth_value ON rumors(truth_value DESC);
CREATE INDEX IF NOT EXISTS idx_rumors_active ON rumors(truth_value) WHERE truth_value > 0;
CREATE INDEX IF NOT EXISTS idx_rumors_current_locations ON rumors USING GIN(current_locations);
CREATE INDEX IF NOT EXISTS idx_rumors_source_event ON rumors(source_event_id);
CREATE INDEX IF NOT EXISTS idx_rumors_origin_type ON rumors(origin_type);
CREATE INDEX IF NOT EXISTS idx_rumors_created_at ON rumors(created_at DESC);

-- GIN index for fast active rumor queries by location
CREATE INDEX IF NOT EXISTS idx_rumors_active_locations ON rumors USING GIN(current_locations) WHERE truth_value > 0;

-- =====================================================
-- Comments for documentation
-- =====================================================
COMMENT ON TABLE history_events IS 'Stores historical events in the world timeline';
COMMENT ON COLUMN history_events.id IS 'Unique identifier for the event';
COMMENT ON COLUMN history_events.event_type IS 'Type of event: war, battle, treaty, etc.';
COMMENT ON COLUMN history_events.significance IS 'Historical significance: trivial, minor, moderate, major, world_changing, legendary';
COMMENT ON COLUMN history_events.narrative_importance IS 'Importance to the story (0-100)';
COMMENT ON COLUMN history_events.location_ids IS 'Array of location UUIDs where event occurred';
COMMENT ON COLUMN history_events.faction_ids IS 'Array of faction UUIDs involved in the event';

COMMENT ON TABLE rumors IS 'Stores rumors that spread through the world';
COMMENT ON COLUMN rumors.truth_value IS 'Truth percentage (0-100), decays as rumor spreads';
COMMENT ON COLUMN rumors.origin_type IS 'Origin: event, npc, player, unknown';
COMMENT ON COLUMN rumors.current_locations IS 'Array of location UUIDs where rumor has spread';
COMMENT ON COLUMN rumors.source_event_id IS 'Reference to the source event if origin is EVENT';
