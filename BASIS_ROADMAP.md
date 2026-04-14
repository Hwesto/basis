# BASIS: Comprehensive Platform Roadmap

> *"We show our working."*
> A civic operating system — connecting evidence, law, local data, and action into a single navigable infrastructure for democratic participation.

---

## Vision

BASIS is not a policy website, a complaint portal, or a legal database. It is the connective tissue between all three. The core insight: citizens lack agency not because the data doesn't exist, not because their rights don't exist, and not because the mechanisms to act don't exist — but because no structured layer connects them.

Enter your postcode. See how your area compares nationally across housing, health, policing, education, planning. Click any issue. See the evidence base, the legal rights that apply, and the specific steps to take — from a council email through to tribunal application or judicial review — with templates pre-populated from your local data and the relevant statute.

Every claim is sourced. Every legal right is cited. Every action pathway is evidence-backed. The system evolves: outcomes feed back into the graph, strengthening routes that work and flagging those that don't. Evidence challenges update confidence scores. New legislation triggers re-extraction.

The theory of change: you raise the cost of governing badly, one evidenced citizen interaction at a time.

---

## Architecture Overview

### The Core Principle: Schema-First, Domain-Agnostic

The single most important architectural decision in BASIS is this: **the domain is irrelevant. The pattern is identical.**

A policy claim with a confidence score, sourced from a specific document, with a tier, verified against source text, and connected to other nodes via typed edges — is the same structure as a legal right sourced from a statute, or a local crime metric sourced from Police.uk, or a citizen action outcome. The entity types differ. The schema contract does not.

This means BASIS does not have a data model per layer. It has **one data model** — `BaseNode` — that every entity in the system is an instance of. Evidence nodes, legal nodes, local data nodes, action nodes, template nodes, FOI records — all subclasses of the same base, inheriting the same cross-cutting fields: source traceability, confidence, curator gate, extraction provenance, jurisdiction, domain.

The practical consequence: the extraction pipeline, the confidence propagation engine, the curator queue, the CI validation, and the cross-layer edge table are all **written once**. Each new layer is an extension, not a rebuild. `FactNode(BaseNode)` with three additional fields. `LegalRightNode(BaseNode)` with five additional fields. The work at the root pays dividends across every phase.

**This also means `domain` is a typed enum, not a free-text field.** Domain-specific assumptions belong on subclasses, not on the base. The base should be clean enough that you could point the engine at any structured knowledge domain — policy, law, science, anything — and it would hold.

```python
class BaseNode(BaseModel):
    id:                str
    node_type:         str              # constrained to allowed types by subclass
    statement:         str              # one declarative sentence
    source_id:         str | None       # references sources table
    source_loc:        str | None       # section/page/paragraph
    confidence:        Literal['HIGH','MEDIUM','LOW'] | None
    computed_confidence: dict | None    # MC output: mean, std, p5, p95, label
    domain:            DomainEnum       # typed, extensible enum
    jurisdiction:      list[JurisdictionEnum] | None
    verified:          bool             # confirmed against source text
    curator_approved:  bool             # hard gate: never shown until true
    extraction_run_id: str              # which pipeline run produced this
    created_at:        datetime
    updated_at:        datetime
```

Every node type inherits this contract. Every domain adds its own fields on top. **The curator queue, CI validator, and confidence engine operate against `BaseNode` — they never need to know what kind of node they're handling.**

---

### Knowledge Graph Layers

```
LAYER 0: LEX GRAPH (external, i.AI / National Archives)
  820K provision nodes, 2.2M structural edges
  Citations, amendments, cross-references between statutes (1267–present)
  Hosted on Hugging Face. Accessed via Lex API MCP (free, 1K req/hr)
  BASIS does not rebuild this. BASIS sits on top of it.

LAYER 1: EVIDENCE LAYER (existing, 389 nodes)
  FactNode / AssumptionNode / ClaimNode / PolicyNode / PositionNode
  All BaseNode subclasses. 12 domains. MC confidence. Fiscal gap computation.

LAYER 2: LEGAL LAYER (to build — Hohfeldian semantic overlay on Layer 0)
  LegalRightNode / DutyNode / MechanismNode / EscalationNode / PrecedentNode
  All BaseNode subclasses. lex_provision_id foreign key links to Lex Graph.
  Amendment tracking inherited from Lex Graph edges.

LAYER 3: LOCAL DATA LAYER (to build)
  AreaMetricNode — BaseNode subclass with area_code, metric_id, percentile
  Time-series, comparator-linked, API-refreshed

LAYER 4: ACTION LAYER (to build)
  TemplateNode / MechanismNode / SubmissionNode / OutcomeNode
  All BaseNode subclasses. Outcomes feed back into confidence propagation.

UNIFIED INFRASTRUCTURE (written once, applies to all layers)
  curator_queue     — one table, node_type field distinguishes
  extraction_runs   — one table, all pipeline runs logged here
  cross_layer_edges — typed edges between any two nodes regardless of layer
  MC engine         — type-aware, single propagation algorithm
  CI validator      — one schema check against BaseNode + subclass rules
  Google Custom Search + Semantic Scholar — source discovery and quality
    signals at ingestion, before any extraction runs
```

---

### Source Model Taxonomy

The single most common architectural mistake in knowledge systems is treating all sources as the same thing. They are not. A peer-reviewed paper, an ONS API response, a Lex Graph amendment edge, a computed fiscal gap, and a minister's Hansard statement are five categorically different epistemic objects. Applying a single T1–T6 tier scale to all five forces category errors and produces false confidence signals.

BASIS uses five source types, each with its own provenance model, quality signals, and MC confidence prior. All are instances of `BaseSource`. The `source_type` field is the discriminator.

```python
class BaseSource(BaseModel):
    source_id:    str
    source_type:  SourceTypeEnum   # the discriminator
    domain:       DomainEnum | None
    jurisdiction: list[JurisdictionEnum] | None
    created_at:   datetime
    updated_at:   datetime
```

**DOCUMENTARY** — human-authored documents: reports, papers, statutes, guidance, manifestos

```python
class DocumentarySource(BaseSource):
    source_type:    Literal['DOCUMENTARY']
    title:          str
    author:         str | None
    publisher:      str
    published_date: str
    url:            str | None
    doi:            str | None
    tier:           Literal['T1','T2','T3','T4','T5','T6']
    tier_justification: str              # mandatory one sentence
    full_text:      str | None           # cached, nullable
    content_hash:   str | None           # sha256; change = re-verify
    fetched_at:     datetime | None
    # academic quality — from Semantic Scholar (free API, no key required)
    # populated at ingestion for any source with DOI; None for grey lit
    citation_count:              int | None
    influential_citation_count:  int | None
    citation_velocity:           float | None  # weighted 3-year average
    venue:                       str | None
    open_access:                 bool | None
```

Tier assignment happens before extraction from real data: DOI → Semantic Scholar → `citation_count` + `venue` → suggested tier. gov.uk domain → T1/T2 by definition. Think tanks → manual assignment with justification. Grey literature → T4/T5 default, upgrade requires citation evidence. The extractor receives a pre-validated source; it does not make tier judgements inside the prompt.

**STRUCTURED_DATA** — datasets and API responses: time-series, statistical releases, registers

```python
class StructuredDataSource(BaseSource):
    source_type:      Literal['STRUCTURED_DATA']
    provider:         str              # 'ONS', 'police.uk', 'land_registry'
    dataset_id:       str
    metric_id:        str | None
    period_start:     date | None
    period_end:       date | None
    methodology_url:  str | None
    provider_tier:    Literal['T1','T2','T3']  # narrower range; T4-T6 don't apply
    api_endpoint:     str | None
    last_refreshed:   datetime | None
```

No full_text. No author. No T4–T6 — a structured dataset from ONS is either a methodologically sound T1/T2 source or it's not a source. Provider tier is assigned by whitelist: ONS, NHS Digital, DWP Stat-Xplore → T1. Police.uk, Land Registry → T2. Council CSVs → T3 with methodology flag.

**LEGISLATIVE_STRUCTURAL** — Lex Graph edges and provision attributes: amendments, citations, commencements, repeals

