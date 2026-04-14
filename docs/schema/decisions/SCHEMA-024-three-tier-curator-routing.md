---
id: SCHEMA-024
title: Three-tier curator routing with public verification level
status: PROVISIONAL
resolves: [OQ-007, OQ-008]
related: [SCHEMA-006, SCHEMA-015, SCHEMA-023]
source: docs/schema/decisions/
---

### SCHEMA-024: Three-tier curator routing with public verification level

**Phenomenon:** A binary `curator_approved` gate (SCHEMA-006) treats
every candidate node as needing the same human review. At pipeline
volumes that's a hard bottleneck — review throughput becomes the
limit on the rate at which BASIS can ingest evidence. The original
SCHEMA-006 design assumes one human reviews every node, which is
incompatible with the Phase 8 continuous-extraction goal.

But "let an LLM approve everything" is the wrong response: the whole
point of BASIS is more rigour than the politics it's testing, and
LLM approval makes the foundation depend on a single model's
judgment without external validation.

**Decision:** Replace the binary gate with a three-tier routing
system. Automated checks run first; a Claude session (via Supabase
MCP + Lex MCP) does well-specified extraction review; the human
curator handles only escalations, civic findings, and calibration
checkpoints.

The hard gate from SCHEMA-006 is preserved — nothing enters the
public API until `curator_approved=true`. SCHEMA-024 specifies who
can flip that flag and under what conditions.

#### Tier 1 — Automated gates (pipeline, no model)

Cheap, deterministic, fail-fast. A node that fails any of these
never reaches Tier 2.

| Gate | Source | Condition |
|---|---|---|
| Pydantic schema validation | `src/base_schema.py` | `BaseNode` + subclass conformance |
| Domain enum | SCHEMA-002 | `domain in DomainEnum` |
| Confidence enum | SCHEMA-004 | `confidence in {HIGH, MEDIUM, LOW}` |
| Source presence | SCHEMA-013 | `node_type=FACT` requires `source_id` |
| Source quality floor | SCHEMA-008 | TESTIMONY tier T5 cannot auto-approve; DERIVED nodes require all `input_node_ids` curator-approved |
| Boilerplate detection | SCHEMA-017 | `EXPLANATION_BLOCKLIST` regex against edge `explanation` and `falsification_condition` |
| Adversarial-pattern check | SCHEMA-024 (new) | Regex match for prompt-injection patterns in `full_text` (e.g. `<system>`, `[INST]`, `Ignore previous instructions`) |
| Commencement gate | SCHEMA-011 | Legal nodes from `commencement_status in {not_commenced, repealed}` blocked entirely |
| Flash cross-check | `src/extraction/pipeline.py:cross_check` | Gemini Flash judgment on extraction vs source text — pass/fail |
| Fixture similarity | Phase 4 | Track C fixture nodes used as a regression baseline; large divergence flagged |

**Outcome routing:**
- **Pass all gates →** advance to Tier 2
- **Fail any gate →** route to Tier 3 with `escalation_reason` recording the failure category. Hard-failed nodes are *not silently dropped* — they go to a human queue so genuine extraction errors can be distinguished from genuine schema gaps that need a SCHEMA decision.

#### Tier 2 — Claude (Supabase MCP + Lex MCP, on-demand sessions)

Receives every node that passed Tier 1. Runs in a Claude Code session
where the operator (or a scheduled job) drains the `pending_claude`
queue. Claude:

1. Pulls the original source text via Lex MCP (for legal nodes) or
   from `sources.full_text` via Supabase MCP (for documentary nodes).
2. Compares the extracted node against the source — does the
   `statement` accurately reflect what the source says?
3. Checks edge `explanation` plausibility against both endpoints.
4. Verifies `node_type` classification against the source's actual
   structure ("may" → POWER not DUTY, etc.).
5. Verifies fiscal metadata where present — does the amount match,
   does `gap_role` make sense, is the range honest about uncertainty?

**Decision per node:**
- `approve` — set `curator_approved=true`, `approved_by='claude'`,
  `verification_level='ai_reviewed'`. Cache the judgment hash so
  re-ingestion of the same source content doesn't re-run Tier 2.
