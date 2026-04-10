# KNOWLEDGE GRAPH CONSTRUCTION — RESEARCH FINDINGS
## How the field does it vs how BASIS should do it

---

## THE STATE OF THE ART

### Microsoft GraphRAG (the dominant approach)
Pipeline: chunk text → LLM extracts entities + relationships in
ONE PASS → merge duplicates → community detection → summaries.

Key detail: entities and relationships are extracted TOGETHER,
not in separate sweeps. The LLM sees a text chunk and outputs:
- Entity: "NHS", type: Organisation
- Entity: "7.6 million", type: Statistic
- Relationship: NHS → has_waiting_list → 7.6 million

This is a single structured output call, not nine sweeps.

### ATLAS System (Oct 2025)
- 900 million nodes, 5.9 billion edges
- Processed 50 million documents from Dolma corpus
- 95% semantic alignment with human-crafted schemas
- Zero manual intervention
- Proves: LLM extraction works at massive scale

### Key finding across all research
"LLMs already understand language structure, entity types, and
common relationships from their training. You don't need to
build specialized models from scratch — you need to teach the
LLM your specific schema and let it extract accordingly."
(Branzan, 2025)

"Few-shot prompting with GPT-4 or Claude achieves accuracy
roughly equivalent to — and sometimes superior to — fully
supervised traditional models, but without requiring thousands
of labeled training examples."

---

## WHAT THIS MEANS FOR BASIS

### Our advantage: constrained schema
Most GraphRAG systems do OPEN extraction — any entity, any
relationship type, discovered from the text. This is harder
because the LLM has to invent the schema.

BASIS has a PREDEFINED schema: 6 node types, 6 edge types,
evidence tiers, fiscal metadata. This is easier. We tell the
LLM exactly what to look for. The extraction prompt IS the
schema definition.

### The correct extraction approach

**For seed data (manifesto files):**
One LLM call per document. The prompt contains the full schema
(node types, edge types, examples) and says: "Extract all nodes
and edges from this document following this schema."

Output: complete JSON with nodes AND edges in one pass.

This is what I (Claude) should be doing — reading the full
manifesto file and outputting the complete graph in one
structured response. Not extracting nodes first, then doing
separate edge sweeps. The relationships are visible IN the
text at the same time as the entities.

**For new documents (production pipeline):**
Same approach. Document comes in → one LLM call extracts all
nodes and edges → merge with existing graph (deduplicate entities
that already exist) → curate.

**For edge densification (cross-document connections):**
This is where embeddings come in. After individual documents
are extracted, nodes from DIFFERENT documents need connecting.
The LLM can't see connections across documents in a single pass
because it only reads one document at a time.

Pipeline:
1. Embed all nodes
2. For each node, find top-K similar nodes from OTHER documents
   (cosine similarity, threshold ~0.75)
3. For each candidate pair above threshold, LLM classifies:
   "Is there a meaningful relationship? What type? Or NONE?"
4. Create edges where LLM confirms

This is the CROSS-DOMAIN DETECTION pipeline from the spec.
It runs AFTER per-document extraction. It's where the
transformer analogy holds — each node attending to every
other node across the full graph.

### The 9-sweep was wrong
The 9-sweep approach in the extraction spec encoded manual
domain knowledge about which type-pairs to check. The automated
version doesn't need this because:
- Embedding similarity naturally surfaces relevant pairs
- The LLM can classify any pair it's shown, regardless of type
- You don't need to enumerate FACT→ASSUMPTION, FACT→CLAIM etc.
  separately — the LLM figures out the relationship type

The 9-sweep is useful as a VALIDATION CHECK (did we miss any
fact-to-assumption connections?) but not as the extraction
method itself.

---

## REVISED EXTRACTION APPROACH FOR BASIS

### Step 1: Per-document extraction (single LLM call)
Input: Full manifesto .md file + schema definition
Prompt: "Extract all sources, facts, assumptions, claims,
policies, positions, AND their relationships from this
document. Output as structured JSON."
Output: nodes.json + edges.json (intra-document)

The LLM sees relationships IN CONTEXT. "Darzi says 7.6m
waiting (FACT) which means lists can't clear in one parliament
(ASSUMPTION verdict)" — the SUPPORTS edge is visible in the
same paragraph.

### Step 2: Cross-document edge generation (embeddings + LLM)
After all 12 domains extracted:
1. Embed all ~600 nodes
2. For each node, find 10 nearest from OTHER domains
3. Filter: cosine similarity > 0.5 (generous threshold)
4. For each candidate pair: LLM classifies relationship
5. This produces cross-domain edges automatically

### Step 3: Validation (the sweep as a check, not a method)
Run the sweep logic as validation:
- Any FACT with 0 outgoing edges? Missed something.
- Any POLICY with 0 DEPENDS_ON? Missed something.
- Any POSITION with 0 edges to a POLICY? Missed something.

The sweep catches gaps. It doesn't do the extraction.

---

## COST COMPARISON

| Approach | API Calls | Est. Cost |
|---|---|---|
| 9-sweep per domain (old spec) | 12 domains × 9 sweeps × ~50 pairs = ~5,400 calls | ~$8 |
| Single-pass extraction (GraphRAG style) | 12 calls (one per domain) + ~3,000 cross-domain pairs | ~$7 |
| Hybrid: single-pass + embed + classify cross-domain | 12 + ~500 (after similarity filtering) | ~$4 |

The hybrid approach is cheapest because embedding similarity
filters out 90%+ of candidate pairs before hitting the LLM.

---

## WHAT CHANGES IN THE SPEC

The extraction agent spec should be updated:

1. **Per-document extraction** is a single structured output call,
   not a sequential node-then-edge process
2. **The 9-sweep becomes a validation check**, not the extraction
   method
3. **Cross-domain edges** use embedding similarity + LLM
   classification (Pipeline 2 from the platform spec)
4. **The extraction order** becomes: extract per document →
   validate → embed → cross-link → validate again
