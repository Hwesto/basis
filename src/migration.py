"""
migration.py — v1 -> v2 field adapters and the canonical v1 domain map.

Shared by:
- scripts/audit_v1_graph.py (conformance report against archived v1 JSON)
- scripts/generate_backlog.py (extract source URLs into v2 ingestion backlog)
- src/scripts/validate_against_base.py (v1-data-against-base validator)

When a new v1 → v2 transform is needed, add it here. Do not duplicate
across callers; that's how the SCHEMA-002 domain extension drifted out
of step in commit history.

Background:
- v1 stored a custom domain vocabulary ("nhs", "welfare", "eu-trade",
  "electoral-reform") that doesn't all align with the v2 DomainEnum.
- v1 stored fiscal metadata as separate `amount_low` / `amount_high`
  fields with `direction in {cost, revenue, saving}` and
  `category in {spending_need, ...}` — see SCHEMA-014 v2 reconciliation.
- v1 stored `type` (not `node_type`), `from`/`to` (not `from_id`/`to_id`),
  integer tiers (not "T1"-"T6"), tier on the source record (not on the
  citation edge — superseded by SCHEMA-009).

References:
    SCHEMA-002 (DomainEnum v2 extension)
    SCHEMA-008 (source taxonomy: 5 types)
    SCHEMA-009 (tier on citation edge, not source)
    SCHEMA-014 (FiscalMetadata range fields restored)
    docs/migration/AUDIT-V1-CONFORMANCE.md (audit results driving these)
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Canonical v1 -> v2 domain map
# ---------------------------------------------------------------------------
#
# v1 domain values that already match v2 DomainEnum members are passed
# through unchanged. The three entries that don't match v2 names map
# to either renamed equivalents (nhs -> health, welfare -> benefits)
# or to v2 entries added in the SCHEMA-002 v2 extension (energy,
# eu-trade -> eu_trade, electoral-reform -> electoral_reform).

V1_DOMAIN_TO_V2: dict[str, str] = {
    "housing": "housing",
    "nhs": "health",
    "education": "education",
    "welfare": "benefits",
    "taxation": "taxation",
    "environment": "environment",
    "immigration": "immigration",
    "defence": "defence",
    "justice": "justice",
    # v2 DomainEnum extended to include these three (SCHEMA-002 v2):
    "energy": "energy",
    "eu-trade": "eu_trade",
    "electoral-reform": "electoral_reform",
}


def map_v1_domain(v1_domain: str | None) -> str | None:
    """Return the v2 DomainEnum value for a v1 domain string, or pass-through."""
    if v1_domain is None:
        return None
    return V1_DOMAIN_TO_V2.get(v1_domain, v1_domain)


# ---------------------------------------------------------------------------
# v1 -> v2 fiscal direction map (SCHEMA-014)
# ---------------------------------------------------------------------------
#
# v1 used `cost | revenue | saving`. v2 uses `spending | revenue | net`.
# saving has no clean v2 analogue — represented as net (a flow that
# doesn't increase spending). The audit at
# docs/migration/AUDIT-V1-CONFORMANCE.md flagged this as a known
# semantic-loss conversion.

V1_FISCAL_DIRECTION_TO_V2: dict[str, str] = {
    "cost": "spending",
    "revenue": "revenue",
    "saving": "net",
}


def map_v1_fiscal_direction(v1_direction: str | None) -> str | None:
    if v1_direction is None:
        return None
    return V1_FISCAL_DIRECTION_TO_V2.get(v1_direction, v1_direction)


# ---------------------------------------------------------------------------
# Node payload adapter
# ---------------------------------------------------------------------------

def adapt_node_v1_to_v2_payload(n: dict) -> dict:
    """
    Best-effort transform from v1 node shape to v2 Pydantic BaseNode payload.

    Does NOT invent data — missing required fields are reported by validation
    downstream. v1 fiscal data is partially adapted (direction values mapped)
    but range fields are passed through under their existing v1 keys, since
    SCHEMA-014 v2 also uses `amount_low` / `amount_high`.
    """
    out: dict[str, Any] = {
        "id": n.get("id"),
        "node_type": n.get("node_type") or n.get("type"),  # v1 uses 'type'
        "statement": n.get("statement"),
        "source_id": n.get("source_id") or None,
        "source_loc": n.get("source_loc"),
        "confidence": n.get("confidence"),
        "domain": map_v1_domain(n.get("domain")),
        "verified": bool(n.get("verified", False)),
    }

    fiscal = n.get("fiscal")
    if isinstance(fiscal, dict):
        adapted_fiscal: dict[str, Any] = dict(fiscal)
        if "direction" in adapted_fiscal:
            adapted_fiscal["direction"] = map_v1_fiscal_direction(
                adapted_fiscal["direction"]
            )
        out["fiscal"] = adapted_fiscal

    return out


# ---------------------------------------------------------------------------
# Source payload adapter
# ---------------------------------------------------------------------------

def adapt_source_v1_to_v2_payload(s: dict) -> dict:
    """
    v1 sources have no source_type discriminator and no
    default_tier_justification. Heuristic: assume DOCUMENTARY for
    everything in the v1 catalogue (which it is — every entry is a
    citable document with author, title, date, tier).

    v1 stored integer tier (1-6); v2 expects 'T1'-'T6' on default_tier.
    """
    raw_tier = s.get("tier")
    if isinstance(raw_tier, int):
        tier = f"T{raw_tier}"
    elif isinstance(raw_tier, str) and raw_tier.startswith("T"):
        tier = raw_tier
    else:
        tier = None

    return {
        "source_id": s.get("source_id") or s.get("id"),
        "source_type": s.get("source_type") or "DOCUMENTARY",
        "title": s.get("title"),
        "author": s.get("author"),
        "publisher": s.get("publisher"),  # v1 lacks; will fail validation
        "published_date": s.get("published_date") or s.get("date"),
        "url": s.get("url"),
        "default_tier": tier,
        "default_tier_justification": s.get("default_tier_justification"),
        "domain": map_v1_domain(s.get("domain")),
    }


# ---------------------------------------------------------------------------
# Edge payload adapter
# ---------------------------------------------------------------------------

def adapt_edge_v1_to_v2_payload(e: dict, synthetic_id: str | None = None) -> dict:
    """v1 edges use `from`/`to`/`type`; v2 EvidenceEdge uses _id suffixed."""
    return {
        "id": e.get("id") or synthetic_id,
        "from_id": e.get("from_id") or e.get("from"),
        "to_id": e.get("to_id") or e.get("to"),
        "edge_type": e.get("edge_type") or e.get("type"),
        "explanation": e.get("explanation"),
        "strength": e.get("strength"),
    }
