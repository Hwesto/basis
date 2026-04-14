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

**v2 field set:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `amount` | `float` | yes | Point estimate. If a range is known, midpoint of `(amount_low + amount_high) / 2`. |
| `amount_low` | `float \| None` | no | Lower bound when the underlying evidence gives a range. |
| `amount_high` | `float \| None` | no | Upper bound when the underlying evidence gives a range. |
| `unit` | `Literal['bn_gbp', 'm_gbp', 'pct_gdp']` | yes | Normalised to `bn_gbp` for aggregation. |
| `gap_role` | `GapRole` | yes | See taxonomy below. |
| `direction` | `Literal['spending', 'revenue', 'net']` | yes | |
| `horizon_years` | `int \| None` | no | For multi-year totals; MC divides by this to annualise. |
| `year` | `int \| None` | no | Base year of the estimate. |
| `notes` | `str \| None` | no | Free text; methodology / caveats. |

**v2 revision (2026-04, range support):** v1 captured monetary uncertainty
as `{amount_low, amount_high}` on 68 nodes. The original v2 `amount: float`
scalar dropped this. Added `amount_low` and `amount_high` as optional
sibling fields. Validator rule: if either bound is set, both must be set
and `amount_low <= amount <= amount_high`. Rationale in
`docs/migration/AUDIT-V1-CONFORMANCE.md`.

**gap_role examples:**

| Role | Meaning | Example |
|---|---|---|
| `additional_need` | A cost that adds to the gap. | NHS workforce uplift: £20–25bn/yr. |
| `baseline` | Current spend or revenue — already funded. | 2024/25 DHSC budget: £181bn. |
| `position_only` | A party's stated target, not an independent estimate. | A manifesto pledge without OBR costing. |
| `summary` | A headline or aggregate reported elsewhere. | IFS total fiscal gap estimate. |
| `uplift` | An incremental increase over baseline. | Pay settlement adding £3–4bn to baseline. |
| `target_total` | The total cost a party commits to, whole-number. | Defence at 2.5% GDP. |

**Assumptions:**
1. The annual fiscal gap is the right frame for aggregation. It excludes
   one-off costs (e.g. Rwanda policy costs) and cumulative multi-year totals
   without amortisation. The current handling divides cumulative amounts by
   `horizon_years`. This is correct for comparing like-for-like annual costs
   but loses information about upfront capital requirements.
2. The six gap_roles are exhaustive. Currently true. Monitor when new
   domains are added.
3. Amount units are normalised to bn_gbp for aggregation. m_gbp amounts are
   divided by 1000 before summing. pct_gdp amounts require a GDP figure.
4. Where `amount_low`/`amount_high` are set, the MC engine samples
   uniformly across the range rather than treating `amount` as a point
   estimate. Non-range nodes use a ±10% noise floor per SCHEMA-018.

**GDP constant:** £3.1tn (OBR Economic and Fiscal Outlook, March 2024).
Updated from the earlier £2.3tn figure, which was ~35% out of date.
Lives in `src/extraction/mc_engine.py` as a module constant and is
refreshed on each OBR outlook publication. OQ-009 tracks the case for
making this a dynamic source.

**Falsification:**
- GDP figure changes materially (>5%) — update the constant and re-run CI.
- A new monetary node type that doesn't fit any gap_role — add a new
  role with documentation rather than forcing it into an existing category.
- A range whose midpoint-as-scalar misleads downstream aggregation
  (skewed distributions, non-linear costs) — revisit range handling.

**Status:** SETTLED — v2 field set with range support; GDP constant updated.
