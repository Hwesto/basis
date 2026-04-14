# BASIS — PLATFORM SPECIFICATION
## Version 2.2 — 9 April 2026

> **⚠ Superseded for data-model detail.** This doc is retained as the
> narrative foundation and historical record. The canonical sources for
> the schema, source types, and CI checks are now:
>
> - `docs/schema/decisions/` — 23 SCHEMA-NNN decisions (status-tracked)
> - `docs/schema/open_questions/` — 10 OQ-NNN questions
> - `src/base_schema.py` + `src/source_models.py` — Pydantic implementations
>
> Known drifts from this doc to current code (as of 14 April 2026):
>
> | Spec says | Current state |
> |---|---|
> | 12 editorial domains | 18 in `DomainEnum` (SCHEMA-002 v2 added energy, eu_trade, electoral_reform) |
> | FiscalMetadata uses `category` | Renamed to `gap_role` with explicit enum (SCHEMA-014) |
> | Tier on SOURCE | Tier on citation edge (`default_tier` on source, `claim_tier_override` on edge — SCHEMA-009) |
> | `LEGISLATIVE_STRUCTURAL` source | Renamed to `STRUCTURAL` with `registry` discriminator (SCHEMA-008 / SCHEMA-010) |
> | 6 CI checks implied | 6 runtime + 2 legal-layer (SCHEMA-023) |
>
> Spec-only content **still canonical** (not yet implemented in code):
> verification pipeline (§2.9), Pipeline 6 GAR query endpoint (§3),
> contested-flag propagation rules (§2.6). These remain design
> requirements for future phases.
>
> Use this doc for theory of change and pipeline overviews; refer to
> `docs/schema/` and the `src/` code for data-model specifics.

This document is the narrative foundation for the BASIS platform.
Pipeline details from basis-pipelines.md are incorporated. Reconciles:
original master notes, product plan, AI architecture, pipeline
architecture, platform audit, and spec v1.0 review.

---

## PART 1: WHAT THIS IS

A platform where political claims are structured as machine-readable
evidence. Every claim sourced. Every assumption stated. Every cost
traceable. Users can explore, challenge, and propose — but evidence
is the price of entry.

**One-liner:** "We show our working."

**Legal structure:** Community Interest Company (CIC). ~£35. Asset-locked.

**Name:** BASIS

**Licensing:** Code: MIT. Content: CC BY-SA 4.0. Public GitHub repository.

**Privacy:** GDPR-compliant. Minimal data collection (email + handle).
Credentials stored encrypted. Analytics via Plausible (privacy-first,
no cookies). Privacy policy published before launch. Data controller:
the CIC.

**What nobody else does:** Combines accountability (tracking what was
promised) with alternative (proposing what should be done) with evidence
(requiring sourced claims as the price of entry). Decidim and Pol.is
collect opinions. IFS and Nuffield broadcast analysis. TheyWorkForYou
tracks MPs. Nobody makes evidence the structural precondition for
participation.

### Theory of Change: Evidence as Structural Pressure

You don't legislate technocracy. You don't elect it. You build a
data layer so complete that governing without reference to it becomes
visibly indefensible.

**Phase 1: Transparency.** Structure the evidence. Every claim
sourced, every assumption stated, every cost traceable. The platform
is read-only and makes no recommendations. It just shows the working.
This earns trust by being obviously non-partisan — it doesn't tell
you what to think, it shows you what's known.

**Phase 2: Density.** Scrutiny, contribution, and cross-domain
detection fill the graph until it's dense enough to do constraint
satisfaction. The fiscal computation pipeline starts revealing hard
trade-offs: you can't promise X, Y, and Z simultaneously. The graph
doesn't have an opinion — it has arithmetic.

**Phase 3: Adoption.** Journalists, researchers, think tanks, and
opposition parties start querying the graph instead of building their
own evidence bases. The platform becomes infrastructure — the place
you go to check a claim, stress-test a proposal, or find the
assumption a minister is hiding behind. Third parties become force
multipliers.

**Phase 4: Cost.** Once enough people treat the graph as the default
reference, ignoring it carries political cost. A policy that
contradicts 14 well-sourced facts and relies on 3 falsified
assumptions is no longer just "contested" — it's structurally
exposed. You haven't forced anyone to govern by evidence. You've
made it expensive not to.

The technocracy isn't the system making decisions. It's the system
making bad decisions so visible that they become unsustainable. You
don't replace democracy — you raise the floor beneath it.

---

## PART 2: THE DATA MODEL

### 2.1 Node Types (6)

| Type | Definition | Example |
|---|---|---|
| SOURCE | A citable document | "OBR Fiscal Risks Report, March 2024" |
| FACT | A single verifiable claim extracted from a source | "NHS waiting list reached 7.6m in 2024" |
| ASSUMPTION | An implicit belief that must be true for a conclusion to hold | "Domestic workers will enter social care at £12/hr" |
| CLAIM | A conclusion derived from facts + assumptions | "NHS funding at current levels is insufficient to deliver the workforce plan" |
| POLICY | A proposed action with mechanism and cost | "Fund NHS at 3.5% real-terms annual growth" |
| POSITION | An actor's stated stance on a policy | "Labour endorses NHS-P01 (2024 manifesto, p.34)" |

**CLAIM vs ASSUMPTION typing rule:**
- ASSUMPTION: can be wrong. Testable with future data. "Domestic workers will enter at £12/hr."
- CLAIM: derivable from existing evidence. "NHS funding is insufficient" (because FACT: 7.6m waiting + FACT: productivity 11.4% below 2019).
- Test: if you'd need to wait and see, it's an ASSUMPTION. If you can derive it now from existing facts, it's a CLAIM.

**POSITION node metadata (required):**
```json
{
  "actor": "Labour",
  "stance": "endorses",
  "maps_to": ["NHS-P01", "NHS-P03"],
  "source_ref": "2024 manifesto, p.34"
}
```
Stance values: endorses | contests | modifies | silent.

**Codebase migration from v1 types:**
- EVIDENCE → FACT (with tier to distinguish)
- TECHNOLOGY → FACT (metadata: {technology: true})
- PARTY → POSITION (with structured metadata above)
- CROSS → whichever type fits; connection handled by cross-domain edges

### 2.2 Evidence Tiers (on every SOURCE)

