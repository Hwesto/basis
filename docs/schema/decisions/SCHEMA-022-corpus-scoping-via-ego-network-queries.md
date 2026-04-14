---
id: SCHEMA-022
title: Corpus scoping via ego network queries
status: PROVISIONAL
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

The open-questions table that belongs after this section now lives in
`docs/schema/open_questions/` (one file per OQ). See `docs/schema/README.md`
for the status index.