```python
class LegislativeStructuralSource(BaseSource):
    source_type:          Literal['LEGISLATIVE_STRUCTURAL']
    lex_provision_id:     str
    edge_type:            Literal['citation','amendment','cross_reference',
                                  'commencement','repeal']
    related_provision_id: str | None
    recorded_date:        date | None
    # No tier. Structural sources have certainty, not tier.
    # A commencement edge either exists or it doesn't.
    # MC confidence alpha = 1.0 on the structural fact itself.
```

This is the epistemically distinct source type. Lex Graph's structural edges are records of legal events — not claims about the world that require quality assessment. They are definitionally true within the legal system. Treating them as T1 documents is wrong: T1 implies "well-researched document we trust highly." `LEGISLATIVE_STRUCTURAL` sources are a different category entirely. The commencement status of a provision, the amendment history of a section, the citation graph connecting Acts — these have `alpha = 1.0` in the MC engine. The uncertainty is in the semantic extraction on top, not in the structural fact.

**DERIVED** — computations from other nodes: fiscal gap, MC confidence scores, percentile ranks, structural stability scores

```python
class DerivedSource(BaseSource):
    source_type:        Literal['DERIVED']
    computation_id:     str       # 'FISCAL_GAP_V3', 'MC_CONF_RUN_42'
    algorithm_version:  str
    input_node_ids:     list[str]
    computed_at:        datetime
    # No tier, no fetch, no author.
    # Quality = quality of inputs, already captured by MC propagation.
```

Derived sources have no independent quality signal — their confidence is fully inherited from their inputs through MC propagation. Assigning a tier to a computed fiscal gap is meaningless; the MC engine already captures this.

**TESTIMONY** — stated positions and submissions: Hansard speeches, inquiry evidence, challenge submissions, FOI responses, ombudsman rulings

```python
class TestimonySource(BaseSource):
    source_type:  Literal['TESTIMONY']
    actor:        str
    actor_type:   Literal['minister','mp','official','expert',
                          'citizen','ombudsman','court']
    date:         date
    context:      str    # 'hansard_debate', 'select_committee',
                         # 'inquiry_submission', 'foi_response'
    verbatim_ref: str | None   # Hansard column, committee ref etc.
    tier:         Literal['T3','T4','T5']  # testimony is never T1/T2
```

Testimony records what someone said, not what the evidence shows. An ombudsman ruling is T3. A minister's claim is T4. A citizen challenge submission is T5 until supported by a DocumentarySource. The tier ceiling of T3 is a hard constraint in the schema.

**MC confidence priors by source type**

```
DOCUMENTARY  T1, citation_count > 100, influential > 5  → alpha 0.95
DOCUMENTARY  T1, citation_count < 10                    → alpha 0.75
DOCUMENTARY  T2                                         → alpha 0.85
DOCUMENTARY  T3                                         → alpha 0.70
DOCUMENTARY  T4-T6                                      → alpha 0.40–0.55
STRUCTURED_DATA  provider_tier T1 (ONS, NHS Digital)    → alpha 0.92
STRUCTURED_DATA  provider_tier T2                       → alpha 0.80
STRUCTURED_DATA  provider_tier T3 (council CSV)         → alpha 0.60
LEGISLATIVE_STRUCTURAL (any edge type)                  → alpha 1.0
DERIVED                                                 → no alpha (MC-propagated)
TESTIMONY    T3 (ombudsman, court)                      → alpha 0.55
TESTIMONY    T4 (minister, official)                    → alpha 0.45
TESTIMONY    T5 (citizen challenge)                     → alpha 0.35
```

**Source discovery**

For finding better sources for unverified FACTs and challenge evaluation: Google Custom Search API restricted to an authoritative domain whitelist. Google's PageRank is not the quality signal — the whitelist is. Google is used as a filtered URL fetcher that returns `DocumentarySource` candidates. Semantic Scholar is queried for any candidate with a DOI to populate academic quality fields before the source is accepted.

---

### Unified Extraction Pipeline

One pipeline. Every node type is an instance of it. Source type determines the entry path.

```
Any input
    ↓
SOURCE TYPE ROUTING
  Has DOI / academic URL?  → DocumentarySource path
    → Semantic Scholar API → citation_count, venue, influential_flag
    → Tier auto-assigned from signals; human can override
  gov.uk / ons.gov.uk domain?  → DocumentarySource, tier = T1/T2
  ONS / Police.uk / NHS API response?  → StructuredDataSource path
    → provider_tier from whitelist
  Lex Graph provision / edge?  → LegislativeStructuralSource path
    → alpha = 1.0, no tier debate, commencement gate runs first
  Computed output?  → DerivedSource path
    → no external ingestion, provenance = algorithm + input_node_ids
  Hansard / FOI / submission?  → TestimonySource path
    → tier ceiling T3
  Source validated and written to sources table before extraction begins
    ↓
Node type classification (Haiku, cheap):
  What BaseNode subclasses does this source produce?
    ↓
Gemma 4 26B MoE — Pydantic-constrained extraction
  response_mime_type = "application/json"
  response_schema = <appropriate BaseNode subclass>
  Guaranteed schema-conformant output. Schema violations fail the call.
    ↓
Gemini Flash cross-check (~$0.001/check):
  "Does this extraction match what the source says?"
  pass  → curator_queue (needs_review: true)
  fail  → curator_queue (flagged: true, reason: ...)
    ↓
curator_queue (one table, all node types, source_type visible)
    ↓
Claude Code session (Max plan, on-demand):
  Supabase MCP → read queue batch
  Lex MCP → pull provision text for LegislativeStructuralSource nodes
  Semantic Scholar / Google → pull source text for DocumentarySource nodes
  Claude judges: approve / reject / escalate
  Supabase MCP → write decisions back
    ↓
node_registry → MC confidence propagation (source_type-aware priors) → frontend
```

Economics: Gemma free tier (1K req/day) for extraction. Gemini Flash (~$0.001/check) for cross-check. Semantic Scholar free (no key required). Claude on existing Max plan for validation. Cash cost in steady state: effectively £0.

---

### Hohfeldian Legal Schema

Every legal relationship decomposes into four correlative pairs:

| Pair | Node types | Example |
|---|---|---|
| Right ↔ Duty | RIGHT, DUTY | Right to habitable dwelling / landlord's duty to repair |
| Power ↔ Liability | POWER, LIABILITY | Council power to issue improvement notice / landlord liability |
| Privilege ↔ No-right | PRIVILEGE | Privilege to complain; no one has a right to prevent it |
| Immunity ↔ Disability | IMMUNITY | Immunity from retaliatory eviction during complaint |

Legal node types (all BaseNode subclasses): RIGHT, DUTY, POWER, LIABILITY, PRIVILEGE, IMMUNITY, REGULATORY_BODY, MECHANISM, EVIDENCE_REQUIREMENT, ESCALATION_PATH, PRECEDENT. STATUTE is replaced by `lex_provision_id` — a foreign key to Lex Graph's provision nodes rather than a duplicated node type.

**On PRINCIPLE nodes:** An earlier design proposed a ninth node type for weight-based norms (ECHR proportionality, legitimate expectation). Decision: deferred. The `deontic_strength` field on existing Hohfeldian nodes (ABSOLUTE, QUALIFIED, CONDITIONAL, DIRECTORY, ASPIRATIONAL) handles 80% of the phenomenon without a new node type or additional Gemma classification burden. Genuine constitutional balancing cases (full Article 8 proportionality assessments) are Phase 4b territory once the basic Hohfeldian layer is validated. Revisit after 200+ legal nodes extracted.

---

## Data Sources

### Tier 1 — Live APIs, immediate integration

