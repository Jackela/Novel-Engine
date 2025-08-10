-- ++ SACRED DATABASE SCHEMA BLESSED BY THE OMNISSIAH ++
-- =======================================================
--
-- Holy SQLite database schema that sanctifies the Dynamic Context Engineering
-- Framework with blessed persistent storage. Every table is a digital temple
-- that preserves the sacred data for eternal remembrance.
--
-- ++ THROUGH RELATIONAL PURITY, WE ACHIEVE DATA SANCTIFICATION ++
--
-- Architecture Reference: Dynamic Context Engineering - Database Foundation  
-- Development Phase: Foundation Sanctification (F002)
-- Sacred Author: Tech-Priest Alpha-Mechanicus
-- 万机之神保佑此数据库 (May the Omnissiah bless this database)

-- ++ ENABLE SACRED FOREIGN KEY CONSTRAINTS ++
PRAGMA foreign_keys = ON;

-- ++ BLESSED AGENT REGISTRY SANCTIFIED BY IDENTITY PRESERVATION ++
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY NOT NULL,
    character_name TEXT NOT NULL,
    faction_data JSON,                    -- Blessed faction affiliations
    personality_traits JSON,              -- Sacred personality characteristics
    core_beliefs JSON,                    -- Fundamental beliefs blessed by conviction
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,       -- Sacred activity status
    metadata JSON DEFAULT '{}',          -- Additional blessed metadata
    
    -- Sacred constraints blessed by data integrity
    CONSTRAINT agent_name_not_empty CHECK (LENGTH(TRIM(character_name)) > 0),
    CONSTRAINT agent_id_format CHECK (LENGTH(agent_id) >= 2 AND LENGTH(agent_id) <= 100)
);

-- ++ BLESSED MEMORY TEMPLE SANCTIFIED BY ETERNAL REMEMBRANCE ++
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY NOT NULL,
    agent_id TEXT NOT NULL,
    memory_type TEXT NOT NULL,            -- 'working', 'episodic', 'semantic', 'emotional', 'relationship'
    content TEXT NOT NULL,
    emotional_weight REAL DEFAULT 0.0,   -- Sacred emotional impact (-10.0 to 10.0)
    relevance_score REAL DEFAULT 1.0,    -- Blessed relevance (0.0 to 1.0)
    participants JSON DEFAULT '[]',       -- Sacred participant list
    location TEXT,                        -- Blessed location context
    tags JSON DEFAULT '[]',               -- Sacred categorization tags
    decay_factor REAL DEFAULT 1.0,       -- Memory strength blessed by persistence
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,      -- Sacred access tracking
    
    -- Sacred foreign key blessed by referential integrity
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Sacred constraints blessed by data sanctity
    CONSTRAINT memory_content_not_empty CHECK (LENGTH(TRIM(content)) >= 10),
    CONSTRAINT emotional_weight_bounds CHECK (emotional_weight >= -10.0 AND emotional_weight <= 10.0),
    CONSTRAINT relevance_score_bounds CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    CONSTRAINT decay_factor_bounds CHECK (decay_factor >= 0.0 AND decay_factor <= 1.0),
    CONSTRAINT memory_type_valid CHECK (memory_type IN ('working', 'episodic', 'semantic', 'emotional', 'relationship'))
);