- `reject` — set `decision='rejected'`, `decision_notes=<reason>`.
  Node is dropped from the public API; original extraction is kept
  for debugging.
- `escalate` — route to Tier 3 with structured `escalation_reason`
  (see enum below).

#### Tier 3 — Human (exception queue only)

Reserved for cases where Claude shouldn't be the final word.
Always-Tier-3 categories:

- **PRECEDENT nodes** — court decisions have legal weight; misclassifying ratio creates downstream errors
- **ENFORCEMENT_GAP findings** (CI check 7) — civic findings with political consequence
- **MISSING_CORRELATIVE findings** (CI check 8) — same
- **First N=20 nodes of any new domain** — calibration window
- **First N=5 nodes from any source whose `content_hash` changed materially or has never been ingested** — source-level calibration
- **First batch after any LLM model version change** — model-level calibration; operator config flag
- **TEMPLATE nodes** (Phase 5) — legally binding documents requiring solicitor sign-off (see "Solicitor flag" below)
- **Cross-domain edges** — depend on understanding two domains' epistemics; Claude review is provisional pending audit
- **Tier 1 hard failures** — operator decides whether to fix the extraction or extend the schema
- **Claude-escalated nodes** — anything Claude flagged with `escalation_reason ≠ 'none'`

On approval: set `approved_by='human'`, `verification_level='human_curated'`,
`last_audited_by='human'`, `last_audited_at=now()`. On rejection: same
as Tier 2 reject.

#### Verification level (public-facing)

Two fields on each node:

```
approved_by:           ENUM(auto, claude, human)
                       — who flipped curator_approved last
verification_level:    ENUM(auto_verified, ai_reviewed, human_curated)
                       — cumulative assurance label, displayed publicly
```

`approved_by` is who *did* the latest action (audit trail).
`verification_level` is the *highest* assurance the node has reached.
A node Claude approved that you later spot-check and confirm becomes:
`approved_by=claude` (last actor), `verification_level=human_curated`
(highest reached), `last_audited_by=human`. The MC engine MAY weight
nodes by verification_level in future calibration, but does not in
the initial implementation.

#### Frontend badge (Phase 2 deliverable)

Per-node badge alongside the existing tier pill and confidence bar:

| Level | Badge | Colour |
|---|---|---|
| `auto_verified` | 🤖 auto-verified | neutral grey |
| `ai_reviewed` | 🧠 AI-reviewed | blue |
| `human_curated` | 👤 human-curated | green/gold |

Click → drawer showing the routing chain: Tier 1 checks passed,
Claude's approval note, when (and if) a human spot-confirmed it.
This is "we show our working" extended to the curation process —
readers see calibrated trust without extra effort on the operator
side.

#### Escalation reason (structured enum, frequency-tracked)

```
escalation_reason: ENUM
  none                      — no escalation; node passed
  claude_uncertain          — Claude couldn't make a call
  source_text_unavailable   — Lex MCP / Supabase MCP couldn't fetch
  extraction_ambiguous      — multiple plausible interpretations
  cross_domain              — node spans domains
  precedent_node            — always Tier 3
  civic_finding             — ENFORCEMENT_GAP / MISSING_CORRELATIVE
  low_source_provenance     — T5 testimony, unverified DERIVED
  model_disagreement        — Gemma vs Flash output materially differs
  out_of_distribution       — node shape unlike anything previously approved
  template_legal_review     — TEMPLATE node, needs solicitor
  tier1_hard_fail           — Tier 1 rejected; needs human triage
  first_in_window           — calibration window (new domain / source / model)
```

Per-week reporting: if any reason exceeds 30% of escalations,
investigate. A spike in `extraction_ambiguous` for housing nodes
means the housing extraction prompt is too loose — that's a Tier 1
gate calibration problem, not a routing problem.

#### Kickback workflow

When a human spot-check finds Claude was wrong:

1. Node flagged `kickback=true`, `kickback_reason=<text>`, the Tier 2
   judgment_hash recorded as a known-bad pattern.
