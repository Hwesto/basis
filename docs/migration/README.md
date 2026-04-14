# Migration: v1 → v2

## Decision: Option B — archive v1, rebuild v2 from scratch

The v1 corpus (389 nodes, 172 sources, 746 edges) was built before the
schema decisions in `docs/schema/` were formalised. The conformance
audit (`AUDIT-V1-CONFORMANCE.md`) showed migration is not viable:

| Category | v1 → v2 pass | Key blocker |
|---|---|---|
| Nodes | 137 / 389 (35%) | 86 in domains not in `DomainEnum`; all 75 ASSUMPTION nodes lack required v2 fields; all 69 POSITION nodes lack `actor` |
| Sources | 0 / 172 (0%) | Every source missing `publisher` + `tier_justification` |
| Edges | 745 / 745 field-valid, but 72 dangle | References to missing nodes |

Migration = re-authoring most records by hand against the v2 contract.
The v1 data shape also differs in meaningful ways (fiscal stored as
ranges, not scalars; tier on source, not citation edge). We archive
and rebuild instead.

## What we keep

- **172 source references** — URLs, titles, authors, dates — become
  `data/v1_ingestion_backlog.json`, the queue for the v2 ingestion
  pipeline.
- **13 manifesto markdowns** — input corpus for evidence extraction,
  unchanged.
- **v1 graph** — frozen on `archive/v1` branch and moved to
  `archive/v1/` subdir on the working branch. Served at `/v1/` on the
  public site after cutover.
- **Learning from Phase 1** — the assumption/fact split, the tiered
  source model, the MC engine design. These are canonical. v1 was
  the prototype that proved them.

## What we rebuild

The v2 build is **pipeline-first**, not data-first. Insight from the
`src/` skeleton survey: ~80% of the ingestion pipeline already exists
(`src/extraction/pipeline.py` 500 lines; `data_sources.py` 474 lines
with live ONS/Police/CQC/Land Registry adapters; `lex_client.py`,
`google_ai_client.py`, `mc_engine.py` 402 lines). What's missing:

1. Generalisation of the evidence-extraction path beyond legal
   sources
2. Persistence layer (the pipeline currently returns dicts, not DB
   rows)
3. Adapters for TESTIMONY and DERIVED source types
4. `citation_edges` / `evidence_nodes` / `curator_queue` SQL tables
5. Code-level propagation of SCHEMA-008/009/002/014 doc
   reconciliations (docs already landed; code lags)

Once those land, v2 Phase 2 re-ingests the v1 backlog through the
pipeline. The resulting graph is schema-compliant by construction.

## Scope of rebuild (default)

**Target:** loose parity with v1 — approximately 150–200 FACT, 60–80
ASSUMPTION, 40–70 CLAIM, 30–60 POLICY, 40–70 POSITION across 12–15
domains. Exact counts don't matter; coverage of the top fiscal / policy
claims does. Quality bar is v2-schema-compliant, not v1-quantity-matching.

## Schema revisions triggered by this migration

Four schema docs get updated as part of Phase B. Defaults applied here
because the audit evidence makes each call clear:

1. **SCHEMA-002 `DomainEnum`** — extend with `energy`, `eu_trade`,
   `electoral_reform`. Audit shows 86 nodes (22% of v1 corpus) blocked
   without these. These are legitimate UK policy domains — omission
   was an oversight.
2. **SCHEMA-014 `FiscalMetadata`** — add `amount_low` / `amount_high`
   fields alongside `amount`, keeping `amount` as point estimate or
   midpoint. v1 captured uncertainty ranges (68 nodes); dropping this
   is an epistemic regression. **Default: support ranges** (option A
   from the plan).
3. **SCHEMA-008** — propagate `LEGISLATIVE_STRUCTURAL` → `STRUCTURAL`
   with `registry` discriminator into `src/source_models.py`. Docs
   reconciled already (commit `0f7d3c0`); code lags.
4. **SCHEMA-009** — implement `citation_edge` model in
   `src/base_schema.py` + `src/sql/citation_edges.sql`. Docs only so
   far.

GDP constant (`SCHEMA-014`) also corrected from £2.3tn → £3.1tn
(OBR 2024).

## Public site during rebuild (default)

Current gh-pages site (v1) **stays live** with a banner at the top of
`site/index.html`:

> BASIS is being rebuilt against a formalised schema.
> This is v1 — kept for reference. v2 ships when the ingestion
> pipeline is validated against the full source backlog.

No redirect, no outage.

At v2 cutover: `site/index.html` → `archive/v1/site/index.html`; new
v2 Next.js app replaces gh-pages root; v1 served at `/v1/` sub-route.

## Phased plan

- **Phase A — Archive v1.** Freeze v1 artefacts. Extract source backlog
  to `data/v1_ingestion_backlog.json`. Update public site with rebuild
  banner. Move `data/basis-kg-*.json`, `data/basis-data.js`,
  `site/index.html` into `archive/v1/`.
- **Phase B — Schema revisions.** Apply the four listed above to
  `src/base_schema.py` and `src/source_models.py`. Add `CitationEdge`
  model. Update SCHEMA-002 / SCHEMA-014 docs.
- **Phase C — Complete ingestion pipeline.** Build `src/ingest/` with
  per-source-type adapters (documentary, structured_data, structural,
  testimony, derived) + persistence module. Add missing SQL tables
  (`evidence_nodes`, `citation_edges`, `curator_queue`). Refactor
  `scripts/audit_v1_graph.py` → `scripts/validate_graph.py` as a CI
  check against the live v2 graph.
- **Phase D — Re-ingest v1 backlog.** Run pipeline over the 172
  sources + 13 manifestos. Curator queue review cycle. Target ~160
  FACT, ~70 ASSUMPTION, ~55 CLAIM, ~45 POLICY, ~55 POSITION.
- **Phase E — Deploy v2 site.** New Next.js frontend reading from
  Supabase. v1 archive at `/v1/` sub-route.

Each phase has its own roadmap file under `docs/roadmap/` (to be
generated as the reframing pass lands).

## Assumptions / defaults applied (flag if incorrect)

- **Fiscal ranges:** supported (SCHEMA-014 revision, option A)
- **Rebuild scope:** loose v1 parity (~400 nodes, ~170 sources)
- **Public site:** freeze v1 with banner, swap at cutover
- **3 missing domains:** added to enum rather than reclassified or
  dropped
- **Source ID namespace:** reserved — v2 sources derived from v1
  entries keep the same `source_id` (`SRC-NHS-001` etc.) so manifesto
  claim-links resolve after re-ingestion
- **LLM usage for re-ingestion:** Gemma (free tier) primary, Flash
  cross-check, Claude Code for curator-adjacent review. Cost target:
  £0 for bulk ingestion, ≤£50 for cross-check and validation passes
- **Branch strategy:** work continues on `claude/general-session-sk1ZA`;
  `archive/v1` branch created from current `main` at the point of Phase
  A cutover

## References

- `docs/migration/AUDIT-V1-CONFORMANCE.md` — full audit report
- `docs/migration/audit-v1-conformance.json` — machine-readable detail
- `/root/.claude/plans/snoopy-hugging-sonnet.md` — execution plan
  (external to repo; generated during planning session)
