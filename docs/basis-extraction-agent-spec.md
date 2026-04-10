# BASIS — EXTRACTION AGENT SPECIFICATION
## Single-pass extraction following GraphRAG research findings

---

## METHOD

Extraction is a SINGLE PASS per document. Nodes and edges are
extracted together because relationships are visible in the same
text as the entities they connect. Extracting them separately
loses context and produces sparse graphs.

**Phase A:** Per-document extraction (one call per manifesto file)
- Read the full document
- Extract ALL node types and ALL intra-domain edges in one pass
- Relationships are captured AS they're encountered in the text

**Phase B:** Cross-domain edge generation (post-extraction)
- After all 12 domains extracted
- Embed all nodes → similarity search across domains → LLM classifies
- This catches connections invisible within a single document

**Phase C:** Validation sweep (quality gate, not extraction method)
- Check minimum edge counts per node type
- Re-examine any node with zero edges

---

## INPUT

One manifesto domain file (e.g., manifesto-nhs-complete.md).
Each file follows the same structure:
1. The Problem (facts, statistics)
2. What The Parties Propose (party positions)
3. What The Evidence Says (assumptions tested with verdicts)
4. The Evidence-Based Position (policies, mechanisms, costs)
5. Where I Might Be Wrong (failure modes)
6. What Else Should Be Done (innovations/proposals)
7. Cross-Domain Connections (table of links)
8. Sources (grouped by tier)

---

## OUTPUT FORMAT

Two JSON files per domain: `nodes.json` and `edges.json`.

### nodes.json
```json
{
  "domain": "nhs",
  "version": "3.0",
  "extracted_at": "2026-04-09",
  "sources": [ ... ],
  "nodes": [ ... ]
}
```

### edges.json
```json
{
  "domain": "nhs",
  "version": "3.0",
  "extracted_at": "2026-04-09",
  "edges": [ ... ],
  "cross_domain_edges": [ ... ]
}
```

---

## NODE TYPE RULES

### SOURCES (populate from Sources section + body text)
- One SOURCE record per distinct document/publication cited.
- ID format: `SRC-{DOMAIN}-{NNN}` (e.g., SRC-NHS-001)
- Assign tier:

