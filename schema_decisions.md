# schema_decisions.md

> Every schema decision is a claim. Claims need sources and reasoning.
> This document records the reasoning behind every design choice in
> `base_schema.py` and `source_models.py`. It must be updated when
> any schema decision changes, and consulted before any new node type,
> edge type, or confidence parameter is added.
>
> Format per entry:
> - **Phenomenon**: what real-world thing we are encoding
> - **Decision**: what we chose
> - **Alternatives**: what we could have chosen instead
> - **Assumptions**: what must be true for this decision to be correct
> - **Falsification**: what would force a revision
> - **Status**: SETTLED | PROVISIONAL | UNDER_REVIEW

---

## Part 1: Foundation

---

### SCHEMA-001: Single base class for all entities

**Phenomenon:** Every entity in the system — a policy claim, a legal right, a local
crime metric, a citizen action outcome — shares a common structure: it is a statement
about the world, it came from somewhere, it has a degree of confidence, and it requires
human sign-off before it affects citizens.

**Decision:** `BaseNode` is the root class. Every entity type is a subclass. The
curator queue, CI validator, and MC engine operate against `BaseNode` only. Domain-
specific fields belong on subclasses, never on the base.

**Alternatives:**
- Separate tables per layer (evidence_nodes, legal_nodes, area_metrics). Rejected:
  produces five curator queues, five CI checks, five confidence engines. We've already
  seen this pattern fail in Phase 1 — the fiscal validator, edge validator, and schema
  validator were written separately and diverged.
- Flat table with nullable columns per type. Rejected: schema drift is undetectable.
  A FACT node with a `duty_holder` field set is a silent error, not a validation failure.
- JSON blob per node with no typed schema. Rejected: same as flat table but worse —
  Gemma would produce inconsistent shapes and we'd never know.

**Assumptions:**
1. All entities in the system share the cross-cutting fields (source traceability,
   confidence, curator gate, provenance). If a future entity type genuinely doesn't
   need a confidence score or a source, this assumption is violated.
2. The cost of subclass overhead is lower than the cost of schema divergence across layers.

**Falsification:**
- A node type that has no meaningful confidence score and no external source — e.g. a
  purely structural computation with deterministic output. This would be a `DERIVED`
  node with `source_type=DERIVED`. Currently handled. Monitor.
- A node type where `curator_approved` makes no sense — e.g. an automatically-computed
  percentile rank. Current handling: `curator_approved=True` set automatically by the
  computation pipeline, not by a human. This is a weak point — the gate is bypassed.
  Acceptable for Phase 3 but needs a cleaner solution.

**Status:** SETTLED

---

### SCHEMA-002: DomainEnum as typed, extensible enum

**Phenomenon:** Every node belongs to a thematic area. These areas determine which
extraction pipeline processes a node, which local data metrics link to it, and how the
frontend organises content.

**Decision:** `DomainEnum` is a Python `str, Enum` with explicit members. Free-text
`domain` fields are rejected at validation time. New domains require an explicit PR
adding them to the enum — they cannot be added by the extraction pipeline.

**Alternatives:**
- Free-text string. Rejected: 'housing' vs 'Housing' vs 'housing_disrepair' in the
  current data/ directory. Already observed in Phase 1. CI check caught some but not all.
- Hierarchical taxonomy (housing > disrepair, housing > eviction). Considered and
  deferred: the classification overhead at extraction time is high, and cross-domain
  queries become complex. Revisit at Phase 4 when domain coverage expands.
- Tag-based (a node has multiple domain tags). Possible but conflicts with the
  cross-layer join logic, which assumes each node belongs to one domain.

**Assumptions:**
1. Domains are mutually exclusive for a given node. A claim about NHS funding for
   housing support arguably spans health AND housing. Current handling: assign to
   the primary domain, add cross-domain SUPPORTS edge to the secondary domain node.
   This is a workaround, not a solution.
2. The initial 12 domains cover the Phase 1-3 evidence corpus. True at time of writing.

**Falsification:**
- A node that genuinely cannot be assigned a primary domain without information loss.
  If this becomes common (>5% of nodes), introduce a `primary_domain` +
  `secondary_domains: list` structure.

**Status:** SETTLED for current corpus. PROVISIONAL on mutual exclusivity assumption.

---

### SCHEMA-003: JurisdictionEnum as a hard constraint on legal content

**Phenomenon:** UK law is devolved. Housing law differs between England, Wales, Scotland,
and Northern Ireland. A right that applies in England may not apply in Scotland.

**Decision:** `JurisdictionEnum` with six members: `england`, `wales`, `scotland`, `ni`,
`england_and_wales`, `uk_wide`. Applied at query time, not display time — a Scottish
postcode never receives England-only legal nodes from the API, even if they happen to be
in the response cache. `england_and_wales` is a first-class jurisdiction (not a
multi-jurisdiction shorthand) because the vast majority of devolved housing, health,
and education legislation applies jointly to those two jurisdictions and distinguishing
them produces false negatives at query time.

