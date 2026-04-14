---
phase: 4
status: planned
source: BASIS_ROADMAP.md
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

BASIS does not import Lex Graph into Supabase. It maintains a narrow reference table of the ~5,000 provisions relevant to the 20 priority issue domains. Each row carries both the cached provision text (for extraction) and the structural signals from Lex Graph (for confidence priors and the commencement gate). These structural signals are `StructuralSource` facts with `registry='lex_graph'` — alpha = 0.95 per SCHEMA-010.

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
  -- structural signals from Lex Graph (StructuralSource facts, registry='lex_graph')
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
    commencement_status:  Literal['in_force','partially_in_force',
                                  'not_commenced','prospectively_repealed',
                                  'repealed','unknown'] | None
    commencement_notes:   str | None   # required when partially_in_force
    extraction_notes:     str | None

# Called via Google AI API with:
#   response_mime_type="application/json"
#   response_schema=LegalNode
# Guaranteed conformant output. Schema violations fail the call.
# source_type on the linked source = 'STRUCTURAL' (registry='lex_graph')
# MC alpha = 0.95 on Lex Graph structural facts (SCHEMA-010);
# semantic extraction adds uncertainty on top
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
- **CI checks 7 and 8 — Legal consistency (structural, automated):** Two database queries run on every commit once legal nodes exist (SCHEMA-023):
  - **Check 7 — `ENFORCEMENT_GAP`:** any DUTY node with no MECHANISM reachable via ENFORCED_BY edges. A duty with no enforcement mechanism is structurally incomplete — either the mechanism wasn't extracted or the law has a genuine gap (both findings are valuable).
  - **Check 8 — `MISSING_CORRELATIVE`:** any RIGHT node with no corresponding DUTY node, or any POWER node with no LIABILITY node. Hohfeld requires correlatives — missing ones indicate an extraction error or a genuine legal incoherence.
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
