-- evidence_nodes.sql
-- Generic evidence-layer table for FACT / ASSUMPTION / CLAIM / POLICY / POSITION.
-- v1 held these in JSON only; v2 persists them per SCHEMA-001 (BaseNode contract).
--
-- References:
--   SCHEMA-001: BaseNode single root
--   SCHEMA-004: confidence as HIGH/MEDIUM/LOW enum
--   SCHEMA-005: computed_confidence separate from extraction confidence
--   SCHEMA-006: curator_approved as hard gate
--   SCHEMA-013: FACT vs ASSUMPTION distinction
--   SCHEMA-014: FiscalMetadata range (amount_low, amount_high)

CREATE TABLE IF NOT EXISTS evidence_nodes (
    id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL CHECK (node_type IN (
        'FACT', 'ASSUMPTION', 'CLAIM', 'POLICY', 'POSITION'
    )),

    -- BaseNode contract
    statement TEXT NOT NULL CHECK (length(statement) >= 10),
    source_id TEXT REFERENCES sources(source_id),
    source_loc TEXT,
    confidence TEXT CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),

    -- MC output (separate from extraction-time confidence per SCHEMA-005)
    computed_confidence_mean NUMERIC CHECK (computed_confidence_mean BETWEEN 0 AND 1),
    computed_confidence_std  NUMERIC CHECK (computed_confidence_std  >= 0),
    computed_confidence_p5   NUMERIC CHECK (computed_confidence_p5   BETWEEN 0 AND 1),
    computed_confidence_p95  NUMERIC CHECK (computed_confidence_p95  BETWEEN 0 AND 1),
    computed_confidence_label TEXT CHECK (
        computed_confidence_label IN ('HIGH', 'MEDIUM', 'LOW')
    ),

    domain TEXT NOT NULL,
    jurisdiction TEXT[],

    verified BOOLEAN NOT NULL DEFAULT false,
    curator_approved BOOLEAN NOT NULL DEFAULT false,  -- SCHEMA-006 gate
    extraction_run_id TEXT,

    -- Fiscal metadata with range support (SCHEMA-014 v2)
    fiscal_amount NUMERIC,
    fiscal_amount_low NUMERIC,
    fiscal_amount_high NUMERIC,
    fiscal_unit TEXT CHECK (fiscal_unit IN ('bn_gbp', 'm_gbp', 'pct_gdp')),
    fiscal_gap_role TEXT CHECK (fiscal_gap_role IN (
        'additional_need', 'baseline', 'position_only',
        'summary', 'uplift', 'target_total'
    )),
    fiscal_direction TEXT CHECK (fiscal_direction IN ('spending', 'revenue', 'net')),
    fiscal_horizon_years INTEGER,
    fiscal_year INTEGER,
    fiscal_notes TEXT,

    -- ASSUMPTION-only fields (SCHEMA-013)
    basis_fact_ids TEXT[],
    falsification_condition TEXT,

    -- POSITION-only fields
    actor TEXT,
    actor_type TEXT CHECK (actor_type IN (
        'minister', 'mp', 'party', 'official',
        'expert', 'body', 'citizen'
    )),
    position_date DATE,

    -- POLICY-only fields
    party TEXT,
    manifesto_year INTEGER,

    extraction_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Subtype-specific required-field enforcement
    CHECK (
        node_type != 'FACT' OR source_id IS NOT NULL
    ),
    CHECK (
        node_type != 'ASSUMPTION'
        OR (basis_fact_ids IS NOT NULL
            AND array_length(basis_fact_ids, 1) > 0
            AND falsification_condition IS NOT NULL
            AND length(falsification_condition) >= 10)
    ),
    CHECK (
        node_type != 'POSITION' OR actor IS NOT NULL
    ),

    -- Fiscal range consistency (SCHEMA-014 v2)
    CHECK (
        (fiscal_amount_low IS NULL) = (fiscal_amount_high IS NULL)
    ),
    CHECK (
        fiscal_amount_low IS NULL
        OR (fiscal_amount_low <= fiscal_amount
            AND fiscal_amount <= fiscal_amount_high)
    )
);

CREATE INDEX IF NOT EXISTS idx_evidence_nodes_type ON evidence_nodes (node_type);
CREATE INDEX IF NOT EXISTS idx_evidence_nodes_domain ON evidence_nodes (domain);
CREATE INDEX IF NOT EXISTS idx_evidence_nodes_curator
    ON evidence_nodes (curator_approved) WHERE curator_approved = false;
CREATE INDEX IF NOT EXISTS idx_evidence_nodes_source
    ON evidence_nodes (source_id) WHERE source_id IS NOT NULL;

CREATE OR REPLACE TRIGGER trg_evidence_nodes_updated
    BEFORE UPDATE ON evidence_nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------
-- Evidence edges (SCHEMA-015, SCHEMA-016, SCHEMA-017)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS evidence_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_id TEXT NOT NULL REFERENCES evidence_nodes(id),
    to_id TEXT NOT NULL REFERENCES evidence_nodes(id),
    edge_type TEXT NOT NULL CHECK (edge_type IN (
        'SUPPORTS', 'CONTRADICTS', 'DEPENDS_ON',
        'ENABLES', 'COMPETES', 'SUPERSEDES'
    )),
    explanation TEXT NOT NULL CHECK (length(explanation) >= 10),
    strength TEXT CHECK (strength IN ('HIGH', 'MEDIUM', 'LOW')),
    evidence_independent BOOLEAN DEFAULT true,  -- SCHEMA-015; true-for-all default
    created_at TIMESTAMPTZ DEFAULT now(),

    -- SCHEMA-015: independence flag only meaningful on SUPPORTS
    CHECK (
        edge_type = 'SUPPORTS' OR evidence_independent = true
    )
);

CREATE INDEX IF NOT EXISTS idx_evidence_edges_from ON evidence_edges (from_id);
CREATE INDEX IF NOT EXISTS idx_evidence_edges_to   ON evidence_edges (to_id);
CREATE INDEX IF NOT EXISTS idx_evidence_edges_type ON evidence_edges (edge_type);