**Alternatives:**
- Soft filtering at display time. Rejected: depends on frontend developers consistently
  applying the filter. Any miss results in displaying wrong law to citizens.
- Single 'united_kingdom' jurisdiction. Rejected: legally incorrect for devolved matters.
  It would be accurate for reserved matters (immigration, benefits) but wrong for
  housing, education, health. Cannot be correct in the general case.
- Free-text jurisdiction. Rejected: same problems as free-text domain.

**Assumptions:**
1. The six-jurisdiction model is sufficient. Currently correct. If we later encounter
   legislation that applies in three but not four jurisdictions (e.g. GB-wide but not
   NI), we extend the enum rather than introduce a `multi_jurisdiction` list field.
2. Postcode-to-jurisdiction resolution is reliable. ONS NSPL is authoritative. True.

**Falsification:**
- Discovery of legislation whose scope cannot be represented by any single enum member
  (e.g. "England and Scotland but not Wales or NI"). No such case observed in the top
  20 priority domains. Flag and extend the enum when first encountered.

**Status:** SETTLED — `england_and_wales` added in `base_schema.py`. Resolves OQ-005.

---

### SCHEMA-004: Confidence as categorical HIGH/MEDIUM/LOW

**Phenomenon:** How much should we trust a claim?

**Decision:** Extraction-time confidence is categorical: HIGH, MEDIUM, LOW. Assigned
by the human extractor (Track C) or by Gemma with curator review (Track B). Not a
decimal number.

**Alternatives:**
- Decimal [0.0, 1.0]. Rejected on the grounds stated in the original spec §2.5: false
  precision. A decimal score implies a measurement process that doesn't exist. Saying
  a claim has confidence 0.73 implies we know it's more confident than 0.72. We don't.
- Binary (verified / unverified). Too coarse — conflates "we haven't checked" with
  "we checked and it's weak."
- Five-level scale (following GRADE: high/moderate/low/very low). Considered seriously.
  GRADE's fourth level (very low) is specifically for "any estimate of effect is very
  uncertain." This is useful for the evidence layer, less useful for legal nodes where
  a provision either applies or it doesn't. Decision: defer to Phase 4 review.

**Assumptions:**
1. Three levels are sufficient to drive meaningful UI differentiation. Currently true.
2. Human extractors can reliably distinguish HIGH from MEDIUM. This is an empirical
   question. No calibration study has been done. Monitor inter-rater agreement when
   Track C extraction produces >50 nodes.
3. Categorical confidence is converted to numerical alpha in the MC engine. The
   conversion table is a design choice — see SCHEMA-014.

**Falsification:**
- Evidence that human extractors are inconsistent on the HIGH/MEDIUM boundary across
  domains. If inter-rater agreement <80%, either the definitions need tightening or
  a fourth level ('very high' for verified T1 sources) would help.

**Status:** SETTLED on categorical. PROVISIONAL on three vs four levels.

---

### SCHEMA-005: computed_confidence as MC output separate from extraction confidence

**Phenomenon:** The extraction-time confidence is a prior. The MC-propagated confidence
is a posterior that incorporates the quality of all upstream evidence.

**Decision:** `confidence` (HIGH/MEDIUM/LOW) is the human-assigned prior, set at
extraction. `computed_confidence` is a dict produced by the MC engine:
`{mean, std, p5, p95, label}`. These are separate fields and can diverge significantly.
The frontend displays `computed_confidence.label`; researchers can see both.

**Alternatives:**
- Replace `confidence` with `computed_confidence` entirely. Rejected: loses the
  extraction-time prior. If MC is re-run with different parameters, you need the
  original human assessment to re-anchor.
- Store only the label from MC, not the distribution. Rejected: the distribution
  (particularly p5 and p95) carries information about stability that the label doesn't.
  A node with mean=0.75 and std=0.40 is very different from mean=0.75 and std=0.05.

**Assumptions:**
1. The MC engine correctly propagates confidence from sources through the graph. This
   is a technical correctness assumption — see SCHEMA-016 through SCHEMA-022 for the
   specific MC design decisions.
2. Re-running MC with the same seed produces stable results. Verified: 10K samples,
   seed=42, <1% variance across runs.

**Status:** SETTLED

---

### SCHEMA-006: curator_approved as a hard gate, never bypassed

**Phenomenon:** Citizens rely on this platform to make decisions about legal complaints,
benefit claims, and other consequential actions. Wrong information causes real harm.

**Decision:** `curator_approved: bool = False` is set to True only by explicit human
action in the curator queue. The API never returns a node where `curator_approved=False`
to the public frontend. No pipeline step sets this to True automatically.

**Exception being considered:** Purely computational nodes — percentile ranks, fiscal
gap components, MC scores — are deterministic derivations that don't require human
judgment. Current handling: these are `DERIVED` nodes; the computation pipeline sets
`curator_approved=True` automatically. This is a genuine exception to the principle and
needs a cleaner contract — possibly `requires_curator_review: bool` as a separate field
from `curator_approved`, where DERIVED nodes have `requires_curator_review=False`.

