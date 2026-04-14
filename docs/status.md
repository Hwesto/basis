# BASIS — build status

Live snapshot of what runs, what's scaffolded, what's blocked. Updated
at the end of each work session. Intended as the single-scan overview
when re-orienting after a break.

**Last updated:** 2026-04-14 (session commits `30f12d8` → HEAD; SCHEMA-024 added)

---

## ✅ Working end-to-end

| Capability | Verified how | Where |
|---|---|---|
| v1 conformance audit | `python scripts/audit_v1_graph.py` → 185/389 nodes pass, 0/172 sources (expected given v1 lacks `publisher` + `default_tier_justification`), 745/745 edges field-valid | `scripts/audit_v1_graph.py`; report at `docs/migration/AUDIT-V1-CONFORMANCE.md` |
| Doc splitter | `python scripts/split_docs.py` — idempotent | `scripts/split_docs.py` |
| `BaseNode` / `CitationEdge` / `FiscalMetadata` (with `amount_low`/`amount_high` range) | Pydantic import + round-trip construction + range validation | `src/base_schema.py` |
| `DocumentarySource` / `StructuralSource` (with `RegistryEnum`) / `StructuredDataSource` / `TestimonySource` / `DerivedSource` | Pydantic construction, MC alpha lookup per registry (`get_structural_alpha('lex_graph') → 0.95`, `'companies_house' → 0.80`) | `src/source_models.py` |
| Ingestion backlog generation | `python scripts/generate_backlog.py` → 172 entries, 172 URLs merged from `archive/v1/data/basis_source_urls.json` | `scripts/generate_backlog.py`, `data/v1_ingestion_backlog.json` |
| URL → DocumentarySource (enrichment path) | `python -m ingest <gov.uk-url>` produces `DocumentarySource(title, publisher='Department of Health and Social Care', default_tier=T2, content_hash, fetched_at, domain)` via gov.uk Content API | `src/ingest/documentary.py`, `src/ingest/enrichment/gov_uk.py` |
| Adapter routing | `DocumentaryAdapter.can_handle` correctly declines ONS API URLs and Lex URLs | `src/ingest/cli.py:ADAPTERS` |
| Scheduled evidence agent | `python src/scripts/run_agent.py evidence --dry-run --max 2` → drains backlog, returns `{ok: 1, fetch_failed: 1}` | `src/scripts/run_agent.py:run_evidence` |
| All 5 agents wired into GitHub Actions cron | `agents.yml` triggers `local_data` 02:00, `structural_signals` 03:00, `legal_extraction` 04:00, `parliamentary` 06:00, `evidence` Mon 05:00 | `src/.github/workflows/agents.yml` |
| Shared v1→v2 migration adapters | Single `src/migration.py` with `V1_DOMAIN_TO_V2`, `V1_FISCAL_DIRECTION_TO_V2`, `map_v1_domain`, `map_v1_fiscal_direction`, `adapt_node_v1_to_v2_payload`, `adapt_source_v1_to_v2_payload`, `adapt_edge_v1_to_v2_payload`. Imported by `scripts/audit_v1_graph.py`, `scripts/generate_backlog.py`, `src/scripts/validate_against_base.py` | `src/migration.py` |
| v1 artefact archive | `archive/v1/data/*` + `archive/v1/site/index.html` preserved with README | `archive/v1/` |

---

## 🟡 Stubbed / scaffolded (imports cleanly, returns safe defaults, needs wiring)

