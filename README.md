# BASIS — Building an Accountable, Structured, Informed Society

An evidence-based civic platform that structures political claims as
machine-readable evidence, links them to primary sources, and tests
them against fiscal arithmetic.

> **🚧 Rebuild in progress.** The v1 prototype (389 nodes, 172 sources)
> is live at [hwesto.github.io/basis](https://hwesto.github.io/basis/)
> and demonstrates the "show your working" framing. The v2 build against
> a formalised schema is under way — see
> [`docs/migration/README.md`](docs/migration/README.md) for the
> reasoning and [`docs/roadmap/README.md`](docs/roadmap/README.md) for
> current status. v1 stays live during the rebuild and will be preserved
> at a `/v1/` sub-route after v2 cutover.

## What this is

A manifesto built from evidence forward to policy, not from ideology
backward to justification. Every assumption is stated. Every claim is
sourced. Every policy is costed. The graph is open. If we're wrong,
show us where — with evidence.

## The central finding (v1)

Add up the evidence-based spending needs across 12 UK policy domains
and compare them to the revenue any party proposes to raise. The gap
is **£44–146 billion per year**. No party acknowledges it.

The v2 rebuild preserves this finding and the methodology, but
re-derives the numbers against the formalised schema so the
computation is auditable end-to-end.

## Repository structure

```
docs/
  schema/             Per-decision schema contract (23 SCHEMA + 10 OQ)
  roadmap/            Per-phase build plan (v1 archived + v2 active)
  migration/          v1 → v2 archive plan + audit
  basis-spec-final.md Combined specification document (v1)
src/                  Python implementation (extracted from skeleton,
                      gitignored until v2 Phase 1 lands)
scripts/              Dev tooling — doc splitter, v1 audit, future validator
data/                 v1 knowledge graph (to be moved to archive/v1/)
manifestos/           13 source manifesto documents (preserved as v2
                      input corpus)
site/                 v1 self-contained HTML (to be moved to
                      archive/v1/ at cutover)
```

## Schema decisions and open questions

The schema contract is split into one file per decision at
[`docs/schema/decisions/`](docs/schema/decisions/) and one file per
open question at [`docs/schema/open_questions/`](docs/schema/open_questions/).
See [`docs/schema/README.md`](docs/schema/README.md) for the live
status index.

23 decisions total — 13 settled, 9 provisional, 1 deferred.
10 open questions — 2 resolved, 1 deferred, 7 open.

## Node types (v2)

- **FACT** — verifiable empirical statement with cited source
- **ASSUMPTION** — interpretive claim; must list basis facts and a
  falsification condition
- **CLAIM** — derived analytical finding from multiple facts
- **POLICY** — evidence-based recommendation
- **POSITION** — what a political party actually proposes
- Legal layer: RIGHT, DUTY, POWER, LIABILITY, PRIVILEGE, IMMUNITY,
  REGULATORY_BODY, MECHANISM, EVIDENCE_REQUIREMENT, ESCALATION_PATH,
  PRECEDENT
- Local: AREA_METRIC
- Action: TEMPLATE, SUBMISSION, OUTCOME

## Source types (v2)

Five categorically different provenance models, one discriminator:

- **DOCUMENTARY** — human-authored documents with tier T1–T6
- **STRUCTURED_DATA** — datasets and API responses, tier T1–T3
- **STRUCTURAL** — registry records; alpha per registry (Lex Graph,
  Companies House, ONS NSPL, Land Registry)
- **DERIVED** — computations from other nodes; confidence inherited
- **TESTIMONY** — stated positions; tier ceiling T3

## Evidence tiers

Tier lives on the **citation edge**, not the source (SCHEMA-009). Each
source carries a `default_tier` as a prior; individual citations can
override with `claim_tier_override` plus mandatory justification.

- **T1** Empirical (peer-reviewed research, ONS headline stats)
- **T2** Official statistics (HMRC, MOD, department publications)
- **T3** Institutional (IFS, OBR, NAO, Select Committees)
- **T4** Expert (think tanks, policy institutes)
- **T5** Political (party manifestos)
- **T6** Contested or low-provenance secondary material

## The 12 v1 domains

v1 coverage by policy domain. v2 extends `DomainEnum` to cover
`energy`, `eu_trade`, and `electoral_reform` as first-class members
(22% of v1 nodes were in these domains with ad-hoc labels).

| Domain | v1 nodes | v1 sources | Key finding |
|---|---|---|---|
| NHS & Health | 44 | 20 | Every party's funding falls £20–25bn/yr short |
| Immigration | 51 | 20 | No blanket fiscal statement is honest |
| Housing | 37 | 17 | 4.3m homes missing, private sector can't deliver alone |
| Taxation | 34 | 11 | Tax locks force fiscal dishonesty |
| Welfare | 33 | 15 | Two-child limit is the clearest policy failure |
| Education | 32 | 10 | Every workforce crisis traces here |
| Energy & Climate | 39 | 19 | The grid is the bottleneck |
| Defence | 25 | 13 | 5% GDP is "incompatible with a welfare state" |
| EU & Trade | 25 | 12 | £5–10bn buys £100–200bn in GDP |
| Environment | 24 | 11 | Nature is infrastructure priced at zero |
| Electoral Reform | 23 | 12 | FPTP is the structural cause |
| Justice | 23 | 12 | The vicious cycle of defunding |

## Development

v2 Phase 1 is in progress. See
[`docs/roadmap/04a-v2-phase-1-pipeline.md`](docs/roadmap/04a-v2-phase-1-pipeline.md)
for the current phase plan.

```bash
# Re-run the v1 conformance audit (diagnostic; does not modify data)
python scripts/audit_v1_graph.py

# Re-split the monolith docs (idempotent)
python scripts/split_docs.py
```

`src/` is extracted from `basis_full_build.tar.gz` and gitignored
while the ingestion pipeline is being completed. Once committed, the
skeleton becomes the canonical source.

## Licence

Content: CC BY-SA 4.0
Code: MIT