**Assumptions:**
1. Human curators are more reliable than automated checks for non-deterministic content.
   True for legal and evidence nodes. Questionable for simple statistical derivations.
2. The curator queue is responsive enough that new content reaches `curator_approved=True`
   within a reasonable time. No SLA is currently defined. Gap.

**Falsification:**
- If curator throughput becomes a bottleneck that prevents timely updates to legal nodes
  when legislation changes, the gate creates more harm than it prevents. Mitigation:
  track time-in-queue as a metric from Phase 4 onwards.

**Status:** SETTLED on the principle. PROVISIONAL on the DERIVED exception.

---

### SCHEMA-007: verified separate from curator_approved

**Phenomenon:** Two different things that look similar:
- `verified`: we have checked the source text and confirmed the statement matches.
- `curator_approved`: a human has reviewed the extraction and approved it.

These are independent. A node can be curator-approved but unverified (extracted by
Claude Code in Track C, approved, but source document not yet fetched for text
comparison). A node can be verified but not yet curator-approved (automated verification
pass succeeded, waiting in queue).

**Decision:** Both fields exist as separate booleans. MC confidence receives a 1.5×
alpha multiplier only when `verified=True`. `curator_approved` controls display only.

**Assumptions:**
1. The distinction matters for users. If a citizen is relying on a claim, knowing it
   was extracted and approved by a human is different from knowing it was confirmed
   against the actual source document.
2. The 1.5× verification multiplier is calibrated correctly. This was set by design
   choice, not by empirical calibration. See SCHEMA-019.

**Status:** SETTLED

---

## Part 2: Source Models

---

### SCHEMA-008: Five source types as a closed taxonomy (currently)

**Phenomenon:** Sources are not all the same kind of thing. A peer-reviewed paper, an
ONS API response, a Lex Graph commencement edge, a computed fiscal gap, and a minister's
Hansard statement have fundamentally different provenance models, quality signals, and
epistemic properties.

**Decision:** Five types: DOCUMENTARY, STRUCTURED_DATA, STRUCTURAL, DERIVED, TESTIMONY.
`SourceTypeEnum` is explicitly extensible — it is not declared as exhaustive.

**Alternatives:**
- Single flat source model with nullable fields. Rejected: STRUCTURAL sources don't
  have tiers. DERIVED sources don't have URLs. Forcing these into a flat model produces
  silent nulls in semantically important fields.
- Two types: document and dataset. Too coarse — loses the STRUCTURAL/TESTIMONY
  distinction that drives materially different MC priors.

**Known gaps in the current five types:**
- Sensor/observational data: a satellite image, a continuous air quality monitor,
  a CCTV timestamp. Not documentary, not structured_data in the API-response sense.
  Currently would be forced into STRUCTURED_DATA with a note. Flag when first encountered.
- Model output: a trained ML classifier's output about a node. Not derived from
  existing BASIS nodes — derived from external training data. DERIVED currently requires
  `input_node_ids` pointing to existing nodes, which model outputs don't have.
  Action: add `INFERRED` as a sixth type before any ML-assisted classification is
  introduced to the pipeline.
- Citizen-submitted evidence: a photograph, a letter, a recording. Closest to
  TESTIMONY but materially different — it's primary evidence, not a statement.
  Action: add `CITIZEN_EVIDENCE` as a seventh type before Phase 5 challenge system.

**Assumptions:**
1. The five types are sufficient for Phases 2-4 content. Currently true.
2. Type assignment is unambiguous for the vast majority of sources. Mostly true.
   Edge case: a government-commissioned academic report — is it DOCUMENTARY (T1 academic)
   or DOCUMENTARY (T2 government)? Decision: tier based on publisher, not commissioner.

**Status:** PROVISIONAL — two known extensions needed before Phase 5.

---

### SCHEMA-009: Tier lives on the citation edge, not the source

**Phenomenon:** Source quality is claim-relative, not source-absolute. ONS is T1 for
UK unemployment statistics. ONS is not authoritative — effectively irrelevant — for a
claim about housing disrepair case law.

**Decision:** `DocumentarySource` carries `default_tier` as a global quality signal.
The `citation_edge` between source and node carries an optional `claim_tier_override`
with mandatory justification when set. The MC engine uses `claim_tier_override` if
present, `default_tier` otherwise.

**Current state:** This decision is not yet implemented. The existing 172 sources in
`data/` have tier on the source, not on the citation edge. This is Phase 1 legacy.
Migration required before Phase 4 legal layer extraction.

**Alternatives:**
- Tier only on source, globally applied. The current state. Produces incorrect MC
  priors in cases of cross-domain citation — an IFS report cited for both a taxation
  claim (appropriate, T1) and a housing claim (potentially T3) gets T1 in both cases.
- Tier only on citation edge, no default. High annotation burden. Every citation
  requires explicit tier assignment. Impractical at scale.

**Assumptions:**
1. The `default_tier` correctly represents the source's quality for the majority of
   citations. True for single-domain sources. Questionable for general reports.
