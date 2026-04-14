---
phase: 8
status: planned
source: BASIS_ROADMAP.md
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
