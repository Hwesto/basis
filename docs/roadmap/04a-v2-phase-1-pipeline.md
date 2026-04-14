---
phase: v2-1
status: in_progress
source: docs/migration/README.md
---

### v2 Phase 1: Pipeline build + schema propagation + archive

**Objective:** Everything that needs to exist in code before the v1
corpus can be re-ingested. Replaces v1 Phase 1 / 2a / 2b.

**Why this phase exists:** The `src/` skeleton has ~80% of an ingestion
pipeline already. What's missing is generalisation across all five
source types, a persistence layer, a small number of new SQL tables,
and code-level propagation of schema decisions that landed only in the
docs. This phase fills those gaps.

**Deliverables:**

1. **Archive v1 artefacts.** Move `data/basis-kg-*.json`,
   `data/basis-data.js`, `site/index.html` into `archive/v1/`. Add a
   "this is a rebuild" banner to the public site. Tag current `main`
   as `v1-final`. Generate `data/v1_ingestion_backlog.json` from the
   172 v1 source entries as the re-ingestion queue.

2. **Propagate schema revisions to code.** Apply the doc-level
   reconciliations that haven't hit `src/`:
   - `src/base_schema.py` — extend `DomainEnum` with `energy`,
     `eu_trade`, `electoral_reform`; add `amount_low` / `amount_high`
     to `FiscalMetadata`; add `CitationEdge` model per SCHEMA-009
   - `src/source_models.py` — rename `LegislativeStructuralSource` →
     `StructuralSource` with `registry` discriminator per SCHEMA-008 /
     SCHEMA-010; update `SourceTypeEnum`
   - `src/extraction/pipeline.py` — propagate renames; generalise
     `extract_evidence()` to accept URLs (not only pre-fetched text)

3. **Complete the ingestion pipeline.** New `src/ingest/` module with
   one adapter per source type, each producing a schema-valid source
   plus candidate node(s):
   - `src/ingest/documentary.py` — URL + PDF fetcher, Semantic Scholar
     enrichment, `DocumentarySource` construction, content_hash
   - `src/ingest/structured_data.py` — wraps the existing
     `data_sources.py` (ONS / Police / CQC / Land Registry /
     Postcodes), emits `StructuredDataSource` + candidate
     `AREA_METRIC` nodes
   - `src/ingest/structural.py` — unifies Lex Graph + Companies House
     + ONS NSPL + Land Registry title searches under
     `StructuralSource` with per-registry alpha
   - `src/ingest/testimony.py` — Hansard + FOI wrappers → `TestimonySource`
     + candidate POSITION nodes
   - `src/ingest/derived.py` — builds `DerivedSource` from
     `input_node_ids` + algorithm output (e.g. fiscal gap computation)
   - `src/ingest/persistence.py` — Supabase writer; runs every insert
     through Pydantic validation; failures go to a rejection log, not
     the DB
   - `src/ingest/cli.py` — `python -m basis.ingest <url|id>` one-shot;
     `python -m basis.ingest backlog` batch mode

4. **SQL: add missing tables.** Currently `src/sql/` has `sources`,
   `legal_nodes`, `lex_provisions`, `area_metrics`, `citizen_actions`.
   Missing:
   - `evidence_nodes` — generic table for FACT / ASSUMPTION / CLAIM /
     POLICY / POSITION (v1 had these in JSON, never in SQL)
   - `citation_edges` — per SCHEMA-009, with `default_tier` fallback +
     `claim_tier_override` + `claim_tier_justification`
   - `curator_queue` — referenced across pipeline.py and the CI
     validator, never created

5. **Validator.** Refactor `scripts/audit_v1_graph.py` →
   `scripts/validate_graph.py`. Same Pydantic validation, but operating
   against the live v2 DB rather than the archived v1 JSON. Wire into
   GitHub Actions as a PR gate.

6. **Rebuild banner on public site.** `site/index.html` gets a visible
   banner at the top pointing at the v2 rebuild status. No redirect,
   no outage.

**Out of scope for this phase:**

- Re-ingestion of the v1 corpus (that's Phase 2)
- New frontend build (Phase 2)
- Curator queue UI (Phase 2; CLI + SQL only in Phase 1)
- `SCHEMA-018` MC engine calibration study (deferred)
- `SCHEMA-019` alpha calibration study (deferred)

**Success criteria:**

- `python -m basis.ingest <ifs-pdf-url> --dry-run` produces a valid
  `DocumentarySource` Pydantic instance + ≥1 candidate FACT node that
  pass `scripts/validate_graph.py`
- `python -m basis.ingest <ons-api-endpoint> --dry-run` produces a
  valid `StructuredDataSource` + candidate `AREA_METRIC`
- `python -m basis.ingest <lex-provision-id> --dry-run` produces a
  valid `StructuralSource` with `registry='lex_graph'`
- `scripts/validate_graph.py` passes against a seeded Supabase with at
  least 1 node of each type
- `data/v1_ingestion_backlog.json` generated and committed (~170
  entries)
- v1 artefacts moved to `archive/v1/`; public site has rebuild banner;
  gh-pages still renders the v1 snapshot

**References:**

- `docs/migration/README.md` — why this phase exists
- `docs/migration/AUDIT-V1-CONFORMANCE.md` — evidence driving the
  scope
- `docs/schema/decisions/SCHEMA-002`, `-008`, `-009`, `-014` — specific
  revisions being propagated
- `src/extraction/pipeline.py` — existing legal-extraction foundation
  being generalised