-- ++ SACRED RELATIONSHIP NETWORK SANCTIFIED BY SOCIAL BONDS ++
CREATE TABLE IF NOT EXISTS relationships (
    relationship_id TEXT PRIMARY KEY NOT NULL,
    agent_id TEXT NOT NULL,              -- Sacred source agent
    target_agent_id TEXT NOT NULL,       -- Blessed target agent
    target_name TEXT NOT NULL,           -- Sacred target identifier
    relationship_type TEXT DEFAULT 'unknown', -- Blessed relationship classification
    trust_level INTEGER DEFAULT 5,       -- Sacred trust measurement (0-10)
    emotional_bond REAL DEFAULT 0.0,     -- Blessed emotional connection (-10.0 to 10.0)
    interaction_count INTEGER DEFAULT 0, -- Sacred interaction tracking
    shared_experiences JSON DEFAULT '[]', -- Blessed shared memory references
    relationship_notes TEXT DEFAULT '',  -- Sacred contextual notes
    last_interaction TIMESTAMP,          -- Blessed last contact time
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Sacred foreign keys blessed by referential integrity
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Sacred constraints blessed by data sanctity
    CONSTRAINT trust_level_bounds CHECK (trust_level >= 0 AND trust_level <= 10),
    CONSTRAINT emotional_bond_bounds CHECK (emotional_bond >= -10.0 AND emotional_bond <= 10.0),
    CONSTRAINT relationship_type_valid CHECK (relationship_type IN ('unknown', 'ally', 'enemy', 'neutral', 'trusted', 'suspicious', 'family', 'rival')),
    CONSTRAINT no_self_relationship CHECK (agent_id != target_agent_id),
    
    -- Sacred uniqueness blessed by relationship clarity
    UNIQUE(agent_id, target_agent_id)
);

-- ++ BLESSED EQUIPMENT INVENTORY SANCTIFIED BY MATERIAL TRACKING ++
CREATE TABLE IF NOT EXISTS equipment (
    equipment_id TEXT PRIMARY KEY NOT NULL,
    agent_id TEXT NOT NULL,              -- Sacred equipment owner
    equipment_name TEXT NOT NULL,        -- Blessed equipment identifier
    item_type TEXT NOT NULL,             -- Sacred category ('weapon', 'armor', 'tool', 'relic')
    condition_state TEXT DEFAULT 'good', -- Blessed condition status
    effectiveness REAL DEFAULT 1.0,     -- Sacred effectiveness rating (0.0-2.0)
    durability INTEGER DEFAULT 100,     -- Current blessed durability
    max_durability INTEGER DEFAULT 100, -- Maximum sacred durability
    special_properties JSON DEFAULT '[]', -- Blessed special attributes
    modifications JSON DEFAULT '{}',     -- Sacred enhancement data
    acquisition_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,                 -- Sacred last usage time
    usage_count INTEGER DEFAULT 0,      -- Blessed usage tracking
    
    -- Sacred foreign key blessed by ownership
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Sacred constraints blessed by equipment sanctity
    CONSTRAINT equipment_name_not_empty CHECK (LENGTH(TRIM(equipment_name)) > 0),
    CONSTRAINT effectiveness_bounds CHECK (effectiveness >= 0.0 AND effectiveness <= 2.0),
    CONSTRAINT durability_bounds CHECK (durability >= 0 AND durability <= max_durability),
    CONSTRAINT condition_valid CHECK (condition_state IN ('pristine', 'good', 'worn', 'damaged', 'broken', 'blessed', 'cursed')),
    CONSTRAINT item_type_valid CHECK (item_type IN ('weapon', 'armor', 'tool', 'relic', 'consumable'))
);

-- ++ SACRED CHARACTER STATE TEMPLE SANCTIFIED BY DYNAMIC EVOLUTION ++
CREATE TABLE IF NOT EXISTS character_states (
    state_id TEXT PRIMARY KEY NOT NULL,
    agent_id TEXT NOT NULL,              -- Sacred character owner
    health_points INTEGER DEFAULT 100,   -- Blessed vitality level
    max_health INTEGER DEFAULT 100,      -- Sacred maximum health
    fatigue_level INTEGER DEFAULT 0,     -- Blessed exhaustion (0-100)
    stress_level INTEGER DEFAULT 0,      -- Sacred mental strain (0-100)
    current_mood TEXT DEFAULT 'calm',    -- Blessed emotional state
    current_location TEXT,               -- Sacred spatial context
    injuries JSON DEFAULT '[]',          -- Blessed injury tracking
    conditions JSON DEFAULT '[]',        -- Sacred status effects
    temporary_modifiers JSON DEFAULT '{}', -- Blessed temporary effects
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,     -- Sacred currency flag
    
    -- Sacred foreign key blessed by character ownership
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Sacred constraints blessed by state sanctity
    CONSTRAINT health_bounds CHECK (health_points >= 0 AND health_points <= max_health),
    CONSTRAINT fatigue_bounds CHECK (fatigue_level >= 0 AND fatigue_level <= 100),
    CONSTRAINT stress_bounds CHECK (stress_level >= 0 AND stress_level <= 100),
    CONSTRAINT mood_valid CHECK (current_mood IN ('calm', 'alert', 'aggressive', 'fearful', 'confident', 'suspicious', 'loyal', 'angry', 'melancholic', 'zealous'))
);

