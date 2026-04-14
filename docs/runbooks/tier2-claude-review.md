# Runbook: Tier 2 review (Claude via MCP)

This is the operator playbook for SCHEMA-024 Tier 2 — Claude judgment
on candidate nodes that passed Tier 1 automated gates. Tier 2 isn't a
piece of code in the pipeline; it's a workflow the operator runs in a
Claude Code session with the Supabase MCP and (where relevant) the
Lex MCP enabled.

## When you do this

Whenever the agent log shows a backlog of `tier=2` rows in
`curator_queue` (or `_routing.tier == 2` in
`data/v2_graph/candidate_nodes.jsonl` while Phase 1 persistence is
local). Cadence:

- After every `evidence` agent run that produced new nodes
- Daily during Phase 2 re-ingestion
- Weekly steady-state once Phase 8 automation is live

## Prerequisites

1. Supabase MCP authenticated in this Claude Code session (or local
   jsonl available if Supabase isn't wired yet).
2. Lex MCP authenticated when reviewing legal nodes.
3. The `docs/schema/decisions/SCHEMA-024-three-tier-curator-routing.md`
   spec in scope — it defines what counts as approve / reject /
   escalate.
4. The reviewer (Claude) has agreed to this rubric explicitly at the
   start of the session.

## Opening the session

In Claude Code in the repo:

> Continuing curator routing per SCHEMA-024. I'm about to drain the
> Tier 2 queue. Please:
>
> 1. List the next N=20 rows from `curator_queue` where `tier=2` and
>    `decision IS NULL`, ordered by `created_at` (oldest first). Use
>    Supabase MCP. (If Supabase isn't authenticated, read
>    `data/v2_graph/candidate_nodes.jsonl` and filter by
>    `_routing.tier == 2` and no `_routing._review_decision` set.)
>
> 2. For each row in batch:
>    - Pull the source's full text (Supabase: `sources.full_text` for
>      DOCUMENTARY; Lex MCP: `get_provision(record_id)` for
>      STRUCTURAL with registry='lex_graph').
>    - Apply the rubric below.
>    - Decide approve / reject / escalate, with a one-paragraph note
>      saying why.
>    - Write the decision back via Supabase MCP (or by editing the
>      jsonl row in place, in Phase 1).
>
> 3. Log a summary at the end: how many approved, how many rejected,
>    how many escalated to Tier 3, with reason breakdown.

## The decision rubric

For each candidate node, in order:

### 1. Does the source support the statement?

Pull the source text. The candidate's `statement` field must be
**directly supported** by the source — not paraphrased to the point of
adding meaning that isn't there, not omitting a qualifier the source
makes explicit. If the source says "approximately 7.6m", the
extracted FACT shouldn't say "exactly 7.6m". If the source says "the
Department estimates", a CLAIM that says "DHSC has confirmed" is
overreaching.

- **Match within reasonable paraphrase →** continue to step 2.
- **Material mismatch →** reject. Note the specific divergence.

### 2. Is the `node_type` correctly assigned?

Per `docs/basis-spec-final.md` §2.1 + extraction-agent-spec.md:
- A statistical figure or measurable observation = **FACT**.
- An interpretive bridge between facts and policies = **CLAIM**.
- An untested or untestable belief that has to be true for a
  conclusion = **ASSUMPTION** (with `basis_fact_ids` and a
  `falsification_condition`).
- A proposed action with a mechanism = **POLICY**.
- A party's stance on a policy = **POSITION** (with `actor`).
- For legal: a single legal capacity = **RIGHT/DUTY/POWER/LIABILITY**;
  enforcement machinery = **MECHANISM**; court reasoning = **PRECEDENT**.

Common confusions to flag:
- "may" is POWER, not DUTY ("must")
- A CLAIM about cause and effect that requires waiting for new data
  to test is actually an ASSUMPTION
- A POSITION without an `actor` field can't be a POSITION

- **Correct →** continue to step 3.
- **Wrong type →** reject with the proposed type, or escalate if
  multiple types defensibly apply.

