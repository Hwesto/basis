---
id: SCHEMA-004
title: Confidence as categorical HIGH/MEDIUM/LOW
status: SETTLED
source: schema_decisions.md
---

### SCHEMA-004: Confidence as categorical HIGH/MEDIUM/LOW

**Phenomenon:** How much should we trust a claim?

**Decision:** Extraction-time confidence is categorical: HIGH, MEDIUM, LOW. Assigned
by the human extractor (Track C) or by Gemma with curator review (Track B). Not a
decimal number.

**Alternatives:**
- Decimal [0.0, 1.0]. Rejected on the grounds stated in the original spec §2.5: false
  precision. A decimal score implies a measurement process that doesn't exist. Saying
  a claim has confidence 0.73 implies we know it's more confident than 0.72. We don't.
- Binary (verified / unverified). Too coarse — conflates "we haven't checked" with
  "we checked and it's weak."
- Five-level scale (following GRADE: high/moderate/low/very low). Considered seriously.
  GRADE's fourth level (very low) is specifically for "any estimate of effect is very
  uncertain." This is useful for the evidence layer, less useful for legal nodes where
  a provision either applies or it doesn't. Decision: defer to Phase 4 review.

**Assumptions:**
1. Three levels are sufficient to drive meaningful UI differentiation. Currently true.
2. Human extractors can reliably distinguish HIGH from MEDIUM. This is an empirical
   question. No calibration study has been done. Monitor inter-rater agreement when
   Track C extraction produces >50 nodes.
3. Categorical confidence is converted to numerical alpha in the MC engine. The
   conversion table is a design choice — see SCHEMA-014.

**Falsification:**
- Evidence that human extractors are inconsistent on the HIGH/MEDIUM boundary across
  domains. If inter-rater agreement <80%, either the definitions need tightening or
  a fourth level ('very high' for verified T1 sources) would help.

**Status:** SETTLED on categorical. PROVISIONAL on three vs four levels.
