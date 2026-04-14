---
id: SCHEMA-012
title: PRINCIPLE as a ninth legal position type
status: DEFERRED
source: schema_decisions.md
---

### SCHEMA-012: PRINCIPLE as a ninth legal position type

**Phenomenon:** Some legal norms operate as principles — they apply "as much as
possible" relative to competing considerations — rather than as binary rules.
Article 8 ECHR, proportionality, legitimate expectation.

**Original decision:** Add PRINCIPLE as a ninth node type with a `strength` field.

**Revised decision (April 2026):** DEFERRED. The `deontic_strength` field on
existing Hohfeldian nodes (ABSOLUTE, QUALIFIED, CONDITIONAL, DIRECTORY, ASPIRATIONAL)
handles 80% of the phenomenon without a new node type or additional Gemma
classification burden. A RIGHT node with `deontic_strength=QUALIFIED` captures
"this right applies unless outweighed by competing considerations" without requiring
a separate PRINCIPLE type.

Genuine constitutional balancing cases (full Article 8 proportionality assessments,
common law proportionality in planning and public law) are Phase 4b territory.
The richer deontic layer from the five-layer legal enrichment schema handles these
properly. Adding PRINCIPLE now as a simplified proxy would require migration in
Phase 4b anyway.

**Condition for revival:** If >10% of extracted legal nodes cannot be correctly
classified as any of the eight Hohfeldian types and the `deontic_strength` field
doesn't resolve the gap, revisit PRINCIPLE as a node type.

**Status:** DEFERRED to Phase 4b. Not rejected — distinction is real, timing is wrong.
