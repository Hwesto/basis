---
id: OQ-007
status: resolved
blocking: —
phase: —
resolved_by: SCHEMA-024
source: schema_decisions.md
---

# OQ-007 — RESOLVED

**Question:** How does `curator_approved` work for DERIVED nodes
computed automatically?

**Resolved by SCHEMA-024 (three-tier curator routing).** DERIVED
nodes auto-pass Tier 1 when all `input_node_ids` are themselves
`curator_approved=true`. The DerivedSource records the input set;
verification_level inherits the minimum level across inputs (a
derivation over `auto_verified` inputs cannot itself be
`human_curated`).

This avoids the original PROVISIONAL gap in SCHEMA-006 — DERIVED
nodes get the gate flipped automatically by the routing tier system,
not by a one-off pipeline override.