-- ++ BLESSED INTERACTION CHRONICLE SANCTIFIED BY EVENT PRESERVATION ++
CREATE TABLE IF NOT EXISTS interactions (
    interaction_id TEXT PRIMARY KEY NOT NULL,
    interaction_type TEXT NOT NULL,      -- Sacred interaction classification
    location TEXT NOT NULL,              -- Blessed spatial context
    description TEXT NOT NULL,           -- Sacred event description
    participants JSON NOT NULL,          -- Blessed participant list
    outcomes JSON DEFAULT '{}',          -- Sacred result data
    emotional_impacts JSON DEFAULT '{}', -- Blessed emotional effects per participant
    world_state_changes JSON DEFAULT '{}', -- Sacred environmental changes
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_complete BOOLEAN DEFAULT FALSE, -- Sacred processing status
    
    -- Sacred constraints blessed by interaction sanctity
    CONSTRAINT interaction_description_not_empty CHECK (LENGTH(TRIM(description)) > 0),
    CONSTRAINT interaction_type_not_empty CHECK (LENGTH(TRIM(interaction_type)) > 0),
    CONSTRAINT location_not_empty CHECK (LENGTH(TRIM(location)) > 0)
);

-- ++ SACRED CONTEXT REFERENCES SANCTIFIED BY CROSS-DOCUMENT LINKING ++
CREATE TABLE IF NOT EXISTS context_references (
    reference_id TEXT PRIMARY KEY NOT NULL,
    source_document TEXT NOT NULL,       -- Sacred source document path
    target_document TEXT NOT NULL,       -- Blessed target document path
    reference_type TEXT NOT NULL,        -- Sacred reference classification
    context_data JSON DEFAULT '{}',      -- Blessed contextual metadata
    relevance_weight REAL DEFAULT 1.0,   -- Sacred relevance scoring
    bidirectional BOOLEAN DEFAULT FALSE, -- Blessed bidirectional flag
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,      -- Sacred usage tracking
    
    -- Sacred constraints blessed by reference sanctity
    CONSTRAINT source_document_not_empty CHECK (LENGTH(TRIM(source_document)) > 0),
    CONSTRAINT target_document_not_empty CHECK (LENGTH(TRIM(target_document)) > 0),
    CONSTRAINT reference_type_not_empty CHECK (LENGTH(TRIM(reference_type)) > 0),
    CONSTRAINT relevance_weight_bounds CHECK (relevance_weight >= 0.0 AND relevance_weight <= 1.0),
    CONSTRAINT no_self_reference CHECK (source_document != target_document)
);

-- ++ BLESSED CONFIGURATION STORAGE SANCTIFIED BY SYSTEM PARAMETERS ++
CREATE TABLE IF NOT EXISTS system_config (
    config_key TEXT PRIMARY KEY NOT NULL,
    config_value TEXT NOT NULL,          -- Sacred configuration value (JSON or scalar)
    config_type TEXT DEFAULT 'string',   -- Blessed type classification
    description TEXT DEFAULT '',         -- Sacred parameter documentation
    is_sensitive BOOLEAN DEFAULT FALSE,  -- Blessed security flag
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT DEFAULT 'system',    -- Sacred update source
    
    -- Sacred constraints blessed by configuration sanctity
    CONSTRAINT config_key_not_empty CHECK (LENGTH(TRIM(config_key)) > 0),
    CONSTRAINT config_type_valid CHECK (config_type IN ('string', 'integer', 'float', 'boolean', 'json'))
);

