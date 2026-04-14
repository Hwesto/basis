---
id: SCHEMA-015
title: Evidence independence on SUPPORTS edges
status: PROVISIONAL
source: schema_decisions.md
---

### SCHEMA-015: Evidence independence on SUPPORTS edges

**Phenomenon:** The MC noisy-OR formula for SUPPORTS edges assumes each supporting
source independently establishes the claim. Independent evidence compounds multiplicatively.
Correlated evidence does not.

**Decision:** `evidence_independent: bool` on every SUPPORTS edge. When `False`, the
MC engine uses additive aggregation (the strongest single source) rather than noisy-OR.
When `True`, noisy-OR applies.

**Default:** `evidence_independent=True`. This is the optimistic default — assumes
independence unless explicitly flagged as correlated. This is wrong in many cases
(multiple papers drawing on the same dataset). The correct default would be `False`
with explicit independence assertion, but that creates excessive annotation burden.
The current default produces overconfident scores in correlated source clusters.

**Immediate action required:** The existing 746 edges in `data/` all implicitly assume
independence. A manual audit of the top 20 highest-confidence CLAIM nodes is needed
to identify and flag the most consequential cases of correlated evidence before Phase 2b.

**Assumptions:**
1. Curators can reliably identify correlated evidence. This requires knowing the
   provenance of sources, which requires the source fetch pipeline to be working.
   Currently 39 sources unfetched — those edges cannot be audited for independence.
2. The additive (max-of-independent) formula is the right correction for correlated
   evidence. Debatable — it's conservative but ignores partial independence. This
   is a known simplification.

**Status:** PROVISIONAL — default is wrong, requires manual audit before Phase 2b.
