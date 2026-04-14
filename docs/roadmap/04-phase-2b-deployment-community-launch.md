---
phase: 2b
status: v1_archived
source: BASIS_ROADMAP.md
---

> **v1 — archived.** Phase 2b was the v1 deployment + community launch
> plan. It was paused mid-flight when the audit revealed the v1 corpus
> couldn't conform to the reconciled schema. Deployment of the v1
> Next.js app is cancelled; v1 stays on gh-pages as a static snapshot
> until v2 cutover. The "next" slot is now v2 Phase 1 (pipeline build)
> — see `docs/roadmap/04a-v2-phase-1-pipeline.md`.

### Phase 2b (v1): Deployment & Community Launch — ARCHIVED

**Objective:** Get the platform publicly accessible. Start building the evidence community before the civic OS is built.

**Deliverables:**

1. **Vercel deployment**
   - Root directory: `apps/web`
   - Env vars: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
   - Auto-deploy on main branch push

2. **CI enforcement**
   - GitHub Actions: run `python scripts/validate.py` on every PR
   - Fail build on: schema errors, orphan nodes, fiscal gap out of range
   - Weekly: run `compute_confidence.py --seed 42`, commit result
   - Weekly: dead link check on all 172 source URLs

3. **Source backfill (Harry manual)**
   - Download 8 IFS PDFs (ifs.org.uk — free, just bot-blocked)
   - Download 4 academic papers (university library access)
   - Archive 7 dead GOV.UK URLs via Wayback Machine manually
   - Re-run `scripts/verify_facts.py` — expected: 70–85 verified (from 51)

4. **Sensitivity analysis**
   - Run `python scripts/compute_confidence.py --sensitivity`
   - Output: which FACTs most influence which POLICYs
   - Add to /about page as "Key evidence dependencies"

5. **Challenge system alpha**
   - Enable the `challenges` and `scrutiny` tables (schema already exists)
   - Simple frontend: authenticated users can submit a counter-source against any node
   - Curator queue: human review of submitted challenges
   - Accepted challenge → MC re-propagation triggered
   - This is the first community feedback mechanism

6. **Email / social**
   - The Phase 0 signup form: ensure submissions reach a list
   - Launch post: the graph is live, the working is shown, challenges welcome

3. **NLI edge QA pass (one-time)**
   - Run all 389×389 node pairs through a DeBERTa NLI cross-encoder
   - Compare model's predicted edge types against curated edges
   - Investigate disagreements — genuine missed connections become new edges via curator queue
   - One half-day of compute, one day of review. Not recurring architecture.

**Success metrics (v1, not pursued):** Deployed, CI green, ≥70 verified
FACTs, first external challenge submitted, NLI QA pass complete.

**What becomes of each deliverable in v2:**

1. Vercel deployment → deferred to v2 Phase 2 with the rebuilt frontend
2. CI enforcement → retargeted at v2 schema (`scripts/validate_graph.py`)
3. Source backfill → superseded by v2 ingestion pipeline processing
   the full 172-source backlog from scratch
4. Sensitivity analysis → re-applied on the v2 graph after
   re-ingestion
5. Challenge system alpha → retained as a v2 Phase 2 deliverable
   (`challenges`, `scrutiny` tables still needed)
6. Email/social → when v2 ships, not before
7. NLI edge QA → one-time pass on the v2 graph after re-ingestion

**Status:** v1-paused, superseded by v2 Phase 1/2 (see `04a-`, `04b-`).
