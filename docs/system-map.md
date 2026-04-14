# BASIS — system map

**What goes in, what happens to it, what comes out, where it's displayed, what it depends on.**

Complementary to `docs/status.md` (state) — this is *topology*. Updated at the end of any session that adds / removes / reroutes data flow.

**Last updated:** 2026-04-14, session commits `30f12d8` → `0546a7f`

---

## 1. Inventory — what we have to ingest

### 1a. Concrete right now (living in `archive/v1/`)

| What | Count | Where | Notes |
|---|---|---|---|
| v1 source references with URLs | **172** | `archive/v1/data/basis_source_urls.json` | 100% URL coverage, hand-curated |
| v1 manifesto markdown files | **13** | `manifestos/*.md` | 256 KB total; one per domain + one consolidation |
| v1 graph export (node details) | 389 nodes, 746 edges | `archive/v1/data/basis-kg-full.json` | **Not being ingested** — superseded by re-extraction from manifestos |
| Lex watchlist (Phase 4 seed) | **11** provisions | `src/data/lex_watchlist.json` | Housing Act 2004 sections; Phase 4 Track C starts here |
| v1 ingestion backlog (generated) | **172** entries | `data/v1_ingestion_backlog.json` | Priority split: 82 high / 28 medium / 62 low |

### 1b. v1 backlog — breakdown

**By publisher** (top 10):

| Host | Count |
|---|---|
| gov.uk | 18 |
| public.conservatives.com | 12 |
| labour.org.uk | 12 |
| libdems.org.uk | 12 |
| greenparty.org.uk | 12 |
| assets.nationbuilder.com (Reform) | 12 |
| ifs.org.uk | 9 |
| commonslibrary.parliament.uk | 8 |
| doi.org | 6 |
| obr.uk | 4 |
| (118 others across ~60 domains) | |

**By domain**:

| v2 domain | v1 count | Note |
|---|---|---|
| health (v1: nhs) | 20 | |
| immigration | 20 | |
| energy | 19 | v2 new domain |
| housing | 17 | |
| benefits (v1: welfare) | 15 | |
| defence | 13 | |
| eu_trade (v1: eu-trade) | 12 | v2 new domain |
| electoral_reform (v1: electoral-reform) | 12 | v2 new domain |
| justice | 12 | |
| taxation | 11 | |
| environment | 11 | |
| education | 10 | |

**By expected source type** (URL heuristic → adapter routing):

| Source type | Count | Routed to |
|---|---|---|
| DOCUMENTARY (general web / .gov.uk / think tanks) | 164 | `src/ingest/documentary.py` |
| DOCUMENTARY (DOI / academic) | 6 | `src/ingest/documentary.py` with CrossRef + Semantic Scholar enrichment |
| STRUCTURED_DATA | 1 | `src/ingest/structured_data.py` |
| TESTIMONY | 1 | `src/ingest/testimony.py` |
| **Total** | **172** | |

**By v1 tier hint (default_tier)**:

| Tier | Count | Meaning |
|---|---|---|
| T1 | 16 | Peer-reviewed / ONS-grade |
| T2 | 18 | Official govt publications |
| T3 | 48 | Institutional research (IFS, OBR, Nuffield) |
| T4 | 28 | Think tanks |
| T5 | 60 | Political (manifestos, party docs) |
| T6 | 2 | Media / commentary |

### 1c. Future inventory (not yet available)

| What | Size | Source | Gated on |
|---|---|---|---|
| Lex Graph full corpus | 820K provisions, 2.2M edges | Lex API at `lex.lab.i.ai.gov.uk` | i.AI MCP access request |
| Lex priority watchlist | ~5,000 provisions | Ego network queries from 20 anchor Acts | Lex access + SCHEMA-022 pilot |
| ONS datasets | ~100 datasets relevant to BASIS | `api.beta.ons.gov.uk` | None — reachable now |
| Police.uk crime data | per-location, all England & Wales | `data.police.uk` | None |
| CQC ratings | per-LA, all England | `api.cqc.org.uk` | None |
| Land Registry prices | per-LA | SPARQL at `landregistry.data.gov.uk` | None |
| Postcode → geography | universal | `api.postcodes.io` | None |
| Hansard positions | daily updates | parliament-mcp (i.AI) | MCP access request |
| BAILII judgments | ~daily | RSS + per-case fetch | None |
| FOI responses | on-demand | WhatDoTheyKnow API | None |

---

## 2. Data-flow pipelines

Five parallel ingestion paths, all producing schema-conformant sources + candidate nodes + routing decisions for the curator queue.

### 2a. DOCUMENTARY — the majority path