| Source | Data | Notes |
|---|---|---|
| ONS Geography API | Postcode → ward/constituency/LA | Free, REST |
| Police.uk API | Crime stats by postcode | Free, real-time |
| Parliament API | Bills, MPs, divisions, committees, Hansard | Free, REST + SPARQL |
| TheyWorkForYou | MP voting records, speeches, responsiveness scores | Free API |
| CQC API | Care home/hospital ratings by area | Free, REST |
| Companies House API | Business data, director networks | Free, REST |
| Land Registry | Property prices by postcode | Free, REST |
| DWP Stat-Xplore | Benefits claimants by area | Free, REST |
| Ofsted API | School inspection ratings | Free |
| NHS Digital / NHSE API | GP data, waiting times by ICS | Mixed quality |
| Environment Agency | Flood risk, permits, pollution events | Free |
| TfL / transport APIs | Where available, transport disruption data | City-level |

### Tier 2 — Structured bulk data, needs pipeline

| Source | Data | Format |
|---|---|---|
| Legislation.gov.uk | Full statute text with amendments | XML/HTML (no formal API, well-structured) |
| DLUHC data | Planning permissions, housing, council tax | CSV/Excel |
| HMRC statistics | Tax receipts, reliefs by area | CSV |
| DfE | School performance, SEND, exclusions | CSV |
| NHS reference data | Waiting times, prescribing, diagnostics | CSV/Excel |
| Council transparency | Spending >£500, contracts, senior salaries | CSV (inconsistent per council) |
| HESA | Higher education data | CSV |
| OECD / World Bank | International comparisons for benchmarking | API + bulk CSV |

### Tier 3 — Unstructured, LLM extraction required

| Source | Data | Challenge |
|---|---|---|
| Gov.uk guidance documents | Departmental guidance on applying law | PDF/HTML, no standard structure |
| BAILII / National Case Reports | Court decisions, precedent | HTML, highly variable |
| Council meeting minutes | Local decisions, debates, votes | PDF, no standard format |
| Public inquiry transcripts | Evidence sessions, consultations | PDF, massive volume |
| FOI disclosures | Released datasets and correspondence | No standard format |
| i.AI LEX project | Structured legal database (if accessible) | TBC — investigate API/export |
| International pilots | What other countries have built/done | Reports, varied |
| Inspection reports (Ofsted, CQC) | Narrative findings | PDF |

### Source Refresh Cadence

| Cadence | Sources |
|---|---|
| Real-time / daily | Police.uk, Parliament API, TheyWorkForYou, NHS waiting estimates |
| Weekly | ONS data releases, CQC updates, new legislation (legislation.gov.uk RSS) |
| Monthly | Council spending, DfE, HMRC, DLUHC |
| Quarterly | Ofsted, HESA, international benchmarks |
| On-change triggers | Legislation.gov.uk RSS, Parliament bills tracker, gov.uk guidance change monitoring |

---

## Action Channels

Every issue in the system maps to one or more of these output mechanisms:

| Channel | Legal basis / trigger | Template type |
|---|---|---|
| Council complaint letter | Statutory complaint procedure | Formal letter citing relevant statute + local data |
| MP constituency casework | Any issue in their constituency | Constituent letter with evidence summary |
| MP surgery referral | Physical meeting request | Referral letter with case summary |
| Ombudsman complaint | Post-exhaustion of council process | Ombudsman form with timeline |
| Parliamentary petition | Any issue, 10k → debate response | Petition text with evidence base |
| Select committee evidence | Open calls, oral/written | Evidence submission |
| Public inquiry submission | Planning, policy inquiries | Structured evidence submission |
| FOI request | s.1 Freedom of Information Act 2000 | FOI letter, tailored to body |
| EIR request | Environmental data specifically | Regulation 5 EIR 2004 letter |
| Section 11 / HHSRS notice | Housing disrepair | Pre-action repair notice |
| Pre-action protocol letter | Legal escalation (housing, clinical) | Letter Before Action with case law |
| Tribunal application | Benefits, employment, immigration, housing | Tribunal form with grounds |
| Regulatory body complaint | CQC, Ofsted, FCA, etc. | Regulator-specific complaint form |
| Legal aid referral | Eligible cases | Referral pack for solicitor/clinic |
| Crowdfunded group action | Systemic issue, many affected | Case summary + CrowdJustice / CLS format |
| Judicial review application | Unlawful public body decision | Pre-action protocol letter + grounds |

---

## Phase Roadmap

---

### COMPLETED — Phase 0: Manifesto Seed

**What it delivered:** A public, shareable demonstration. Single-link proof that "we show our working" means something: every claim in the manifesto has a visible source, tier, and confidence. Evidence graph explorer. GitHub Pages deployment.

**Status:** ✅ Live at hwesto.github.io/basis

---

### Foundation — schema_decisions.md + base_schema.py + source_models.py (prerequisite for all phases)

**Three files. Written in this order. The contract everything is built against.**

`schema_decisions.md` comes first. Before any code. Every node type, edge type, and confidence parameter has an entry recording: the phenomenon it represents, what we chose, alternatives considered, assumptions made, and what would cause us to revise. This is the manifesto applied to the schema itself — every design choice is a claim that needs a source and reasoning. Without it, when Gemma makes extraction errors you can't tell whether it's a model failure or a schema ambiguity. When a legal challenge surfaces a case the schema can't handle, you don't know which assumption is being violated.

`base_schema.py` then implements what the decisions file specifies. `source_models.py` implements the five source type subclasses with MC alpha values and type-specific validation rules.

**Key decisions documented in schema_decisions.md (v0.1):**

- **SCHEMA-001:** Single BaseNode root class — one curator queue, one CI validator, one MC engine. Domain-specific fields on subclasses only.
- **SCHEMA-002:** DomainEnum typed — free-text domain fields rejected at validation.
- **SCHEMA-003:** JurisdictionEnum — requires `england_and_wales` extension before Phase 4.
- **SCHEMA-004:** Confidence categorical (HIGH/MEDIUM/LOW) — false precision argument against decimal scores upheld.
- **SCHEMA-006:** curator_approved as hard gate — DERIVED node exception requires cleaner contract (OQ-007).
- **SCHEMA-009:** Tier lives on citation edge, not source — migration from Phase 1 source-level tier required.
- **SCHEMA-010:** STRUCTURAL source alpha by registry, not by category — values are provisional priors, not measurements.
- **SCHEMA-011:** Commencement status as six-value enum — `in_force_partial`, `in_force_conditional` added.
- **SCHEMA-012:** PRINCIPLE as ninth legal position — weight-based norms that can't be encoded as binary Hohfeld.
- **SCHEMA-015:** Evidence independence flag on SUPPORTS edges — current default (True) is overconfident; manual audit of top 20 high-confidence CLAIMs required before Phase 2b.
- **SCHEMA-019:** MC alpha values are design choices, not measurements — provisional, require calibration study.
- **SCHEMA-020:** Assumption contestability discount (HIGH→0.85, MEDIUM→0.70, LOW→0.50) — provisional values.
- **SCHEMA-021:** Lex Graph as reference table — principal external dependency risk documented.

**10 open questions** requiring resolution before specific phases — see schema_decisions.md §Part 7.

**Immediate actions before any further extraction:**
1. Manual audit of top 20 high-confidence CLAIM nodes for correlated evidence (SCHEMA-015)
2. Validate all 389 existing nodes against BaseNode — every mismatch is a known gap
3. Validate all 172 sources against BaseSource — identify tier-on-source instances requiring migration
4. Resolve OQ-005 (england_and_wales jurisdiction) before Phase 4 begins

**Status:** ⏳ schema_decisions.md v0.1 written. base_schema.py and source_models.py to follow.

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

### Legislation Accountability Audit (schedulable after Phase 2b)

**What it is:** A standalone deliverable — no new schema, no new pipeline — that answers the question nobody has answered systematically: did major legislation achieve what it said it would?

Explanatory notes in Lex Graph record what Parliament was told each Act would do. The evidence layer records what actually happened. The gap between the two is computable with existing infrastructure.

**Why it comes here:** It's the first real proof that the Lex integration works in practice before committing to the full Phase 4 build. It generates press and select committee attention before the local data layer exists. It demonstrates the platform's core claim — that policy assertions can be checked against evidence — in the most concrete form possible.

**Acts to start with (priority order):**

