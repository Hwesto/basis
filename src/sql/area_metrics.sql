-- area_metrics.sql
-- Phase 3: Local data layer.
-- Each area_metric references a StructuredDataSource.
-- Provider tier drives MC confidence prior.

-- ---------------------------------------------------------------------------
-- metric_definitions (reference table for all tracked metrics)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS metric_definitions (
    metric_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    domain TEXT NOT NULL,
    source_api TEXT,                                -- 'police.uk', 'nhs_digital', etc.
    provider_tier TEXT CHECK (provider_tier IN ('T1', 'T2', 'T3')),
    refresh_cadence TEXT,                           -- 'daily', 'weekly', 'monthly', 'quarterly'
    higher_is_better BOOLEAN,                       -- for RAG status computation
    unit TEXT,                                      -- 'days', 'per_1000', 'gbp', 'pct', 'count'
    node_ids TEXT[],                                -- links to evidence graph nodes
    right_ids TEXT[]                                -- links to legal layer (Phase 4)
);

-- ---------------------------------------------------------------------------
-- area_metrics (the data)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS area_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_code TEXT NOT NULL,                        -- ONS GSS code
    area_type TEXT NOT NULL CHECK (area_type IN (
        'lsoa', 'ward', 'la', 'constituency', 'ics'
    )),
    metric_id TEXT NOT NULL REFERENCES metric_definitions(metric_id),
    domain TEXT NOT NULL,
    value NUMERIC,
    unit TEXT,
    period_start DATE,
    period_end DATE,
    national_average NUMERIC,
    percentile INTEGER CHECK (percentile >= 0 AND percentile <= 100),
    -- Percentile recomputed on each refresh. 0 = worst, 100 = best.
    -- Interpretation depends on metric_definitions.higher_is_better.

    source_id TEXT,                                 -- must be source_type='STRUCTURED_DATA'
    fetched_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(area_code, metric_id, period_start)
);

CREATE INDEX IF NOT EXISTS idx_area_metrics_area ON area_metrics (area_code);
CREATE INDEX IF NOT EXISTS idx_area_metrics_metric ON area_metrics (metric_id);
CREATE INDEX IF NOT EXISTS idx_area_metrics_domain ON area_metrics (domain);
CREATE INDEX IF NOT EXISTS idx_area_metrics_period ON area_metrics (period_start DESC);

-- ---------------------------------------------------------------------------
-- geography_lookup (postcode -> all geographic levels)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS geography_lookup (
    postcode TEXT PRIMARY KEY,                      -- normalised, no spaces
    lsoa_code TEXT,
    lsoa_name TEXT,
    ward_code TEXT,
    ward_name TEXT,
    la_code TEXT,
    la_name TEXT,
    constituency_code TEXT,
    constituency_name TEXT,
    ics_code TEXT,
    ics_name TEXT,
    country TEXT CHECK (country IN ('england', 'wales', 'scotland', 'ni')),
    last_updated DATE
);

CREATE INDEX IF NOT EXISTS idx_geo_la ON geography_lookup (la_code);
CREATE INDEX IF NOT EXISTS idx_geo_constituency ON geography_lookup (constituency_code);
CREATE INDEX IF NOT EXISTS idx_geo_ward ON geography_lookup (ward_code);

-- ---------------------------------------------------------------------------
-- Seed metric_definitions for launch set (Phase 3.2)
-- ---------------------------------------------------------------------------

INSERT INTO metric_definitions (metric_id, name, domain, source_api, provider_tier, refresh_cadence, higher_is_better, unit) VALUES
    ('health_gp_wait',       'GP appointment wait time',    'health',      'nhs_digital',       'T1', 'monthly',   false, 'days'),
    ('health_ae_performance','A&E 4-hour performance',      'health',      'nhs_digital',       'T1', 'weekly',    true,  'pct'),
    ('health_waiting_list',  'Hospital waiting list size',  'health',      'nhse',              'T1', 'monthly',   false, 'count'),
    ('crime_total_rate',     'Total crime rate',            'policing',    'police.uk',         'T2', 'monthly',   false, 'per_1000'),
    ('crime_asb_rate',       'Anti-social behaviour rate',  'policing',    'police.uk',         'T2', 'monthly',   false, 'per_1000'),
    ('edu_ofsted_good',      'Schools rated Good/Outstanding', 'education','ofsted',            'T2', 'quarterly', true,  'pct'),
    ('edu_gcse_pass',        'GCSE 5+ standard passes',    'education',   'dfe',               'T1', 'yearly',    true,  'pct'),
    ('housing_avg_price',    'Average house price',         'housing',     'land_registry',     'T2', 'monthly',   null,  'gbp'),
    ('housing_planning_rate','Planning permission approval rate', 'housing','dluhc',            'T1', 'quarterly', null,  'pct'),
    ('housing_council_stock','Council housing stock',       'housing',     'dluhc',             'T1', 'yearly',    null,  'count'),
    ('benefits_claimant',    'Claimant count',              'benefits',    'dwp_stat_xplore',   'T1', 'monthly',   false, 'count'),
    ('env_air_quality',      'Air quality index',           'environment', 'defra',             'T2', 'daily',     false, 'index'),
    ('env_flood_risk',       'Flood risk areas',            'environment', 'environment_agency', 'T2', 'quarterly', false, 'pct'),
    ('council_spend_head',   'Council spending per head',   'housing',     'council_transparency','T3','yearly',   null,  'gbp'),
    ('council_tax',          'Council tax Band D',          'housing',     'dluhc',             'T1', 'yearly',    false, 'gbp'),
    ('council_cqc_good',     'CQC-rated Good care homes',  'social_care', 'cqc',              'T2', 'quarterly', true,  'pct')
ON CONFLICT (metric_id) DO NOTHING;