2. Curators will notice and override when a source is being cited outside its primary
   domain. No automated detection currently. Gap: add a CI check that flags when a
   source's `domain` field doesn't match the citing node's domain.

**Falsification:**
- If >20% of citation edges require an override, the default mechanism isn't doing
  useful work. Track this metric from Phase 4.

**Status:** PROVISIONAL — migration from source-tier to citation-tier required.

---

### SCHEMA-010: STRUCTURAL sources are not alpha=1.0 — alpha varies by registry

**Phenomenon:** A STRUCTURAL source is an authoritative registry record. But registries
differ in data quality, update frequency, and known error rates.

**Decision:** STRUCTURAL source alpha is assigned by registry from a lookup table, not
from the source type category. Default values (provisional, to be updated as evidence
accumulates):

```python
STRUCTURAL_ALPHA = {
    'lex_graph_commencement':    0.95,  # known partial commencement gaps
    'lex_graph_amendment':       0.98,  # high reliability, occasional lag
    'ons_nspl_postcode':         0.99,  # highly reliable, quarterly refresh
    'land_registry_title':       0.90,  # known lag on recent transactions
    'companies_house_active':    0.85,  # known data quality issues, stale directors
    'electoral_commission':      0.92,  # reliable for registered entities
    'ico_register':              0.93,  # reliable
    'fca_register':              0.94,  # reliable
    'charity_commission':        0.91,  # known gaps in small charities
}
```

These values are design choices based on documented data quality assessments for each
registry. They are not empirically calibrated — that would require comparing registry
data against ground truth, which we don't have. They should be treated as priors to
be updated as errors are discovered.

**Alternatives:**
- alpha=1.0 for all STRUCTURAL. The original decision. Falsified by known registry
  data quality problems — see companies_house and land_registry.
- alpha=0.95 flat for all STRUCTURAL. Better than 1.0 but hides material differences
  between registries.

**Assumptions:**
1. The alpha values in the lookup table are approximately correct as priors.
   These are informed guesses, not measurements. Flag for empirical calibration.
2. Registry quality is stable over time. False — Companies House data quality has
   deteriorated since the PSC register became mandatory. The lookup table needs
   versioning: `alpha_as_of: date`.

**Falsification:**
- Any discovered case where a STRUCTURAL source was wrong (e.g. a provision shown
   as in_force when it was repealed). Log as an error event. Update the alpha
   for that registry downward. Build the error log from Phase 4 onwards.

**Status:** PROVISIONAL — alpha values are priors not measurements.

---

### SCHEMA-011: Commencement status as a six-value enum

**Phenomenon:** A provision can exist in law but not be in force. It can be in force
for some people but not others, or in some regions but not others. A repeal can also
be enacted before it takes effect.

**Decision:** `commencement_status` uses six values:
`in_force`, `partially_in_force`, `not_commenced`, `prospectively_repealed`,
`repealed`, `unknown`.

- `partially_in_force`: in force in some jurisdictions or for some persons. Requires
  `commencement_notes` with plain English explanation. Displayed with prominent warning.
- `prospectively_repealed`: repeal enacted but not yet effective. Nodes flagged for
  imminent deprecation review.
- `not_commenced` and `repealed`: commencement gate blocks these entirely.
- `unknown`: displayed with disclaimer.

**Real-world driver for the extension:** Renters' Rights Act 2025. Section 2A is
prospective (not yet commenced), section 2B is partially commenced for England
but not Wales. The previous four-value enum could not represent either case.
These are live provisions affecting citizen rights right now.

**Resolves OQ-002:** No separate `commencement_condition` field needed. The six
values plus `commencement_notes` (free text) handle all encountered cases.
If date-triggered commencement (common in financial regulation) proves necessary,
add `commencement_date: date | None` as a separate field at that point.

**Assumptions:**
1. Lex Graph's commencement data is reliable (alpha=0.95 per SCHEMA-010).
2. `commencement_notes` will be legible to citizens — add to curator review checklist.

**Status:** SETTLED — OQ-002 resolved.

---

### SCHEMA-012: PRINCIPLE as a ninth legal position type

**Phenomenon:** Some legal norms operate as principles — they apply "as much as
possible" relative to competing considerations — rather than as binary rules.
Article 8 ECHR, proportionality, legitimate expectation.

**Original decision:** Add PRINCIPLE as a ninth node type with a `strength` field.

**Revised decision (April 2026):** DEFERRED. The `deontic_strength` field on
existing Hohfeldian nodes (ABSOLUTE, QUALIFIED, CONDITIONAL, DIRECTORY, ASPIRATIONAL)
handles 80% of the phenomenon without a new node type or additional Gemma
classification burden. A RIGHT node with `deontic_strength=QUALIFIED` captures
"this right applies unless outweighed by competing considerations" without requiring
a separate PRINCIPLE type.

Genuine constitutional balancing cases (full Article 8 proportionality assessments,
common law proportionality in planning and public law) are Phase 4b territory.
The richer deontic layer from the five-layer legal enrichment schema handles these
properly. Adding PRINCIPLE now as a simplified proxy would require migration in
Phase 4b anyway.