| Capability | Stub returns | What's needed |
|---|---|---|
| Gemma / Flash LLM extraction | `documentary.py` calls `extract_evidence`; currently returns HTTP 403 from `generativelanguage.googleapis.com` with the current key | Google AI key enabled for Generative Language API (AI Studio or GCP Console) |
| Supabase persistence | `SupabasePersistence.write` raises `NotImplementedError` | Wire supabase-py client against `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`; connect to live schema |
| PDF extraction in DocumentaryAdapter | PDF URLs return `FETCH_FAILED` with TODO | `pdfplumber` integration |
| Structural adapter (non-Lex) | Accepts `registry` metadata, emits valid `StructuralSource`, but doesn't fetch | Wire Companies House / Land Registry / ONS NSPL API clients |
| Testimony adapter | Returns `PARSE_FAILED` unless metadata pre-populated | Wire Hansard / TheyWorkForYou / WhatDoTheyKnow fetchers |
| Derived adapter | Constructs `DerivedSource` from passed `input_node_ids` | Caller-populated; no stub code to fix |
| Parliamentary + local_data agents in `run_agent.py` | Print TODO messages | Connect to parliament-mcp (Phase 4 dep) and ONS release calendar |
| v2 frontend | Only v1 static `archive/v1/site/index.html` exists | New Next.js build per `docs/roadmap/04b-v2-phase-2-reingest-deploy.md` |
| Curator queue UI | `src/sql/curator_queue.sql` defines schema, no review UI | Next.js admin page in v2 build (Tier 3 review per SCHEMA-024) |
| Three-tier curator routing (SCHEMA-024) | Decision doc landed; SQL fields + `src/curator/routing.py` not yet implemented | Phase 1 deliverable: SCHEMA-024 fields on `curator_queue` + `evidence_nodes`; Tier 1 logic in `src/curator/routing.py` |
| Verification badge (SCHEMA-024) | Frontend only; no v2 frontend exists yet | Phase 2 deliverable: badge component + routing-chain drawer |
| Calibration study (SCHEMA-024) | Methodology specced; can't run until ≥100 Tier-2 approved nodes exist | Phase 2 gate before any `verification_level=ai_reviewed` enters public API |

---

## 🔴 Blocked on external action

| Blocker | Impact | Fix |
|---|---|---|
| `GOOGLE_AI_API_KEY` returns 403 on `/v1beta/models` | No LLM-assisted node extraction — all ingests produce valid sources but zero candidate nodes | Create a fresh key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) (auto-enables Generative Language API) and paste into `.env` |
| Supabase MCP reauth every session | Can't query live DB from new sessions without browser OAuth dance | Generate Personal Access Token at [supabase.com/dashboard/account/tokens](https://supabase.com/dashboard/account/tokens), add `SUPABASE_ACCESS_TOKEN=sbp_...` to `.env`, add `"headers": {"Authorization": "Bearer ${SUPABASE_ACCESS_TOKEN}"}` to `.mcp.json` |
| `extract_evidence()` expects the legacy `tier: str` signature | Accepts T-letter but skeleton prompt uses old vocabulary | Works as-is; monitor if Gemma output needs prompt tuning when key is enabled |

---

## 🧹 Known duplication / debt

| What | Where | Plan |
|---|---|---|
| ~~`V1_DOMAIN_TO_V2` + node adapter duplicated~~ | ~~`scripts/audit_v1_graph.py` + `src/scripts/validate_against_base.py`~~ | **Resolved** — `src/migration.py` is canonical, all 3 callers import from it |
| Three agents missing from `agents.yml` cron | ~~Only `legal_extraction` + `structural_signals` ran on schedule~~ | **Resolved** — all 5 agents wired |
| Two monolith docs retained with banners | `BASIS_ROADMAP.md` + `schema_decisions.md` at repo root | Kept as historical; canonical lives in `docs/` per-file |
| `docs/basis-spec-final.md` drifted from code in 5 named ways | Banner added in commit `25b3d6e`; still useful for narrative | Migrate unimplemented pipelines (verification §2.9, GAR §3, contested propagation §2.6) to open questions when each becomes Phase-relevant |

---

## Commit log (this session)

