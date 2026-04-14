---
phase: 2b
status: in_progress
source: BASIS_ROADMAP.md
---

### NEXT — Phase 2b: Deployment & Community Launch

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

**Success metrics:** Deployed, CI green, ≥70 verified FACTs, first external challenge submitted, NLI QA pass complete.

---
