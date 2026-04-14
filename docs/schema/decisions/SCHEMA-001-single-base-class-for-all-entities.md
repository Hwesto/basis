---
id: SCHEMA-001
title: Single base class for all entities
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-001: Single base class for all entities

**Phenomenon:** Every entity in the system — a policy claim, a legal right, a local
crime metric, a citizen action outcome — shares a common structure: it is a statement
about the world, it came from somewhere, it has a degree of confidence, and it requires
human sign-off before it affects citizens.

**Decision:** `BaseNode` is the root class. Every entity type is a subclass. The
curator queue, CI validator, and MC engine operate against `BaseNode` only. Domain-
specific fields belong on subclasses, never on the base.

**Alternatives:**
- Separate tables per layer (evidence_nodes, legal_nodes, area_metrics). Rejected:
  produces five curator queues, five CI checks, five confidence engines. We've already
  seen this pattern fail in Phase 1 — the fiscal validator, edge validator, and schema
  validator were written separately and diverged.
- Flat table with nullable columns per type. Rejected: schema drift is undetectable.
  A FACT node with a `duty_holder` field set is a silent error, not a validation failure.
- JSON blob per node with no typed schema. Rejected: same as flat table but worse —
  Gemma would produce inconsistent shapes and we'd never know.

**Assumptions:**
1. All entities in the system share the cross-cutting fields (source traceability,
   confidence, curator gate, provenance). If a future entity type genuinely doesn't
   need a confidence score or a source, this assumption is violated.
2. The cost of subclass overhead is lower than the cost of schema divergence across layers.

**Falsification:**
- A node type that has no meaningful confidence score and no external source — e.g. a
  purely structural computation with deterministic output. This would be a `DERIVED`
  node with `source_type=DERIVED`. Currently handled. Monitor.
- A node type where `curator_approved` makes no sense — e.g. an automatically-computed
  percentile rank. Current handling: `curator_approved=True` set automatically by the
  computation pipeline, not by a human. This is a weak point — the gate is bypassed.
  Acceptable for Phase 3 but needs a cleaner solution.

**Status:** SETTLED