```
  URL (from backlog or manual)
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  src/ingest/documentary.py:DocumentaryAdapter        │
│    1. HTTP GET (requests)                            │
│    2. content_hash (sha256)                          │
│    3. Enrichment (parallel):                         │
│         - CrossRef (if DOI)                          │
│         - Semantic Scholar (if DOI)                  │
│         - gov.uk Content API (if gov.uk host)        │
│    4. suggest_tier_from_url (SCHEMA-009 heuristic)   │
│    5. Build DocumentarySource (Pydantic)             │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  extract_evidence (LLM)                              │
│    - Gemma 4 prompt: GEMMA_EVIDENCE_EXTRACTION       │
│    - Single-pass: nodes + intra-domain edges         │
│    - Output: candidate_nodes[]                       │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  Gemini Flash cross-check (per node)                 │
│    - FLASH_CROSS_CHECK prompt                        │
│    - PASS / FAIL:reason                              │
│    - Result attached as node.flash_check_result      │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  curator.route() per node (SCHEMA-024)               │
│    → Tier 1 auto-pass   (passed all gates)           │
│    → Tier 2 Claude queue                             │
│    → Tier 3 human queue                              │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  persistence.write()                                 │
│    - source → sources table                          │
│    - candidate_nodes → evidence_nodes table          │
│    - citations → citation_edges table                │
│    - routing decision → curator_queue table          │
└──────────────────────────────────────────────────────┘
```

### 2b. STRUCTURED_DATA — live APIs

```
  (provider, dataset_id) pair
    │
    ▼
  src/ingest/structured_data.py wraps one of:
    - extraction/data_sources.py:ons_get_observations
    - data_sources.py:get_crimes_at_location
    - data_sources.py:cqc_ratings_summary
    - data_sources.py:land_registry_average_price
    - data_sources.py:statxplore_list_schemas
    │
    ▼
  StructuredDataSource (Pydantic)
    + candidate AREA_METRIC nodes (Phase 3)
    │
    ▼
  curator.route() → tier
    │
    ▼
  area_metrics + sources tables
```

### 2c. STRUCTURAL — registry records

```
  (registry, record_id) — e.g. ('lex_graph', 'ukpga/2004/34/section/5')
    │
    ▼
  src/ingest/structural.py routes by registry enum
    │
    ├─ lex_graph ─→ extraction/lex_client.py
    │                 - get_provision
    │                 - get_explanatory_note
    │                 - commencement_gate (SCHEMA-011)
    │                 - structural_stability signals
    ├─ companies_house ─→ TODO
    ├─ ons_nspl ─→ TODO
    ├─ land_registry ─→ TODO
    └─ ... (ico_register, fca_register, charity_commission, electoral_commission)
    │
    ▼
  StructuralSource (registry discriminator)
  + Phase 4 legal nodes via Gemma + Hohfeldian schema constraint
    │
    ▼
  legal_nodes + lex_provisions + sources tables
```

### 2d. TESTIMONY — stated positions

```
  Hansard ref / FOI response / ombudsman ruling
    │
    ▼
  src/ingest/testimony.py
    - (parliament-mcp integration: TODO)
    - (WhatDoTheyKnow API: TODO)
    - Metadata-driven fallback for now
    │
    ▼
  TestimonySource (tier ceiling T3)
  + candidate POSITION nodes
    │
    ▼
  curator.route() → tier 3 by default if T5 citizen
    │
    ▼
  evidence_nodes + sources
```

### 2e. DERIVED — computations

```
  input_node_ids + algorithm_version
    │
    ▼
  src/ingest/derived.py
    - Checks inputs_curator_approved
    - Builds DerivedSource (no tier)
    │
    ▼
  computation output → evidence_nodes or fiscal_gap row
  (inherits verification_level = min(inputs))
```

---

## 3. External API connection inventory

