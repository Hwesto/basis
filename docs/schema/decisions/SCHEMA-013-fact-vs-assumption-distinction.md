---
id: SCHEMA-013
title: FACT vs ASSUMPTION distinction
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-013: FACT vs ASSUMPTION distinction

**Phenomenon:** Some statements are directly observable or measurable in the world.
Others require inference, interpretation, or projection.

**Decision:** FACT nodes have `source_id` pointing to a DOCUMENTARY or
STRUCTURED_DATA source that directly supports the statement. ASSUMPTION nodes have
`basis_fact_ids` — a list of FACT IDs that make the assumption plausible — plus a
`falsification_condition` field: what would disprove it.

The minimum one basis_fact_id constraint on ASSUMPTION is a schema-enforced check —
orphan assumptions (assumptions with no factual basis) fail Pydantic validation.

**Assumptions:**
1. The FACT/ASSUMPTION boundary is clear. It often isn't. "NHS waiting times have
   increased since 2019" — FACT (measurable, sourced). "Increased waiting times are
   primarily caused by underfunding" — ASSUMPTION (causal inference, not directly
   measurable). But "underfunding is a cause" might be established by controlled
   studies — in which case it could be a FACT.
   The boundary is determined by whether the statement can be directly sourced or
   requires interpretive inference. When ambiguous, the extractor should prefer FACT
   with a caveat in `extraction_notes` over ASSUMPTION.
2. `falsification_condition` is completable for all assumptions. True for well-formed
   assumptions. Some assumption statements resist falsification — these are the ones
   most likely to be wrong. If an extractor cannot write a falsification condition,
   the statement is probably not an assumption — it may be a POSITION or a CLAIM.

**Status:** SETTLED
