# Schema Decisions — Plain English

> This is the readable companion to schema_decisions.md.
> Same decisions, same open questions, less ceremony.
> When you need the full reasoning, go to schema_decisions.md.
> When you need to remember what we decided and why, read this.

---

## The big picture

Every design choice in the schema is a bet. This document records what bets we made,
why we made them, and what would tell us we got it wrong.

---

## Foundation

**One base class for everything (SCHEMA-001)**

Every entity — a policy fact, a legal right, a crime statistic, a complaint outcome —
inherits from `BaseNode`. Same fields, same validation, same confidence engine.
The alternative was separate schemas per layer. We tried that in Phase 1 and got five
slightly different validators that slowly diverged. One base class means one of everything.

**Domains are a fixed list, not free text (SCHEMA-002)**

`DomainEnum`. If you type 'Housing' instead of 'housing', it fails immediately.
We had 'housing', 'Housing', and 'housing_disrepair' all in the Phase 1 data.
New domains require a code change — they can't be added by the extraction pipeline.

**Jurisdictions are typed (SCHEMA-003 — settled)**

england, wales, scotland, ni, england_and_wales, uk_wide. Six values.
`england_and_wales` is its own first-class jurisdiction because most devolved
housing, health, and education law applies jointly to those two. Added in
`base_schema.py`. OQ-005 resolved.

**Confidence is HIGH / MEDIUM / LOW, not a decimal (SCHEMA-004)**

Saying a claim is 0.73 confident implies we measured something. We didn't.
Categorical is honest. Three levels are enough to drive different UI states.
We considered four (adding VERY_LOW, following the GRADE framework for medical evidence).
Not yet — revisit after Phase 4.

**Two confidence fields, not one (SCHEMA-005)**

`confidence` is what the human extractor assigned at extraction time.
`computed_confidence` is what the MC engine calculates after propagating through the graph.
They can diverge a lot. Both are kept. The frontend shows the computed one.

**Nothing goes live without a human approving it (SCHEMA-006)**

`curator_approved = False` by default. The API never returns unapproved nodes.
The one awkward case is computed outputs — fiscal gaps, percentile ranks — where
there's no human judgment to apply. Currently these get auto-approved by the pipeline.
That's a gap we haven't cleanly resolved yet (see OQ-007).

**"Verified" and "curator approved" are different things (SCHEMA-007)**

Verified means: we fetched the source document and confirmed the statement matches.
Curator approved means: a human reviewed the extraction and said it's good.
You can have one without the other. Verified gets a 1.5× confidence boost in the MC engine.

---

## Sources

**Five types of source, not one (SCHEMA-008)**

A government report, an ONS API call, a Lex Graph amendment edge, a computed fiscal
gap, and a minister's Hansard statement are epistemically different things. We
shouldn't model them the same way.

The five types:
- **DOCUMENTARY** — something someone wrote and published (reports, papers, statutes)
- **STRUCTURED_DATA** — a dataset or API response (ONS, Police.uk, Land Registry)
- **STRUCTURAL** — a registry record that's either there or it isn't (Lex Graph, Companies House)
- **DERIVED** — something we computed from other nodes (fiscal gap, MC score)
- **TESTIMONY** — what someone said (Hansard, FOI response, citizen challenge)

We know this list is incomplete. We'll need INFERRED (ML model output) before Phase 5
and CITIZEN_EVIDENCE (photographs, letters) before the challenge system.

**Tier belongs on the citation, not the source (SCHEMA-009)**

ONS is T1 for unemployment statistics. ONS is not particularly authoritative for
housing disrepair case law. Currently we store tier on the source globally.
That's wrong and we know it — it's Phase 1 legacy.

The fix: tier stays as a default on the source, but citations can override it
with a mandatory justification. The MC engine uses the override if it exists.

This migration needs to happen before Phase 4.

**"Registry sources are certain" is too strong (SCHEMA-010)**

We originally said STRUCTURAL sources get alpha=1.0 — certainty — because they're
official records. But Companies House has stale director data. Lex Graph has known
commencement gaps. Land Registry lags real transactions by months.

Instead: alpha varies by registry. Lex Graph commencement = 0.95. Companies House
active status = 0.85. ONS postcode = 0.99. These are informed guesses — we haven't
measured them against ground truth. They'll get updated as we find errors.