```
25b3d6e feat: wire ingestion pipeline end-to-end; mark spec as narrative
3130522 chore: add Supabase MCP server config
e6ff24e data: restore v1 basis_source_urls.json, merge URLs into backlog
287dc31 code+archive: ingest pipeline scaffold, enrichment clients, v1 archive
0e0e6a3 code: propagate v2 schema revisions into src/ (SCHEMA-002, 008, 009, 014)
e3ff9aa chore: commit skeleton under src/ as baseline for v2 Phase 1 edits
04e7677 docs: rewrite top-level README for v2 rebuild framing
fe28f13 docs: reframe roadmap for v2 rebuild (archive v1 phases, add v2 1/2)
30f12d8 docs: migration anchor + SCHEMA-002/014 revisions + splitter cleanup
9a698b6 audit: conformance check of v1 graph against reconciled v2 schema
9869976 docs: split roadmap and schema decisions into per-file canonical form
0f7d3c0 docs: reconcile 7 inconsistencies between roadmap and schema decisions
```

---

## Calibration knobs

Numeric thresholds whose right value isn't known yet. Initial values
are placeholders. Each row records what observation would justify
changing it and which pipeline stage produces that observation. Do
not change without evidence.

| Knob | Initial value | Source | Change when... | Data comes from |
|---|---|---|---|---|
| Calibration sample size | 100 nodes | SCHEMA-024 | Agreement variance is too high to trust the % at this N | First Tier 2 batch in Phase 2 |
| Calibration agreement bar | ≥90% | SCHEMA-024 | Bar repeatedly missed even after Tier 1 tightening (signal: design is wrong, not threshold) | Phase 2 calibration study |
| Ongoing spot-check rate | 5% of `approved_by=claude` weekly | SCHEMA-024 | Drift detected (lower agreement than initial calibration) — increase rate; or no drift over 6 months — decrease | Weekly spot-check job (Phase 2+) |
| First-N: new domain calibration | 20 nodes | SCHEMA-024 | First batch hits ≥95% agreement consistently — drop. Or hits <85% — raise. | First time each new domain is ingested |
| First-N: new source calibration | 5 nodes | SCHEMA-024 | Same logic as new-domain | Each new source first appears |
| Kickback recurrence threshold | 3 errors / 30 days → propose Tier 1 rule | SCHEMA-024 | Too many false alarms (3 is too low) or too many genuine patterns slipping (3 is too high) | Kickback workflow logs |
| Escalation-reason alarm | >30% of weekly escalations from one reason | SCHEMA-024 | Alarm fires too often / never — adjust | Weekly escalation_reason histogram |
| MC engine sample count | 10,000 | SCHEMA-018 | Confidence interval at p5/p95 too wide — increase | After first MC run on v2 graph |
| Documentary alpha (T1, verified, well-cited) | 0.95 | SCHEMA-019 | Empirical accuracy of T1 nodes diverges materially from 0.95 prior | After 6 months of audited node accuracy |
| Assumption contestability cap | HIGH→0.85, MEDIUM→0.70, LOW→0.50 | SCHEMA-020 | Top-5 ASSUMPTION node accuracies don't match these caps | After top-20 CLAIM audit (SCHEMA-015) |

**Promotion rule:** when a knob's empirical evidence justifies a
change, update both the SCHEMA decision (with a note recording the
change) and this row. Do not silently change values in code without
the doc trail.

---

## Maintenance rule

This doc is the first thing edited at the end of every session that
materially changes what works. Sections:

1. **Working end-to-end** — promote only when verified by running the
   code, not by reading it.
2. **Stubbed / scaffolded** — things that import cleanly and return
   safe values but don't actually do the advertised job.
3. **Blocked on external action** — infrastructure gaps that no code
   change can fix.
4. **Known duplication / debt** — carried-forward cleanup items.
5. **Calibration knobs** — numeric thresholds awaiting empirical
   observation; never change without evidence + doc trail.

Remove from this doc only when the underlying issue is closed, not
when it's merely deferred.
