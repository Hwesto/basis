-- legal_nodes.sql
-- Hohfeldian legal layer tables + cross-layer edges + curator queue.
-- All legal nodes are BaseNode subclasses. curator_approved is the hard gate.

-- ---------------------------------------------------------------------------
-- Legal node type enum
-- ---------------------------------------------------------------------------

DO $$ BEGIN
    CREATE TYPE legal_node_type AS ENUM (
        'RIGHT', 'DUTY', 'POWER', 'LIABILITY',
        'PRIVILEGE', 'IMMUNITY', 'REGULATORY_BODY',
        'MECHANISM', 'EVIDENCE_REQUIREMENT', 'ESCALATION_PATH', 'PRECEDENT'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ---------------------------------------------------------------------------
-- legal_nodes
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS legal_nodes (
    id TEXT PRIMARY KEY,                          -- 'RIGHT-HOUSING-HHSRS-001'
    node_type legal_node_type NOT NULL,
    statement TEXT NOT NULL,                       -- plain English
    lex_provision_id TEXT REFERENCES lex_provisions(lex_id),
    jurisdiction TEXT[] NOT NULL,
    domain TEXT,

    -- Who this applies to
    applies_to TEXT[],                            -- ['tenant', 'homeowner']
    duty_holder TEXT,
    duty_holder_type TEXT CHECK (duty_holder_type IN (
        'local_authority', 'private_landlord',
        'public_body', 'employer', 'individual'
    )),

    -- Deontic strength (SCHEMA-012: replaces PRINCIPLE for 80% of cases)
    deontic_strength TEXT CHECK (deontic_strength IN (
        'ABSOLUTE', 'QUALIFIED', 'CONDITIONAL', 'DIRECTORY', 'ASPIRATIONAL'
    )),

    -- Source and confidence (BaseNode fields)
    source_id TEXT,
    source_loc TEXT,
    confidence TEXT CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),
    computed_confidence JSONB,                     -- {mean, std, p5, p95, label}
    verified BOOLEAN DEFAULT false,
    curator_approved BOOLEAN DEFAULT false,        -- SCHEMA-006: hard gate
    extraction_run_id TEXT,

    -- Structural signals (denormalised from lex_provisions for MC)
    structural_stability TEXT CHECK (structural_stability IN ('HIGH', 'MEDIUM', 'LOW')),
    commencement_status TEXT CHECK (commencement_status IN (
        'in_force', 'partially_in_force', 'not_commenced',
        'prospectively_repealed', 'repealed', 'unknown'
    )),
    commencement_notes TEXT,

    extraction_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_legal_nodes_type ON legal_nodes (node_type);
CREATE INDEX IF NOT EXISTS idx_legal_nodes_domain ON legal_nodes (domain);
CREATE INDEX IF NOT EXISTS idx_legal_nodes_lex ON legal_nodes (lex_provision_id);
CREATE INDEX IF NOT EXISTS idx_legal_nodes_approved
    ON legal_nodes (curator_approved) WHERE curator_approved = true;

CREATE OR REPLACE TRIGGER trg_legal_nodes_updated
    BEFORE UPDATE ON legal_nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------
-- legal_edges
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS legal_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    edge_type TEXT NOT NULL CHECK (edge_type IN (
        'CREATES', 'IMPOSES', 'ENFORCED_BY', 'ACCEPTED_BY',
        'REQUIRES', 'ESCALATES_TO', 'ESTABLISHED_BY', 'SUPERSEDES'
    )),
    jurisdiction TEXT[],
    explanation TEXT NOT NULL,
    strength TEXT CHECK (strength IN ('HIGH', 'MEDIUM', 'LOW'))
);

CREATE INDEX IF NOT EXISTS idx_legal_edges_from ON legal_edges (from_id);
CREATE INDEX IF NOT EXISTS idx_legal_edges_to ON legal_edges (to_id);
CREATE INDEX IF NOT EXISTS idx_legal_edges_type ON legal_edges (edge_type);

-- ---------------------------------------------------------------------------
-- cross_layer_edges (one table, all cross-layer connections)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS cross_layer_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_layer TEXT NOT NULL CHECK (from_layer IN ('evidence', 'legal', 'local', 'action')),
    from_id TEXT NOT NULL,
    to_layer TEXT NOT NULL CHECK (to_layer IN ('evidence', 'legal', 'local', 'action')),
    to_id TEXT NOT NULL,
    edge_type TEXT NOT NULL CHECK (edge_type IN (
        'EVIDENCES', 'ESTABLISHES', 'TRIGGERS', 'QUANTIFIES'
    )),
    CHECK (from_layer != to_layer)
);

CREATE INDEX IF NOT EXISTS idx_cross_layer_from ON cross_layer_edges (from_layer, from_id);
CREATE INDEX IF NOT EXISTS idx_cross_layer_to ON cross_layer_edges (to_layer, to_id);

-- ---------------------------------------------------------------------------
-- curator_queue (one table, all node types, all layers)
-- SCHEMA-006: The gate through which all content passes.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS curator_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id TEXT,                                  -- NULL until node is created
    node_type TEXT NOT NULL,                        -- distinguishes layer
    lex_provision_id TEXT,                          -- for legal extractions
    source_type TEXT,                               -- for routing to correct MCP
    extracted_json JSONB NOT NULL,                  -- the extraction output
    extraction_run_id TEXT,

    -- Flash cross-check results
    flash_check_result TEXT CHECK (flash_check_result IN ('pass', 'fail')),
    flash_check_note TEXT,

    -- Fixture comparison
    fixture_match BOOLEAN,
    fixture_delta TEXT,

    -- Curator decision
    curator_approved BOOLEAN DEFAULT false,
    curator_decision TEXT CHECK (curator_decision IN ('approve', 'reject', 'escalate')),
    curator_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,

    -- Queue management
    needs_review BOOLEAN DEFAULT true,
    flagged BOOLEAN DEFAULT false,
    flag_reason TEXT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_curator_queue_pending
    ON curator_queue (needs_review) WHERE needs_review = true;
CREATE INDEX IF NOT EXISTS idx_curator_queue_flagged
    ON curator_queue (flagged) WHERE flagged = true;
CREATE INDEX IF NOT EXISTS idx_curator_queue_type ON curator_queue (node_type);

CREATE OR REPLACE TRIGGER trg_curator_queue_updated
    BEFORE UPDATE ON curator_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------
-- extraction_runs (one table, all pipeline runs logged)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS extraction_runs (
    id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,                         -- 'legal_gemma', 'evidence_manual', etc.
    source_type TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    node_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    model_version TEXT,
    notes TEXT
);
