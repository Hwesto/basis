---
id: SCHEMA-021
title: Lex Graph as a reference table, not an import
status: PROVISIONAL
source: schema_decisions.md
---

### SCHEMA-021: Lex Graph as a reference table, not an import

**Phenomenon:** Lex Graph has 820,000 provision nodes and 2.2 million structural edges.
We need ~5,000 of them.

**Decision:** `lex_provisions` in Supabase is a narrow reference table keyed on
`lex_id` (Lex Graph's stable provision ID). We cache `full_text` and `explanatory_note`
for extraction purposes. We store structural signals (`in_degree`, `amendment_count`,
`commencement_status`, `structural_stability`) derived from Lex Graph's edges. We do
not attempt to replicate the full graph.

**Assumptions:**
1. Lex Graph's stable provision IDs remain stable. Assumed but not guaranteed. If i.AI
   changes their ID scheme, all `lex_provision_id` foreign keys in `legal_nodes` break.
   Mitigation: also store `title` (e.g. 'Housing Act 2004, s.11') as a human-readable
   fallback for re-linking.
2. The content_hash change detection is reliable for detecting amendments. True for
   text changes. Not true for metadata-only changes (e.g. commencement order issued
   without text change). The Structural Signals Agent should check commencement status
   independently of content_hash.
3. i.AI will maintain the Lex API for the duration of BASIS's development. i.AI
   explicitly labels this as "experimental, not for production use." This is the
   principal external dependency risk. Mitigation: cached full_text means the
   extraction pipeline can continue without the API; only freshness is affected.

**Status:** PROVISIONAL — depends on continued i.AI API availability.
