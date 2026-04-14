-- curator_queue.sql
-- SCHEMA-006: curator_approved is a hard gate. This table holds every
-- extracted candidate awaiting human review.
--
-- Rows land here via:
--   - scripts/run_agent.py after Gemma/Flash extraction
--   - ingest/cli.py after automated source ingestion
--   - challenge system (Phase 5) for citizen-submitted edits
--
-- Rows leave when a curator flips curator_approved=true on the
-- corresponding evidence_nodes / legal_nodes record, at which point the
-- queue_item.resolved_at is set.

CREATE TABLE IF NOT EXISTS curator_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What's being reviewed
    node_type TEXT NOT NULL,
    target_table TEXT NOT NULL CHECK (target_table IN (
        'evidence_nodes', 'legal_nodes', 'area_metrics',
        'citizen_actions', 'challenges'
    )),
    target_id TEXT,                 -- null until the row exists; set post-approval

    -- The candidate payload
    extracted_json JSONB NOT NULL,  -- the Pydantic-validated candidate
    source_id TEXT REFERENCES sources(source_id),
    extraction_run_id TEXT NOT NULL,

    -- Automated pre-checks (from Gemma -> Flash cross-check pass)
    flash_check_result TEXT CHECK (
        flash_check_result IN ('pass', 'fail', 'error', 'skipped')
    ),
    flash_check_note TEXT,

    -- Commencement gate (SCHEMA-011) — only meaningful for legal_nodes
    commencement_status TEXT CHECK (commencement_status IN (
        'in_force', 'partially_in_force', 'not_commenced',
        'prospectively_repealed', 'repealed', 'unknown'
    )),

    -- Review state
    needs_review BOOLEAN NOT NULL DEFAULT true,
    flagged BOOLEAN NOT NULL DEFAULT false,
    flag_reason TEXT,

    -- Outcome
    decision TEXT CHECK (decision IN (
        'approved', 'rejected', 'edited', 'deferred'
    )),
    decision_notes TEXT,
    decided_by TEXT,
    decided_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Decision rows must carry a decider + timestamp
    CHECK (
        decision IS NULL
        OR (decided_by IS NOT NULL AND decided_at IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_curator_queue_pending
    ON curator_queue (needs_review, created_at) WHERE needs_review = true;
CREATE INDEX IF NOT EXISTS idx_curator_queue_source
    ON curator_queue (source_id) WHERE source_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_curator_queue_flagged
    ON curator_queue (flagged) WHERE flagged = true;

CREATE OR REPLACE TRIGGER trg_curator_queue_updated
    BEFORE UPDATE ON curator_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
