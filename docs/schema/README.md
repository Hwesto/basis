# Schema decisions — index

Canonical source for each decision and open question lives in this folder.
`schema_decisions.md` in the repo root is retained as a read-only monolith and
will be regenerated from these files.

## Decisions

| ID | Title | Status | Resolves |
|---|---|---|---|
| [SCHEMA-001](decisions/SCHEMA-001-single-base-class-for-all-entities.md) | Single base class for all entities | SETTLED |  |
| [SCHEMA-002](decisions/SCHEMA-002-domainenum-as-typed-extensible-enum.md) | DomainEnum as typed, extensible enum | SETTLED |  |
| [SCHEMA-003](decisions/SCHEMA-003-jurisdictionenum-as-a-hard-constraint-on-legal-content.md) | JurisdictionEnum as a hard constraint on legal content | SETTLED | OQ-005 |
| [SCHEMA-004](decisions/SCHEMA-004-confidence-as-categorical-high-medium-low.md) | Confidence as categorical HIGH/MEDIUM/LOW | SETTLED |  |
| [SCHEMA-005](decisions/SCHEMA-005-computed-confidence-as-mc-output-separate-from-extraction-co.md) | computed_confidence as MC output separate from extraction confidence | SETTLED |  |
| [SCHEMA-006](decisions/SCHEMA-006-curator-approved-as-a-hard-gate-never-bypassed.md) | curator_approved as a hard gate, never bypassed | SETTLED |  |
| [SCHEMA-007](decisions/SCHEMA-007-verified-separate-from-curator-approved.md) | verified separate from curator_approved | SETTLED |  |
| [SCHEMA-008](decisions/SCHEMA-008-five-source-types-as-a-closed-taxonomy-currently.md) | Five source types as a closed taxonomy (currently) | PROVISIONAL |  |
| [SCHEMA-009](decisions/SCHEMA-009-tier-lives-on-the-citation-edge-not-the-source.md) | Tier lives on the citation edge, not the source | PROVISIONAL |  |
| [SCHEMA-010](decisions/SCHEMA-010-structural-sources-are-not-alpha-1-0-alpha-varies-by-registr.md) | STRUCTURAL sources are not alpha=1.0 — alpha varies by registry | PROVISIONAL |  |
| [SCHEMA-011](decisions/SCHEMA-011-commencement-status-as-a-six-value-enum.md) | Commencement status as a six-value enum | SETTLED | OQ-002 |
| [SCHEMA-012](decisions/SCHEMA-012-principle-as-a-ninth-legal-position-type.md) | PRINCIPLE as a ninth legal position type | DEFERRED |  |
| [SCHEMA-013](decisions/SCHEMA-013-fact-vs-assumption-distinction.md) | FACT vs ASSUMPTION distinction | SETTLED |  |
| [SCHEMA-014](decisions/SCHEMA-014-fiscalmetadata-and-gap-role-taxonomy.md) | FiscalMetadata and gap_role taxonomy | SETTLED |  |
| [SCHEMA-015](decisions/SCHEMA-015-evidence-independence-on-supports-edges.md) | Evidence independence on SUPPORTS edges | PROVISIONAL |  |
| [SCHEMA-016](decisions/SCHEMA-016-six-evidence-edge-types.md) | Six evidence edge types | SETTLED |  |
| [SCHEMA-017](decisions/SCHEMA-017-explanation-minimum-length-and-blocklist.md) | Explanation minimum length and blocklist | SETTLED |  |
| [SCHEMA-018](decisions/SCHEMA-018-monte-carlo-over-analytical-propagation.md) | Monte Carlo over analytical propagation | SETTLED |  |
| [SCHEMA-019](decisions/SCHEMA-019-source-alpha-values-and-the-1-5-verification-multiplier.md) | Source alpha values and the 1.5× verification multiplier | PROVISIONAL |  |
| [SCHEMA-020](decisions/SCHEMA-020-assumption-contestability-discount.md) | Assumption contestability discount | PROVISIONAL |  |
| [SCHEMA-021](decisions/SCHEMA-021-lex-graph-as-a-reference-table-not-an-import.md) | Lex Graph as a reference table, not an import | PROVISIONAL |  |
| [SCHEMA-022](decisions/SCHEMA-022-corpus-scoping-via-ego-network-queries.md) | Corpus scoping via ego network queries | PROVISIONAL |  |
| [SCHEMA-023](decisions/SCHEMA-023-legal-consistency-flags-as-ci-checks-7-8.md) | Legal consistency flags as CI checks 7-8 | SETTLED |  |

## Open questions

| ID | Status | Blocking | Phase |
|---|---|---|---|
| [OQ-001](open_questions/OQ-001-should-claim-confidence-and-instantiation-confidence-be-sepa.md) | open | No | 3 |
| [OQ-002](open_questions/OQ-002-what-format-for-conditional-commencement-notes.md) | resolved | — | — |
| [OQ-003](open_questions/OQ-003-how-should-principle-nodes-interact-with-mc-propagation-weig.md) | deferred | No | 4b |
| [OQ-004](open_questions/OQ-004-should-evidence-independent-default-to-true-or-false-current.md) | open | No | 2b |
| [OQ-005](open_questions/OQ-005-how-do-we-handle-provisions-that-apply-to-england-and-wales.md) | resolved | — | — |
| [OQ-006](open_questions/OQ-006-what-is-the-correct-alpha-for-inferred-sources-ml-classifier.md) | open | No | 5 |
| [OQ-007](open_questions/OQ-007-how-does-curator-approved-work-for-derived-nodes-computed-au.md) | open | No | 3 |
| [OQ-008](open_questions/OQ-008-inter-rater-agreement-study-are-high-medium-low-consistently.md) | open | No | 3 |
| [OQ-009](open_questions/OQ-009-gdp-constant-for-pct-gdp-unit-conversion-should-this-be-a-dy.md) | open | No | 2b |
| [OQ-010](open_questions/OQ-010-what-happens-when-lex-graph-provision-ids-change-recovery-pr.md) | open | Yes | 4 |
