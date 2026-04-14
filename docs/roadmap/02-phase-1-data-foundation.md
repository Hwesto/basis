---
phase: 1
status: v1_archived
source: BASIS_ROADMAP.md
---

> **v1 — archived.** This is the historical v1 Phase 1 build. The corpus
> does not conform to the reconciled v2 schema (audit:
> `docs/migration/AUDIT-V1-CONFORMANCE.md` — 35% node conformance, 0%
> source conformance). See `docs/migration/README.md` for the archive
> decision and `docs/roadmap/04a-v2-phase-1-pipeline.md` for the
> replacement build.

### Phase 1 (v1): Data Foundation — ARCHIVED

**What it delivered:** An honest graph. 389 nodes, 746 edges, 12 domains.
Fiscal gap computed from metadata (£52.6–101.6bn), not hardcoded. Monte
Carlo confidence propagation with verdict-tiered assumption discount.
Supabase seeded with 1,319 rows. 51/130 FACTs verified against source
text.

**Key systems built:**

- 6-check CI validator (schema, edges, topics, fiscal, confidence,
  source integrity) — retained in `src/scripts/validate.py`
- Monte Carlo confidence engine (10k samples, 389 nodes, 25s runtime) —
  retained in `src/extraction/mc_engine.py`
- Assumption contestability discount (HIGH→0.85, MEDIUM→0.70, LOW→0.50)
  — codified in `src/source_models.py`
- Source fetch pipeline (133/172 sources fetched, 26 PDFs extracted) —
  not reusable; v1 corpus archived; URLs become the v2 ingestion
  backlog
- Fiscal gap_role taxonomy (additional_need, baseline, position_only,
  summary, uplift, target_total) — retained verbatim in `SCHEMA-014`
- Verification pipeline (51 confirmed, 0 refuted) — v1 metric; v2
  rebuilds verification on top of the new `citation_edges` model

**What becomes of this in v2:**

- `src/extraction/mc_engine.py` — reusable as-is
- `src/scripts/validate.py` — will be refactored into
  `scripts/validate_graph.py` to run against the live v2 graph rather
  than the v1 JSON dump
- `src/source_models.py` — reusable but needs STRUCTURAL rename
  (SCHEMA-008 reconciliation)
- The 172 v1 source references become `data/v1_ingestion_backlog.json`
  — input to the v2 pipeline
- The 389 v1 nodes are not migrated. Their structural role (FACT /
  ASSUMPTION / CLAIM / POLICY / POSITION distinction, per-domain
  counts) informs the v2 rebuild target

**Known gaps carried forward as v2 work items (not blocking):**

- 79 unverified FACTs from v1 — re-ingestion will produce fresh
  verification status against the v2 `citation_edges` model
- Sensitivity analysis design — re-applied on top of the v2 graph
  once re-ingestion completes

**Status:** ✅ v1-shipped. Superseded by v2 Phase 1 (see `04a-`).
