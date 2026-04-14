---
id: SCHEMA-023
title: Legal consistency flags as CI checks 7-8
status: SETTLED
related: [OQ-002, OQ-003, OQ-005]
source: schema_decisions.md
---

### SCHEMA-023: Legal consistency flags as CI checks 7-8

**Phenomenon:** Single-node verification (is this extraction correct?) misses structural
problems between nodes (is this legal structure coherent?). A duty that cannot be
enforced is not just an extraction gap — it may be a genuine flaw in the legislation
that citizens need to know about.

**Decision:** Two database queries added as CI check 7 and 8, running against the
legal layer on every commit once legal nodes exist.

**Check 7 — ENFORCEMENT_GAP:**
```sql
SELECT n.id, n.statement, n.domain
FROM legal_nodes n
WHERE n.node_type = 'DUTY'
AND NOT EXISTS (
  SELECT 1 FROM legal_edges e
  JOIN legal_nodes m ON m.id = e.to_id
  WHERE e.from_id = n.id
  AND e.edge_type = 'ENFORCED_BY'
  AND m.node_type = 'MECHANISM'
)
AND n.curator_approved = true;
```
A DUTY node with no reachable MECHANISM via ENFORCED_BY is either an extraction
error (mechanism not yet extracted) or a genuine enforcement gap in the law. Both
findings are valuable. The CI check surfaces them; the curator decides which it is.

Housing Act 2004 example: category 2 hazards create no enforceable obligation on
local authorities — there is a power to act but no duty. The ENFORCEMENT_GAP check
surfaces this as a known finding, not an extraction error.

**Check 8 — MISSING_CORRELATIVE:**
Hohfeld requires correlatives — every RIGHT has a corresponding DUTY, every POWER
has a corresponding LIABILITY. Absence may be an extraction gap or a legal incoherence.

```sql
SELECT n.id, n.node_type, n.statement
FROM legal_nodes n
WHERE n.node_type = 'RIGHT'
AND NOT EXISTS (
  SELECT 1 FROM legal_nodes n2
  WHERE n2.node_type = 'DUTY'
  AND EXISTS (
    SELECT 1 FROM legal_edges e
    WHERE (e.from_id = n.id AND e.to_id = n2.id)
    OR (e.from_id = n2.id AND e.to_id = n.id)
  )
)
AND n.curator_approved = true;
-- Repeat for POWER/LIABILITY pairs
```

**What's deferred:** CIRCULAR_DEFEASIBILITY and TEMPORAL_IMPOSSIBILITY require
the five-layer legal enrichment schema (Phase 4b). AGENT_UNRESOLVED requires the
institutional power typing layer. These are not implementable against the current
LegalNode schema.

**Assumptions:**
1. The queries return a manageable number of results. At 200 nodes (Phase 4 target),
   maybe 10-20 flagged items per run. Acceptable. At 5,000 nodes, needs batching.
2. ENFORCEMENT_GAP is an informative finding, not a blocking error. Correct — a
   genuine enforcement gap in legislation is a civic finding worth surfacing. Only
   extraction errors should block; legal gaps should be reported.

**Status:** SETTLED for checks 7-8. DEFERRED for checks 9-12 (enrichment layers).

---

*Version: 0.3 — updated April 2026: SCHEMA-003 settled (OQ-005 resolved, `england_and_wales` added), OQ-003 aligned to DEFERRED/Phase 4b, duplicate OQ-002 row removed, SCHEMA-009 citation_edge model clarified (see roadmap §Source Taxonomy). v0.2 added SCHEMA-011 (six-value commencement, OQ-002 resolved), SCHEMA-012 DEFERRED, SCHEMA-023 (legal consistency CI checks 7 and 8).*
*Next review: before Phase 4 legal extraction begins*
*Owner: Harry Weston*