**Condition for revival:** If >10% of extracted legal nodes cannot be correctly
classified as any of the eight Hohfeldian types and the `deontic_strength` field
doesn't resolve the gap, revisit PRINCIPLE as a node type.

**Status:** DEFERRED to Phase 4b. Not rejected — distinction is real, timing is wrong.

---

## Part 3: Evidence Layer Nodes

---

### SCHEMA-013: FACT vs ASSUMPTION distinction

**Phenomenon:** Some statements are directly observable or measurable in the world.
Others require inference, interpretation, or projection.

**Decision:** FACT nodes have `source_id` pointing to a DOCUMENTARY or
STRUCTURED_DATA source that directly supports the statement. ASSUMPTION nodes have
`basis_fact_ids` — a list of FACT IDs that make the assumption plausible — plus a
`falsification_condition` field: what would disprove it.

The minimum one basis_fact_id constraint on ASSUMPTION is a schema-enforced check —
orphan assumptions (assumptions with no factual basis) fail Pydantic validation.

**Assumptions:**
1. The FACT/ASSUMPTION boundary is clear. It often isn't. "NHS waiting times have
   increased since 2019" — FACT (measurable, sourced). "Increased waiting times are
   primarily caused by underfunding" — ASSUMPTION (causal inference, not directly
   measurable). But "underfunding is a cause" might be established by controlled
   studies — in which case it could be a FACT.
   The boundary is determined by whether the statement can be directly sourced or
   requires interpretive inference. When ambiguous, the extractor should prefer FACT
   with a caveat in `extraction_notes` over ASSUMPTION.
2. `falsification_condition` is completable for all assumptions. True for well-formed
   assumptions. Some assumption statements resist falsification — these are the ones
   most likely to be wrong. If an extractor cannot write a falsification condition,
   the statement is probably not an assumption — it may be a POSITION or a CLAIM.

**Status:** SETTLED

---

### SCHEMA-014: FiscalMetadata and gap_role taxonomy

**Phenomenon:** Monetary claims in the evidence graph are heterogeneous — current
spending, additional needs, revenues, projections. The £44-146bn headline figure is
only meaningful if we distinguish which monetary nodes contribute to it.

**Decision:** `FiscalMetadata` as a nested Pydantic model on FACT, CLAIM, and POLICY
nodes. `gap_role` determines whether a node contributes to the computed fiscal gap.
The six gap_roles: `additional_need`, `baseline`, `position_only`, `summary`,
`uplift`, `target_total`. The fiscal self-test in CI recomputes the gap from gap_role
metadata and asserts it overlaps the stated £44-146bn range.

**Assumptions:**
1. The annual fiscal gap is the right frame for aggregation. It excludes one_off costs
   (e.g. Rwanda policy costs) and cumulative multi-year totals without amortisation.
   The current handling divides cumulative amounts by `horizon_years`. This is correct
   for comparing like-for-like annual costs but loses information about upfront
   capital requirements.
2. The six gap_roles are exhaustive. Currently true. Monitor when new domains added.
3. Amount units are normalised to bn_gbp for aggregation. m_gbp amounts are divided
   by 1000 before summing. pct_gdp amounts require a GDP figure — currently hardcoded
   at £2.3tn. This is a known approximation.

**Falsification:**
- GDP figure changes materially (>5%) — update the GDP constant and re-run CI.
- A new monetary node type that doesn't fit any gap_role — add a new role with
  documentation rather than forcing it into an existing category.

**Status:** SETTLED on structure. PROVISIONAL on GDP constant.

---

## Part 4: Edge Semantics

---

### SCHEMA-015: Evidence independence on SUPPORTS edges

**Phenomenon:** The MC noisy-OR formula for SUPPORTS edges assumes each supporting
source independently establishes the claim. Independent evidence compounds multiplicatively.
Correlated evidence does not.

**Decision:** `evidence_independent: bool` on every SUPPORTS edge. When `False`, the
MC engine uses additive aggregation (the strongest single source) rather than noisy-OR.
When `True`, noisy-OR applies.

**Default:** `evidence_independent=True`. This is the optimistic default — assumes
independence unless explicitly flagged as correlated. This is wrong in many cases
(multiple papers drawing on the same dataset). The correct default would be `False`
with explicit independence assertion, but that creates excessive annotation burden.
The current default produces overconfident scores in correlated source clusters.

**Immediate action required:** The existing 746 edges in `data/` all implicitly assume
independence. A manual audit of the top 20 highest-confidence CLAIM nodes is needed
to identify and flag the most consequential cases of correlated evidence before Phase 2b.

**Assumptions:**
1. Curators can reliably identify correlated evidence. This requires knowing the
   provenance of sources, which requires the source fetch pipeline to be working.
   Currently 39 sources unfetched — those edges cannot be audited for independence.
2. The additive (max-of-independent) formula is the right correction for correlated
   evidence. Debatable — it's conservative but ignores partial independence. This
   is a known simplification.

