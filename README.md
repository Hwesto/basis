# BASIS — Building an Accountable, Structured, Informed Society

An evidence-based civic platform that structures political claims as machine-readable evidence.

**389 nodes · 745 edges · 172 sources · 12 domains · 9 facts literature-verified**

## Phase 0: Manifesto Seed

**Live:** https://hwesto.github.io/basis/

## What this is

A manifesto built from evidence forward to policy, not from ideology backward to justification. Every assumption is stated. Every claim is sourced. Every policy is costed. The graph is open. If we're wrong, show us where — with evidence.

## The central finding

Add up the evidence-based spending needs across 12 UK policy domains and compare them to the revenue any party proposes to raise. The gap is **£44–146 billion per year**. No party acknowledges it.

## Structure

```
site/           → Self-contained HTML site (deploy to any static host)
data/           → Consolidated knowledge graph (JSON)
data/domains/   → Per-domain node and edge files
manifestos/     → 12 domain source documents + cross-domain consolidation
docs/           → Platform spec, extraction methodology, verification findings
```

## The 12 domains

| Domain | Nodes | Sources | Key finding |
|--------|-------|---------|-------------|
| NHS & Health | 44 | 20 | Every party's funding falls £20-25bn/yr short |
| Immigration | 51 | 20 | No blanket fiscal statement is honest |
| Housing | 37 | 17 | 4.3m homes missing, private sector can't deliver alone |
| Taxation | 34 | 11 | Tax locks force fiscal dishonesty |
| Welfare | 33 | 15 | Two-child limit is the clearest policy failure |
| Education | 32 | 10 | Every workforce crisis traces here |
| Energy & Climate | 39 | 19 | The grid is the bottleneck |
| Defence | 25 | 13 | 5% GDP is "incompatible with a welfare state" |
| EU & Trade | 25 | 12 | £5-10bn buys £100-200bn in GDP |
| Environment | 24 | 11 | Nature is infrastructure priced at zero |
| Electoral Reform | 23 | 12 | FPTP is the structural cause |
| Justice | 23 | 12 | The vicious cycle of defunding |

## Node types

- **FACT** — Verifiable empirical statement with cited source
- **ASSUMPTION** — Commonly believed claim, tested against evidence (with verdict)
- **CLAIM** — Derived analytical finding from multiple facts
- **POLICY** — Evidence-based recommendation
- **POSITION** — What a political party actually proposes

## Evidence tiers

- **T1** Empirical (peer-reviewed research)
- **T2** Official statistics (ONS, HMRC, MOD)
- **T3** Institutional (IFS, OBR, NAO, Select Committees)
- **T4** Expert (think tanks, policy institutes)
- **T5** Political (party manifestos)

## Deployment

The site is a single self-contained HTML file. Deploy to any static host:

```bash
cp site/index.html public/index.html
```

## Licence

Content: CC BY-SA 4.0  
Code: MIT
