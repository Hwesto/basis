---
id: SCHEMA-005
title: computed_confidence as MC output separate from extraction confidence
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-005: computed_confidence as MC output separate from extraction confidence

**Phenomenon:** The extraction-time confidence is a prior. The MC-propagated confidence
is a posterior that incorporates the quality of all upstream evidence.

**Decision:** `confidence` (HIGH/MEDIUM/LOW) is the human-assigned prior, set at
extraction. `computed_confidence` is a dict produced by the MC engine:
`{mean, std, p5, p95, label}`. These are separate fields and can diverge significantly.
The frontend displays `computed_confidence.label`; researchers can see both.

**Alternatives:**
- Replace `confidence` with `computed_confidence` entirely. Rejected: loses the
  extraction-time prior. If MC is re-run with different parameters, you need the
  original human assessment to re-anchor.
- Store only the label from MC, not the distribution. Rejected: the distribution
  (particularly p5 and p95) carries information about stability that the label doesn't.
  A node with mean=0.75 and std=0.40 is very different from mean=0.75 and std=0.05.

**Assumptions:**
1. The MC engine correctly propagates confidence from sources through the graph. This
   is a technical correctness assumption — see SCHEMA-016 through SCHEMA-022 for the
   specific MC design decisions.
2. Re-running MC with the same seed produces stable results. Verified: 10K samples,
   seed=42, <1% variance across runs.

**Status:** SETTLED
