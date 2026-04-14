---
id: SCHEMA-007
title: verified separate from curator_approved
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-007: verified separate from curator_approved

**Phenomenon:** Two different things that look similar:
- `verified`: we have checked the source text and confirmed the statement matches.
- `curator_approved`: a human has reviewed the extraction and approved it.

These are independent. A node can be curator-approved but unverified (extracted by
Claude Code in Track C, approved, but source document not yet fetched for text
comparison). A node can be verified but not yet curator-approved (automated verification
pass succeeded, waiting in queue).

**Decision:** Both fields exist as separate booleans. MC confidence receives a 1.5×
alpha multiplier only when `verified=True`. `curator_approved` controls display only.

**Assumptions:**
1. The distinction matters for users. If a citizen is relying on a claim, knowing it
   was extracted and approved by a human is different from knowing it was confirmed
   against the actual source document.
2. The 1.5× verification multiplier is calibrated correctly. This was set by design
   choice, not by empirical calibration. See SCHEMA-019.

**Status:** SETTLED

---

## Part 2: Source Models