**Status:** PROVISIONAL — default is wrong, requires manual audit before Phase 2b.

---

### SCHEMA-016: Six evidence edge types

**Phenomenon:** Relationships between evidence nodes are not all the same. A source
that directly establishes a claim is different from one that undermines it, which is
different from one that the claim logically requires.

**Decision:** Six edge types with defined logical properties:

| Type | Logic type | Transitive? | Symmetric? | Notes |
|---|---|---|---|---|
| SUPPORTS | Epistemic | No | No | A→B→C does not mean A→C |
| CONTRADICTS | Epistemic | No | Yes | If A contradicts B, B contradicts A |
| DEPENDS_ON | Structural | Yes | No | If C depends on B, C inherits B's weakness |
| ENABLES | Deontic | No | No | A right enables a mechanism |
| COMPETES | Normative | No | Yes | Two policies competing for the same resources |
| SUPERSEDES | Temporal | No | No | Later evidence replaces earlier |

These properties are enforced in the MC engine — DEPENDS_ON propagates with weakest-
link semantics, SUPPORTS uses noisy-OR (with independence flag), CONTRADICTS applies a
discount, SUPERSEDES marks the earlier node as deprecated.

**Assumptions:**
1. Six types cover all meaningful relationships in the evidence layer. Currently true.
   Monitor: if extractors are using `extraction_notes` to describe relationships that
   don't fit a type, that's a signal a new type is needed.
2. The transitivity rules above are correct. SUPPORTS non-transitivity is the most
   important: a study that supports a hypothesis about mechanism A does not automatically
   support a downstream policy B that rests on A. This is enforced by the MC architecture
   (each edge has its own weight) rather than a hard rule.

**Status:** SETTLED on types and properties.

---

### SCHEMA-017: Explanation minimum length and blocklist

**Phenomenon:** Edge explanations are the mechanism by which "we show our working" is
made legible. A one-word explanation defeats the purpose.

**Decision:** Minimum 10 characters on `explanation` field. Regex blocklist rejects
template phrases: 'supports', 'related', 'depends on', 'see above', 'as noted', and
any explanation that merely restates the target node statement.

**Assumptions:**
1. 10 characters is the right minimum. It's a floor, not a target. An explanation of
   "X increases Y" is 12 characters and meaningless. The blocklist is doing more work
   than the length constraint.
2. The blocklist covers the main failure modes. Currently covers the cases observed in
   Phase 1 data. Extend as new patterns are discovered.

**Status:** SETTLED on principle. PROVISIONAL on specific thresholds.

---

## Part 5: Confidence Engine (MC)

---

### SCHEMA-018: Monte Carlo over analytical propagation

**Phenomenon:** Confidence propagates through the graph from source nodes to terminal
nodes via typed edges. We need a method that handles the mixed edge types (noisy-OR,
weakest-link, discount) in a unified framework.

**Decision:** Monte Carlo simulation: 10,000 samples per run, each sample propagates
confidence from FACT nodes upward using edge-type-specific rules. The distribution
of outcomes gives mean, std, p5, p95.

**Alternatives:**
- Analytical propagation: derive exact formulas for each edge type combination.
  Possible for simple chains. Intractable for general DAGs with mixed edge types.
- Bayesian network: principled, but requires specifying conditional probability
  tables for all node combinations. Too much specification overhead for 389 nodes.
- Simple average of upstream confidence. Rejected: loses the structural information
  that DEPENDS_ON edges should use weakest-link semantics.

**Assumptions:**
1. 10,000 samples is sufficient for stable estimates. Verified: variance <1% across
   runs with seed=42. For p5/p95 stability, 10K is the minimum. Could reduce to 5K
   for speed without material accuracy loss.
2. The graph is approximately a DAG (directed acyclic graph). Verified: 4 cycles
   exist in the current graph. All cycles involve POSITION nodes (political positions
   referencing each other). The MC handles cycles by capping propagation depth.
3. 25 seconds runtime is acceptable. True for 389 nodes. At 5,000 nodes (legal layer
   added), runtime will scale roughly linearly to ~4 minutes. Scope-limited propagation
   (within domain only in steady state) will be required before Phase 4.

**Status:** SETTLED on approach. PROVISIONAL on runtime scaling.

---

### SCHEMA-019: Source alpha values and the 1.5× verification multiplier

**Phenomenon:** Source quality determines the initial confidence anchor for FACT nodes.
A verified source should be weighted more heavily than an unverified one.

**Decision (current alpha table — provisional):**