| API | Role | Currently reachable? | Auth | Used by |
|---|---|---|---|---|
| **Gemma / Gemini via `generativelanguage.googleapis.com`** | LLM bulk extraction + Flash cross-check | **❌ 403 from this sandbox (Google blocks datacenter IPs for free tier). Works from residential / Azure / GitHub-hosted runners.** | `GOOGLE_AI_API_KEY` env | `src/extraction/google_ai_client.py`, `pipeline.py`, `agents.py` |
| **Supabase** | Live DB + frontend backend | Config present; **MCP OAuth flow requires per-session reconnect (no PAT yet)** | `SUPABASE_SERVICE_KEY`, or PAT via MCP | `src/scripts/run_migrations.py`, `ingest/persistence.py` (stub) |
| **CrossRef** | DOI → metadata | ✅ reachable, no auth | public API, User-Agent header | `src/ingest/enrichment/crossref.py` |
| **Semantic Scholar** | citation_count, venue, abstract | ✅ reachable, no auth | rate-limited (~100 req/5min) | `src/ingest/enrichment/semantic_scholar.py` |
| **OpenAlex** | fallback for non-DOI works | ✅ reachable | `mailto=` param | `src/ingest/enrichment/openalex.py` |
| **gov.uk Content API** | publisher + doc_type from any gov.uk URL | ✅ reachable | none | `src/ingest/enrichment/gov_uk.py` |
| **ONS Beta API** | statistical datasets | ✅ reachable | none (120 req/10s limit) | `src/extraction/data_sources.py:ons_*` |
| **Police.uk** | crime data | ✅ reachable | none | `data_sources.py:get_crimes_at_location` |
| **Postcodes.io** | postcode → geography | ✅ reachable | none (100 req/min free) | `data_sources.py:resolve_postcode` |
| **CQC public API** | care home ratings | ✅ reachable | none | `data_sources.py:cqc_*` |
| **Land Registry SPARQL** | property prices | ✅ reachable | none | `data_sources.py:land_registry_average_price` |
| **DWP Stat-Xplore** | benefits stats | ⚠️ limited (full access needs key) | API key (not set up) | `data_sources.py:statxplore_*` |
| **Lex API / Lex MCP** | UK legislation graph | ❌ not requested yet | i.AI onboarding | `src/extraction/lex_client.py` (stub) |
| **parliament-mcp** | Hansard, bills, committees | ❌ not requested yet | i.AI onboarding | not yet wired |
| **BAILII** | court judgments | ✅ reachable (RSS + HTML) | none | not yet wired |
| **WhatDoTheyKnow** | FOI responses | ✅ reachable | none | not yet wired |
| **Anthropic API** | fallback LLM (Sonnet 4.5) | ✅ reachable from this sandbox | API key (not yet acquired) | alternative to Gemma for Phase 2 extraction |

### API connection health summary

- **9 APIs live, reachable, no auth friction** (gov.uk, CrossRef, Sem.Scholar, OpenAlex, ONS, Police, CQC, Land Reg, Postcodes)
- **2 APIs blocked for this environment** (Gemma/Gemini 403 from datacenter; Supabase MCP needs PAT)
- **2 APIs gated on external access requests** (Lex, parliament-mcp)
- **3 APIs reachable but not wired yet** (Stat-Xplore, BAILII, WhatDoTheyKnow)

---

## 4. Per-frontend-page mapping

The v2 frontend (`apps/web/`, to be rebuilt in Phase 2) has these planned pages. Each row: what the user sees → where the data comes from → how it got there.

| Page | Displays | DB tables | Populated by |
|---|---|---|---|
| `/` | Landing: domain count, node count, verified count, fiscal gap | `evidence_nodes` (counts, aggregates), `sources` | Seed + ongoing ingestion |
| `/domains` | 12+ domain cards with headline finding per domain | `evidence_nodes` (filtered by domain) | DocumentaryAdapter extractions |
| `/domains/[slug]` | Nodes by type, confidence badges, tier pills, **verification_level badge** | `evidence_nodes`, `citation_edges`, `sources` | DocumentaryAdapter + curator.route + review_queue |
| `/domains/[slug]/nodes/[id]` | Full node detail: MC confidence bar, edges, source list with override pills, fiscal range, **routing-chain drawer** | `evidence_nodes`, `evidence_edges`, `citation_edges`, `sources`, `curator_queue` | everything above + `mc_engine` |
| `/postcode/[pc]` (Phase 3) | Local data: crime, CQC, property prices, percentile ranks | `area_metrics` | StructuredDataAdapter via `data_sources.py` |
| `/fiscal-gap` | Live computation: spending vs revenue, range | `evidence_nodes` with `fiscal_*` fields, `sources` where `source_type='DERIVED'` | DerivedAdapter + fiscal self-test CI check |
| `/search` | Full-text + filters: domain / type / confidence / verification_level | all evidence tables, full-text index | populated by ingestion |
| `/challenges` (Phase 2 alpha) | Submitted counter-sources | `challenges`, `scrutiny` (tables TBD) | authenticated user submissions |
| `/about` | Methodology, MC explanation, SCHEMA decisions, routing model (SCHEMA-024) | static + link to `docs/schema/` | manually authored |
| `/v1/` | Archived v1 site for provenance | `archive/v1/site/index.html` reading `archive/v1/data/*` | pre-Phase-1 snapshot |
| `/admin/queue` (operator only) | Tier 3 review UI (Phase 2 deliverable) | `curator_queue` where tier=3 | populated by every ingestion |

