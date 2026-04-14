---
id: OQ-008
status: resolved
blocking: —
phase: —
resolved_by: SCHEMA-024
source: schema_decisions.md
---

# OQ-008 — RESOLVED (folded into SCHEMA-024 calibration)

**Question:** Inter-rater agreement study: are HIGH/MEDIUM/LOW
consistently assigned across extractors?

**Resolved by SCHEMA-024 (three-tier curator routing).** Now that
Claude is the de-facto rater for most nodes (Tier 2), inter-rater
agreement IS Claude-vs-Harry agreement on the same source. SCHEMA-024
mandates a calibration study (100 random Claude-approved nodes,
≥90% agreement bar) plus a 5% ongoing spot-check, which together
provide the same evidence the original OQ-008 was asking for.

The original framing assumed multiple human raters; in practice the
rater pool is one human + one LLM, and the calibration design
matches that.