**Commencement status has six states, not two (SCHEMA-011) — OQ-002 resolved**

A provision can be:
- Fully in force
- Partially in force (e.g. England but not Wales) — displayed with a warning
- Not yet commenced
- Prospectively repealed (repeal passed but not yet effective) — flagged for deprecation
- Repealed
- Unknown

The Renters' Rights Act 2025 made this urgent — s.2A is not yet commenced, s.2B is partially commenced for England only. The old four-value enum couldn't represent either. This also closes OQ-002: no separate conditional commencement field needed, `commencement_notes` as free text handles what we've seen. If date-triggered commencement becomes an issue (financial regulation), add `commencement_date` at that point.

**PRINCIPLE as a ninth legal position — DEFERRED (SCHEMA-012)**

The original idea: add a PRINCIPLE node type for weight-based norms like Article 8 ECHR that can't be encoded as binary Hohfeld positions.

The revised decision: not now. The `deontic_strength` field on existing nodes (ABSOLUTE, QUALIFIED, CONDITIONAL, DIRECTORY, ASPIRATIONAL) covers 80% of this without a new node type or another thing for Gemma to classify. Full constitutional proportionality cases — the hard ones — belong in the Phase 4b enrichment layer anyway, not the Phase 4 bootstrap. Adding a simplified PRINCIPLE type now would require migration later.

Condition for revival: if more than 10% of extracted provisions can't be classified as any of the eight Hohfeld types even with deontic_strength, revisit.

---

## Evidence nodes

**FACT vs ASSUMPTION is a real distinction (SCHEMA-013)**

FACT: directly sourced from a document. "7.6 million people are on the NHS waiting list."
ASSUMPTION: requires interpretation. "The waiting list is primarily caused by underfunding."

The second statement might have a lot of evidence pointing at it — but it's still
an inference, not a direct observation. Assumptions must list which facts they rest on.
Assumptions with no factual basis fail validation.

**The fiscal gap is computed, not asserted (SCHEMA-014)**

Every monetary node has a gap_role: does it count toward the £44-146bn headline or not?
The CI check recomputes the gap from metadata on every commit. If it falls outside the
stated range, the build breaks. The number in the README is a computation, not a claim.

---

## Edges

**Four supporting sources aren't four times the evidence (SCHEMA-015)**

The MC formula for SUPPORTS edges assumes each source independently establishes the claim.
If four papers all cite the same IFS report, they're not independent — they're one
piece of evidence cited four times. The current formula produces inflated confidence
wherever correlated sources cluster.

The fix: `evidence_independent: bool` on SUPPORTS edges. Correlated evidence
compounds much less aggressively than independent evidence.

The default is currently `True` (independent). That's the wrong default — we're
being optimistic. The 20 highest-confidence CLAIM nodes need a manual audit before
Phase 2b goes live.

**Six edge types with defined logical rules (SCHEMA-016)**

SUPPORTS: not transitive. A→B→C doesn't mean A supports C.
CONTRADICTS: symmetric. If A contradicts B, B contradicts A.
DEPENDS_ON: transitive. If C depends on B, B's weakness becomes C's weakness.
ENABLES: not transitive. A right enabling a mechanism doesn't mean it enables the mechanism's mechanism.
COMPETES: symmetric. Two policies competing for the same resources.
SUPERSEDES: not transitive. Later evidence replaces earlier.

These rules are in the MC engine. They're not conventions — they're enforced.

**Explanations must say something (SCHEMA-017)**

Minimum 10 characters. Blocklist rejects: "supports", "related", "depends on",
"see above", any phrase that just restates the target node. This matters because
"we show our working" is the whole point — if the edge explanation is useless,
the working is hidden.

---

## Confidence engine

**Monte Carlo over analytical propagation (SCHEMA-018)**

We sample 10,000 times from the confidence distributions, propagate each sample
through the graph using the edge rules, and read off the distribution of outcomes.
This gives us a confidence mean, standard deviation, and p5/p95 range.

Why not derive formulas analytically? The mixed edge types (noisy-OR for SUPPORTS,
weakest-link for DEPENDS_ON, discount for CONTRADICTS) don't compose cleanly into
a single formula. MC handles all of them in the same loop.

25 seconds for 389 nodes. Will need scope-limited propagation (within domain only)
when the legal layer adds several thousand more nodes.

