---
phase: 2a
status: v1_archived
source: BASIS_ROADMAP.md
---

> **v1 — archived.** Built against the v1 graph shape (tier on source,
> scalar fiscal amount, no citation_edges, no curator_queue). The v2
> frontend replaces this rather than migrating the Next.js code, since
> the underlying data contract changed. See
> `docs/roadmap/04b-v2-phase-2-reingest-deploy.md` for the v2 frontend.

### Phase 2a (v1): Platform Frontend — ARCHIVED

**What it delivered:** Next.js app reading from live Supabase. 7 working
routes.

| Route | Content |
|---|---|
| / | Landing — 389 nodes, 12 domains, 50 verified |
| /domains | 12 domain cards with headline and diagnosis |
| /domains/[slug] | Nodes by type, confidence badges, tier pills |
| /domains/[slug]/nodes/[id] | Full detail — MC confidence bar, edges, source, fiscal |
| /fiscal-gap | Live computation: spending vs revenue vs net gap |
| /search | Full-text with domain/type/confidence filters |
| /about | Methodology, evidence hierarchy, MC explanation |

**What becomes of this in v2:**

- Route shapes (domain list, node detail, fiscal gap, search, about)
  are correct and transfer. The data contract changes:
  - `source.tier` → `source.default_tier` + optional
    `citation_edge.claim_tier_override`
  - `fiscal.amount` (scalar) → `fiscal.{amount, amount_low, amount_high}`
  - `source_type` discriminator required (was absent in v1)
- The v2 frontend rebuilds against the new contract. Next.js/Supabase
  stack retained; component library (confidence badges, tier pills,
  fiscal bars) mostly reusable with prop-shape changes.
- v1 site served at `/v1/` sub-route after cutover; reads from the
  archived JSON in `archive/v1/data/` for provenance.

**Status:** ✅ v1-built (never publicly deployed on Vercel). Superseded
by v2 Phase 2 (see `04b-`).