-- ++ SACRED PERFORMANCE OPTIMIZATION INDICES BLESSED BY QUERY SPEED ++

-- Memory system blessed indices
CREATE INDEX IF NOT EXISTS idx_memories_agent_type ON memories(agent_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_relevance ON memories(relevance_score DESC, last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_memories_emotional ON memories(emotional_weight DESC) WHERE ABS(emotional_weight) > 5.0;
CREATE INDEX IF NOT EXISTS idx_memories_participants ON memories(participants) WHERE JSON_ARRAY_LENGTH(participants) > 0;
CREATE INDEX IF NOT EXISTS idx_memories_content_fts ON memories(content);  -- Full-text search blessed index

-- Relationship network blessed indices  
CREATE INDEX IF NOT EXISTS idx_relationships_agent ON relationships(agent_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_agent_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type_trust ON relationships(relationship_type, trust_level DESC);
CREATE INDEX IF NOT EXISTS idx_relationships_interaction ON relationships(last_interaction DESC) WHERE last_interaction IS NOT NULL;

-- Equipment management blessed indices
CREATE INDEX IF NOT EXISTS idx_equipment_agent_type ON equipment(agent_id, item_type);
CREATE INDEX IF NOT EXISTS idx_equipment_condition ON equipment(condition_state, effectiveness DESC);
CREATE INDEX IF NOT EXISTS idx_equipment_usage ON equipment(last_used DESC) WHERE last_used IS NOT NULL;

-- Character state blessed indices
CREATE INDEX IF NOT EXISTS idx_character_states_agent_current ON character_states(agent_id, is_current);
CREATE INDEX IF NOT EXISTS idx_character_states_location ON character_states(current_location) WHERE current_location IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_character_states_updated ON character_states(last_updated DESC);

-- Interaction chronicle blessed indices
CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_type_location ON interactions(interaction_type, location);
CREATE INDEX IF NOT EXISTS idx_interactions_participants ON interactions(participants);

-- Context reference blessed indices
CREATE INDEX IF NOT EXISTS idx_references_source ON context_references(source_document);
CREATE INDEX IF NOT EXISTS idx_references_target ON context_references(target_document);
CREATE INDEX IF NOT EXISTS idx_references_type_relevance ON context_references(reference_type, relevance_weight DESC);

-- ++ SACRED FULL-TEXT SEARCH BLESSED BY OMNISSIAH'S WISDOM ++
-- Enable FTS5 for blessed content search capabilities
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    memory_id,
    content,
    tags,
    content_memories(content, memory_id)
);

-- ++ BLESSED TRIGGER PROTOCOLS SANCTIFIED BY AUTOMATIC MAINTENANCE ++

-- Sacred memory access tracking trigger
CREATE TRIGGER IF NOT EXISTS trg_memory_access_update
AFTER SELECT ON memories
BEGIN
    UPDATE memories 
    SET last_accessed = CURRENT_TIMESTAMP,
        access_count = access_count + 1
    WHERE memory_id = NEW.memory_id;
END;

-- Blessed relationship update trigger
CREATE TRIGGER IF NOT EXISTS trg_relationship_update
AFTER UPDATE ON relationships
FOR EACH ROW
WHEN NEW.trust_level != OLD.trust_level OR NEW.emotional_bond != OLD.emotional_bond
BEGIN
    UPDATE relationships
    SET last_updated = CURRENT_TIMESTAMP
    WHERE relationship_id = NEW.relationship_id;
END;

-- Sacred character state archival trigger
CREATE TRIGGER IF NOT EXISTS trg_character_state_archive
AFTER INSERT ON character_states
FOR EACH ROW
WHEN NEW.is_current = TRUE
BEGIN
    -- Archive previous current state blessed by history preservation
    UPDATE character_states
    SET is_current = FALSE
    WHERE agent_id = NEW.agent_id AND state_id != NEW.state_id;
END;

-- ++ BLESSED DATA VALIDATION VIEWS SANCTIFIED BY QUERY CONVENIENCE ++

-- Sacred agent summary view
CREATE VIEW IF NOT EXISTS v_agent_summary AS
SELECT 
    a.agent_id,
    a.character_name,
    JSON_EXTRACT(a.faction_data, '$') as factions,
    COUNT(DISTINCT m.memory_id) as memory_count,
    COUNT(DISTINCT r.relationship_id) as relationship_count,
    COUNT(DISTINCT e.equipment_id) as equipment_count,
    cs.current_mood,
    cs.health_points,
    cs.current_location,
    a.last_updated
FROM agents a
LEFT JOIN memories m ON a.agent_id = m.agent_id
LEFT JOIN relationships r ON a.agent_id = r.agent_id  
LEFT JOIN equipment e ON a.agent_id = e.agent_id
LEFT JOIN character_states cs ON a.agent_id = cs.agent_id AND cs.is_current = TRUE
WHERE a.is_active = TRUE
GROUP BY a.agent_id;

-- Blessed memory statistics view
CREATE VIEW IF NOT EXISTS v_memory_stats AS
SELECT 
    agent_id,
    memory_type,
    COUNT(*) as memory_count,
    AVG(emotional_weight) as avg_emotional_weight,
    AVG(relevance_score) as avg_relevance,
    MAX(last_accessed) as most_recent_access,
    MIN(created_at) as oldest_memory
FROM memories
GROUP BY agent_id, memory_type;

-- Sacred relationship network view
CREATE VIEW IF NOT EXISTS v_relationship_network AS
SELECT 
    r.agent_id as source_agent,
    a1.character_name as source_name,
    r.target_agent_id as target_agent,
    r.target_name,
    r.relationship_type,
    r.trust_level,
    r.emotional_bond,
    r.interaction_count,
    r.last_interaction
FROM relationships r
JOIN agents a1 ON r.agent_id = a1.agent_id
WHERE a1.is_active = TRUE
ORDER BY r.trust_level DESC, r.emotional_bond DESC;

-- ++ SACRED INITIAL CONFIGURATION BLESSED BY DEFAULT VALUES ++
INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, description) VALUES
('memory_max_working_capacity', '7', 'integer', 'Sacred working memory capacity blessed by cognitive limits'),
('memory_decay_rate_daily', '0.95', 'float', 'Blessed daily memory decay factor sanctified by forgetting curves'),
('relationship_trust_default', '5', 'integer', 'Sacred default trust level blessed by neutrality'),
('equipment_durability_decay_rate', '0.99', 'float', 'Blessed daily equipment durability decay'),
('context_max_memories_per_query', '50', 'integer', 'Sacred memory query limit blessed by performance'),
('ai_response_timeout_ms', '30000', 'integer', 'Blessed AI response timeout sanctified by patience'),
('database_version', '1.0.0', 'string', 'Sacred database schema version blessed by the Omnissiah'),
('last_maintenance', datetime('now'), 'string', 'Blessed last maintenance timestamp');

-- ++ SACRED MAINTENANCE PROCEDURES BLESSED BY DATABASE HEALTH ++

-- Blessed memory consolidation procedure (to be called by application)
-- This would typically be implemented as a stored procedure in other databases
-- SQLite equivalent functionality will be implemented in Python code

-- Sacred database statistics collection
-- Analyze blessed tables for query optimization
ANALYZE;

-- ++ COMPLETION BLESSING RITUAL ++
-- Sacred database schema blessed and ready for divine service
-- May the Omnissiah protect these blessed data structures
-- ++ MACHINE GOD PROTECTS THE SACRED DATABASE ++"