```python
SOURCE_ALPHA = {
    # DOCUMENTARY
    ('DOCUMENTARY', 'T1', True, True):   0.95,  # T1, verified, citation>100
    ('DOCUMENTARY', 'T1', True, False):  0.75,  # T1, verified, citation<10
    ('DOCUMENTARY', 'T1', False, None):  0.85,  # T1, unverified
    ('DOCUMENTARY', 'T2', True, None):   0.85,  # T2, verified
    ('DOCUMENTARY', 'T2', False, None):  0.70,  # T2, unverified
    ('DOCUMENTARY', 'T3', None, None):   0.70,
    ('DOCUMENTARY', 'T4', None, None):   0.55,
    ('DOCUMENTARY', 'T5', None, None):   0.45,
    ('DOCUMENTARY', 'T6', None, None):   0.40,
    # STRUCTURED_DATA
    ('STRUCTURED_DATA', 'T1', None, None): 0.92,  # ONS, NHS Digital
    ('STRUCTURED_DATA', 'T2', None, None): 0.80,
    ('STRUCTURED_DATA', 'T3', None, None): 0.60,  # council CSVs
    # STRUCTURAL — by registry, see SCHEMA-010
    # DERIVED — no alpha, MC-propagated from inputs
    # TESTIMONY
    ('TESTIMONY', 'T3', None, None): 0.55,   # ombudsman, court
    ('TESTIMONY', 'T4', None, None): 0.45,   # minister, official
    ('TESTIMONY', 'T5', None, None): 0.35,   # citizen challenge
}

VERIFIED_MULTIPLIER = 1.5  # multiplier applied when verified=True for DOCUMENTARY
```

**These values are design choices, not measurements.** They were set to produce
intuitively correct outputs on the current 389-node corpus. They have not been
calibrated against ground truth. The following properties were used as informal
checks:
- NHS-F01 (7.6M waiting list, T2 ONS, verified) should score ~0.89 HIGH. ✓
- A LOW-verdict assumption should not exceed 0.50. ✓
- A T5 testimony source should not exceed 0.40. ✓

**Assumptions:**
1. The alpha values produce correctly-ordered confidence across node types. Currently
   true. No FACT node with a T5 source outscores one with a T1 source (holding
   other factors equal).
2. The 1.5× verification multiplier is appropriate. Arbitrary. It was chosen to
   produce a visible and meaningful difference between verified and unverified nodes
   without allowing verification alone to push a node to HIGH.

**Falsification:**
- Expert review of 20 random HIGH-confidence nodes that should obviously be HIGH.
   If any are obviously wrong, recalibrate.
- Expert review of 20 random LOW-confidence nodes that should obviously be LOW.
   Same.

**Status:** PROVISIONAL — requires calibration study.

---

### SCHEMA-020: Assumption contestability discount

**Phenomenon:** An assumption supported by many facts should not converge to certainty,
because it remains an assumption — an interpretive claim about unobserved states.

**Decision:** Post-noisy-OR, ASSUMPTION nodes receive a multiplicative discount keyed
to extraction-time confidence:

```python
ASSUMPTION_DISCOUNT = {
    'HIGH':   0.85,
    'MEDIUM': 0.70,
    'LOW':    0.50,
}
```

Even the strongest possible ASSUMPTION (all T1 verified sources, HIGH verdict) cannot
exceed 0.85 × (near-1.0 noisy-OR) ≈ 0.85.

**Alternatives:**
- Flat discount (0.80) for all assumptions. Previous version. Rejected: conflates
  "we have strong evidence for this assumption" with "we don't".
- No discount. The noisy-OR produces near-certainty for well-supported assumptions.
  This is wrong — "the housing benefit cap causes homelessness" is better supported
  by evidence than "the cap doesn't", but it's still not certain in the way that
  a direct measurement is.

**Assumptions:**
1. The extraction-time verdict (HIGH/MEDIUM/LOW) reliably reflects contestability.
   Partially true. The verdict was assigned by the extractor, not by a domain expert.
   In Phase 1, some LOW-verdict assumptions should probably have been MEDIUM, and
   vice versa. The discount is only as good as the verdict assignment.
2. The discount values (0.85, 0.70, 0.50) are approximately correct.
   Same status as alpha values above — provisional.

**Status:** PROVISIONAL — values need calibration.

---

## Part 6: External Dependencies

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

---

### SCHEMA-022: Corpus scoping via ego network queries

**Phenomenon:** For each issue domain, we need to identify which Lex Graph provisions
are relevant. Manual selection misses amending SIs. Full import is impractical.

**Decision:** Use ego network queries from anchor Acts (e.g. Housing Act 2004 for the
housing domain), 2 hops out on citation and amendment edges, filtered by entity type
(tenant, homeowner, local_authority, etc.).

**Assumptions:**
1. The 2-hop radius captures all materially relevant provisions. Untested. Some
   relevant provisions may be reachable only via 3+ hops (e.g. a provision in
   an amending Act that itself amends a cross-referenced Act).
2. Entity type filtering correctly scopes the corpus. The filter uses text matching
   on provision content — "tenant OR homeowner" in the full_text. This may miss
   provisions that use different terminology ("occupier", "lessee").

**Action:** Run pilot ego network query for Housing Act 2004 before Phase 4 begins.
Manually check sample of 2-hop provisions for relevance. Check sample of 3-hop
provisions to see if the 2-hop boundary is losing material content.

**Status:** PROVISIONAL — requires pilot before Phase 4.

---

## Part 7: Open Questions

These are unresolved design decisions that will need to be addressed before the
phases indicated.

