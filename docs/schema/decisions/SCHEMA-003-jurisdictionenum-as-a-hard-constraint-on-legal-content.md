---
id: SCHEMA-003
title: JurisdictionEnum as a hard constraint on legal content
status: SETTLED
resolves: [OQ-005]
source: schema_decisions.md
---

### SCHEMA-003: JurisdictionEnum as a hard constraint on legal content

**Phenomenon:** UK law is devolved. Housing law differs between England, Wales, Scotland,
and Northern Ireland. A right that applies in England may not apply in Scotland.

**Decision:** `JurisdictionEnum` with six members: `england`, `wales`, `scotland`, `ni`,
`england_and_wales`, `uk_wide`. Applied at query time, not display time — a Scottish
postcode never receives England-only legal nodes from the API, even if they happen to be
in the response cache. `england_and_wales` is a first-class jurisdiction (not a
multi-jurisdiction shorthand) because the vast majority of devolved housing, health,
and education legislation applies jointly to those two jurisdictions and distinguishing
them produces false negatives at query time.

**Alternatives:**
- Soft filtering at display time. Rejected: depends on frontend developers consistently
  applying the filter. Any miss results in displaying wrong law to citizens.
- Single 'united_kingdom' jurisdiction. Rejected: legally incorrect for devolved matters.
  It would be accurate for reserved matters (immigration, benefits) but wrong for
  housing, education, health. Cannot be correct in the general case.
- Free-text jurisdiction. Rejected: same problems as free-text domain.

**Assumptions:**
1. The six-jurisdiction model is sufficient. Currently correct. If we later encounter
   legislation that applies in three but not four jurisdictions (e.g. GB-wide but not
   NI), we extend the enum rather than introduce a `multi_jurisdiction` list field.
2. Postcode-to-jurisdiction resolution is reliable. ONS NSPL is authoritative. True.

**Falsification:**
- Discovery of legislation whose scope cannot be represented by any single enum member
  (e.g. "England and Scotland but not Wales or NI"). No such case observed in the top
  20 priority domains. Flag and extend the enum when first encountered.

**Status:** SETTLED — `england_and_wales` added in `base_schema.py`. Resolves OQ-005.
