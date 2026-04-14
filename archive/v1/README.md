# archive/v1/ — frozen v1 artefacts

This directory preserves the v1 build — 389 nodes, 172 sources, 746
edges — as it existed at the point the v2 rebuild started. It is
**read-only**. Do not edit these files; do not regenerate them.

The v1 site at `hwesto.github.io/basis` continues to render from this
archive until v2 cutover, at which point `site/index.html` becomes
accessible at the `/v1/` sub-route of the new site.

## Contents

```
archive/v1/
├── README.md                 (this file)
├── data/
│   ├── basis-kg-full.json    389 nodes · 172 sources · 745 edges
│   ├── basis-kg-compact.json Derived compact view
│   ├── basis-data.js         Inline JS bundle for the single-page site
│   └── domains/              12 per-domain {nodes,edges}.json files
└── site/
    └── index.html            Single-page gh-pages site
```

## Why this is archived

The v1 schema pre-dates `docs/schema/`. The conformance audit
(`docs/migration/AUDIT-V1-CONFORMANCE.md`) showed the v1 corpus cannot
migrate cleanly:

- 0 / 172 sources pass the v2 `BaseSource` contract (missing
  `publisher` and `default_tier_justification`)
- 137 / 389 nodes pass `BaseNode` pre-migration; 185 / 389 after
  v2 `DomainEnum` extension (SCHEMA-002 revision)
- v1 captured fiscal metadata as `[amount_low, amount_high]` ranges;
  the v2 draft dropped this. SCHEMA-014 has since been revised to
  restore range support.
- v1 sources have **no URLs** (`url: null` on every entry).
  `data/v1_ingestion_backlog.json` at the repo root lists them by
  title/author/date for v2 re-ingestion with URL recovery via
  CrossRef / Semantic Scholar / gov.uk / publisher search.

See `docs/migration/README.md` for the full rebuild plan.

## What v1 proved

- The "show your working" framing works as a product concept
- 389 evidence nodes across 12 domains produced a £44–146bn fiscal gap
  from metadata alone — the central finding is epistemically
  reproducible
- Next.js + Supabase frontend stack renders the graph legibly
- Monte Carlo confidence propagation converges on a manageable set of
  categorical labels (HIGH/MEDIUM/LOW) without decimal false precision

These lessons are canonical. The code that produced them is not.

## Regeneration / replacement

Once v2 Phase 2 completes (`docs/roadmap/04b-v2-phase-2-reingest-deploy.md`):

- Live site at `hwesto.github.io/basis` is replaced with the v2 Next.js
  app reading from Supabase
- This directory is served at `/v1/` sub-route for provenance
- The `archive/v1` branch (if created) is the tag point for v1-final
