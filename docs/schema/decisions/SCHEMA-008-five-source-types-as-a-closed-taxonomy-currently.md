---
id: SCHEMA-008
title: Five source types as a closed taxonomy (currently)
status: PROVISIONAL
source: schema_decisions.md
---

### SCHEMA-008: Five source types as a closed taxonomy (currently)

**Phenomenon:** Sources are not all the same kind of thing. A peer-reviewed paper, an
ONS API response, a Lex Graph commencement edge, a computed fiscal gap, and a minister's
Hansard statement have fundamentally different provenance models, quality signals, and
epistemic properties.

**Decision:** Five types: DOCUMENTARY, STRUCTURED_DATA, STRUCTURAL, DERIVED, TESTIMONY.
`SourceTypeEnum` is explicitly extensible — it is not declared as exhaustive.

**Alternatives:**
- Single flat source model with nullable fields. Rejected: STRUCTURAL sources don't
  have tiers. DERIVED sources don't have URLs. Forcing these into a flat model produces
  silent nulls in semantically important fields.
- Two types: document and dataset. Too coarse — loses the STRUCTURAL/TESTIMONY
  distinction that drives materially different MC priors.

**Known gaps in the current five types:**
- Sensor/observational data: a satellite image, a continuous air quality monitor,
  a CCTV timestamp. Not documentary, not structured_data in the API-response sense.
  Currently would be forced into STRUCTURED_DATA with a note. Flag when first encountered.
- Model output: a trained ML classifier's output about a node. Not derived from
  existing BASIS nodes — derived from external training data. DERIVED currently requires
  `input_node_ids` pointing to existing nodes, which model outputs don't have.
  Action: add `INFERRED` as a sixth type before any ML-assisted classification is
  introduced to the pipeline.
- Citizen-submitted evidence: a photograph, a letter, a recording. Closest to
  TESTIMONY but materially different — it's primary evidence, not a statement.
  Action: add `CITIZEN_EVIDENCE` as a seventh type before Phase 5 challenge system.

**Assumptions:**
1. The five types are sufficient for Phases 2-4 content. Currently true.
2. Type assignment is unambiguous for the vast majority of sources. Mostly true.
   Edge case: a government-commissioned academic report — is it DOCUMENTARY (T1 academic)
   or DOCUMENTARY (T2 government)? Decision: tier based on publisher, not commissioner.

**Status:** PROVISIONAL — two known extensions needed before Phase 5.
