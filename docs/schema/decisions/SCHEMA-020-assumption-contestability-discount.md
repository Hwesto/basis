---
id: SCHEMA-020
title: Assumption contestability discount
status: PROVISIONAL
source: schema_decisions.md
---

### SCHEMA-020: Assumption contestability discount

**Phenomenon:** An assumption supported by many facts should not converge to certainty,
because it remains an assumption — an interpretive claim about unobserved states.

**Decision:** Post-noisy-OR, ASSUMPTION nodes receive a multiplicative discount keyed
to extraction-time confidence:

```python
ASSUMPTION_DISCOUNT = {
    'HIGH':   0.85,
    'MEDIUM': 0.70,
    'LOW':    0.50,
}
```

Even the strongest possible ASSUMPTION (all T1 verified sources, HIGH verdict) cannot
exceed 0.85 × (near-1.0 noisy-OR) ≈ 0.85.

**Alternatives:**
- Flat discount (0.80) for all assumptions. Previous version. Rejected: conflates
  "we have strong evidence for this assumption" with "we don't".
- No discount. The noisy-OR produces near-certainty for well-supported assumptions.
  This is wrong — "the housing benefit cap causes homelessness" is better supported
  by evidence than "the cap doesn't", but it's still not certain in the way that
  a direct measurement is.

**Assumptions:**
1. The extraction-time verdict (HIGH/MEDIUM/LOW) reliably reflects contestability.
   Partially true. The verdict was assigned by the extractor, not by a domain expert.
   In Phase 1, some LOW-verdict assumptions should probably have been MEDIUM, and
   vice versa. The discount is only as good as the verdict assignment.
2. The discount values (0.85, 0.70, 0.50) are approximately correct.
   Same status as alpha values above — provisional.

**Status:** PROVISIONAL — values need calibration.

---

## Part 6: External Dependencies
