---
id: SCHEMA-011
title: Commencement status as a six-value enum
status: SETTLED
resolves: [OQ-002]
source: schema_decisions.md
---

### SCHEMA-011: Commencement status as a six-value enum

**Phenomenon:** A provision can exist in law but not be in force. It can be in force
for some people but not others, or in some regions but not others. A repeal can also
be enacted before it takes effect.

**Decision:** `commencement_status` uses six values:
`in_force`, `partially_in_force`, `not_commenced`, `prospectively_repealed`,
`repealed`, `unknown`.

- `partially_in_force`: in force in some jurisdictions or for some persons. Requires
  `commencement_notes` with plain English explanation. Displayed with prominent warning.
- `prospectively_repealed`: repeal enacted but not yet effective. Nodes flagged for
  imminent deprecation review.
- `not_commenced` and `repealed`: commencement gate blocks these entirely.
- `unknown`: displayed with disclaimer.

**Real-world driver for the extension:** Renters' Rights Act 2025. Section 2A is
prospective (not yet commenced), section 2B is partially commenced for England
but not Wales. The previous four-value enum could not represent either case.
These are live provisions affecting citizen rights right now.

**Resolves OQ-002:** No separate `commencement_condition` field needed. The six
values plus `commencement_notes` (free text) handle all encountered cases.
If date-triggered commencement (common in financial regulation) proves necessary,
add `commencement_date: date | None` as a separate field at that point.

**Assumptions:**
1. Lex Graph's commencement data is reliable (alpha=0.95 per SCHEMA-010).
2. `commencement_notes` will be legible to citizens — add to curator review checklist.

**Status:** SETTLED — OQ-002 resolved.