| Act | Year | What was promised | Outcome data available |
|---|---|---|---|
| Water Act | 1989 | Privatisation would drive investment and efficiency | Ofwat performance data, sewage spill records, price indices |
| NHS & Community Care Act | 1990 | Internal market would improve efficiency and patient choice | NHS waiting times, satisfaction data |
| Housing Act | 1988 | Deregulation would increase supply and improve conditions | DLUHC housing supply, EHS conditions data |
| Welfare Reform Act | 2012 | UC would simplify the system and increase work incentives | DWP UC data, employment outcomes, food bank data |
| Health and Social Care Act | 2012 | Clinical commissioning would improve outcomes and reduce costs | NHS outcomes data, administrative cost data |
| Housing and Planning Act | 2016 | Starter Homes and Right to Buy extension would increase ownership | DLUHC ownership data, Starter Homes delivery |
| Environment Act | 2021 | Legally binding targets would restore nature | ONS natural capital, EA water quality |

**What the output looks like:** For each Act, a structured comparison: stated predictions from the explanatory note, measured outcomes from the evidence layer, verdict (achieved / partially achieved / not achieved / too early to tell), confidence score on the verdict, and sources.

Presented on the platform as a dedicated section. Each Act generates a shareable card. The aggregate scorecard — "of the last 40 years of major legislation, here is how often Parliament's stated intentions were achieved" — is the headline.

**What it needs:** Lex API calls for explanatory notes (available now). Evidence nodes already in the graph for most domains. Gap-filling via targeted source fetch where outcome data is missing. Claude Code sessions for structured comparison. No new schema. No new tables. No new pipeline.

**Estimated effort:** 2–4 weeks depending on source gaps. Schedulable as soon as Phase 2b is deployed. Does not block Phase 3.

---

### Phase 3: Local Data Layer

**Objective:** Connect national evidence to local reality. Enter a postcode; see your area.

**The core UX:** Postcode → constituency + council + ward resolver → dashboard showing your area's metrics vs national averages across all 12 domains. Every metric links back into the evidence graph ("your area's NHS waiting time is 1.4× the national average → this is what the evidence says about NHS funding → this is what you can do").

**3.1 Geography resolution**

- ONS Geography API: postcode → LSOA → ward → constituency → local authority → ICS
- Postcode lookup table (ONS NSPL): ~2.7m postcodes, refreshed quarterly
- Jurisdiction routing: England / Wales / Scotland / NI — determines which legal framework applies downstream
- Store resolved geography on user profile (optional, privacy-preserving)

**3.2 Core metric integrations (launch set)**

| Domain | Metric | Source | Granularity |
|---|---|---|---|
| Health | GP wait times, A&E performance | NHS Digital | ICS / LA |
| Health | Hospital waiting list size | NHSE | ICS |
| Crime | Crime rates by category | Police.uk | Ward / LSOA |
| Education | School Ofsted ratings | Ofsted | School / LA |
| Education | GCSE/A-Level outcomes | DfE | School / LA |
| Housing | Average house price | Land Registry | Ward / LA |
| Housing | Planning permission rates | DLUHC | LA |
| Housing | Council housing stock | DLUHC | LA |
| Benefits | Claimant count | DWP Stat-Xplore | LA / ward |
| Environment | Air quality index | DEFRA | LA |
| Environment | Flood risk areas | Environment Agency | LSOA |
| Council | Spending per head | Council transparency | LA |
| Council | Council tax level | DLUHC | LA |
| Council | CQC-rated care homes | CQC | LA |

**3.3 Local data schema (Supabase additions)**

Each `area_metric` row references a `StructuredDataSource` — not a `DocumentarySource`. Provider tier drives the MC confidence prior (ONS → 0.92, Police.uk → 0.80, council CSV → 0.60). The `source_id` foreign key points to a row in the sources table with `source_type = 'STRUCTURED_DATA'`.

```sql
CREATE TABLE area_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  area_code TEXT NOT NULL,          -- ONS GSS code
  area_type TEXT NOT NULL,          -- lsoa, ward, la, constituency, ics
  metric_id TEXT NOT NULL,
  domain TEXT NOT NULL,
  value NUMERIC,
  unit TEXT,
  period_start DATE,
  period_end DATE,
  national_average NUMERIC,
  percentile INTEGER,               -- 0-100, recomputed on each refresh
  source_id TEXT REFERENCES sources(id),  -- must be source_type='STRUCTURED_DATA'
  fetched_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(area_code, metric_id, period_start)
);

CREATE TABLE metric_definitions (
  metric_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  domain TEXT,
  source_api TEXT,
  provider_tier TEXT CHECK (provider_tier IN ('T1','T2','T3')),
  refresh_cadence TEXT,
  higher_is_better BOOLEAN,
  node_ids TEXT[],                  -- links to evidence graph nodes
  right_ids TEXT[]                  -- links to legal layer (phase 4)
);
```

**3.4 Dashboard frontend**

- Postcode input on homepage (replaces or sits alongside current domain grid)
- Area dashboard: metric tiles with RAG status vs national average
- **Comparison default: your area vs best-performing comparable area** — not national average. "Your area is 4× worse than the best-performing similar council" is a political fact. "Your area is 1.3× the national average" is forgettable. This is a design philosophy, not a cosmetic choice — it directly serves the theory of change.
- Domain drill-down: "Housing in [your area]" → local metrics + national evidence nodes
- Time series: "how has this changed over 5 years?"
- Missing data transparency: where we don't have local data, say so explicitly

**Shareability design constraint**

Every metric card must work as a standalone shareable object. People who actively seek civic information are a small minority. Everyone else will encounter BASIS because someone shared something.

Concrete requirements:
- Every metric card renders cleanly at mobile screenshot dimensions (375×280px minimum)
- Postcode appears in the URL — shared links are personalised: `basis.uk/area/BS3/housing`
- OG meta generates postcode-specific preview cards: "Bristol BS3: GP wait 19 days, rent £1,825/mo, sewage spills 47 in 2024"
- Share button on every card, one tap
- The comparison shown in the shared card uses best-performing area, not national average — the stark contrast is what makes people share

**Additional success metric for Phase 3:** ≥1 metric card format producing valid postcode-specific OG preview image, measurable share rate on social.

**3.5 Automated refresh pipeline**