### 3. Are edge `explanation` fields specific?

If the candidate is an edge or carries edges, every `explanation`
must describe the *specific* relationship between this pair, not a
generic phrase like "supports" or "depends on". This is the SCHEMA-017
constraint and it's already enforced as a Tier 1 hard-fail for
verbatim blocklist matches — Tier 2 catches the longer
"X supports Y" boilerplate that gets through.

### 4. Fiscal metadata sanity (where present)

- `amount` matches the source figure (or `amount_low`/`amount_high`
  range matches the source's stated uncertainty)
- `unit` is correct (a £180bn departmental budget is `bn_gbp`, not
  `m_gbp`)
- `gap_role` is plausible — does this node actually contribute to
  the £44–146bn fiscal gap? See SCHEMA-014 examples table
- `direction` is correct (`spending` for a cost, `revenue` for a tax,
  `net` for something like a saving that's a flow but not new spend)

### 5. Confidence is calibrated

- HIGH = direct, multi-source, T1/T2 evidence
- MEDIUM = clear in one strong source or implied across a few
- LOW = inferred or single-source-T4-or-below

If the source backs the statement at HIGH but the candidate is
labelled LOW (or vice versa) — note as `out_of_distribution` or
`extraction_ambiguous` and consider escalating instead of fixing.

## Decision: approve / reject / escalate

| Action | When |
|---|---|
| **approve** | Source supports it; type, edges, fiscal, confidence all check out. Set `curator_approved=true`, `approved_by='claude'`, `verification_level='ai_reviewed'`. Add a one-line note. |
| **reject** | Material divergence from source, or wrong type that's clearly fixable. Set `decision='rejected'`, `decision_notes` = the specific reason. The original extraction stays for debugging. |
| **escalate** | You're uncertain, the source text wasn't fetchable, multiple types defensibly apply, the source is from a registry / domain you haven't seen before, OR the node is in the always-Tier-3 categories that somehow slipped through. Set `tier=3`, `escalation_reason` = one of: `claude_uncertain`, `source_text_unavailable`, `extraction_ambiguous`, `out_of_distribution`. Operator (Harry) sees it next. |

## What you must NOT do

- Approve a node by inferring intent from the title / publisher
  alone. Pull the source text. The whole point of Tier 2 is that
  Tier 1 already passed the structural gates.
- Approve a PRECEDENT, ENFORCEMENT_GAP, MISSING_CORRELATIVE, or
  TEMPLATE node — these are always Tier 3 per SCHEMA-024. If one
  reaches Tier 2 it's a routing bug; flag it instead of approving.
- Lower the bar to clear the queue. The 90% calibration agreement
  threshold (SCHEMA-024) is the gate to becoming a default
  reviewer. Approving borderline cases inflates apparent throughput
  but degrades accuracy.
- Rewrite the candidate's content. Reject + note + let extraction
  re-run. Editing in Tier 2 hides which extractor errors recur.

## Cache hits

If the cached `claude_judgment_hash` matches a previous approval,
skip the source fetch and apply the cached decision. Cache key is
`hash(source.content_hash + extraction_prompt_version + node_type +
canonical(node_payload))`. Misses in the cache are full reviews.

## Logging

At the end of every Tier 2 session:

```
TIER 2 SESSION SUMMARY
  reviewed:    {N}
  approved:    {N}  -> verification_level=ai_reviewed
  rejected:    {N}
  escalated:   {N}  (by reason: ...)
  cache_hits:  {N}
  duration:    {minutes}
```

This summary goes into `agent_log` (when Supabase is wired) and into
`logs/tier2_session_<timestamp>.md` locally. The 5% spot-check
sampler (when scheduled in Phase 2) draws from these sessions.

## When to escalate the runbook itself

If a recurring decision pattern doesn't fit the rubric — same kind of
ambiguity escalating week after week — that's a SCHEMA-024 gap, not a
session problem. Open a SCHEMA-NNN-style note in
`docs/schema/decisions/` and bring it to the next planning session.
The runbook should change as the system learns.