| Tier | Definition | Examples | Confidence |
|---|---|---|---|
| T1 | Peer-reviewed research | Lancet, NBER, Science | HIGH |
| T2 | Official statistics | ONS, OBR, NHS Digital | HIGH |
| T3 | Government report/review | Darzi Report, MAC Annual | MEDIUM |
| T4 | Think tank / academic | IFS, Nuffield, Resolution Foundation | MEDIUM |
| T5 | Manifesto / party claim | 2024 Conservative Manifesto | LOW |
| T6 | Opinion / media | Editorial, commentary, polling | LOW |

Confidence is categorical, not numeric. No false precision.
HIGH means the methodology is sound and the data is verifiable.
MEDIUM means the analysis is credible but depends on modelling
choices or interpretation. LOW means the claim is asserted
without independent verification or rigorous methodology.

### 2.3 Edge Types (6)

| Type | Meaning | Direction |
|---|---|---|
| SUPPORTS | A provides evidence for B | A → B |
| CONTRADICTS | A undermines B | A → B |
| DEPENDS_ON | A requires B to be true | A → B |
| ENABLES | A makes B more feasible | A → B |
| COMPETES | A and B draw from same finite resource | A ↔ B |
| SUPERSEDES | A replaces B (newer/better evidence) | A → B |

Every edge has: type, strength (0-1), explanation (one sentence,
minimum 10 characters), provenance (editorial/agent/user),
status (canonical/staging).

### 2.4 Fiscal Metadata

On any node carrying a monetary figure:

```json
{
  "fiscal": {
    "amount_low": 20,
    "amount_high": 25,
    "unit": "bn_gbp",
    "period": "annual",
    "direction": "cost",
    "category": "spending_need"
  }
}
```

Categories: spending_need | tax_reform_revenue | trade_revenue |
efficiency_saving | cost_avoidance.

The fiscal gap is ALWAYS computed from these tags, never hardcoded.

### 2.5 Confidence Propagation

When a node's confidence changes (new evidence, upheld challenge,
or superseding source):

1. Node confidence = its source tier category (HIGH/MEDIUM/LOW).
2. Scrutiny adjusts: defended challenges can promote (LOW → MEDIUM,
   MEDIUM → HIGH). Upheld challenges demote.
3. Propagation along SUPPORTS and DEPENDS_ON edges:
   - HIGH confidence survives 2 hops before downgrading to MEDIUM.
   - MEDIUM survives 1 hop before downgrading to LOW.
   - LOW does not propagate positive confidence at all.
4. CONTRADICTS edges: if contradicting node is at same or higher
   confidence than target, target is flagged CONTESTED.
5. CONTESTED is a separate flag, not a confidence level. A node
   can be HIGH confidence AND contested (strong evidence on both
   sides). Contested status propagates to all dependents.

No decimals. No multiplication. The categories are honest about
what they represent: source quality, not probability of truth.

### 2.6 Contested Handling

When two sources at comparable tiers contradict:
- Both FACT nodes persist.
- Both are flagged `contested: true`.
- All downstream CLAIMs and POLICYs inherit contested flag.
- Resolution: via scrutiny (one side gains enough support) or
  via SUPERSEDES edge (newer evidence resolves it).

### 2.7 Graph Versioning

Every node update preserves the previous version in a history table.
The graph at any point in time is reconstructable. Implemented via:
- `node_history` table (copies of previous state on every update)
- `updated_at` timestamp on canonical nodes
- Phase 3 implementation (not launch-critical but required for
  the "audit trail" trust claim).

### 2.8 Domains

12 editorial domains at launch. Domains are curator-managed.
New domains require: curator proposal + minimum 50 nodes.
Domains cannot be deleted, only archived.

### 2.9 Source Verification

Every node in the graph has a `verified` flag (default: false).
Verification means: the source document has been fetched and a
human or agent has confirmed that the node's statement accurately
represents what the source says.

**Why this matters:** The graph may contain claims that are one
or more layers of interpretation away from the original source.
The seed data is extracted from manifesto analysis documents which
themselves summarise primary sources. User submissions may cite a
URL without accurately representing its content. The `verified`
flag distinguishes "we believe this is what the source says" from
"we have confirmed this is what the source says."

**Verification mechanism:**
1. Fetch the source URL or full text (stored in `full_text_ref`)
2. LLM reads the fetched content alongside the node's statement
3. LLM answers: "Does this source actually say what the node
   claims it says?"
4. Output: `verified: true/false` + verification note
5. If false: node is flagged for curator review, not auto-deleted

**Verification status affects confidence display:**
- Verified nodes show their tier-derived confidence normally
- Unverified nodes show confidence with a caveat marker (⚠)
- The platform is honest: "This claim has not been independently
  verified against its stated source"

**For seed data:** All editorial nodes enter as `verified: false`.
Source verification is the first post-launch curator/agent task.
This is the platform demonstrating its own mechanism on its own
content.

**For user submissions:** Source verification runs automatically
on challenge submission (Pipeline 3, step 2). For proposals,
verification runs on each cited source during the proposal
integration pipeline (Pipeline 4).

**For agent-extracted content:** The extraction agent stores the
source full text at ingest time. Verification is inherent — the
agent extracted directly from the source, so `verified` is set
to `true` with provenance `agent`. Curators can override.

---

## PART 3: THE SIX PIPELINES

### Pipeline 1: Evidence

Purpose: Transform raw source material into structured, layered,
traceable knowledge.

```
SOURCE DOCUMENT
  │
  │  Ingest: fetch and store full text (full_text_ref),
  │  assign evidence tier (T1-T6), store URL
  │
  ▼
SOURCE RECORD
  tier, full_text_ref, url, date
  verified: true (source text stored and readable)
  │
  │  LLM extraction: reads the actual source document,
  │  extracts discrete verifiable statements.
  │  Each references source + page/section.
  │  Extraction works from the SOURCE DIRECTLY, not summaries.
  │
  ▼
FACT NODES
  statement: single verifiable claim (complete sentence, min 30 chars)
  source_id → source record
  location: page, section, paragraph
  confidence: inherited from tier
  verified: true (extracted directly from stored source text)
```

**Verification at every layer:** Because the extraction agent reads
the actual source document and stores it, every extracted FACT is
verifiable by anyone — fetch `full_text_ref`, read `source_loc`,
confirm the statement matches. This is the mechanism that makes
"we show our working" auditable, not just aspirational.

