---
id: SCHEMA-006
title: curator_approved as a hard gate, never bypassed
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-006: curator_approved as a hard gate, never bypassed

**Phenomenon:** Citizens rely on this platform to make decisions about legal complaints,
benefit claims, and other consequential actions. Wrong information causes real harm.

**Decision:** `curator_approved: bool = False` is set to True only by explicit human
action in the curator queue. The API never returns a node where `curator_approved=False`
to the public frontend. No pipeline step sets this to True automatically.

**Exception being considered:** Purely computational nodes — percentile ranks, fiscal
gap components, MC scores — are deterministic derivations that don't require human
judgment. Current handling: these are `DERIVED` nodes; the computation pipeline sets
`curator_approved=True` automatically. This is a genuine exception to the principle and
needs a cleaner contract — possibly `requires_curator_review: bool` as a separate field
from `curator_approved`, where DERIVED nodes have `requires_curator_review=False`.

**Assumptions:**
1. Human curators are more reliable than automated checks for non-deterministic content.
   True for legal and evidence nodes. Questionable for simple statistical derivations.
2. The curator queue is responsive enough that new content reaches `curator_approved=True`
   within a reasonable time. No SLA is currently defined. Gap.

**Falsification:**
- If curator throughput becomes a bottleneck that prevents timely updates to legal nodes
  when legislation changes, the gate creates more harm than it prevents. Mitigation:
  track time-in-queue as a metric from Phase 4 onwards.

**Status:** SETTLED on the principle. PROVISIONAL on the DERIVED exception.