| Tier | Assign when source is... |
|---|---|
| 1 | Peer-reviewed journal (Lancet, BMJ, NBER, Science) |
| 2 | Official statistics body (ONS, OBR, NHS Digital, DWP) |
| 3 | Government-commissioned report/review (Darzi, MAC) |
| 4 | Think tank / academic (IFS, Nuffield, IPPR, King's Fund) |
| 5 | Party manifesto or official party document |
| 6 | Media, commentary, polling |

- `url`: include if present. null if not.
- `date`: YYYY-MM if known. null if not.

### FACT nodes
- One FACT = one verifiable statistical or empirical claim.
- COMPLETE SENTENCE, minimum 30 characters.
- Must reference a source_id.
- Confidence: T1-T2 → HIGH. T3-T4 → MEDIUM. T5-T6 → LOW.
- ID format: `{DOMAIN}-F{NN}`
- Include fiscal metadata where monetary figures present.

**DO:** "7.6 million people were waiting for NHS treatment as of June 2024"
**DON'T:** "Waiting lists are bad" / "7.6m waiting"

### ASSUMPTION nodes
- Each ### Assumption section produces one ASSUMPTION node.
- Statement = the assumption being tested, as a declarative sentence.
- Verdict = the verdict text from the source.
- Confidence: mapped to categorical (HIGH/MEDIUM/LOW).
- ID format: `{DOMAIN}-A{NN}`

### CLAIM nodes
- Analytical conclusions that bridge facts to policies.
- Derived from evidence, not asserted.
- Test: derivable from current data = CLAIM. Testable with future data = ASSUMPTION.
- ID format: `{DOMAIN}-C{NN}`

### POLICY nodes
- Specific proposed actions with mechanism.
- Must describe HOW, not just WHAT.
- Include fiscal metadata where cost/revenue figures exist.
- Innovations from "What Else Should Be Done" get `{"innovation": true}`.
- ID format: `{DOMAIN}-P{NN}`

### POSITION nodes
- One per party per distinct policy stance.
- Complete sentences, not fragments.
- Metadata MUST include:
```json
{"actor": "Conservative", "stance": "endorses", "maps_to": ["NHS-P01"]}
```
- Stance: endorses | contests | modifies | silent
- ID format: `{DOMAIN}-POS-{PARTY}-{NN}`
- Party codes: CON, LAB, LIB, GRN, REF

---

## EDGE RULES

### Edge types
| Type | Meaning |
|---|---|
| SUPPORTS | A provides evidence for B |
| CONTRADICTS | A undermines B |
| DEPENDS_ON | A requires B to be true |
| ENABLES | A makes B more feasible |
| COMPETES | A and B draw from same finite resource |
| SUPERSEDES | A replaces B (newer evidence) |

### Edge format
```json
{
  "from": "NHS-F01",
  "to": "NHS-A01",
  "type": "SUPPORTS",
  "strength": "HIGH",
  "explanation": "The 7.6m waiting list is the primary evidence that clearing lists in one parliament is not achievable"
}
```

### Strength
- HIGH: The text explicitly states the relationship
- MEDIUM: The relationship is clearly implied
- LOW: Plausible but requires inference

### Explanation
- Minimum 10 characters. One sentence. Specific to the pair.
- **DO:** "Darzi's £37bn shortfall undermines the claim that productivity alone closes the gap"
- **DON'T:** "Supports" / "Related" / "Fact supports assumption"

---

## SINGLE-PASS EXTRACTION PROCESS

Read the document section by section. For each section, extract
nodes AND edges simultaneously:

### Section: "The Problem"
→ Extract FACT nodes (statistics, data points)
→ As each fact is extracted, check: does this fact SUPPORT or
  CONTRADICT any assumption or claim that will appear later?
  Note the relationship for edge creation.

### Section: "What The Parties Propose"
→ Extract POSITION nodes (one per party per stance)
→ As each position is extracted, check: which POLICY nodes
  does this relate to? Create maps_to AND an explicit edge.
→ Does any previously extracted FACT contradict this position?
  If so, CONTRADICTS edge.

### Section: "What The Evidence Says"
→ Extract ASSUMPTION nodes (one per ### subsection)
→ As each assumption is extracted:
  - Which FACTs support or contradict the verdict? SUPPORTS/CONTRADICTS edges.
  - Does this assumption feed into a claim? Note for CLAIM edges.

### Section: "The Evidence-Based Position"
→ Extract CLAIM nodes (analytical conclusions)
→ Extract POLICY nodes (proposed actions)
→ As each claim is extracted:
  - Which FACTs and ASSUMPTIONs does it depend on? SUPPORTS/DEPENDS_ON edges.
  - Which POLICYs does this claim inform? DEPENDS_ON edges.
→ As each policy is extracted:
  - Which CLAIMs must be true for this to make sense? DEPENDS_ON edges.
  - What evidence ENABLES this? ENABLES edges.
  - Does this policy COMPETE with another for the same resource? COMPETES edges.

### Section: "Where I Might Be Wrong"
→ These map to LOW confidence edges or contested flags on
  existing nodes. Each "I might be wrong" maps to a specific
  assumption or claim that could fail.

### Section: "What Else Should Be Done"
→ Extract POLICY nodes with `{"innovation": true}`
→ Link to supporting evidence (DEPENDS_ON, ENABLES edges).

### Section: "Cross-Domain Connections"
→ Extract cross-domain edges from the table.
→ Use domain-qualified IDs: "nhs:NHS-A03" → "immigration:IMM-A08"

### Section: "Sources"
→ Populate SOURCE records. Assign tiers.

The key: edges are created IN CONTEXT as you encounter
the relationships in the text, not bolted on afterwards.

---

## FISCAL METADATA RULES

On ANY node with a monetary figure:

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

- `unit`: "bn_gbp" | "m_gbp" | "k_gbp" | "gbp"
- `period`: "annual" | "one_off" | "per_parliament" | "cumulative"
- `direction`: "cost" | "revenue" | "saving"
- `category`: "spending_need" | "tax_reform_revenue" |
  "trade_revenue" | "efficiency_saving" | "cost_avoidance"

---

## VALIDATION (Phase C — quality gate after extraction)

### Node validation
Reject any node where:
- [ ] Statement < 30 characters
- [ ] Source is "See domain sources" or "Platform analysis"
- [ ] Type not in: SOURCE, FACT, ASSUMPTION, CLAIM, POLICY, POSITION
- [ ] FACT has no source_id
- [ ] POSITION has no actor or stance
- [ ] Confidence not in: HIGH, MEDIUM, LOW

### Edge validation
Reject any edge where:
- [ ] Explanation < 10 characters
- [ ] Type not in the 6 valid types
- [ ] Explanation is generic

### Minimum edge counts (re-examine if not met)
- Every FACT: at least 2 outgoing edges
- Every ASSUMPTION: at least 1 incoming + 1 outgoing
- Every CLAIM: at least 1 incoming + 1 outgoing
- Every POLICY: at least 1 DEPENDS_ON
- Every POSITION: at least 1 edge to a POLICY
- Zero-edge nodes mean something was missed

---

## EXPECTED OUTPUT SIZE (per domain)

| Type | Expected count |
|---|---|
| SOURCES | 10-20 |
| FACTs | 10-20 |
| ASSUMPTIONs | 5-10 |
| CLAIMs | 5-10 |
| POLICYs | 8-15 |
| POSITIONs | 10-25 |
| Intra-domain edges | 60-120 (1.5-2.5× node count) |
| Cross-domain edges | 4-10 (from connections table) |

Total across 12 domains: ~600-1000 nodes, 700-1400 edges.
Cross-domain edges multiply significantly after Phase B
embedding similarity pass.
