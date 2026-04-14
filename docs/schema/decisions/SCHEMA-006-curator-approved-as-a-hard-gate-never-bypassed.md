---
id: SCHEMA-006
title: curator_approved as a hard gate, never bypassed
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-006: curator_approved as a hard gate, never bypassed

**Phenomenon:** Citizens rely on this platform to make decisions about legal complaints,
benefit claims, and other consequential actions. Wrong information causes real harm.

**Decision:** `curator_approved: bool = False` is the hard gate.
The API never returns a node where `curator_approved=False` to the
public frontend. The flag is flipped via the routing flow specified
in **SCHEMA-024 (three-tier curator routing)** — automated checks,
Claude judgment via MCP, and human exception review.

The principle is preserved (nothing public until the gate flips);
SCHEMA-024 specifies *who* can flip it for *which* node and under
*what* conditions. A companion field `verification_level`
(`auto_verified` / `ai_reviewed` / `human_curated`) is exposed
publicly so readers see calibrated trust per node.

**DERIVED node exception (was OQ-007, now resolved):** DERIVED nodes
auto-pass Tier 1 when all `input_node_ids` are themselves
`curator_approved=true`. The DerivedSource records the input set;
verification_level inherits the *minimum* level across inputs
(a derivation over `auto_verified` inputs cannot itself be
`human_curated`). See SCHEMA-024.

**Assumptions:**
1. Human curators are more reliable than automated checks for non-deterministic content.
   True for legal and evidence nodes. Questionable for simple statistical derivations.
2. The curator queue is responsive enough that new content reaches `curator_approved=True`
   within a reasonable time. No SLA is currently defined. Gap.

**Falsification:**
- If curator throughput becomes a bottleneck that prevents timely updates to legal nodes
  when legislation changes, the gate creates more harm than it prevents. Mitigation:
  track time-in-queue as a metric from Phase 4 onwards.

**Status:** SETTLED on the principle. The flow is specified by
SCHEMA-024 (PROVISIONAL pending calibration). DERIVED exception
resolved by SCHEMA-024's input-inheritance rule.
