---
id: SCHEMA-009
title: Tier lives on the citation edge, not the source
status: PROVISIONAL
source: schema_decisions.md
---

### SCHEMA-009: Tier lives on the citation edge, not the source

**Phenomenon:** Source quality is claim-relative, not source-absolute. ONS is T1 for
UK unemployment statistics. ONS is not authoritative — effectively irrelevant — for a
claim about housing disrepair case law.

**Decision:** `DocumentarySource` carries `default_tier` as a global quality signal.
The `citation_edge` between source and node carries an optional `claim_tier_override`
with mandatory justification when set. The MC engine uses `claim_tier_override` if
present, `default_tier` otherwise.

**Current state:** This decision is not yet implemented. The existing 172 sources in
`data/` have tier on the source, not on the citation edge. This is Phase 1 legacy.
Migration required before Phase 4 legal layer extraction.

**Alternatives:**
- Tier only on source, globally applied. The current state. Produces incorrect MC
  priors in cases of cross-domain citation — an IFS report cited for both a taxation
  claim (appropriate, T1) and a housing claim (potentially T3) gets T1 in both cases.
- Tier only on citation edge, no default. High annotation burden. Every citation
  requires explicit tier assignment. Impractical at scale.

**Assumptions:**
1. The `default_tier` correctly represents the source's quality for the majority of
   citations. True for single-domain sources. Questionable for general reports.
2. Curators will notice and override when a source is being cited outside its primary
   domain. No automated detection currently. Gap: add a CI check that flags when a
   source's `domain` field doesn't match the citing node's domain.

**Falsification:**
- If >20% of citation edges require an override, the default mechanism isn't doing
  useful work. Track this metric from Phase 4.

**Status:** PROVISIONAL — migration from source-tier to citation-tier required.
