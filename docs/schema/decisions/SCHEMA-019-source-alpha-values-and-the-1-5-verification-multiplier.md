---
id: SCHEMA-019
title: Source alpha values and the 1.5× verification multiplier
status: PROVISIONAL
source: schema_decisions.md
---

### SCHEMA-019: Source alpha values and the 1.5× verification multiplier

**Phenomenon:** Source quality determines the initial confidence anchor for FACT nodes.
A verified source should be weighted more heavily than an unverified one.

**Decision (current alpha table — provisional):**

```python
SOURCE_ALPHA = {
    # DOCUMENTARY
    ('DOCUMENTARY', 'T1', True, True):   0.95,  # T1, verified, citation>100
    ('DOCUMENTARY', 'T1', True, False):  0.75,  # T1, verified, citation<10
    ('DOCUMENTARY', 'T1', False, None):  0.85,  # T1, unverified
    ('DOCUMENTARY', 'T2', True, None):   0.85,  # T2, verified
    ('DOCUMENTARY', 'T2', False, None):  0.70,  # T2, unverified
    ('DOCUMENTARY', 'T3', None, None):   0.70,
    ('DOCUMENTARY', 'T4', None, None):   0.55,
    ('DOCUMENTARY', 'T5', None, None):   0.45,
    ('DOCUMENTARY', 'T6', None, None):   0.40,
    # STRUCTURED_DATA
    ('STRUCTURED_DATA', 'T1', None, None): 0.92,  # ONS, NHS Digital
    ('STRUCTURED_DATA', 'T2', None, None): 0.80,
    ('STRUCTURED_DATA', 'T3', None, None): 0.60,  # council CSVs
    # STRUCTURAL — by registry, see SCHEMA-010
    # DERIVED — no alpha, MC-propagated from inputs
    # TESTIMONY
    ('TESTIMONY', 'T3', None, None): 0.55,   # ombudsman, court
    ('TESTIMONY', 'T4', None, None): 0.45,   # minister, official
    ('TESTIMONY', 'T5', None, None): 0.35,   # citizen challenge
}

VERIFIED_MULTIPLIER = 1.5  # multiplier applied when verified=True for DOCUMENTARY
```

**These values are design choices, not measurements.** They were set to produce
intuitively correct outputs on the current 389-node corpus. They have not been
calibrated against ground truth. The following properties were used as informal
checks:
- NHS-F01 (7.6M waiting list, T2 ONS, verified) should score ~0.89 HIGH. ✓
- A LOW-verdict assumption should not exceed 0.50. ✓
- A T5 testimony source should not exceed 0.40. ✓

**Assumptions:**
1. The alpha values produce correctly-ordered confidence across node types. Currently
   true. No FACT node with a T5 source outscores one with a T1 source (holding
   other factors equal).
2. The 1.5× verification multiplier is appropriate. Arbitrary. It was chosen to
   produce a visible and meaningful difference between verified and unverified nodes
   without allowing verification alone to push a node to HIGH.

**Falsification:**
- Expert review of 20 random HIGH-confidence nodes that should obviously be HIGH.
   If any are obviously wrong, recalibrate.
- Expert review of 20 random LOW-confidence nodes that should obviously be LOW.
   Same.

**Status:** PROVISIONAL — requires calibration study.
