---
phase: 2a
status: completed
source: BASIS_ROADMAP.md
---

### COMPLETED — Phase 2a: Platform Frontend

**What it delivered:** Next.js app reading from live Supabase. 7 working routes.

| Route | Content |
|---|---|
| / | Landing — 389 nodes, 12 domains, 50 verified |
| /domains | 12 domain cards with headline and diagnosis |
| /domains/[slug] | Nodes by type, confidence badges, tier pills |
| /domains/[slug]/nodes/[id] | Full detail — MC confidence bar, edges, source, fiscal |
| /fiscal-gap | Live computation: spending vs revenue vs net gap |
| /search | Full-text with domain/type/confidence filters |
| /about | Methodology, evidence hierarchy, MC explanation |

**Status:** ✅ Built, awaiting Vercel deployment

---
