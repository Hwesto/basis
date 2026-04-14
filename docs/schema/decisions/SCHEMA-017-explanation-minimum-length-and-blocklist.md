---
id: SCHEMA-017
title: Explanation minimum length and blocklist
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-017: Explanation minimum length and blocklist

**Phenomenon:** Edge explanations are the mechanism by which "we show our working" is
made legible. A one-word explanation defeats the purpose.

**Decision:** Minimum 10 characters on `explanation` field. Regex blocklist rejects
template phrases: 'supports', 'related', 'depends on', 'see above', 'as noted', and
any explanation that merely restates the target node statement.

**Assumptions:**
1. 10 characters is the right minimum. It's a floor, not a target. An explanation of
   "X increases Y" is 12 characters and meaningless. The blocklist is doing more work
   than the length constraint.
2. The blocklist covers the main failure modes. Currently covers the cases observed in
   Phase 1 data. Extend as new patterns are discovered.

**Status:** SETTLED on principle. PROVISIONAL on specific thresholds.
