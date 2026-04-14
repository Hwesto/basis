---
phase: 0
status: v1_archived
source: BASIS_ROADMAP.md
---

> **v1 — archived.** This phase shipped a working prototype that proved the
> "show your working" framing. That site is still live at
> `hwesto.github.io/basis` and will be preserved at the `/v1/` sub-route
> after v2 cutover. The schema this phase was built against was superseded
> by `docs/schema/` — see `docs/migration/README.md` for why the v1 corpus
> is archived rather than migrated.

### Phase 0 (v1): Manifesto Seed — ARCHIVED

**What it delivered:** A public, shareable demonstration. Single-link
proof that "we show our working" means something: every claim in the
manifesto had a visible source, tier, and confidence. Evidence graph
explorer. GitHub Pages deployment.

**Outcome:** The framing worked. Users understood "underlined claims
open a side panel with the source". The 389-node graph was sufficient
to demonstrate the £44–146bn fiscal gap from metadata alone.

**What becomes of this in v2:** The manifesto markdowns
(`manifestos/*.md`) are preserved unchanged as input corpus for the v2
re-ingestion pass. The single-page site at `site/index.html` is frozen
and served from `archive/v1/site/` at `/v1/` after cutover.

**Status:** ✅ v1-shipped. Frozen for the v2 rebuild.