**Verification badge spec (SCHEMA-024)** — every node-detail view carries one of:

| Level | Badge | When |
|---|---|---|
| 🤖 `auto_verified` | neutral grey | Tier 1 gates passed, no review yet |
| 🧠 `ai_reviewed` | blue | Claude Tier 2 approved + Tier 1 passed |
| 👤 `human_curated` | green/gold | Above + spot-confirmed / reviewed by operator |

Click → drawer showing the full routing chain (which Tier 1 gates passed, Claude's note, audit trail).

---

## 5. Dependency graph

What's blocking what right now. ✅ = ready, 🟡 = scaffolded, 🔴 = blocked.

```
Ingestion pipeline (URL → DocumentarySource)          ✅
  │
  ├─ Enrichment APIs (CrossRef, SemScholar, gov.uk)   ✅
  │
  ├─ Gemma extraction                                 🔴 Google API blocks datacenter; needs
  │                                                     (a) GitHub Actions probe,
  │                                                     (b) self-hosted runner, OR
  │                                                     (c) Anthropic fallback
  │
  ├─ curator.route() (Tier 1 logic)                   ✅
  │   ├─ Tier 2 Claude workflow (subscription)        🟡 runbook written; waits on Tier 2 queue
  │   └─ Tier 3 review_queue.py                       ✅ tested with seed data
  │
  └─ Persistence                                      🟡 local jsonl works; Supabase stub
      └─ Supabase MCP                                  🔴 needs PAT for session-persistent auth

Phase 2 frontend (v2 site)                            📋 not started
  │
  └─ All of the above feeding real Supabase rows      depends on LLM backend + Supabase PAT

Phase 3 local data (postcode → metrics)               🟡 adapters built, not wired
  │
  └─ Depends on: ingestion live, frontend exists

Phase 4 legal layer                                   📋 gated on Lex API access request

Phase 5 action routing + templates                    📋 gated on solicitor pipeline
```

---

## 6. What's actually running vs what's rendering vs what's planned

### Running today (you could exercise right now)

- `python3 -m pytest tests/test_curator_routing.py` → 21/21 green
- `python3 -m ingest https://www.gov.uk/...` → produces schema-valid DocumentarySource with gov.uk enrichment, content_hash, tier T2
- `python3 src/scripts/run_agent.py evidence --max 2 --dry-run` → drains 2 backlog entries through the pipeline, reports tier counts
- `python3 src/scripts/review_queue.py --count` → shows tier + escalation histogram of local candidate queue
- `python3 src/scripts/generate_backlog.py` → regenerates `data/v1_ingestion_backlog.json` from archive

### Rendering today

- Live site at **hwesto.github.io/basis** — v1 single-page HTML, reads `archive/v1/data/*` — static, no live DB, no ingestion dependency

### Blocked pending external action

- LLM-driven candidate-node extraction — needs one of: working GCP-enabled Gemini key from residential/Azure IP; Anthropic API key; Agent-tool workaround
- Live Supabase writes — needs PAT for MCP session persistence
- Phase 4 legal extraction — needs Lex API access
- Parliamentary ingestion — needs parliament-mcp access
- v2 frontend — not yet written

---

## 7. Realistic daily throughput per current tooling

Assuming Gemma/Flash are reachable (GitHub Actions or local), the free tier permits:

| Workload | Calls/day used | Free tier cap | Headroom |
|---|---|---|---|
| Full v1 re-ingestion (one-off) | ~390 (200 Gemma + 190 Flash) | 14,400 Gemma / 1,500 Flash | ~40× |
| Phase 4 watchlist (11 items/day when changed) | ~22 | 14,400 Gemma | ~650× |
| Phase 8 steady state | ~30–50 | 14,400 Gemma | ~300× |
| Bulk historical extract of top 5K Lex provisions | ~10,000 | 14,400 Gemma / day | fits in 1 day (tight) or 3 days split |

**Conclusion:** free tier is not a constraint on normal operation. GitHub Actions on public repo: unlimited minutes, not a constraint either.

---

## 8. Maintenance rule

This doc updates whenever:

- A new source type, API, or frontend page is added
- A dependency changes (something unblocks or newly blocks)
- A table or pipeline stage is added / renamed / deprecated
- Throughput assumptions change materially

Kept alongside `docs/status.md`:

- `status.md` = **what state each thing is in** (working / stubbed / blocked)
- `system-map.md` = **how things connect** (this doc)

If both say different things, `status.md` is the truth for component state; this doc is the truth for topology. When they disagree, something just changed — update both.