**Seed data exception:** Seed nodes extracted from manifesto .md
files (which are themselves LLM summaries of primary sources)
enter as `verified: false`. These get verified post-launch by
fetching each original source URL and confirming the claim. See §2.9.
  │
  │  LLM analysis: what assumptions bridge facts to conclusions?
  │
  ▼
ASSUMPTION NODES
  statement: what must be true for the conclusion to hold
  basis: which facts support this assumption being reasonable
  confidence: assessed
  │
  │  LLM assembly: facts + assumptions → testable conclusions
  │
  ▼
CLAIM NODES
  statement: the conclusion
  depends_on: [fact IDs, assumption IDs]
  confidence: computed from dependency chain (§2.5)
  │
  │  Claims assemble into policy positions
  │
  ▼
POLICY NODES
  statement, mechanism, cost (fiscal metadata §2.4)
  depends_on: [claim IDs]
  │
  │  Parties/users endorse or contest
  │
  ▼
POSITION NODES
  actor, stance, maps_to: [policy IDs], source_ref
```

**Reverse:** New source at same or higher tier contradicts existing
fact → existing fact confidence drops → downstream recalculates
(§2.5) → exposed positions flagged.

### Pipeline 2: Cross-Domain Detection

Purpose: Surface connections between domains that no single-domain
analysis would reveal.

```
TRIGGER: new or modified node
  │
  │  Embed the node statement
  │
  ▼
SIMILARITY SEARCH
  Compare against all nodes in OTHER domains
  Threshold: cosine similarity > 0.75 (tunable)
  │
  │  LLM classifies relationship type and direction
  │
  ▼
PROPOSED CROSS-DOMAIN EDGE
  from_node, to_node
  type: DEPENDS_ON | CONTRADICTS | COMPETES | ENABLES
  strength, explanation
  status: staging → curator review → canonical
```

**Resource competition detection:** When two POLICY nodes in
different domains both DEPEND_ON the same finite quantity (budget,
workforce, time), edge type = COMPETES. This is how the platform
detects that defence at 3.5% and education restoration can't
coexist under current tax commitments.

### Pipeline 3: Scrutiny

Purpose: Allow any claim to be challenged with evidence.

```
ANY NODE
  │
  │  User submits challenge (statement + source required)
  │
  ▼
CHALLENGE
  target: node ID
  statement, source, source_url, source_tier
  │
  │  Automated source verification (§2.9):
  │
  │  Step 1: Does URL resolve? (HTTP HEAD — free, instant)
  │  Step 2: Fetch source content (web_fetch or PDF download)
  │  Step 3: LLM reads fetched content alongside challenge statement
  │          → "Does this source actually say what the challenger
  │             claims it says?"
  │          → source_supports_claim: true/false
  │  Step 4: LLM classifies relationship to target node
  │          → contradicts / refines / supersedes / irrelevant
  │  Step 5: Quality score based on steps 1-4
  │
  │  Without API key: only Step 1 runs (URL check).
  │  With API key: all 5 steps. Cost: ~$0.01 per challenge.
  │
  ▼
EVALUATED CHALLENGE
  url_verified, source_supports_claim,
  challenge_type: contradicts | refines | supersedes | irrelevant
  quality_score, evaluation_note
  status: open
  │
  │  Community scrutiny (other users, evidence required)
  │
  ▼
RESOLUTION
  defended  → original node GAINS confidence (survived scrutiny)
  upheld    → triggers evidence pipeline re-evaluation
  refined   → node modified, downstream recalculates proportionally
  contested → both positions persist, node flagged (§2.6)
```

**Key:** Defended challenges strengthen the node. "Challenged 3 times,
defended each time" is a positive trust signal.

### Pipeline 4: Proposal Integration

Purpose: Map a user's proposal onto the existing evidence graph.

```
USER SUBMITS PROPOSAL
  Fields: problem, mechanism, cost, assumptions, precedent, failure_modes
  │
  │  Field-by-field mapping against graph:
  │
  ▼
FIELD MAPPING

  Problem → search FACT nodes
    "Does evidence support that this problem exists?"
    Output: matching facts + confidence, or "no evidence found"

  Mechanism → search POLICY nodes
    "Has something similar been proposed or tried?"
    Output: related policies, outcomes if known

  Cost → search fiscal FACT nodes
    "Is this estimate consistent with known figures?"
    Output: supporting/contradicting cost data

  Assumptions → search ASSUMPTION nodes
    "Are these already in the graph? At what confidence?"
    Output per assumption:
      — exists, confidence X
      — contradicts existing assumption Y
      — novel (no existing evidence for or against)

  Precedent → search FACT nodes (methodology: international)
    "Do international examples support this?"
    Output: matching evidence, tier, relevance

  Failure modes → search CONTRADICTS edges
    "What existing evidence threatens this proposal?"
    Output: known risks, competing policies
  │
  │  Assembly
  │
  ▼
PROPOSAL REPORT
  "Your proposal depends on X assumptions.
   Y already in graph (mostly HIGH/MEDIUM confidence).
   W contradict existing evidence.
   V are novel — no evidence for or against."
  │
  │  User confirms → staging nodes created
  │
  ▼
STAGING NODES
  New POLICY node + new ASSUMPTION nodes (for novel ones)
  + edges to existing graph
  All staging — curator review before canonical promotion
  Triggers: cross-domain detection + fiscal computation
```

**Reverse:** The graph validates ("assumptions well-supported,
assumptions well-supported, mostly HIGH confidence") or destroys
("key assumption contradicts
T1 evidence from ONS") the proposal.

**Fork:** User can modify an existing POLICY node instead of
creating new. Fork creates linked variant (parent_id). Both
persist. Scrutiny determines which survives.

### Pipeline 5: Fiscal Computation

Purpose: Derive headline fiscal numbers from the graph.

```
ALL NODES WITH FISCAL METADATA
  │
  │  Aggregation per domain
  │
  ▼
