---
id: SCHEMA-002
title: DomainEnum as typed, extensible enum
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-002: DomainEnum as typed, extensible enum

**Phenomenon:** Every node belongs to a thematic area. These areas determine which
extraction pipeline processes a node, which local data metrics link to it, and how the
frontend organises content.

**Decision:** `DomainEnum` is a Python `str, Enum` with explicit members. Free-text
`domain` fields are rejected at validation time. New domains require an explicit PR
adding them to the enum — they cannot be added by the extraction pipeline.

**Current members (18):**
`housing`, `health`, `education`, `benefits`, `economy`, `taxation`,
`environment`, `immigration`, `policing`, `defence`, `transport`,
`social_care`, `employment`, `consumer`, `justice`, `energy`, `eu_trade`,
`electoral_reform`.

**v2 revision (2026-04):** added `energy`, `eu_trade`, `electoral_reform`.
The v1 audit (`docs/migration/AUDIT-V1-CONFORMANCE.md`) showed 86 nodes
(22% of the v1 corpus) were in these three domains and were blocked
from v2 conformance. These are legitimate, non-overlapping UK policy
domains — their absence was an oversight. Naming normalised to snake
case (`eu_trade`, `electoral_reform`) to match the Python convention
already in use across the enum.

**Alternatives:**
- Free-text string. Rejected: 'housing' vs 'Housing' vs 'housing_disrepair' in the
  current data/ directory. Already observed in Phase 1. CI check caught some but not all.
- Hierarchical taxonomy (housing > disrepair, housing > eviction). Considered and
  deferred: the classification overhead at extraction time is high, and cross-domain
  queries become complex. Revisit at Phase 4 when domain coverage expands.
- Tag-based (a node has multiple domain tags). Possible but conflicts with the
  cross-layer join logic, which assumes each node belongs to one domain.

**Assumptions:**
1. Domains are mutually exclusive for a given node. A claim about NHS funding for
   housing support arguably spans health AND housing. Current handling: assign to
   the primary domain, add cross-domain SUPPORTS edge to the secondary domain node.
   This is a workaround, not a solution.
2. The initial 12 domains cover the Phase 1-3 evidence corpus. True at time of writing.

**Falsification:**
- A node that genuinely cannot be assigned a primary domain without information loss.
  If this becomes common (>5% of nodes), introduce a `primary_domain` +
  `secondary_domains: list` structure.

**Status:** SETTLED for current corpus. PROVISIONAL on mutual exclusivity assumption.
