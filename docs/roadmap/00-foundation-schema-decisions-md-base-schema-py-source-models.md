---
phase: foundation
status: settled
source: docs/schema/
---

### Foundation — Schema contract (settled)

**The contract everything is built against.**

The schema comes first. Before any code. Every node type, edge type, and
confidence parameter has an entry recording: the phenomenon it represents,
what we chose, alternatives considered, assumptions made, and what would
cause us to revise. Without it, when Gemma makes extraction errors you
can't tell whether it's a model failure or a schema ambiguity. When a
legal challenge surfaces a case the schema can't handle, you don't know
which assumption is being violated.

**Canonical sources:**

- `docs/schema/decisions/` — one file per SCHEMA-NNN (23 decisions)
- `docs/schema/open_questions/` — one file per OQ-NNN (10 open questions)
- `docs/schema/README.md` — status index with live resolution state
- `src/base_schema.py` — Pydantic implementation of the decisions
- `src/source_models.py` — five source type subclasses with MC alpha
  priors and per-type validation rules

**Key decisions:**

- **SCHEMA-001** — Single `BaseNode` root class. One curator queue, one
  CI validator, one MC engine. Domain-specific fields on subclasses.
- **SCHEMA-002** — `DomainEnum` typed. v2 members: `housing`, `health`,
  `education`, `benefits`, `economy`, `taxation`, `environment`,
  `immigration`, `policing`, `defence`, `transport`, `social_care`,
  `employment`, `consumer`, `justice`, `energy`, `eu_trade`,
  `electoral_reform`. Audit-driven extension applied 2026-04.
- **SCHEMA-003** — `JurisdictionEnum` with six members including
  `england_and_wales`. Resolves OQ-005.
- **SCHEMA-004** — Confidence categorical (HIGH/MEDIUM/LOW). No decimal
  scores at the extraction layer.
- **SCHEMA-008** — Five source types: DOCUMENTARY, STRUCTURED_DATA,
  STRUCTURAL (with `registry` discriminator per SCHEMA-010), DERIVED,
  TESTIMONY. `SourceTypeEnum` explicitly extensible.
- **SCHEMA-009** — Tier lives on the citation edge (`claim_tier_override`),
  not the source. Source carries `default_tier` as prior.
- **SCHEMA-011** — Commencement status as six-value enum. Resolves OQ-002.
- **SCHEMA-014** — `FiscalMetadata` with `amount` + optional
  `amount_low` / `amount_high` range fields. GDP constant £3.1tn (OBR
  2024). gap_role taxonomy canonical.
- **SCHEMA-018** — Monte Carlo over analytical propagation.
- **SCHEMA-020** — Assumption contestability discount (HIGH→0.85,
  MEDIUM→0.70, LOW→0.50). Provisional.
- **SCHEMA-023** — Legal consistency flags as CI checks 7 and 8.

**Open questions (current):**

10 open questions total — 2 resolved (OQ-002, OQ-005), 1 deferred
(OQ-003, deferred with SCHEMA-012 to Phase 4b), 7 open. See
`docs/schema/README.md` for the live status index.

**Gaps between docs and code (Phase 1 work):**

The reconciled decisions above are landed in `docs/` but not all are
reflected in the `src/` skeleton yet:

- `DomainEnum` in `src/base_schema.py` still has the 15-member v1 list;
  needs `energy`, `eu_trade`, `electoral_reform` added (SCHEMA-002)
- `FiscalMetadata` in `src/base_schema.py` still has scalar `amount`
  only; needs `amount_low` / `amount_high` (SCHEMA-014)
- `src/source_models.py` still uses `LegislativeStructuralSource`;
  needs rename to `StructuralSource` with `registry` discriminator
  (SCHEMA-008, SCHEMA-010)
- `CitationEdge` model does not exist in `src/base_schema.py`;
  `src/sql/citation_edges.sql` also missing (SCHEMA-009)
- `src/extraction/pipeline.py` references `LEGISLATIVE_STRUCTURAL`;
  needs propagation of the SCHEMA-008 rename

All of these are v2 Phase 1 deliverables — see
`docs/roadmap/04a-v2-phase-1-pipeline.md`.

**Status:** ✅ Settled in `docs/`. Code propagation in-flight (v2 Phase 1).