DOMAIN FISCAL SUMMARY
  total_spending_gap: sum of costs - identified funding
  confidence_range: [optimistic, central, cautious]
                    based on assumption confidence categories
  key_dependencies: which assumptions most affect the number
  │
  │  Cross-domain deduplication
  │  (immigration costs appear in both immigration and NHS —
  │   don't double-count)
  │
  ▼
DEDUPLICATION
  Identify fiscal nodes referenced from multiple domains
  Assign primary domain, mark cross-references
  │
  │  Headline computation
  │
  ▼
FISCAL GAP
  total: sum of domain gaps - overlaps
  range: [low, high] from sensitivity analysis over assumption categories
  trace: for every £, a path back to source data
  │
  │  Sensitivity analysis
  │
  ▼
SENSITIVITY REPORT
  "If TAX-A06 is wrong, gap widens by £X"
  "If NHS-A03 is wrong, gap narrows by £Y"
  Ranked by impact on headline number
```

**The fiscal gap page is the output of this pipeline.** The
£80-130bn figure is never stored — always computed. If better
evidence narrows it, the number changes automatically.

### Pipeline 6: Query (GAR)

Purpose: Answer policy questions with sourced, graph-traced reasoning.

```
USER QUESTION
  "What would happen if the UK rejoined the single market?"
  │
  │  Embed the question
  │
  ▼
NODE RETRIEVAL
  N nearest nodes by embedding similarity (across all domains)
  │
  │  Graph expansion (1-2 hops)
  │
  ▼
SUBGRAPH EXTRACTION
  For each retrieved node: expand along edges
  Include: edge types, directions, confidences, contested flags
  │
  │  Context assembly (NOT flat text — structured graph)
  │
  ▼
STRUCTURED CONTEXT
  NODE: [id, statement, type, confidence, source, tier]
  EDGE: [from → to, type, strength]
  CONTESTED: [disputed nodes, dispute details]
  GAPS: [where evidence is weak or missing]
  │
  │  LLM generation with constraints
  │
  ▼
SOURCED ANSWER
  Rules:
  — Every claim cites a node ID
  — Contradicting evidence stated equally clearly
  — "Insufficient evidence" when appropriate
  — Contested nodes flagged as contested
  — Assumption dependencies listed
  — No synthesis beyond graph support
  │
  ▼
RESPONSE
  Sourced claims with node citations
  Confidence range
  Key assumptions the answer depends on
  Evidence gaps (what would strengthen this answer)
  Cross-domain implications
  Read-only: no graph modification
```

**Gap detection as output:** When the pipeline can't answer part
of a question, the gap is surfaced to the user AND logged. Repeated
gaps become evidence collection priorities. User questions drive
the platform's evidence-gathering agenda.

### Pipeline Interconnections

```
                    ┌──────────────┐
                    │   EVIDENCE   │ ← new sources, upheld challenges
                    └──────┬───────┘
                           │
              creates/modifies nodes at all layers
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
   ┌────────────┐  ┌──────────────┐  ┌──────────┐
   │CROSS-DOMAIN│  │   FISCAL     │  │ SCRUTINY │
   │ DETECTION  │  │ COMPUTATION  │  │ PIPELINE │
   └─────┬──────┘  └──────┬───────┘  └────┬─────┘
         │                │               │
         ▼                ▼               │
   ┌─────────────────────────────────┐    │
   │         THE GRAPH               │◄───┘
   └───────────┬──────────┬──────────┘
               ▼          ▼
      ┌────────────┐  ┌────────────┐
      │  PROPOSAL  │  │   QUERY    │
      │INTEGRATION │  │  (GAR)     │
      └────────────┘  └────────────┘
       writes staging   read-only
```

**Trigger chain:** New ONS data → evidence pipeline ingests →
fact contradicts NHS-F01 → confidence drops → cross-domain finds
impact on immigration assumptions → fiscal recomputes → query
pipeline gives different answers → scrutiny flags downstream for
review. One source. Six pipelines. Automatic.

### Extraction Agent Process (generalised)

This is HOW Pipeline 1 operates in practice — whether processing
the seed manifesto files, a newly published IFS report, an FOI
response, or a user-uploaded document.

**Input:** Any document (PDF, HTML, plaintext).

**Step 1: Ingest and create SOURCE record.**
```
- Fetch or receive the document
- Store full text (full_text_ref)
- Store URL if web-sourced
- Classify tier (T1-T6) based on publisher
- Create SOURCE record with verified: true
  (the agent has the actual text)
```

**Step 2: Extract FACT nodes.**
```
- LLM reads the source document directly
- Extracts discrete, verifiable, single-sentence claims
- Each FACT references the SOURCE by ID + location (page/section)
- Confidence inherited from source tier
- Fiscal metadata extracted where monetary figures present
- verified: true (extracted from stored source text)
- Validation: reject statements < 30 chars, reject duplicates
```

**Step 3: Extract ASSUMPTION nodes.**
```
- LLM identifies implicit beliefs bridging facts to conclusions
- "What must be true for this conclusion to hold?"
- Each ASSUMPTION linked to the FACTs that inform it (via edges)
- Confidence assessed by the LLM (HIGH/MEDIUM/LOW)
```

**Step 4: Derive CLAIM nodes.**
```
- LLM assembles: facts + assumptions → testable conclusions
- Each CLAIM records its dependency chain (via DEPENDS_ON edges)
- Confidence computed from dependencies (§2.5)
```

**Step 5: Identify POLICY nodes (if the source proposes actions).**
```
- Only if the source contains policy proposals
- Each POLICY must have mechanism (how, not just what)
- Fiscal metadata where cost/revenue figures present
- DEPENDS_ON edges to the CLAIMs and ASSUMPTIONs it relies on
```

**Step 6: Map POSITION nodes (if the source is party/actor material).**
```
- Each POSITION: actor, stance (endorses/contests/modifies),
  maps_to (POLICY IDs), source_ref
- One POSITION per distinct stance per actor
- Complete sentences, not fragments
```

**Step 7: Generate edges.**
```
- SUPPORTS: fact provides evidence for assumption/claim
- CONTRADICTS: fact undermines existing node
- DEPENDS_ON: policy/claim requires assumption to be true
- ENABLES: fact makes policy more feasible
- COMPETES: policies draw from same finite resource
- SUPERSEDES: newer source replaces older on same point
- Every edge requires: type, strength, explanation (min 10 chars)
- Only create edges the text states or clearly implies
```

**Step 8: Validate.**
```
- No statement < 30 characters
- No generic sources ("See domain sources", "Platform analysis")
- No generic edge explanations ("supports", "related")
- Every FACT has a source_id
- Every POSITION has actor + stance in metadata
- Every fiscal tag has amount, unit, period, direction, category
- Duplicates detected via embedding similarity > 0.95
```

**Output:** JSON files (nodes.json, edges.json) per domain,
following the schema in Part 8.

**Contexts where this process runs:**

| Context | Input | Trigger | verified |
|---|---|---|---|
| Seed extraction | Manifesto .md files | Manual (one-time) | false (summaries, not primary sources) |
| New publication | IFS/OBR/ONS PDF | Evidence monitor RSS alert | true (agent reads actual document) |
| FOI response | Government response document | FOI tracker | true (primary source) |
| User upload | Any document | User action | true (agent reads the upload) |
| Parliamentary | Hansard transcript | Parliament monitor | true (official transcript) |

The same extraction logic applies in every context. The only
difference is whether `verified` is true (agent read the primary
source) or false (agent read an intermediate summary).

---

## PART 4: USER SYSTEM

### 4.1 Roles

| Role | Can Do | Requirements |
|---|---|---|
| Casual | Browse, read, search, use GAR, quick-flag nodes | None |
| Contributor | Challenge, propose, scrutinise, fork | Handle + email |
| Curator | Approve staging → canonical, tag sources, moderate | Track record OR invitation |
| Reviewer | All above + credential-tagged contributions | Professional body verification |

**Quick-flag:** Any user (including casual) can tap a node and
flag it: "seems weak" / "seems strong" / "outdated." No source
required for a flag. Flags aggregate into a signal visible to
curators. This is the one-click entry point to contribution —
the "bus-friendly 30-second" interaction.

### 4.2 Identity Model

- Surface: anonymous handle (@evidence_nerd)
- Underneath: verified email (Supabase Auth)
- Optional: verified professional credentials
- Display: "Challenged by verified solicitor" not "John Smith"
- Credentials give enhanced VISIBILITY, not enhanced PERMISSIONS
- Anyone can challenge anything — verified expertise gets surfaced
  more prominently

### 4.3 Credential Verification (graduated)

Phase 2: Self-declared professional background, shown as unverified.
Phase 3: Manual verification (user submits proof, curator confirms).
Phase 5: API integration with professional bodies:
  SRA (solicitors), GMC (doctors), RICS (surveyors),
  ICAEW/CIMA (accountants), Engineering Council, BCS (computing).

### 4.4 Reputation

Profile displays:
```
@evidence_nerd
14 challenges submitted, 11 survived scrutiny (78%)
23 evidence verifications
3 proposals, 1 forked by others
Primary domains: NHS, Taxation
Verified: ICAEW member
```

This IS your follower count. It means something.

### 4.5 Engagement Loops

Notifications (email initially, push later):
- "An assumption you challenged has been defended — here's the counter"
- "New evidence contradicts a claim you verified"
- "Someone forked your proposal with a different cost model"
- "An assumption you flagged just failed in practice — here's the data"

Anti-patterns:
- NOT Change.org (emotion, no evidence)
- NOT Twitter (hot takes, no accountability)
- NOT gov.uk (no engagement)
- Tone: Reddit at its best — irreverent but substantive

### 4.6 Moderation

Curators can flag and hide contributions that violate community
standards: no personal attacks, no hate speech, no deliberately
misleading citations. Flagged content is hidden pending review,
not deleted. Appeals via email to CIC. Repeat offenders can have
contributor status revoked by curator quorum (2 curators).

### 4.7 Curation Workflow (graduated)

**Phase 0-2 (pre-scale): Wiki model.**
All user contributions go straight to canonical with
`reviewed: false`. No staging gate. Curators review reactively —
fix bad content when they see it, not gate everything proactively.
This prevents the curator bottleneck from killing early momentum.
One person cannot review every node, edge, and challenge at scale.

**Phase 3+ (post-scale): PR model.**
Once 3+ active curators exist, switch to staging → canonical
promotion:
- 1 curator approval for: new nodes, new edges, challenge resolutions.
- Auto-promote: quick-flags (aggregate signal, no gate needed).
- Rejection: sets `status: deprecated` with reason. Author notified.

**Curator selection:**
- Initial curators: platform founders.
- New curators: invitation by existing curator, OR track record
  threshold (20 verified submissions, ≥80% survive scrutiny).

The wiki model accepts some bad content in exchange for not
strangling contribution. The PR model adds quality gates once
there are enough reviewers to operate them without bottlenecking.

---

## PART 5: WHAT'S BUILT

| Component | Status | Quality | Action |
|---|---|---|---|
| Next.js app, 11 routes | Compiles clean | Solid | Keep architecture |
| 780 extracted nodes | 59% bad sources | Poor | REBUILD (Phase 1) |
| 745 edges | Mechanical | Poor | DELETE AND REBUILD (Phase 1) |
| 23 cross-domain edges | Sparse | Partial | REBUILD (Phase 1) |
| Supabase schema + dual-mode store | Works | Good | Update schema (Phase 1) |
| Reader manifesto (HTML) | 78 linked tags | Good | Keep as landing page |
| TF-IDF embeddings | Works | OK | Replace with sentence-transformers |
| GNN pipeline | Produces real results | Good | Retrain on clean data |
| GAR retrieval | Correct subgraphs | Good | Keep, improve |
| 4 agents | Work standalone | OK | Wire to UI (Phase 2) |
| Fiscal gap page | Hardcoded | False | REWRITE (Phase 2) |
| Search | Substring | False | REWRITE (Phase 2) |
| Proposal form | No linking | False | WIRE (Phase 2) |
| Challenge system | No evaluation | Incomplete | WIRE (Phase 2) |
| Credential verification | Not built | — | Phase 3 |
| Reputation system | Not built | — | Phase 3 |
| Fork mechanism | Not built | — | Phase 3 |
| Notifications | Not built | — | Phase 3 |
| Quick-flag | Not built | — | Phase 2 |
| FOI automation | Not built | — | Phase 5 |
| Parliamentary monitoring | Not built | — | Phase 5 |

---

## PART 6: BUILD ORDER

### Definition of "launch"

**Static launch (Phase 0):** Reader manifesto goes live as a
standalone site. Email signup. Social sharing. This can happen
immediately using existing assets.

**Platform launch (Phase 1 + 2a):** Phase 1 complete (clean data)
plus: embedding search (2.1), evidence tiers in UI (2.7), false
claims removed (2.8). This is the minimum viable platform — browse,
search, explore evidence chains.

**Full Phase 2:** Proposal linking, fiscal computation from graph,
challenge evaluation, GNN on node pages. Ships in weeks 2-4
post-platform-launch.

---

### PHASE 0 — STATIC LAUNCH
*Immediate. Uses existing built assets.*

- Deploy reader manifesto to Vercel as landing page
- Email signup (Supabase or Formspree)
- Social sharing metadata (OG cards)
- Analytics (Plausible)
- Marketing leads with the methodology, not the conclusion:
  - "12 domains. 338 sources. Every claim referenced."
  - "The manifesto that shows its working."
  - "Think we're wrong? Click any claim and check."
  NOT "£80-130bn gap no party acknowledges" — that's a finding
  inside the platform, not the headline. Let users discover
  the fiscal gap by exploring. It's more powerful as a discovery
  than as a marketing claim. A platform built on "we show our
  working" can't lead with a politically contested headline.
- Target: r/ukpolitics, r/unitedkingdom, UK politics Twitter/X,
  Substack politics newsletters

---

### PHASE 1 — DATA FOUNDATION
*Before platform launch. Nothing else matters until this is right.*

**1.1 Re-extract all 12 domains**
- Input: 12 manifesto .md files (the 60,000 words of evidence)
- Tool: Claude Opus structured extraction prompt
- Output: ~600 clean nodes following 6-type schema
- Validation: no node without real source, min 30 char, tier assigned
- Cost: ~$3

**1.2 Generate meaningful edges**
- Delete all 745 mechanical edges
- Embed all clean nodes (sentence-transformers, local)
- For each node: 5 most similar in-domain → LLM classifies relationship
- Only create edges LLM confirms with explanation
- Cost: ~$4

**1.3 Generate cross-domain edges**
- Same pipeline, across domain boundaries only
- Target: 80-150 edges (from 23)
- Cost: ~$2

**1.4 Compute fiscal metadata**
- Tag every node with monetary figure (§2.4 schema)
- Validate: fiscal gap computable from tags alone

**1.5 Update Supabase schema**
- Apply revised schema (Part 8)
- Run seed script with clean data
- Regenerate embeddings
- Retrain GNN on clean graph

**Phase 1 complete when:**
- [ ] All nodes have real sources with evidence tiers
- [ ] All edges have explanations
- [ ] Fiscal gap computable from graph data
- [ ] No node statement < 30 characters
- [ ] Schema matches Part 8

---

### PHASE 2 — DELIVER PROMISES + LAUNCH FEATURES

**2a: Launch-critical (ship with platform launch)**

**2.1 Embedding search** — replace substring with cosine similarity
**2.7 Evidence tiers in UI** — tier badge on every node, colour-coded,
filterable (HIGH green, MEDIUM amber, LOW grey, CONTESTED red outline)
**2.8 Remove false UI claims** — delete "auto-links via semantic
similarity" and any other undelivered promise

**2b: Post-launch (weeks 2-4)**

**2.2 Proposal auto-linking** — field-by-field mapping per Pipeline 4
**2.3 Fiscal gap from graph** — computed from fiscal metadata,
sensitivity analysis, each bar traces to nodes
**2.4 Challenge evaluation** — HTTP HEAD on URL + LLM quality score
**2.5 GNN data on node pages** — robustness, load-bearing scores
**2.6 Quick-flag** — casual one-click "seems weak/strong/outdated"

**Phase 2 complete when:**
- [ ] Search uses embeddings
- [ ] Proposals get field-by-field graph feedback
- [ ] Challenges get quality signals (source verified/not found)
- [ ] Fiscal gap page computes from graph
- [ ] Zero false claims in UI
- [ ] Quick-flag live

---

### PHASE 3 — TRUST LAYER

**3.1** User profiles with track record
**3.2** Self-declared credentials (unverified initially)
**3.3** Curator manual verification of credentials
**3.4** Reputation scoring (survived scrutiny rate)
**3.5** Notification system (email)
**3.6** Fork mechanism (linked variants, both persist)
**3.7** Contested fact handling (§2.6)
**3.8** Graph history table (§2.7)

**Phase 3 complete when:**
- [ ] User profiles show track records
- [ ] At least one credential-verified reviewer active
- [ ] Notifications sending
- [ ] Fork mechanism works
- [ ] Contested handling works

---

### PHASE 4 — ASK THE EVIDENCE

**4.1** GAR endpoint (Pipeline 6)
**4.2** "Ask the Evidence" page with structured answers
**4.3** Share-friendly answer cards (OG-style with citations)
**4.4** Gap detection logged for evidence priorities

**Phase 4 complete when:**
- [ ] Answers 20 test questions correctly with node citations
- [ ] "Insufficient evidence" returned when appropriate
- [ ] Answer cards shareable

---

### PHASE 5 — AUTOMATION

**5.1** Evidence monitoring (RSS/webhook → flag updates)
**5.2** FOI automation (WhatDoTheyKnow integration)
**5.3** Parliamentary monitoring (Hansard → position extraction)
**5.4** Professional body API integration (SRA, GMC, etc.)

---

### PARKED

| Feature | Reason | Revisit When |
|---|---|---|
| Petition clustering | Needs user base | 10,000+ users |
| Legal crowdfunding | Needs CIC + legal counsel | Post-CIC |
| Sovereign model | Needs 2,000+ clean nodes | 12-18 months |
| Mobile app | Responsive web sufficient | Product-market fit |
| Party subscriptions | Needs demonstrated value | Post-press |
| Public API | Needs stable schema | Phase 4+ |

### CUT

| Feature | Reason |
|---|---|
| Seven-agent swarm | One pattern (embed→retrieve→generate) ×4. Code kept. |
| GNN as launch gate | Monte Carlo gives 90% of insight. GNN trains offline. |
| Sugiyama graph viz | List view with filters works. Polish, not product. |

---

## PART 7: TECH STACK

```
Frontend:     Next.js + TypeScript + Tailwind
Database:     Supabase (PostgreSQL + Auth + Realtime + pgvector)
Hosting:      Vercel (frontend) + Supabase (backend)
Embeddings:   sentence-transformers (local) or TF-IDF (fallback)
LLM:          Claude API (Opus: extraction. Sonnet: GAR. Haiku: classification)
AI pipeline:  Python scripts (local or Supabase Edge Functions)
GNN:          PyTorch Geometric (offline, results as JSON)
Analytics:    Plausible (privacy-first)
```

---

## PART 8: DATABASE SCHEMA

```sql
CREATE TABLE sources (
  id            TEXT PRIMARY KEY,
  title         TEXT NOT NULL,
  url           TEXT,
  tier          INT NOT NULL CHECK (tier BETWEEN 1 AND 6),
  author        TEXT,
  published_date DATE,
  full_text_ref TEXT,
  verified      BOOLEAN DEFAULT false,
  verified_at   TIMESTAMPTZ,
  verified_by   TEXT,              -- 'agent', 'curator:handle', or null
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE domains (
  slug          TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  number        TEXT,
  headline      TEXT,
  diagnosis     TEXT,
  node_count    INT DEFAULT 0,
  source_count  INT DEFAULT 0,
  archived      BOOLEAN DEFAULT false,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE nodes (
  id            TEXT NOT NULL,
  domain        TEXT NOT NULL REFERENCES domains(slug),
  type          TEXT NOT NULL CHECK (type IN (
                'SOURCE','FACT','ASSUMPTION','CLAIM','POLICY','POSITION')),
  statement     TEXT NOT NULL CHECK (length(statement) >= 30),
  confidence    TEXT NOT NULL DEFAULT 'MEDIUM'
                CHECK (confidence IN ('HIGH','MEDIUM','LOW')),
  source_id     TEXT REFERENCES sources(id),
  source_loc    TEXT,
  verdict       TEXT,
  fiscal        JSONB,
  metadata      JSONB DEFAULT '{}',
  provenance    TEXT DEFAULT 'editorial'
                CHECK (provenance IN ('editorial','agent','user')),
  status        TEXT DEFAULT 'canonical'
                CHECK (status IN ('canonical','staging','deprecated')),
  contested     BOOLEAN DEFAULT false,
  reviewed      BOOLEAN DEFAULT false,
  verified      BOOLEAN DEFAULT false,  -- source checked against claim (§2.9)
  verified_at   TIMESTAMPTZ,
  author_id     UUID REFERENCES auth.users(id),
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (domain, id)
);

CREATE TABLE node_history (
  id            SERIAL PRIMARY KEY,
  domain        TEXT NOT NULL,
  node_id       TEXT NOT NULL,
  previous_state JSONB NOT NULL,
  changed_by    UUID REFERENCES auth.users(id),
  change_reason TEXT,
  changed_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE edges (
  id            SERIAL PRIMARY KEY,
  from_domain   TEXT NOT NULL,
  from_node     TEXT NOT NULL,
  to_domain     TEXT NOT NULL,
  to_node       TEXT NOT NULL,
  type          TEXT NOT NULL CHECK (type IN (
                'SUPPORTS','CONTRADICTS','DEPENDS_ON',
                'ENABLES','COMPETES','SUPERSEDES')),
  strength      FLOAT DEFAULT 0.5,
  explanation   TEXT NOT NULL CHECK (length(explanation) >= 10),
  provenance    TEXT DEFAULT 'editorial',
  status        TEXT DEFAULT 'canonical',
  author_id     UUID REFERENCES auth.users(id),
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE profiles (
  id                    UUID PRIMARY KEY REFERENCES auth.users(id),
  handle                TEXT UNIQUE NOT NULL,
  role                  TEXT DEFAULT 'contributor'
                        CHECK (role IN ('contributor','curator','reviewer')),
  self_declared_role    TEXT,
  credential_verified   BOOLEAN DEFAULT false,
  credential_body       TEXT,
  credential_ref        TEXT,
  verified_by           UUID REFERENCES auth.users(id),
  challenges_submitted  INT DEFAULT 0,
  challenges_survived   INT DEFAULT 0,
  scrutiny_given        INT DEFAULT 0,
  proposals_submitted   INT DEFAULT 0,
  verifications_given   INT DEFAULT 0,
  primary_domains       TEXT[],
  created_at            TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE challenges (
  id              TEXT PRIMARY KEY,
  target_domain   TEXT NOT NULL,
  target_node     TEXT NOT NULL,
  statement       TEXT NOT NULL CHECK (length(statement) >= 20),
  source          TEXT NOT NULL,
  source_url      TEXT,
  source_tier     INT CHECK (source_tier BETWEEN 1 AND 6),
  author_id       UUID REFERENCES auth.users(id),
  author_handle   TEXT NOT NULL,
  url_verified    BOOLEAN,
  source_supports BOOLEAN,
  challenge_type  TEXT CHECK (challenge_type IN (
                  'contradicts','refines','supersedes','irrelevant')),
  quality_score   FLOAT,
  evaluation_note TEXT,
  status          TEXT DEFAULT 'open' CHECK (status IN (
                  'open','defended','upheld','refined','contested')),
  resolved_by     UUID REFERENCES auth.users(id),
  resolved_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE scrutiny (
  id              SERIAL PRIMARY KEY,
  challenge_id    TEXT NOT NULL REFERENCES challenges(id),
  action          TEXT NOT NULL CHECK (action IN ('support','dispute')),
  evidence        TEXT,
  source_url      TEXT,
  comment         TEXT,
  author_id       UUID REFERENCES auth.users(id),
  author_handle   TEXT NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE proposals (
  id                TEXT PRIMARY KEY,
  domain            TEXT NOT NULL,
  title             TEXT NOT NULL,
  problem           TEXT NOT NULL,
  mechanism         TEXT NOT NULL,
  cost_estimate     TEXT,
  assumptions       TEXT,
  precedent         TEXT,
  failure_modes     TEXT,
  problem_matches   JSONB,
  mechanism_matches JSONB,
  cost_matches      JSONB,
  assumption_matches JSONB,
  precedent_matches  JSONB,
  risk_matches      JSONB,
  author_id         UUID REFERENCES auth.users(id),
  author_handle     TEXT NOT NULL,
  parent_id         TEXT REFERENCES proposals(id),
  forks             INT DEFAULT 0,
  status            TEXT DEFAULT 'draft',
  created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE node_flags (
  id              SERIAL PRIMARY KEY,
  domain          TEXT NOT NULL,
  node_id         TEXT NOT NULL,
  flag_type       TEXT NOT NULL CHECK (flag_type IN (
                  'seems_weak','seems_strong','outdated')),
  author_id       UUID REFERENCES auth.users(id),
  created_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE (domain, node_id, author_id)
);

CREATE TABLE agent_log (
  id              SERIAL PRIMARY KEY,
  agent_id        TEXT NOT NULL,
  action          TEXT NOT NULL,
  input_ref       TEXT,
  output_ref      TEXT,
  tokens_used     INT,
  cost_usd        FLOAT,
  duration_ms     INT,
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## PART 9: COMMERCIAL MODEL

### Free tier (always)
- Browse, read, search, use GAR, quick-flag
- Submit challenges and proposals
- Build reputation

### Revenue streams (Phase 4+)
- **API access** for think tanks, academics, journalists (tiered pricing)
- **Institutional accounts** for policy teams (charities, councils, parties)
- **Grants:** Nesta, Luminate, Open Society Foundations, Nuffield Foundation,
  Mozilla Foundation — all fund civic tech
- **Professional profiles** with enhanced credential display (future)

### Sustainability
CIC asset lock ensures revenue funds the platform, not shareholders.
Target: grant-funded through Phase 3, self-sustaining from Phase 4
API revenue.

---

## PART 10: COST ESTIMATES

### One-time rebuild (Phase 1)
| Item | Cost |
|---|---|
| Re-extract 12 domains (Opus × 12) | ~$3 |
| Edge classification (Haiku × 4,000) | ~$4 |
| Cross-domain edges (Haiku × 2,000) | ~$2 |
| Embeddings (local) | $0 |
| **Total** | **~$9** |

### Monthly running (Phase 2+)
| Item | Cost |
|---|---|
| Supabase free tier | $0 |
| Vercel free tier | $0 |
| Claude API | ~$5-10 |
| Domain name (.org) | ~$1 |
| Plausible analytics | $0 (self-host) or $9 |
| **Total** | **~$6-20/month** |

**LLM cost ceiling:** Hard monthly cap at $50. If reached:
- GAR degrades to non-LLM mode (returns subgraph for user to read)
- Challenge evaluation falls back to URL verification only (free)
- Daily query budget on "Ask the Evidence" (100 queries/day)
- The platform works without LLM calls. They improve it, they're
  not load-bearing.

### CIC registration: ~£35

---

## PART 11: SUCCESS METRICS

### Phase 1: all checklist items in §Phase 1
### Phase 2: all checklist items in §Phase 2
### Phase 3: all checklist items in §Phase 3
### Phase 4: all checklist items in §Phase 4

### Launch metrics (first 3 months post-platform-launch):
- 10,000 visitors
- 500 email signups
- 100 user accounts
- 50 challenges submitted
- 10 challenges that survive scrutiny
- 1 media mention
- 1 verified professional contributor

---

## PART 12: WHAT THIS REPLACES

| Document | Status |
|---|---|
| Original master notes | SUPERSEDED |
| Product plan | SUPERSEDED |
| AI architecture | SUPERSEDED |
| Pipeline architecture | INCORPORATED IN FULL (Part 3) |
| Platform audit | INCORPORATED (findings → Phase 1-2) |
| Spec v1.0 | SUPERSEDED |
| Spec v1.0 review | INCORPORATED (17 items → appendix) |
| Spec v2.0 | SUPERSEDED |
| Final review | INCORPORATED (6 items → appendix) |
| Extraction agent spec | INCORPORATED (generalised process in Part 3) |

This is the only specification document. It is finished.

---

## APPENDIX: REVIEW ITEM RESOLUTION

### Spec v1.0 review (17 items)
| # | Item | Resolution |
|---|---|---|
| D1 | Quick interactions dropped | Added: quick-flag in §4.1, Phase 2.6 |
| D2 | Commercial model missing | Added: Part 9 |
| D3 | Launch strategy missing | Added: Phase 0 with distribution targets |
| D4 | Reader manifesto role undefined | Defined: landing page in Phase 0, §6 |
| D5 | Open source not stated | Added: Part 1 (MIT + CC BY-SA) |
| D6 | Positioning not referenced | Added: Part 1 "what nobody else does" |
| D7 | API not in parked table | Added: Parked table |
| U1 | Staging workflow underspec | Defined: §4.7 (graduated wiki → PR) |
| U2 | Confidence propagation underspec | Defined: §2.5 (categorical, not decimal) |
| U3 | POSITION metadata underspec | Defined: §2.1 |
| U4 | Domain mutability undefined | Defined: §2.8 |
| U5 | CLAIM vs ASSUMPTION unclear | Defined: typing rule in §2.1 |
| U6 | No moderation policy | Added: §4.6 |
| U7 | No GDPR position | Added: Part 1 |
| S1 | Pipelines not self-contained | Incorporated in full: Part 3 |
| S2 | Launch undefined | Defined: §6 launch definition |
| S3 | No graph versioning | Added: §2.7, node_history table |

### Final review (6 items)
| # | Item | Resolution |
|---|---|---|
| R1 | Cold start underaddressed | Operational, not spec. Seed users = personal network. |
| R2 | Curator bottleneck | Changed: §4.7 wiki model initially, staging gates at 3+ curators |
| R3 | LLM cost scaling | Added: cost ceiling $50/month, degradation strategy in Part 10 |
| R4 | Fiscal gap politically loaded | Changed: Phase 0 leads with methodology, not conclusion |
| R5 | Confidence false precision | Changed: §2.2 and §2.5 categorical (HIGH/MEDIUM/LOW), no decimals |
| R6 | Over-engineered for current state | Acknowledged. The spec is done. Ship Phase 0 now. |

### Spec v2.2 additions
| # | Item | Resolution |
|---|---|---|
| V1 | Source verification mechanism | Added: §2.9, updated Pipeline 1, Pipeline 3, schema |
| V2 | Generalised extraction agent process | Added: §Pipeline interconnections (extraction agent subsection) |
| V3 | verified flag on sources and nodes | Added: schema (sources.verified, nodes.verified) |
| V4 | Seed data marked unverified | Defined: §2.9, Pipeline 1 seed exception |
