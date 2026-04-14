---
id: SCHEMA-016
title: Six evidence edge types
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-016: Six evidence edge types

**Phenomenon:** Relationships between evidence nodes are not all the same. A source
that directly establishes a claim is different from one that undermines it, which is
different from one that the claim logically requires.

**Decision:** Six edge types with defined logical properties:

| Type | Logic type | Transitive? | Symmetric? | Notes |
|---|---|---|---|---|
| SUPPORTS | Epistemic | No | No | A→B→C does not mean A→C |
| CONTRADICTS | Epistemic | No | Yes | If A contradicts B, B contradicts A |
| DEPENDS_ON | Structural | Yes | No | If C depends on B, C inherits B's weakness |
| ENABLES | Deontic | No | No | A right enables a mechanism |
| COMPETES | Normative | No | Yes | Two policies competing for the same resources |
| SUPERSEDES | Temporal | No | No | Later evidence replaces earlier |

These properties are enforced in the MC engine — DEPENDS_ON propagates with weakest-
link semantics, SUPPORTS uses noisy-OR (with independence flag), CONTRADICTS applies a
discount, SUPERSEDES marks the earlier node as deprecated.

**Assumptions:**
1. Six types cover all meaningful relationships in the evidence layer. Currently true.
   Monitor: if extractors are using `extraction_notes` to describe relationships that
   don't fit a type, that's a signal a new type is needed.
2. The transitivity rules above are correct. SUPPORTS non-transitivity is the most
   important: a study that supports a hypothesis about mechanism A does not automatically
   support a downstream policy B that rests on A. This is enforced by the MC architecture
   (each edge has its own weight) rather than a hard rule.

**Status:** SETTLED on types and properties.
