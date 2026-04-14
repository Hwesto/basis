---
id: SCHEMA-022
title: Corpus scoping via ego network queries
status: PROVISIONAL
related: [OQ-001, OQ-002, OQ-003, OQ-004, OQ-005, OQ-006, OQ-007, OQ-008, OQ-009, OQ-010]
source: schema_decisions.md
---

### SCHEMA-022: Corpus scoping via ego network queries

**Phenomenon:** For each issue domain, we need to identify which Lex Graph provisions
are relevant. Manual selection misses amending SIs. Full import is impractical.

**Decision:** Use ego network queries from anchor Acts (e.g. Housing Act 2004 for the
housing domain), 2 hops out on citation and amendment edges, filtered by entity type
(tenant, homeowner, local_authority, etc.).

**Assumptions:**
1. The 2-hop radius captures all materially relevant provisions. Untested. Some
   relevant provisions may be reachable only via 3+ hops (e.g. a provision in
   an amending Act that itself amends a cross-referenced Act).
2. Entity type filtering correctly scopes the corpus. The filter uses text matching
   on provision content — "tenant OR homeowner" in the full_text. This may miss
   provisions that use different terminology ("occupier", "lessee").

**Action:** Run pilot ego network query for Housing Act 2004 before Phase 4 begins.
Manually check sample of 2-hop provisions for relevance. Check sample of 3-hop
provisions to see if the 2-hop boundary is losing material content.

**Status:** PROVISIONAL — requires pilot before Phase 4.

---

## Part 7: Open Questions

These are unresolved design decisions that will need to be addressed before the
phases indicated.

| ID | Question | Blocking | Phase |
|---|---|---|---|
| OQ-001 | Should claim_confidence and instantiation_confidence be separate fields? | No | 3 |
| OQ-002 | ~~What format for conditional commencement notes?~~ **RESOLVED** by SCHEMA-011 revision — six-value enum + commencement_notes free text. | — | — |
| OQ-003 | How should PRINCIPLE nodes interact with MC propagation? Weight ≠ probability. (Deferred with SCHEMA-012 — not blocking Phase 4.) | No | 4b |
| OQ-004 | Should `evidence_independent` default to True or False? Current default (True) is overconfident. | No | 2b |
| OQ-005 | ~~How do we handle provisions that apply to England and Wales jointly?~~ **RESOLVED** by SCHEMA-003 revision — `england_and_wales` added to `JurisdictionEnum` in `base_schema.py`. | — | — |
| OQ-006 | What is the correct alpha for INFERRED sources (ML classifier outputs)? | No | 5 |
| OQ-007 | How does `curator_approved` work for DERIVED nodes computed automatically? | No | 3 |
| OQ-008 | Inter-rater agreement study: are HIGH/MEDIUM/LOW consistently assigned across extractors? | No | 3 |
| OQ-009 | GDP constant for pct_gdp unit conversion — should this be a dynamic source? | No | 2b |
| OQ-010 | What happens when Lex Graph provision IDs change? Recovery procedure needed. | Yes | 4 |
