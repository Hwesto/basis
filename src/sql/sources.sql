-- sources.sql
-- Unified sources table. source_type is the discriminator.
-- SCHEMA-008: Five source types, type-specific nullable columns.
-- SCHEMA-009: tier is a default; citation edges can override.

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL CHECK (source_type IN (
        'DOCUMENTARY', 'STRUCTURED_DATA', 'LEGISLATIVE_STRUCTURAL',
        'DERIVED', 'TESTIMONY'
    )),
    domain TEXT,
    jurisdiction TEXT[],

    -- DOCUMENTARY fields
    title TEXT,
    author TEXT,
    publisher TEXT,
    published_date TEXT,
    url TEXT,
    doi TEXT,
    tier TEXT CHECK (tier IN ('T1', 'T2', 'T3', 'T4', 'T5', 'T6')),
    tier_justification TEXT,
    full_text TEXT,
    content_hash TEXT,              -- sha256; change = re-verify nodes
    fetched_at TIMESTAMPTZ,
    citation_count INTEGER,
    influential_citation_count INTEGER,
    citation_velocity NUMERIC,
    venue TEXT,
    open_access BOOLEAN,

    -- STRUCTURED_DATA fields
    provider TEXT,
    dataset_id TEXT,
    metric_id TEXT,
    period_start DATE,
    period_end DATE,
    methodology_url TEXT,
    provider_tier TEXT CHECK (provider_tier IN ('T1', 'T2', 'T3')),
    api_endpoint TEXT,
    last_refreshed TIMESTAMPTZ,

    -- LEGISLATIVE_STRUCTURAL fields
    lex_provision_id TEXT,
    edge_type TEXT CHECK (edge_type IN (
        'citation', 'amendment', 'cross_reference', 'commencement', 'repeal'
    )),
    related_provision_id TEXT,
    recorded_date DATE,

    -- DERIVED fields
    computation_id TEXT,
    algorithm_version TEXT,
    input_node_ids TEXT[],
    computed_at TIMESTAMPTZ,

    -- TESTIMONY fields
    actor TEXT,
    actor_type TEXT CHECK (actor_type IN (
        'minister', 'mp', 'official', 'expert',
        'citizen', 'ombudsman', 'court'
    )),
    testimony_date DATE,
    context TEXT,
    verbatim_ref TEXT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sources_type ON sources (source_type);
CREATE INDEX IF NOT EXISTS idx_sources_domain ON sources (domain);
CREATE INDEX IF NOT EXISTS idx_sources_doi ON sources (doi) WHERE doi IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sources_url ON sources (url) WHERE url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sources_lex ON sources (lex_provision_id)
    WHERE lex_provision_id IS NOT NULL;

CREATE OR REPLACE TRIGGER trg_sources_updated
    BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------
-- Citation edges (SCHEMA-009: tier lives here, not on source)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS citation_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    node_id TEXT NOT NULL,          -- the node this source supports
    claim_tier_override TEXT CHECK (claim_tier_override IN (
        'T1', 'T2', 'T3', 'T4', 'T5', 'T6'
    )),
    override_justification TEXT,    -- mandatory when claim_tier_override is set
    source_loc TEXT,                -- section/page/paragraph in the source
    evidence_independent BOOLEAN DEFAULT true,  -- SCHEMA-015
    created_at TIMESTAMPTZ DEFAULT now(),

    -- Ensure justification when override is used
    CHECK (
        claim_tier_override IS NULL
        OR override_justification IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS idx_citation_edges_source ON citation_edges (source_id);
CREATE INDEX IF NOT EXISTS idx_citation_edges_node ON citation_edges (node_id);
