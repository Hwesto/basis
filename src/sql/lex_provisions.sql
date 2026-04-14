-- lex_provisions.sql
-- Narrow reference table for Lex Graph provisions relevant to BASIS.
-- SCHEMA-021: We reference Lex Graph, we don't import it.
-- SCHEMA-011: Six-value commencement status.
-- SCHEMA-010: structural_stability feeds MC prior.

CREATE TABLE IF NOT EXISTS lex_provisions (
    lex_id TEXT PRIMARY KEY,                     -- Lex Graph's stable provision ID
    title TEXT NOT NULL,                          -- 'Housing Act 2004, s.1'
    domain TEXT,
    jurisdiction TEXT[],
    full_text TEXT,                               -- cached from Lex API for extraction
    explanatory_note TEXT,                        -- co-fetched if exists; free validator
    content_hash TEXT,                            -- sha256; change = re-extract
    last_checked DATE,
    amendment_watch BOOLEAN DEFAULT true,

    -- Structural signals from Lex Graph (LegislativeStructuralSource facts)
    -- These have alpha = 1.0 in the MC engine on the structural fact itself.
    in_degree INTEGER,                           -- how many Acts cite this provision
    amendment_count INTEGER,                     -- times amended since enacted
    last_amended DATE,
    commencement_status TEXT CHECK (commencement_status IN (
        'in_force', 'partially_in_force', 'not_commenced',
        'prospectively_repealed', 'repealed', 'unknown'
    )),
    commencement_notes TEXT,                     -- plain English for partial/conditional

    structural_stability TEXT CHECK (structural_stability IN ('HIGH', 'MEDIUM', 'LOW')),
    -- HIGH = untouched >10yrs; MEDIUM = amended 1-3 times; LOW = amended >3 times in 5yrs

    citing_acts TEXT[],                          -- top 5 citing Acts by recency (UI provenance)

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for amendment-watch cron
CREATE INDEX IF NOT EXISTS idx_lex_provisions_watch
    ON lex_provisions (amendment_watch) WHERE amendment_watch = true;

-- Index for domain-scoped queries
CREATE INDEX IF NOT EXISTS idx_lex_provisions_domain
    ON lex_provisions (domain);

-- Trigger to update updated_at on modification
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_lex_provisions_updated
    BEFORE UPDATE ON lex_provisions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
