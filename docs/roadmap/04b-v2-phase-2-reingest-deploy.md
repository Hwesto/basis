---
phase: v2-2
status: planned
source: docs/migration/README.md
---

### v2 Phase 2: Re-ingest v1 backlog + deploy v2 site

**Objective:** Put data through the pipeline built in v2 Phase 1. Ship
a publicly-accessible v2 site that reads from that data.

**Depends on:** v2 Phase 1 complete (`04a-`).

**Deliverables:**

1. **Re-ingest the v1 backlog.** Run `python -m basis.ingest backlog`
   against `data/v1_ingestion_backlog.json` (172 source references).
   Expected:
   - ~130 resolvable sources auto-ingest (gov.uk, ONS, academic DOIs)
   - ~30 require manual content fetch (IFS PDFs that are bot-blocked,
     dead URLs requiring Wayback Machine)
   - ~10 drop out (genuinely dead, low priority, or reclassified)
   All inserts run through the curator queue with
   `curator_approved=false`; none visible in public API until flipped.

2. **Re-extract claims from the manifesto corpus.** Run evidence
   extraction over the 13 manifesto markdowns in `manifestos/`, using
   the v2 prompts. Produces candidate FACT / CLAIM / POLICY / POSITION
   nodes linked to the freshly-ingested sources via `citation_edges`.
   Target ~380 candidate nodes.

3. **Curator queue review cycle.** Approve / reject / edit the
   candidate nodes. Target:
   - ~160 FACT (down from v1's 130 — reflecting stricter v2 contract)
   - ~70 ASSUMPTION (v2 requires `basis_fact_ids` +
     `falsification_condition` on every assumption, so count drops
     from v1's 75)
   - ~55 CLAIM
   - ~45 POLICY
   - ~55 POSITION
   Figures are loose targets; coverage of the top fiscal and policy
   claims is the real bar.

4. **Run MC engine on the seeded graph.** Verify runtime < 30s at
   target graph size. Output `data/confidence_results.json` committed
   to the repo as the Phase 2 checkpoint.

5. **Build v2 frontend.** Rebuild the Next.js app from Phase 2a
   against the new data contract:
   - Domain list + per-domain detail
   - Node detail: MC confidence bar, edges, source list with
     `default_tier` pills and `claim_tier_override` overlays where set
   - Fiscal gap page with range support on the axis
   - Search with domain / type / confidence / source-tier filters
   - About page: methodology, MC explanation, schema decisions
     summary, link to `docs/schema/`
   - `/v1/` sub-route serving the archived v1 site from
     `archive/v1/site/`
   Deploy on Vercel (root directory: `apps/web`).

6. **Replace gh-pages.** Cut over `hwesto.github.io/basis` from the
   static v1 HTML to the v2 Next.js app. Previous v1 remains
   accessible at `/v1/`.

7. **Challenge system alpha.** Ship the `challenges` + `scrutiny`
   tables and a simple authenticated-user submission form. Curator
   queue review. Accepted challenges trigger MC re-propagation. This
   was a v1 Phase 2b deliverable carried forward.

8. **CI enforcement.** `scripts/validate_graph.py` runs on every PR.
   Weekly: MC engine re-run, dead-link check on every source URL. Fail
   the build on schema errors, orphan nodes, fiscal gap outside the
   stated range.

**Out of scope:**

- Local data layer (Phase 3)
- Legal knowledge layer (Phase 4)
- Action routing (Phase 5)
- Any ML-assisted classification (INFERRED source type, Phase 5+)

**Success criteria:**

- v2 site live at `hwesto.github.io/basis` reading from Supabase
- v1 site preserved at `/v1/` sub-route
- ≥150 curator-approved nodes across ≥12 domains
- CI gate active; `validate_graph.py` passes on every PR
- At least one external challenge submitted and processed

**References:**

- `docs/roadmap/04a-v2-phase-1-pipeline.md` — prerequisite
- `docs/migration/README.md` — rebuild framing
- Archived v1 Phase 2b (`04-phase-2b-*.md`) — original deliverables
  list; items 1 / 5 / 7 / 8 carry forward