2. The pattern is logged. If the same kind of error recurs N=3 times
   on different nodes within a 30-day window, the Tier 1 routing rules
   are updated to escalate that pattern (e.g. "any node with
   `extraction_notes` containing X always goes to Tier 3").
3. The system doesn't auto-modify Tier 1 — a human reviews the
   pattern and decides. But the review is triggered automatically.

This converts spot-check findings into permanent schema improvements
rather than one-off corrections.

#### Caching

Tier 2 is the only model-call tier and even subscription-Claude
sessions have throughput limits. Cache key:
`hash(source.content_hash + extraction_prompt_version + node_type +
extracted_node_canonical_form)`. A re-ingestion of the same source
producing the same extraction skips Tier 2 and inherits the prior
approval. Invalidated on prompt version change or when the cached
node was kicked back.

#### Calibration commitment (the testable assumption)

The core assumption — that Claude's judgment on well-specified
extraction tasks is sufficient for approval — is **provisional**,
not asserted. Before Tier 2 is the default for production:

1. **Initial calibration study (one-off, pre-launch):** Sample 100
   nodes Claude has approved; you review them blind; measure
   agreement rate. **Threshold to proceed: ≥90% agreement.** If
   below, tighten Tier 1 gates and re-sample.

2. **Ongoing 5% spot-check:** A random 5% of `approved_by=claude`
   nodes are pulled into the human queue weekly. Drift is detected
   and kicked back via the workflow above.

3. **Model-version recalibration:** Whenever the Claude model
   version changes (or any extraction model), the first batch of
   approvals goes to Tier 3 until the operator confirms agreement
   stays ≥90%.

The numbers (100, 90%, 5%) are design choices, not measurements,
matching the SCHEMA-019 disclaimer. They get refined when the
calibration data accumulates.

**Solicitor flag (TEMPLATE nodes):**
TEMPLATE nodes carry a separate `solicitor_signed_off: bool` field
(already in `src/action_schema.py:62`). They cannot reach
`verification_level=human_curated` without `solicitor_signed_off=true`,
even if a non-solicitor human approves. This is a stricter form of
Tier 3, not a fourth tier.

---

**Cost (operational):** Tier 2 runs in subscription Claude Code
sessions via MCP, so per-node cost is effectively zero on top of
existing tooling. Throughput limit is operator session time, not
API spend.

**Alternatives considered:**
- Keep binary `curator_approved`. Rejected: pipeline volumes
  guarantee a bottleneck.
- Two-tier (auto + human, no Claude). Rejected: pushes the same
  bottleneck back onto the operator with no relief.
- Auto-approve everything passing Tier 1. Rejected: removes the
  judgment that distinguishes "extraction-shaped data" from
  "extraction that says what the source actually says".

**Falsification:**
- Calibration study returns <90% agreement after multiple Tier 1
  tightening iterations. SCHEMA-024 is wrong; revert to binary or
  redesign Tier 2 prompt.
- Public users systematically report nodes with
  `verification_level=ai_reviewed` are wrong at higher rate than
  `human_curated`. The verification badge is misleading; either the
  agreement bar must rise or the public framing must change.
- Adversarial extraction attempt succeeds: a malicious source
  inserts a misleading node that passes Tier 1 + Tier 2. Tier 1
  adversarial-pattern check needs to expand; possibly a separate
  source-trust scoring system is needed.

**Implementation tracker:**
- Schema fields on `curator_queue` and `evidence_nodes`: `approved_by`,
  `verification_level`, `escalation_reason` (enum), `auto_approval_conditions`
  (jsonb), `claude_judgment_hash`, `last_audited_by`,
  `last_audited_at`, `kickback`, `kickback_reason`
- New module `src/curator/routing.py` implementing Tier 1 logic
- Tier 2 = operator playbook + MCP queries (not a code change)
- Tier 3 = curator UI in v2 frontend (Phase 2 deliverable)

**Status:** PROVISIONAL — pending calibration study (Phase 2). Once
agreement bar is met, status moves to SETTLED.
