---
phase: 3
status: planned
source: BASIS_ROADMAP.md
---

### Phase 3: Local Data Layer

**Objective:** Connect national evidence to local reality. Enter a postcode; see your area.

**The core UX:** Postcode → constituency + council + ward resolver → dashboard showing your area's metrics vs national averages across all 12 domains. Every metric links back into the evidence graph ("your area's NHS waiting time is 1.4× the national average → this is what the evidence says about NHS funding → this is what you can do").

**3.1 Geography resolution**

- ONS Geography API: postcode → LSOA → ward → constituency → local authority → ICS
- Postcode lookup table (ONS NSPL): ~2.7m postcodes, refreshed quarterly
- Jurisdiction routing: England / Wales / Scotland / NI — determines which legal framework applies downstream
- Store resolved geography on user profile (optional, privacy-preserving)

**3.2 Core metric integrations (launch set)**

| Domain | Metric | Source | Granularity |
|---|---|---|---|
| Health | GP wait times, A&E performance | NHS Digital | ICS / LA |
| Health | Hospital waiting list size | NHSE | ICS |
| Crime | Crime rates by category | Police.uk | Ward / LSOA |
| Education | School Ofsted ratings | Ofsted | School / LA |
| Education | GCSE/A-Level outcomes | DfE | School / LA |
| Housing | Average house price | Land Registry | Ward / LA |
| Housing | Planning permission rates | DLUHC | LA |
| Housing | Council housing stock | DLUHC | LA |
| Benefits | Claimant count | DWP Stat-Xplore | LA / ward |
| Environment | Air quality index | DEFRA | LA |
| Environment | Flood risk areas | Environment Agency | LSOA |
| Council | Spending per head | Council transparency | LA |
| Council | Council tax level | DLUHC | LA |
| Council | CQC-rated care homes | CQC | LA |

**3.3 Local data schema (Supabase additions)**

Each `area_metric` row references a `StructuredDataSource` — not a `DocumentarySource`. Provider tier drives the MC confidence prior (ONS → 0.92, Police.uk → 0.80, council CSV → 0.60). The `source_id` foreign key points to a row in the sources table with `source_type = 'STRUCTURED_DATA'`.

```sql
CREATE TABLE area_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  area_code TEXT NOT NULL,          -- ONS GSS code
  area_type TEXT NOT NULL,          -- lsoa, ward, la, constituency, ics
  metric_id TEXT NOT NULL,
  domain TEXT NOT NULL,
  value NUMERIC,
  unit TEXT,
  period_start DATE,
  period_end DATE,
  national_average NUMERIC,
  percentile INTEGER,               -- 0-100, recomputed on each refresh
  source_id TEXT REFERENCES sources(id),  -- must be source_type='STRUCTURED_DATA'
  fetched_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(area_code, metric_id, period_start)
);

CREATE TABLE metric_definitions (
  metric_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  domain TEXT,
  source_api TEXT,
  provider_tier TEXT CHECK (provider_tier IN ('T1','T2','T3')),
  refresh_cadence TEXT,
  higher_is_better BOOLEAN,
  node_ids TEXT[],                  -- links to evidence graph nodes
  right_ids TEXT[]                  -- links to legal layer (phase 4)
);
```

**3.4 Dashboard frontend**

- Postcode input on homepage (replaces or sits alongside current domain grid)
- Area dashboard: metric tiles with RAG status vs national average
- **Comparison default: your area vs best-performing comparable area** — not national average. "Your area is 4× worse than the best-performing similar council" is a political fact. "Your area is 1.3× the national average" is forgettable. This is a design philosophy, not a cosmetic choice — it directly serves the theory of change.
- Domain drill-down: "Housing in [your area]" → local metrics + national evidence nodes
- Time series: "how has this changed over 5 years?"
- Missing data transparency: where we don't have local data, say so explicitly

**Shareability design constraint**

Every metric card must work as a standalone shareable object. People who actively seek civic information are a small minority. Everyone else will encounter BASIS because someone shared something.

Concrete requirements:
- Every metric card renders cleanly at mobile screenshot dimensions (375×280px minimum)
- Postcode appears in the URL — shared links are personalised: `basis.uk/area/BS3/housing`
- OG meta generates postcode-specific preview cards: "Bristol BS3: GP wait 19 days, rent £1,825/mo, sewage spills 47 in 2024"
- Share button on every card, one tap
- The comparison shown in the shared card uses best-performing area, not national average — the stark contrast is what makes people share

**Additional success metric for Phase 3:** ≥1 metric card format producing valid postcode-specific OG preview image, measurable share rate on social.

**3.5 Automated refresh pipeline**

- GitHub Actions cron jobs per source cadence
- Incremental upsert (new period rows, don't overwrite history)
- Change detection: if value moves >10% from previous period, flag for review
- Percentile recomputation: on each refresh, rerank all areas

**Success metrics:** All 650 constituencies resolvable, ≥10 metrics per postcode, dashboard live.

---
