---
phase: foundation
status: planned
source: BASIS_ROADMAP.md
---

### Foundation — schema_decisions.md + base_schema.py + source_models.py (prerequisite for all phases)

**Three files. Written in this order. The contract everything is built against.**

`schema_decisions.md` comes first. Before any code. Every node type, edge type, and confidence parameter has an entry recording: the phenomenon it represents, what we chose, alternatives considered, assumptions made, and what would cause us to revise. This is the manifesto applied to the schema itself — every design choice is a claim that needs a source and reasoning. Without it, when Gemma makes extraction errors you can't tell whether it's a model failure or a schema ambiguity. When a legal challenge surfaces a case the schema can't handle, you don't know which assumption is being violated.

`base_schema.py` then implements what the decisions file specifies. `source_models.py` implements the five source type subclasses with MC alpha values and type-specific validation rules.

**Key decisions documented in schema_decisions.md (v0.1):**

- **SCHEMA-001:** Single BaseNode root class — one curator queue, one CI validator, one MC engine. Domain-specific fields on subclasses only.
- **SCHEMA-002:** DomainEnum typed — free-text domain fields rejected at validation.
- **SCHEMA-003:** JurisdictionEnum — six members: `england`, `wales`, `scotland`, `ni`, `england_and_wales`, `uk_wide`. Resolves OQ-005.
- **SCHEMA-004:** Confidence categorical (HIGH/MEDIUM/LOW) — false precision argument against decimal scores upheld.
- **SCHEMA-006:** curator_approved as hard gate — DERIVED node exception requires cleaner contract (OQ-007).
- **SCHEMA-009:** Tier lives on citation edge, not source — migration from Phase 1 source-level tier required.
- **SCHEMA-010:** STRUCTURAL source alpha by registry, not by category — values are provisional priors, not measurements.
- **SCHEMA-011:** Commencement status as six-value enum — `in_force`, `partially_in_force`, `not_commenced`, `prospectively_repealed`, `repealed`, `unknown`. Resolves OQ-002.
- **SCHEMA-012:** PRINCIPLE as ninth legal position — weight-based norms that can't be encoded as binary Hohfeld.
- **SCHEMA-015:** Evidence independence flag on SUPPORTS edges — current default (True) is overconfident; manual audit of top 20 high-confidence CLAIMs required before Phase 2b.
- **SCHEMA-019:** MC alpha values are design choices, not measurements — provisional, require calibration study.
- **SCHEMA-020:** Assumption contestability discount (HIGH→0.85, MEDIUM→0.70, LOW→0.50) — provisional values.
- **SCHEMA-021:** Lex Graph as reference table — principal external dependency risk documented.

**10 open questions** requiring resolution before specific phases — see schema_decisions.md §Part 7.

**Immediate actions before any further extraction:**
1. Manual audit of top 20 high-confidence CLAIM nodes for correlated evidence (SCHEMA-015)
2. Validate all 389 existing nodes against BaseNode — every mismatch is a known gap
3. Validate all 172 sources against BaseSource — identify tier-on-source instances requiring migration
4. ~~Resolve OQ-005~~ **RESOLVED** — `england_and_wales` added to `JurisdictionEnum` in `base_schema.py`

**Status:** ⏳ schema_decisions.md v0.1 written. base_schema.py and source_models.py to follow.

---
