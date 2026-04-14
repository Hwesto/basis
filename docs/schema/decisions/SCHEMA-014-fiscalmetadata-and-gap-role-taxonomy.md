---
id: SCHEMA-014
title: FiscalMetadata and gap_role taxonomy
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-014: FiscalMetadata and gap_role taxonomy

**Phenomenon:** Monetary claims in the evidence graph are heterogeneous — current
spending, additional needs, revenues, projections. The £44-146bn headline figure is
only meaningful if we distinguish which monetary nodes contribute to it.

**Decision:** `FiscalMetadata` as a nested Pydantic model on FACT, CLAIM, and POLICY
nodes. `gap_role` determines whether a node contributes to the computed fiscal gap.
The six gap_roles: `additional_need`, `baseline`, `position_only`, `summary`,
`uplift`, `target_total`. The fiscal self-test in CI recomputes the gap from gap_role
metadata and asserts it overlaps the stated £44-146bn range.

**Assumptions:**
1. The annual fiscal gap is the right frame for aggregation. It excludes one_off costs
   (e.g. Rwanda policy costs) and cumulative multi-year totals without amortisation.
   The current handling divides cumulative amounts by `horizon_years`. This is correct
   for comparing like-for-like annual costs but loses information about upfront
   capital requirements.
2. The six gap_roles are exhaustive. Currently true. Monitor when new domains added.
3. Amount units are normalised to bn_gbp for aggregation. m_gbp amounts are divided
   by 1000 before summing. pct_gdp amounts require a GDP figure — currently hardcoded
   at £2.3tn. This is a known approximation.

**Falsification:**
- GDP figure changes materially (>5%) — update the GDP constant and re-run CI.
- A new monetary node type that doesn't fit any gap_role — add a new role with
  documentation rather than forcing it into an existing category.

**Status:** SETTLED on structure. PROVISIONAL on GDP constant.

---

## Part 4: Edge Semantics