- GitHub Actions cron jobs per source cadence
- Incremental upsert (new period rows, don't overwrite history)
- Change detection: if value moves >10% from previous period, flag for review
- Percentile recomputation: on each refresh, rerank all areas

**Success metrics:** All 650 constituencies resolvable, ≥10 metrics per postcode, dashboard live.

---

### Phase 4: Legal Knowledge Layer

**Objective:** Build a Hohfeldian semantic overlay on top of i.AI's Lex Graph. Extract citizen rights, duties, bodies, and mechanisms for the top 20 issue types from an already-structured, already-chunked, already-amendment-tracked legal corpus — without rebuilding what Lex already provides.

**The strategic foundation: Lex Graph**

i.AI (the UK government's AI incubator, DSIT) has published Lex Graph on Hugging Face: 820,000 provision-level nodes and 2.2 million structural edges covering all UK legislation from 1267 to present, complete from 1963. Citation relationships, amendment relationships, cross-references. Open Government Licence v3.0.

Lex API provides live access to the same corpus: 220K Acts and Statutory Instruments, 892K amendments, 89K explanatory notes, semantic + exact search. Free. 1,000 requests/hour. MCP server available.

BASIS does not rebuild this. It inherits the structure and adds the semantic layer Lex doesn't have: what a provision *means for a citizen* — the rights it creates, the duties it imposes, the mechanisms to enforce them.

**4.1 What Lex Graph solves (problems we no longer need to solve)**

| Problem | Old approach | Lex Graph solution |
|---|---|---|
| Statute chunking | Build XML parser, split by section | Every provision is already a discrete node with a stable ID |
| Extraction corpus scoping | Know in advance which Acts are relevant | Ego network query from anchor Act → all connected provisions in 2 hops |
| Amendment tracking | Monitor legislation.gov.uk RSS | Lex Graph amendment edges point directly at affected provision nodes |
| Update triggers | RSS → re-extract whole Act | New amendment edge on a watched provision → targeted re-extraction of that node only |
| Explanatory note validation | Second LLM call to verify extraction | 89K explanatory notes are free plain-English validators co-located with provision text |

The explanatory note point deserves emphasis: for any provision with a note, extraction validation is nearly free. Feed (provision text + explanatory note + extracted schema) to Haiku: "does this extraction match what the note says the provision does?" That's a 1p check, not a 50p Opus call.

**4.2 Schema: lex_provisions as the reference table**

BASIS does not import Lex Graph into Supabase. It maintains a narrow reference table of the ~5,000 provisions relevant to the 20 priority issue domains. Each row carries both the cached provision text (for extraction) and the structural signals from Lex Graph (for confidence priors and the commencement gate). These structural signals are `LegislativeStructuralSource` facts — they have `alpha = 1.0` in the MC engine.

```sql
CREATE TABLE lex_provisions (
  lex_id               TEXT PRIMARY KEY,  -- Lex Graph's stable provision ID
  title                TEXT NOT NULL,     -- 'Housing Act 2004, s.1'
  domain               TEXT,
  jurisdiction         TEXT[],
  full_text            TEXT,              -- cached from Lex API
  explanatory_note     TEXT,              -- co-fetched if exists
  content_hash         TEXT,              -- sha256; change = re-extract
  last_checked         DATE,
  amendment_watch      BOOLEAN DEFAULT true,
  -- structural signals from Lex Graph (LegislativeStructuralSource facts)
  in_degree            INTEGER,           -- how many Acts cite this provision
  amendment_count      INTEGER,           -- times amended since enacted
  last_amended         DATE,
  commencement_status  TEXT CHECK (commencement_status IN (
                         'in_force', 'partially_in_force', 'not_commenced',
                         'prospectively_repealed', 'repealed', 'unknown'
                       )),
  -- partially_in_force: in force in some jurisdictions or for some persons
  -- prospectively_repealed: repeal enacted but not yet effective
  -- commencement_notes: plain English explanation for partial/conditional status
  structural_stability TEXT CHECK (structural_stability IN ('HIGH','MEDIUM','LOW')),
  -- HIGH = untouched >10yrs; MEDIUM = amended 1-3 times; LOW = amended >3 times in 5yrs
  citing_acts          TEXT[]             -- top 5 citing Acts by recency (UI provenance)
);
```

When Lex Graph shows a new amendment edge on a watched provision, `content_hash` changes → extraction job queued → curator review triggered for linked `legal_nodes`. The structural signals are refreshed at the same time.

`structural_stability` feeds directly into MC confidence as a prior on the legal node: a RIGHT extracted from a provision with `structural_stability = LOW` starts with a lower computed_confidence than one from a provision untouched since 1977. This is structural epistemic work — no LLM, no extraction, pure graph traversal.

```sql
-- legal_nodes links to the provision it was extracted from
ALTER TABLE legal_nodes
  ADD COLUMN lex_provision_id TEXT REFERENCES lex_provisions(lex_id);
```

**4.3 Legal node types (Hohfeldian)**

```sql
CREATE TYPE legal_node_type AS ENUM (
  'RIGHT', 'DUTY', 'POWER', 'LIABILITY',
  'PRIVILEGE', 'IMMUNITY', 'REGULATORY_BODY',
  'MECHANISM', 'EVIDENCE_REQUIREMENT', 'ESCALATION_PATH', 'PRECEDENT'
);
-- Note: STATUTE is replaced by lex_provisions — we reference Lex Graph's
-- provision nodes directly rather than duplicating statute text as nodes.

CREATE TABLE legal_nodes (
  id                TEXT PRIMARY KEY,       -- 'RIGHT-HOUSING-HHSRS-001'
  node_type         legal_node_type NOT NULL,
  statement         TEXT NOT NULL,          -- plain English
  lex_provision_id  TEXT REFERENCES lex_provisions(lex_id),
  jurisdiction      TEXT[] NOT NULL,
  applies_to        TEXT[],                 -- ['tenant', 'homeowner']
  duty_holder       TEXT,
  duty_holder_type  TEXT,
  verified          BOOLEAN DEFAULT false,
  confidence        TEXT CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),
  computed_confidence JSONB,
  curator_approved  BOOLEAN DEFAULT false,  -- hard gate before display
  domain            TEXT,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE legal_edges (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_id      TEXT NOT NULL,
  to_id        TEXT NOT NULL,
  edge_type    TEXT NOT NULL CHECK (edge_type IN (
                 'CREATES', 'IMPOSES', 'ENFORCED_BY', 'ACCEPTED_BY',
                 'REQUIRES', 'ESCALATES_TO', 'ESTABLISHED_BY', 'SUPERSEDES'
               )),
  jurisdiction TEXT[],
  explanation  TEXT NOT NULL,
  strength     TEXT CHECK (strength IN ('HIGH', 'MEDIUM', 'LOW'))
);

CREATE TABLE cross_layer_edges (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_layer TEXT NOT NULL,   -- 'evidence', 'legal', 'local'
  from_id    TEXT NOT NULL,
  to_layer   TEXT NOT NULL,
  to_id      TEXT NOT NULL,
  edge_type  TEXT NOT NULL    -- 'EVIDENCES', 'ESTABLISHES', 'TRIGGERS', 'QUANTIFIES'
);
```

**4.4 Extraction pipeline**

The pipeline has two distinct roles that map to two distinct model tiers: bulk extraction (cheap, async, automated) and validation (capable, on-demand, human-assisted). These are never conflated.

```
┌─────────────────────────────────────────────────────────┐
│  ASYNC — GitHub Actions daily cron (£0)                 │
│                                                         │
│  Lex API → provision text + explanatory note            │
│      ↓                                                  │
│  Gemma 4 26B MoE (Google AI API, free tier, 1K req/day)     │
│  Pydantic-constrained structured output:                │
│    response_mime_type = "application/json"              │
│    response_schema = LegalNode (Pydantic model)         │
│  → guaranteed schema-conformant JSON, no parsing        │
│      ↓                                                  │
│  Gemini Flash cross-check (~$0.001/check)               │
│  "Does this extraction match what the provision says?"  │
│  pass  → curator_queue (needs_review: true)             │
│  fail  → curator_queue (flagged: true, reason: ...)     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  SUPABASE — curator_queue table                         │
│                                                         │
│  id, lex_provision_id, extracted_json,                  │
│  flash_check_result, flash_check_note,                  │
│  fixture_match (bool), fixture_delta (text),            │
│  curator_approved (bool, default false),                │
│  needs_review (bool), flagged (bool), reason (text)     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  ON-DEMAND — Claude Code session (Max plan, £0 cash)    │
│                                                         │
│  Supabase MCP → read curator_queue batch                │
│  Lex MCP → pull original provision text + note          │
│  Claude judges each item against source:                │
│    approve  → curator_approved = true                   │
│             → INSERT into legal_nodes                   │
│    reject   → flagged with reason, Gemma prompt updated │
│    escalate → manual review pile (edge cases, law gaps) │
│  Supabase MCP → write decisions back                    │
│                                                         │
│  Sampled review: Claude only sees flagged items +       │
│  random 20% of passed items — not every extraction.     │
│  Full coverage without full review overhead.            │
└─────────────────────────────────────────────────────────┘
```

**Why this separation works**

Gemma does what it's good at: slot-filling against a constrained schema on well-structured legislative text. It is not doing open-ended legal reasoning. The Pydantic schema removes hallucinated structure entirely — output is either valid or the call fails.

Gemini Flash is the cheap first-pass filter (~£40/month for the entire corpus at current pricing, dropping toward zero on free tier for daily incremental runs). It catches systematic Gemma errors before they reach the queue. Failures go straight to Claude; passes are sampled.

Claude is the daddy model in the precise sense: it reads the original provision text via Lex MCP, compares it against Gemma's extraction, and makes a legal judgment. It handles the contested cases and the random sample. It does not do bulk extraction. This is the right use of the most capable model in the stack.

**Pydantic schema (Python) — extends BaseNode**

```python
from pydantic import BaseModel
from typing import Literal
from base_schema import BaseNode, JurisdictionEnum

class LegalNode(BaseNode):
    # BaseNode fields inherited: id, node_type, statement, source_id,
    # confidence, computed_confidence, domain, jurisdiction,
    # verified, curator_approved, extraction_run_id
    node_type: Literal[
        'RIGHT', 'DUTY', 'POWER', 'LIABILITY',
        'PRIVILEGE', 'IMMUNITY', 'REGULATORY_BODY',
        'MECHANISM', 'EVIDENCE_REQUIREMENT',
        'ESCALATION_PATH', 'PRECEDENT'
    ]
    lex_provision_id:     str           # foreign key to lex_provisions
    applies_to:           list[str]     # ['tenant', 'homeowner', ...]
    duty_holder:          str | None
    duty_holder_type:     Literal[
                            'local_authority', 'private_landlord',
                            'public_body', 'employer', 'individual'
                          ] | None
    # structural signals inherited from lex_provisions at node creation
    # (denormalised here for MC engine access without join)
    structural_stability: Literal['HIGH','MEDIUM','LOW'] | None
    commencement_status:  Literal['in_force','not_commenced',
                                  'repealed','unknown'] | None
    extraction_notes:     str | None

# Called via Google AI API with:
#   response_mime_type="application/json"
#   response_schema=LegalNode
# Guaranteed conformant output. Schema violations fail the call.
# source_type on the linked source = 'LEGISLATIVE_STRUCTURAL'
# MC alpha = 1.0 on structural facts; semantic extraction adds uncertainty on top
```

**Track C — Bootstrap (Claude Code + Lex MCP, first)**

Before any automation runs, Claude Code sessions establish the first ~200 high-quality nodes across the top 5 domains. These become the fixture set that Gemini Flash's cross-check is calibrated against, and the regression baseline for all future batches.

```
claude mcp add --transport http lex https://lex.lab.i.ai.gov.uk/mcp
→ Lex skill activates automatically (.claude/skills/lex-uk-law/)
→ Ego network query per domain → scoped provision corpus
→ Interactive extraction + immediate curator approval in session
→ ~200 nodes, all curator_approved: true, all fixture: true
→ Cost: £0. These are the ground truth.
```

**First fixture set:** Housing Act 2004 Chapter 1 — 10 provisions annotated across all Hohfeldian types, 21 typed edges, 5 cross-cutting findings (including ENFORCEMENT_GAP on s.4 and MISSING_CORRELATIVE on category 2 hazard duty). Stored in `fixtures/housing_act_2004_ch1.json`. This is the Track C output that validates the schema against real legislation before automation begins. Every subsequent automated batch compares against it.

**Track D — Precedent (BAILII, on-demand)**

```
BAILII RSS → new significant judgments
→ Lex API case law search (when re-enabled post-TNA licence)
→ Manual Claude Code extraction for first 6 months
→ Volume is low, quality matters, no automation yet
→ Automated once fixture set includes case law patterns
```

**Quality standing check**

Fixture comparison catches cases where Gemma diverges from known-good outputs. It does not catch systematic errors Gemma makes consistently across all provisions (it would reproduce those in the fixtures too). Mitigation: quarterly random sample of 20 live nodes across different Act types, human-verified against source text. If error rate > 10%, Gemma prompt is retuned before the next batch runs.

**4.5 Corpus scoping by domain (ego network approach)**

Rather than manually selecting which Acts to process, use Lex Graph's citation structure:

```
Housing domain anchor: Housing Act 2004
→ 2-hop ego network → ~340 connected provisions
→ Filter: applies_to includes 'tenant' OR 'homeowner' OR 'local_authority'
→ ~120 relevant provisions → extraction corpus for housing domain

Benefits domain anchor: Welfare Reform Act 2012
→ 2-hop ego network → ~280 connected provisions
→ Filter: applies_to includes 'claimant' OR 'dwp' OR 'tribunal'
→ ~95 relevant provisions
```

This is repeatable, auditable, and catches amending SIs that a manual selection would miss.

**4.6 Issue domains for legal mapping (priority order)**

1. Housing: disrepair, damp/mould, eviction, planning objections
2. Benefits: UC, PIP, DLA, sanctions, mandatory reconsideration, appeals
3. Health: waiting times, NHS complaints, mental health, care standards
4. Education: SEND, exclusions, school place allocation, home education
5. Social care: needs assessment, charging disputes, care home quality
6. Environment: pollution, flooding, planning, statutory nuisance
7. Employment: redundancy, discrimination, unfair dismissal, tribunal
8. Consumer/utilities: energy, telecoms, postal services complaints
9. Immigration: visa, asylum, right to remain, detention
10. Police/justice: complaints, stop and search, custody, data subject rights

**4.7 Legal accuracy safeguards**

- **Commencement gate (structural, automated):** Before any legal node enters the curator queue, a structural pre-check runs against `lex_provisions.commencement_status`. `not_commenced` or `repealed` → extraction blocked. `partially_in_force` → extraction proceeds with mandatory `commencement_notes`, displayed with prominent warning to citizens. `prospectively_repealed` → extraction proceeds but nodes flagged for imminent deprecation review. This check costs nothing — it's a database column, not an LLM call.
- **CI check 7 — Legal consistency (structural, automated):** Two database queries run on every commit once legal nodes exist:
  - `ENFORCEMENT_GAP`: any DUTY node with no MECHANISM reachable via ENFORCED_BY edges. A duty with no enforcement mechanism is structurally incomplete — either the mechanism wasn't extracted or the law has a genuine gap (both findings are valuable).
  - `MISSING_CORRELATIVE`: any RIGHT node with no corresponding DUTY node, or any POWER node with no LIABILITY node. Hohfeld requires correlatives — missing ones indicate an extraction error or a genuine legal incoherence.
  These checks catch structural problems between nodes that single-node verification misses.
- `curator_approved: false` by default — API never returns unapproved nodes to frontend
- HIGH confidence threshold enforced at query level: legal routing only surfaces HIGH nodes
- Jurisdiction hard-routing: postcode → jurisdiction → filtered at query time, not display time
- `structural_stability` feeds MC prior: LOW stability provisions produce legal nodes starting with lower computed_confidence, flagged for more frequent re-review
- Fixture regression: every automated batch compares against Track C bootstrap fixtures; regression rate > 15% blocks the batch
- Gemini Flash cross-check on every automated extraction before it enters the curator queue
- Quarterly standing check: 20 random live nodes verified by human against source text; error rate > 10% → Gemma prompt retune
- Prominent disclaimer on all legal content: "This is information, not legal advice."
- Legal aid signpost on every route that may qualify
- `lex_provision_id` on every legal node: direct link to source statute text on legislation.gov.uk — two distinct epistemic claims shown separately in the UI: structural (provision exists, is in force) and semantic (it creates this right)
- Template structure requires one-time sign-off from solicitor or law clinic per template type — governance step separate from per-node curator review

**4.8 Strategic note**

i.AI explicitly invites organisations building on Lex to contact them at lex@cabinetoffice.gov.uk. A working BASIS + Lex integration — citizen rights extraction on top of their legislative graph — is directly aligned with what they describe as the project's intended downstream use. This is a warm contact for both funding conversations and the i.AI employment target.

The stronger positioning argument: i.AI has built Lex MCP (legislation) and Parliament MCP (parliamentary proceedings). BASIS MCP (evidence reasoning and local data) is the natural third piece. Together they form a complete UK civic AI stack — any AI agent can connect all three and answer: what does the law say, what is parliament doing, and what does the evidence show. No single organisation currently provides all three. The conversation with i.AI is not "please fund our civic platform." It is "we have built the third piece of your infrastructure."

**Success metrics:** ≥200 curator-approved legal nodes across top 5 domains via Track A; Track B pipeline running and validated against fixtures; amendment-watch triggering correctly on ≥3 test provisions; jurisdiction routing tested across all four UK jurisdictions.

---

### Phase 5: Action Routing Engine

**Objective:** For any issue a citizen identifies, route them through the correct escalation pathway with pre-populated templates.

**5.1 Routing logic**

The escalation tree is itself part of the knowledge graph. A MECHANISM node carries:

```json
{
  "mechanism_id": "ENV_HEALTH_COMPLAINT",
  "name": "Environmental Health complaint to council",
  "applicable_issues": ["housing_disrepair", "mould", "pests", "noise"],
  "applicable_to": ["tenant", "homeowner"],
  "jurisdiction": ["england", "wales"],
  "prerequisite_ids": [],
  "statutory_response_window_days": 21,
  "template_id": "TPL-ENV-HEALTH-001",
  "evidence_required": ["photographs", "correspondence_log", "dates_reported"],
  "success_rate": null,             -- populated from outcomes
  "escalates_to": ["HOUSING_OMBUDSMAN", "DISREPAIR_CLAIM"],
  "escalation_trigger": "no_response_21_days | unsatisfactory_response"
}
```

Routing algorithm:
1. User describes issue (free text + structured questions)
2. Issue classifier → domain + issue_type + tenure_type + jurisdiction
3. Graph traversal from issue_type → applicable RIGHT nodes → available MECHANISMs
4. Filter by jurisdiction, tenure, prerequisites met
5. Rank mechanisms by: success_rate (if known) → statutory strength → effort level
6. Present ordered pathway to user with explanation of each step

**5.2 Template engine**

Templates are structured documents with named slots. Slots are populated from:
- User's personal data (name, address — stored locally, never on server unless consented)
- Local data layer (postcode → council name, MP name, relevant local metric)
- Legal layer (relevant statute, section reference, regulatory body name)
- Evidence layer (confidence-weighted supporting facts)

Template types:
- Council complaint letter (HTML → PDF)
- MP constituency letter
- Ombudsman complaint form (pre-fills where possible)
- FOI request letter
- EIR request letter
- Pre-action protocol letter (housing disrepair)
- Letter Before Action (general)
- Tribunal application grounds
- Public inquiry submission
- Parliamentary petition text

**5.3 Contact resolution**

- MP lookup: postcode → constituency (ONS) → TheyWorkForYou API → email + surgery times
- Council lookup: postcode → LA (ONS) → council website scrape → complaint portal URL
- Regulatory body lookup: issue_type → REGULATORY_BODY node → contact details
- Legal aid: postcode → Civil Legal Advice regional directory

**5.4 Action tracking**

```sql
CREATE TABLE citizen_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  issue_type TEXT NOT NULL,
  jurisdiction TEXT NOT NULL,
  mechanism_id TEXT NOT NULL,
  template_id TEXT,
  submitted_at TIMESTAMPTZ,
  response_deadline TIMESTAMPTZ,
  outcome TEXT CHECK (outcome IN ('resolved', 'escalated', 'withdrawn', 'pending', 'no_response')),
  outcome_recorded_at TIMESTAMPTZ,
  escalated_to TEXT,                -- mechanism_id of next step if escalated
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

User-facing: a simple "my actions" timeline showing what was sent, when a response is due, and what to do next if nothing happens.

**5.5 Collective action detection**

- Daily aggregation: group actions by (mechanism_id, area_code, issue_type)
- If ≥10 people in same ward with same issue in 30 days → "You're not alone" notification
- If ≥50 → suggest coordinated response (joint letter, group FOI, collective legal action)
- Aggregate data (never individual) shared as public stats: "237 housing complaints in [council] in the last 6 months"
- Group action routing: CrowdJustice referral, CLAiT collective legal action, media briefing pack

**Success metrics:** ≥10 escalation trees built and tested, ≥3 template types live, contact resolution working for all 650 constituencies.

---

### Phase 6: Outcome Intelligence

**Objective:** The graph learns from what works. Outcomes feed back into confidence scores; systemic failures surface to the right people.

**6.1 Outcome tracking and graph updates**

When a user records an outcome:
- `success` on a MECHANISM → success_rate increments, MECHANISM confidence edges strengthen
- `no_response` → response_rate decrements, may trigger escalation suggestion
- `escalated` → escalation edge strengthens
- `resolved_after_escalation` → first-level mechanism weakness flagged

Outcomes aggregate into mechanism-level stats:
```
ENV_HEALTH_COMPLAINT:
  attempts: 847
  resolved: 421 (49.7%)
  escalated: 312 (36.8%)
  no_response: 114 (13.5%)
  median_resolution_days: 34
  by_council: { Westminster: 61%, Slough: 31%, ... }
```

This data is uniquely valuable. No one else has it. It becomes: (a) a guide for citizens ("complaining to this council works less often — skip straight to ombudsman"), (b) a campaigning tool ("Slough council ignores 69% of housing complaints"), (c) an evidence base for systemic advocacy.

**6.2 Systemic signal surfacing**

- If ≥100 identical mechanism failures against same body in 6 months → flag as systemic failure pattern
- Generate evidence summary: dates, issue types, non-response rates
- Route to appropriate escalation: Housing Ombudsman systemic investigations, CQC thematic reviews, select committee evidence calls
- Auto-draft: systemic complaint letter to regulatory body, pre-populated with aggregate data

**6.3 Parliamentary and media bridge**

- Pattern detection → suggested parliamentary question (PQ) text
- Evidence package for select committee inquiry submissions
- Press release template for systemic findings
- FOI request batch: if pattern detected, auto-suggest coordinated FOI to surface hidden data
- Petition trigger: if issue is clearly systemic and widespread → petition text pre-drafted

**6.4 Policy feedback loop**

Outcomes connect back to the evidence layer:
- High resolution rate on a mechanism → SUPPORTS edge to relevant POLICY node
- Persistent failure rate → CONTRADICTS edge to policy claims about that body's effectiveness
- This is how the graph stays honest as the real world changes

---

### Phase 7: Intelligence Layer

**Objective:** Ask questions; get evidenced answers. The graph becomes a reasoning surface.

**7.1 Guided Evidence Reasoning (GAR)**

Natural language policy question → traversal of evidence, legal, and local layers → sourced answer with:
- Every claim citing a node ID and source
- Contradicting evidence stated with equal weight
- Contested nodes flagged
- Assumptions the answer depends on listed separately
- "Insufficient evidence" is a valid answer
- Identified gaps logged as evidence-gathering priorities

**GAR responses are structured as self-contained documents** — not HTML renderer outputs, not frontend-coupled JSON. Each response must be valid as a REST API payload, embeddable in an external AI agent's context, and wrappable as an MCP tool response. This constraint is set now because retrofitting it after Phase 7 is built is expensive. The document format also enables pre-computation of hot query paths as standalone cached documents, reducing graph traversal cost for common queries.

Example:
> "What would happen if the UK rejoined the single market?"

Response structure:
1. What the evidence says (CLAIM nodes, with confidence scores)
2. Fiscal impact (from fiscal gap computation, with range)
3. Legal implications (STATUTE nodes that would be affected)
4. Local impact for your area (trade-exposed sectors, regional breakdown)
5. Contested assumptions (what would have to be true for this to work)
6. Evidence gaps (what we don't know)
7. Share card (shareable summary with source citations)

**7.2 Postcode-personalised intelligence**

Every GAR answer is filterable by postcode:
- National picture → "how does this affect [your area] specifically?"
- Local data layer supplies the personalisation
- MP/council context injected where relevant

**7.3 Challenge integration**

- Any claim in a GAR answer can be challenged with a counter-source
- Challenge goes through the same validation pipeline as the evidence graph
- Accepted challenges update node confidence, which updates future answers
- This is the participatory intelligence model: the platform gets smarter from use

**7.4 Reasoning feedback loop**

When GAR synthesises a novel cross-domain connection — a relationship between nodes that no edge currently captures — that connection is flagged for curator review. Accepted connections become new edges in the graph. GAR discoveries that survive curator review are not ephemeral answers; they are permanent additions to the knowledge graph. The platform gets structurally smarter from being used, not just informationally smarter.

---

### Phase 8: Continuous Extraction & Automation

**Objective:** The knowledge graph maintains itself. Humans review, not extract.

**8.1 Source monitoring**

- **Legal layer (Lex Graph):** Daily hash check on watched `lex_provisions`. Changed `content_hash` → targeted re-extraction of that provision only, curator review triggered for linked `legal_nodes`. No RSS monitoring needed — amendment tracking is inherited from Lex Graph's edge structure.
- **Parliament API / parliament-mcp (i.AI):** Bills tracker, Hansard monitoring for POSITION nodes, select committee reports. parliament-mcp is the same integration pattern as Lex MCP — add it once, it runs.
- **Gov.uk:** Weekly hash comparison of guidance documents; change → extraction job
- **BAILII:** RSS for significant judgments → PRECEDENT extraction queue
- **Council websites:** Meeting agendas and minutes scraping (where robots.txt permits)
- **ONS release calendar:** Automatic ingestion on data release
- **FOI disclosures:** Scrape disclosure logs of key public bodies

**8.2 Agent architecture**

Four extraction agents running on schedule:

| Agent | Trigger | Model | Output |
|---|---|---|---|
| Legal Extraction Agent | `lex_provisions` content_hash change (daily) | Gemma 4 26B MoE (extract) + Gemini Flash (cross-check) | curator_queue rows; commencement gate blocks not_commenced/repealed automatically |
| Structural Signals Agent | Lex Graph daily diff | graph traversal, no LLM | Refreshes in_degree, amendment_count, commencement_status, structural_stability on watched provisions; triggers re-extraction if stability drops |
| Legal Validation | Claude Code session (on-demand) | Claude (Max plan) via Supabase MCP + Lex MCP | curator_approved decisions written back; reads source_type to route to correct MCP |
| Evidence Agent | ONS/DWP/NHS release calendar + manual | Gemma + Gemini Flash | StructuredDataSource and DocumentarySource nodes; FACT/ASSUMPTION updates; MC re-propagation |
| Parliamentary Agent | parliament-mcp daily (i.AI) | — | TestimonySource POSITION nodes from Hansard; BILL tracking; committee reports |
| Local Data Agent | Per-source cadence | — | StructuredDataSource area_metrics upsert; percentile recomputation; anomaly flags |

Each agent run is logged in `agent_log` table with: input hashes, output node counts, errors, model version.

**8.3 FOI automation**

- Evidence gap detection: if a metric is missing for >30% of LAs → auto-generate FOI request
- Queue management: batch similar FOIs (same body, same data type) into single request
- WhatDoTheyKnow integration: submit via API, track response
- Response ingestion: FOI responses → extraction pipeline → new nodes

**8.4 Human oversight**

Automation handles ingestion; humans handle judgment:
- Any new legal node requires curator sign-off before live
- Edge type changes require explanation
- Systemic findings require human review before surfacing to media/parliamentary channels
- Model updates require test suite pass (regression fixtures) before deployment

---

## Technical Architecture (Full Stack)

### Current (Phase 2a)
- **Frontend:** Next.js 14 + TypeScript + Tailwind, `apps/web/`
- **Database:** Supabase (Postgres + pgvector), project `nxlerszckdzvilqxwjfj`
- **Auth:** Supabase Auth (ready, not yet exposed in UI)
- **Hosting:** GitHub Pages (Phase 0), Vercel (Phase 2b)
- **CI:** GitHub Actions (to be wired)

### Additions by phase
- **Foundation:** `base_schema.py` (BaseNode + enums) + `source_models.py` (five BaseSource subclasses + MC priors). Validate existing 389 nodes and 172 sources against these before any further work.
- **Phase 3:** ONS Geography API, area_metrics table (StructuredDataSource), local data ingestion pipeline
- **Phase 4:** lex_provisions table with structural signal columns, legal_nodes + legal_edges tables, commencement gate CI check, Lex MCP + Gemma extraction pipeline, curator queue UI, cross_layer_edges table
- **Phase 5:** MechanismNode + TemplateNode (BaseNode subclasses), template engine, action tracking
- **Phase 6:** OutcomeNode, aggregation jobs, systemic pattern detection, outcome → MC feedback
- **Phase 7:** GAR endpoint (streaming, self-contained document format), share card generator, reasoning feedback loop → curator queue, pre-computed hot query paths
- **Phase 8:** Structural Signals Agent, agent scheduler (GitHub Actions or Inngest), FOI integration

### Planned: BASIS MCP server

i.AI has built Lex MCP (legislation) and Parliament MCP (proceedings). A BASIS MCP server exposing evidence reasoning chains and local data completes the triptych — any AI agent connecting all three can answer what the law says, what parliament is doing, and what the evidence shows. GAR responses structured as self-contained documents (Phase 7 constraint) make wrapping them as MCP tool responses a single day of work when the time comes. No build required now; design constraint captured.

### Cost model

- Phase 0–2: £0/month (GitHub Pages, Vercel free, Supabase free)
- Phase 3–5: ~£95/month (Supabase Pro ~£25, Vercel Pro ~£20, LLM ~£50)
- Phase 4 legal extraction: **£0 cash** — Track A uses existing Max plan; Track B uses Gemini free tier (1K req/day); explanatory note validation uses Haiku (~1p/check). No Opus budget consumed on bulk legal extraction.
- LLM ceiling £50/month in steady state; Haiku for classification/validation, Sonnet for GAR, Opus for contested escalations only
- **Documented fallback:** DeepSeek V3.2 at $0.28/$0.42 per million tokens (input/output) if Gemini free tier rate limits during bulk extraction. Native JSON schema support, comparable structured output quality. Drop-in replacement for the extraction step — same Pydantic schema, different API call.

### Privacy architecture
- Postcode stored locally (client-side) or on profile (opt-in, encrypted)
- Action tracking: user-associated, never published individually
- Aggregate data: published without any individual linkage
- No third-party analytics
- GDPR-compliant: right to erasure wired into profiles table from the start

---

## Legal and Governance

### Structure
- Community Interest Company (CIC) — assets locked, cannot be extracted
- MIT licence (code) + CC BY-SA (data and graph content)
- "We show our working" applies to the platform itself: methodology, extraction prompts, model versions all public

### Liability management
- All legal content: "This is information, not legal advice."
- Legal aid and solicitor referral signposted on every legal route
- Legal nodes only go live after curator review
- Quarterly solicitor review of a random sample of legal nodes
- Clear versioning: every node carries the date it was last verified

### Funding model
- Phase 0–2: GitHub Pages / Vercel free tier + Supabase free tier = £0/month
- Phase 3–5: Supabase Pro (~£25/month), Vercel Pro (~£20/month), LLM spend (~£50/month) = ~£95/month
- Revenue: grant funding (Joseph Rowntree, Nuffield, MHCLG PropTech Innovation Fund), civic tech accelerators, eventually subscription for bulk data/API access by third parties
- The outcome data (phase 6) is uniquely valuable — mechanism success rates by council is a dataset no one else has

---

## What This Is Not

- Not a replacement for legal advice
- Not a platform for misinformation (every claim is sourced and verified before display)
- Not a party-political platform (evidence is evidence; the graph has no ideology)
- Not another civic tech project that builds and abandons (the self-updating extraction loop and outcome feedback mean the platform degrades without maintenance, creating incentive to keep it current)
- Not a surveillance tool (aggregate only; individual data never published)

---

## Summary: The Theory of Change

```
Phase 0: Makes the idea visible
Phase 1: Makes the evidence honest
Phase 2: Makes evidence accessible
Phase 3: Makes it local and personal
Phase 4: Connects it to legal rights
Phase 5: Routes people to action
Phase 6: Learns from what works
Phase 7: Becomes a reasoning surface
Phase 8: Maintains itself
```

At each phase, the cost of governing badly — ignoring evidence, violating rights, failing to respond — increases. Not through confrontation, but through transparency, organisation, and the quiet accumulation of documented outcomes.

This is what democracy's infrastructure looks like when it actually works.

---

*Last updated: April 2026 — schema-first architecture, source taxonomy, Lex Graph structural signals integrated throughout*
*Status: Phase 2a complete, Phase 2b in progress*
*Repository: github.com/Hwesto/basis*
*Platform: nxlerszckdzvilqxwjfj.supabase.co*
*Legal data foundation: Lex Graph (i.AI / National Archives) — huggingface.co/datasets/i-dot-ai/lex-graph*