**The alpha values are guesses (SCHEMA-019)**

The table that maps source tier to initial confidence (T1 = 0.85, T2 = 0.70, etc.)
produces intuitively correct results on the current corpus. But they've never been
calibrated against anything. An expert reviewing 40 nodes — 20 that should obviously
be HIGH, 20 that should obviously be LOW — would tell us whether the numbers are right.
This is on the list for Phase 3.

**Assumptions can never reach certainty (SCHEMA-020)**

Even a perfectly-supported assumption — T1 verified sources, all pointing the same way —
caps at 0.85 in the MC engine. An assumption with LOW extraction verdict caps at 0.50.

This is because no matter how much evidence points at an assumption, it's still
an interpretive claim about something that wasn't directly observed. The 1977 housing
report said "tower blocks build community." The evidence pointed one way. The world
disagreed. Assumptions have a ceiling.

---

## Lex Graph

**We reference it, we don't import it (SCHEMA-021)**

820,000 nodes, 2.2 million edges. We need about 5,000 of them.
The `lex_provisions` table in Supabase is a narrow reference table with the provisions
we care about. We cache the text for extraction. We store structural signals
(how often cited, how many times amended, is it in force) derived from the graph.

Main risk: i.AI label this API as "experimental, not for production." If it goes down,
our freshness monitoring breaks. Our extraction pipeline is fine — it uses cached text.
We're not dependent on the API for correctness, only for keeping current.

**We find relevant provisions using the graph's own structure (SCHEMA-022)**

Rather than manually listing every relevant Act, we start at an anchor (Housing Act 2004)
and follow citation and amendment edges two hops outward. Everything reachable is a
candidate for extraction. This catches amending Statutory Instruments we'd miss manually.

Untested assumption: two hops is enough. Some relevant provisions might only be
reachable in three. We'll run a pilot before Phase 4 and check.

**Legal consistency as CI checks (SCHEMA-023)**

Two new automated checks run against the legal layer once legal nodes exist.

ENFORCEMENT_GAP: any DUTY node with no MECHANISM reachable via ENFORCED_BY edges. This catches either an extraction gap (mechanism not yet extracted) or a genuine legal problem — a duty with no enforcement route. The Housing Act 2004 has real examples of this: category 2 hazards create no enforceable obligation on councils, only a power to act. That's a civic finding worth surfacing, not just a data quality issue.

MISSING_CORRELATIVE: any RIGHT node with no corresponding DUTY, or POWER with no LIABILITY. Hohfeld requires these pairs. Missing ones are either extraction errors or legal incoherence.

Both are pure database queries against the existing schema. Deferred: CIRCULAR_DEFEASIBILITY and TEMPORAL_IMPOSSIBILITY require the Phase 4b enrichment layers.

---

## Open questions

| # | Question | Blocking? | When |
|---|---|---|---|
| OQ-001 | Should national and local confidence be separate fields? | No | Phase 3 |
| ~~OQ-002~~ | ~~Conditional commencement format?~~ **Resolved** — six-value enum + free text notes | — | — |
| OQ-003 | How does MC work for PRINCIPLE nodes? (Deferred with SCHEMA-012) | No | Phase 4b |
| OQ-004 | Should evidence_independent default to False (cautious) not True (optimistic)? | No | Phase 2b |
| ~~OQ-005~~ | ~~How do we handle England+Wales joint jurisdiction?~~ **Resolved** — `england_and_wales` added to `JurisdictionEnum` | — | — |
| OQ-006 | What alpha for ML classifier outputs (INFERRED sources)? | No | Phase 5 |
| OQ-007 | How does curator_approved work for auto-computed DERIVED nodes? | No | Phase 3 |
| OQ-008 | Are HIGH/MEDIUM/LOW assigned consistently across extractors? (No study done) | No | Phase 3 |
| OQ-009 | Should the GDP constant for unit conversion be a dynamic source? | No | Phase 2b |
| OQ-010 | What's the recovery procedure if Lex Graph provision IDs change? | **Yes** | Phase 4 |

---

*v0.3 — April 2026. SCHEMA-003 settled (OQ-005 resolved). OQ-003 aligned with SCHEMA-012 deferral. SCHEMA-009 citation_edge model clarified (see roadmap). v0.2 added SCHEMA-011, SCHEMA-012 deferral, SCHEMA-023.*
