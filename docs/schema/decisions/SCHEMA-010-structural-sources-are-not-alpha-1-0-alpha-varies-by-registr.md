---
id: SCHEMA-010
title: STRUCTURAL sources are not alpha=1.0 — alpha varies by registry
status: PROVISIONAL
source: schema_decisions.md
---

### SCHEMA-010: STRUCTURAL sources are not alpha=1.0 — alpha varies by registry

**Phenomenon:** A STRUCTURAL source is an authoritative registry record. But registries
differ in data quality, update frequency, and known error rates.

**Decision:** STRUCTURAL source alpha is assigned by registry from a lookup table, not
from the source type category. Default values (provisional, to be updated as evidence
accumulates):

```python
STRUCTURAL_ALPHA = {
    'lex_graph_commencement':    0.95,  # known partial commencement gaps
    'lex_graph_amendment':       0.98,  # high reliability, occasional lag
    'ons_nspl_postcode':         0.99,  # highly reliable, quarterly refresh
    'land_registry_title':       0.90,  # known lag on recent transactions
    'companies_house_active':    0.85,  # known data quality issues, stale directors
    'electoral_commission':      0.92,  # reliable for registered entities
    'ico_register':              0.93,  # reliable
    'fca_register':              0.94,  # reliable
    'charity_commission':        0.91,  # known gaps in small charities
}
```

These values are design choices based on documented data quality assessments for each
registry. They are not empirically calibrated — that would require comparing registry
data against ground truth, which we don't have. They should be treated as priors to
be updated as errors are discovered.

**Alternatives:**
- alpha=1.0 for all STRUCTURAL. The original decision. Falsified by known registry
  data quality problems — see companies_house and land_registry.
- alpha=0.95 flat for all STRUCTURAL. Better than 1.0 but hides material differences
  between registries.

**Assumptions:**
1. The alpha values in the lookup table are approximately correct as priors.
   These are informed guesses, not measurements. Flag for empirical calibration.
2. Registry quality is stable over time. False — Companies House data quality has
   deteriorated since the PSC register became mandatory. The lookup table needs
   versioning: `alpha_as_of: date`.

**Falsification:**
- Any discovered case where a STRUCTURAL source was wrong (e.g. a provision shown
   as in_force when it was repealed). Log as an error event. Update the alpha
   for that registry downward. Build the error log from Phase 4 onwards.

**Status:** PROVISIONAL — alpha values are priors not measurements.
