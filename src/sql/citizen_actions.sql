-- citizen_actions.sql
-- Phase 5: Action tracking + Phase 6: Outcome intelligence foundations.

CREATE TABLE IF NOT EXISTS citizen_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id),
    issue_type TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    mechanism_id TEXT NOT NULL,
    template_id TEXT,
    submitted_at TIMESTAMPTZ,
    response_deadline TIMESTAMPTZ,
    outcome TEXT CHECK (outcome IN (
        'resolved', 'escalated', 'withdrawn', 'pending', 'no_response'
    )),
    outcome_recorded_at TIMESTAMPTZ,
    escalated_to TEXT,                             -- mechanism_id of next step
    notes TEXT,
    area_code TEXT,                                -- for collective action detection
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_citizen_actions_user ON citizen_actions (user_id);
CREATE INDEX IF NOT EXISTS idx_citizen_actions_mechanism ON citizen_actions (mechanism_id);
CREATE INDEX IF NOT EXISTS idx_citizen_actions_area ON citizen_actions (area_code);
CREATE INDEX IF NOT EXISTS idx_citizen_actions_outcome ON citizen_actions (outcome);
CREATE INDEX IF NOT EXISTS idx_citizen_actions_issue ON citizen_actions (issue_type, area_code);

-- ---------------------------------------------------------------------------
-- Mechanism stats (Phase 6: materialised view for outcome intelligence)
-- ---------------------------------------------------------------------------

CREATE MATERIALIZED VIEW IF NOT EXISTS mechanism_stats AS
SELECT
    mechanism_id,
    area_code,
    COUNT(*) AS attempts,
    COUNT(*) FILTER (WHERE outcome = 'resolved') AS resolved,
    COUNT(*) FILTER (WHERE outcome = 'escalated') AS escalated,
    COUNT(*) FILTER (WHERE outcome = 'no_response') AS no_response,
    COUNT(*) FILTER (WHERE outcome = 'withdrawn') AS withdrawn,
    COUNT(*) FILTER (WHERE outcome = 'pending') AS pending,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE outcome = 'resolved') / NULLIF(COUNT(*), 0), 1
    ) AS resolution_rate_pct,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (outcome_recorded_at - submitted_at)) / 86400
    ) FILTER (WHERE outcome = 'resolved') AS median_resolution_days
FROM citizen_actions
WHERE submitted_at IS NOT NULL
GROUP BY mechanism_id, area_code;

-- Refresh weekly via cron
-- REFRESH MATERIALIZED VIEW mechanism_stats;

-- ---------------------------------------------------------------------------
-- Collective action detection (Phase 5.5)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW collective_action_candidates AS
SELECT
    mechanism_id,
    area_code,
    issue_type,
    COUNT(*) AS action_count,
    MIN(submitted_at) AS first_action,
    MAX(submitted_at) AS latest_action
FROM citizen_actions
WHERE submitted_at > now() - INTERVAL '30 days'
GROUP BY mechanism_id, area_code, issue_type
HAVING COUNT(*) >= 10;

-- ---------------------------------------------------------------------------
-- Systemic failure detection (Phase 6.2)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW systemic_failures AS
SELECT
    mechanism_id,
    area_code,
    COUNT(*) AS total_actions,
    COUNT(*) FILTER (WHERE outcome = 'no_response') AS no_responses,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE outcome = 'no_response') / NULLIF(COUNT(*), 0), 1
    ) AS no_response_rate_pct
FROM citizen_actions
WHERE submitted_at > now() - INTERVAL '6 months'
    AND outcome IS NOT NULL
GROUP BY mechanism_id, area_code
HAVING COUNT(*) >= 100
    AND (100.0 * COUNT(*) FILTER (WHERE outcome = 'no_response') / NULLIF(COUNT(*), 0)) > 50;