| ID | Question | Blocking | Phase |
|---|---|---|---|
| OQ-001 | Should claim_confidence and instantiation_confidence be separate fields? | No | 3 |
| OQ-002 | ~~What format for conditional commencement notes?~~ **RESOLVED** by SCHEMA-011 revision — six-value enum + commencement_notes free text. | — | — |
| OQ-003 | How should PRINCIPLE nodes interact with MC propagation? Weight ≠ probability. (Deferred with SCHEMA-012 — not blocking Phase 4.) | No | 4b |
| OQ-004 | Should `evidence_independent` default to True or False? Current default (True) is overconfident. | No | 2b |
| OQ-005 | ~~How do we handle provisions that apply to England and Wales jointly?~~ **RESOLVED** by SCHEMA-003 revision — `england_and_wales` added to `JurisdictionEnum` in `base_schema.py`. | — | — |
| OQ-006 | What is the correct alpha for INFERRED sources (ML classifier outputs)? | No | 5 |
| OQ-007 | How does `curator_approved` work for DERIVED nodes computed automatically? | No | 3 |
| OQ-008 | Inter-rater agreement study: are HIGH/MEDIUM/LOW consistently assigned across extractors? | No | 3 |
| OQ-009 | GDP constant for pct_gdp unit conversion — should this be a dynamic source? | No | 2b |
| OQ-010 | What happens when Lex Graph provision IDs change? Recovery procedure needed. | Yes | 4 |

---

### SCHEMA-023: Legal consistency flags as CI checks 7-8

**Phenomenon:** Single-node verification (is this extraction correct?) misses structural
problems between nodes (is this legal structure coherent?). A duty that cannot be
enforced is not just an extraction gap — it may be a genuine flaw in the legislation
that citizens need to know about.

**Decision:** Two database queries added as CI check 7 and 8, running against the
legal layer on every commit once legal nodes exist.

**Check 7 — ENFORCEMENT_GAP:**
```sql
SELECT n.id, n.statement, n.domain
FROM legal_nodes n
WHERE n.node_type = 'DUTY'
AND NOT EXISTS (
  SELECT 1 FROM legal_edges e
  JOIN legal_nodes m ON m.id = e.to_id
  WHERE e.from_id = n.id
  AND e.edge_type = 'ENFORCED_BY'
  AND m.node_type = 'MECHANISM'
)
AND n.curator_approved = true;
```
A DUTY node with no reachable MECHANISM via ENFORCED_BY is either an extraction
error (mechanism not yet extracted) or a genuine enforcement gap in the law. Both
findings are valuable. The CI check surfaces them; the curator decides which it is.

Housing Act 2004 example: category 2 hazards create no enforceable obligation on
local authorities — there is a power to act but no duty. The ENFORCEMENT_GAP check
surfaces this as a known finding, not an extraction error.

**Check 8 — MISSING_CORRELATIVE:**
Hohfeld requires correlatives — every RIGHT has a corresponding DUTY, every POWER
has a corresponding LIABILITY. Absence may be an extraction gap or a legal incoherence.

```sql
SELECT n.id, n.node_type, n.statement
FROM legal_nodes n
WHERE n.node_type = 'RIGHT'
AND NOT EXISTS (
  SELECT 1 FROM legal_nodes n2
  WHERE n2.node_type = 'DUTY'
  AND EXISTS (
    SELECT 1 FROM legal_edges e
    WHERE (e.from_id = n.id AND e.to_id = n2.id)
    OR (e.from_id = n2.id AND e.to_id = n.id)
  )
)
AND n.curator_approved = true;
-- Repeat for POWER/LIABILITY pairs
```

**What's deferred:** CIRCULAR_DEFEASIBILITY and TEMPORAL_IMPOSSIBILITY require
the five-layer legal enrichment schema (Phase 4b). AGENT_UNRESOLVED requires the
institutional power typing layer. These are not implementable against the current
LegalNode schema.

**Assumptions:**
1. The queries return a manageable number of results. At 200 nodes (Phase 4 target),
   maybe 10-20 flagged items per run. Acceptable. At 5,000 nodes, needs batching.
2. ENFORCEMENT_GAP is an informative finding, not a blocking error. Correct — a
   genuine enforcement gap in legislation is a civic finding worth surfacing. Only
   extraction errors should block; legal gaps should be reported.

**Status:** SETTLED for checks 7-8. DEFERRED for checks 9-12 (enrichment layers).

---

*Version: 0.3 — updated April 2026: SCHEMA-003 settled (OQ-005 resolved, `england_and_wales` added), OQ-003 aligned to DEFERRED/Phase 4b, duplicate OQ-002 row removed, SCHEMA-009 citation_edge model clarified (see roadmap §Source Taxonomy). v0.2 added SCHEMA-011 (six-value commencement, OQ-002 resolved), SCHEMA-012 DEFERRED, SCHEMA-023 (legal consistency CI checks 7 and 8).*
*Next review: before Phase 4 legal extraction begins*
*Owner: Harry Weston*
