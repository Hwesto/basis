---
phase: 7
status: planned
source: BASIS_ROADMAP.md
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
