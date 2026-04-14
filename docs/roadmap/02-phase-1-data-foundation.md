---
phase: 1
status: completed
source: BASIS_ROADMAP.md
---

### COMPLETED — Phase 1: Data Foundation

**What it delivered:** An honest graph. 389 nodes, 746 edges, 12 domains. Fiscal gap computed from metadata (£52.6–101.6bn), not hardcoded. Monte Carlo confidence propagation with verdict-tiered assumption discount. Supabase seeded with 1,319 rows. 51/130 FACTs verified against source text.

**Key systems built:**
- 6-check CI validator (schema, edges, topics, fiscal, confidence, source integrity)
- Monte Carlo confidence engine (10k samples, 389 nodes, 25s runtime)
- Assumption contestability discount (HIGH→0.85, MEDIUM→0.70, LOW→0.50)
- Source fetch pipeline (133/172 sources fetched, 26 PDFs extracted)
- Fiscal gap_role taxonomy (additional_need, baseline, position_only, summary, uplift, target_total)
- Verification pipeline (51 confirmed, 0 refuted)

**Known gaps to backfill:**
- 79 unverified FACTs: 8 IFS PDFs (bot-blocked, manually downloadable), 4 academic papers, 7 dead GOV.UK URLs
- 39 unfetched sources
- IMM-POS-GRN-01 empty maps_to (Green immigration — no matching policy node; intentional)
- Sensitivity analysis run not yet completed (built, ~3-5min runtime)

**Status:** ✅ Complete (backfill items tracked, non-blocking)

---
