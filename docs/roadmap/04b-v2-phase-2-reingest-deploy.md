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

3. **Three-tier routing pass + calibration study.** Per SCHEMA-024:
   - Tier 1 (automated) processes the bulk; expected 60–70% of
     candidate nodes pass straight through.
   - Tier 2 (Claude via Supabase MCP) reviews the remainder in
     subscription Claude Code sessions; per-source content_hash
     caching means repeated re-ingestions don't re-run Tier 2.
   - Tier 3 (human) handles only escalations + the always-Tier-3
     categories (PRECEDENT, civic findings, first-20-of-domain
     calibration windows).

   **Calibration gate:** before Claude Tier 2 approvals are accepted
   into the public API, run the SCHEMA-024 calibration study —
   sample 100 nodes Claude has approved, you review them blind,
   require ≥90% agreement. If below, tighten Tier 1 gates and
   re-sample. This is the gate, not the curation pass itself.

   Target curated graph after Phase 2 (loose):
   - ~160 FACT (down from v1's 130 — reflecting stricter v2 contract)
   - ~70 ASSUMPTION (v2 requires `basis_fact_ids` +
     `falsification_condition` on every assumption)
   - ~55 CLAIM
   - ~45 POLICY
   - ~55 POSITION

   Each node carries an `approved_by` field (auto / claude / human)
   and a public `verification_level` (auto_verified / ai_reviewed /
   human_curated) per SCHEMA-024.

4. **Run MC engine on the seeded graph.** Verify runtime < 30s at
   target graph size. Output `data/confidence_results.json` committed
   to the repo as the Phase 2 checkpoint.

5. **Build v2 frontend.** Rebuild the Next.js app from Phase 2a
   against the new data contract:
   - Domain list + per-domain detail
   - Node detail: MC confidence bar, edges, source list with
     `default_tier` pills and `claim_tier_override` overlays where set
   - **Verification badge** per node (SCHEMA-024): 🤖 `auto-verified`
     (neutral grey) / 🧠 `AI-reviewed` (blue) / 👤 `human-curated`
     (green/gold). Click → drawer showing the routing chain (Tier 1
     checks passed, Claude approval note, human spot-check status).
   - Fiscal gap page with range support on the axis
   - Search with domain / type / confidence / source-tier /
     verification-level filters
   - **Curator queue admin UI** (Tier 3 review) — operator-only
     authenticated route. Pulls `tier=3` rows from `curator_queue`,
     shows extracted JSON + source preview + Claude's note,
     approve / reject / edit / kickback buttons.
   - About page: methodology, MC explanation, schema decisions
     summary including SCHEMA-024 routing model, link to `docs/schema/`
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
- SCHEMA-024 calibration study: ≥90% Harry / Claude agreement on the
  100-node blind sample, before any `verification_level=ai_reviewed`
  node enters the public API
- Verification badge live on every node; routing-chain drawer works
- Curator queue admin UI accepts / rejects / kicks back Tier 3 items;
  kickback workflow logs patterns to `agent_log` for Tier 1 review
- 5% ongoing spot-check job scheduled (weekly) and producing
  agreement-rate metrics
- CI gate active; `validate_graph.py` passes on every PR
- At least one external challenge submitted and processed

**References:**

- `docs/roadmap/04a-v2-phase-1-pipeline.md` — prerequisite
- `docs/migration/README.md` — rebuild framing
- Archived v1 Phase 2b (`04-phase-2b-*.md`) — original deliverables
  list; items 1 / 5 / 7 / 8 carry forward
