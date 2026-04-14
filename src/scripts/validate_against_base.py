#!/usr/bin/env python3
"""
validate_against_base.py — Validate existing Phase 1 data against new schema.

Immediate actions from Foundation roadmap:
1. Validate all 389 existing nodes against BaseNode — every mismatch is a known gap
2. Validate all 172 sources against BaseSource — identify tier-on-source migration needs
3. Flag nodes missing required fields for their subclass type
4. Report SCHEMA-009 migration candidates (tier on source, needs to move to citation edge)

Run once before any Phase 2b work begins.
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError

from base_schema import (
    BaseNode,
    ClaimNode,
    DomainEnum,
    FactNode,
    AssumptionNode,
    NodeType,
    PolicyNode,
    PositionNode,
)
from source_models import (
    BaseSource,
    DocumentarySource,
    SourceTypeEnum,
    StructuredDataSource,
    TestimonySource,
)


NODE_TYPE_MAP = {
    "FACT": FactNode,
    "ASSUMPTION": AssumptionNode,
    "CLAIM": ClaimNode,
    "POLICY": PolicyNode,
    "POSITION": PositionNode,
}


def load_all_json(directory: Path) -> list[dict]:
    """Recursively load all JSON from a directory."""
    items = []
    if not directory.exists():
        return items
    for f in directory.rglob("*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    items.extend(data)
                elif isinstance(data, dict):
                    if "nodes" in data:
                        items.extend(data["nodes"])
                    elif "id" in data:
                        items.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    return items


def validate_nodes(nodes: list[dict]) -> dict:
    """Validate each node against BaseNode and its appropriate subclass."""
    report = {
        "total": len(nodes),
        "valid_base": 0,
        "valid_subclass": 0,
        "base_errors": [],
        "subclass_errors": [],
        "missing_fields": [],
        "domain_issues": [],
        "type_distribution": Counter(),
    }

    valid_domains = {d.value for d in DomainEnum}

    for node in nodes:
        node_id = node.get("id", "UNKNOWN")
        node_type = node.get("node_type", "UNKNOWN")
        report["type_distribution"][node_type] += 1

        # Check domain
        domain = node.get("domain")
        if domain and domain not in valid_domains:
            report["domain_issues"].append({
                "id": node_id,
                "domain": domain,
                "suggestion": domain.lower().replace(" ", "_"),
            })

        # Validate against BaseNode
        try:
            BaseNode.model_validate(node)
            report["valid_base"] += 1
        except ValidationError as e:
            report["base_errors"].append({
                "id": node_id,
                "errors": [str(err) for err in e.errors()],
            })

        # Validate against subclass
        model_class = NODE_TYPE_MAP.get(node_type)
        if model_class:
            try:
                model_class.model_validate(node)
                report["valid_subclass"] += 1
            except ValidationError as e:
                report["subclass_errors"].append({
                    "id": node_id,
                    "type": node_type,
                    "errors": [str(err) for err in e.errors()],
                })

                # Identify which fields are missing
                for err in e.errors():
                    if err["type"] == "missing":
                        report["missing_fields"].append({
                            "id": node_id,
                            "type": node_type,
                            "field": err["loc"],
                        })

    return report


def validate_sources(sources: list[dict]) -> dict:
    """
    Validate sources and identify SCHEMA-009 migration candidates.
    Tier-on-source instances need to move tier to citation edge.
    """
    report = {
        "total": len(sources),
        "valid": 0,
        "errors": [],
        "tier_migration_needed": [],  # SCHEMA-009
        "type_distribution": Counter(),
        "missing_type": [],
    }

    for source in sources:
        source_id = source.get("source_id") or source.get("id", "UNKNOWN")
        source_type = source.get("source_type")

        if not source_type:
            report["missing_type"].append(source_id)
            # Try to infer type
            if source.get("doi") or source.get("url"):
                source_type = "DOCUMENTARY"
            elif source.get("provider"):
                source_type = "STRUCTURED_DATA"

        if source_type:
            report["type_distribution"][source_type] += 1

        # Check for tier-on-source (SCHEMA-009 migration candidate)
        if source.get("tier") and source_type == "DOCUMENTARY":
            report["tier_migration_needed"].append({
                "source_id": source_id,
                "current_tier": source.get("tier"),
                "note": "Tier currently on source. Needs migration to citation edge.",
            })

        # Basic validation
        try:
            BaseSource.model_validate({
                "source_id": source_id,
                "source_type": source_type or "DOCUMENTARY",
                **{k: v for k, v in source.items() if k not in ("source_id", "source_type")},
            })
            report["valid"] += 1
        except ValidationError as e:
            report["errors"].append({
                "source_id": source_id,
                "errors": [str(err) for err in e.errors()],
            })

    return report


def main():
    data_dir = Path("data")

    print("=" * 60)
    print("BASIS Schema Migration Validator")
    print("Validating Phase 1 data against v0.2 schema")
    print("=" * 60)

    # Load data
    nodes = load_all_json(data_dir)
    sources_dir = data_dir / "sources"
    sources = load_all_json(sources_dir) if sources_dir.exists() else []

    # Also try loading from a single file
    for candidate in [data_dir / "nodes.json", data_dir / "graph.json"]:
        if candidate.exists() and not nodes:
            with open(candidate) as f:
                data = json.load(f)
                if isinstance(data, dict) and "nodes" in data:
                    nodes = data["nodes"]
                    sources = data.get("sources", sources)

    for candidate in [data_dir / "sources.json"]:
        if candidate.exists() and not sources:
            with open(candidate) as f:
                sources = json.load(f)

    if not nodes:
        print("\nNo node data found in data/. Skipping.")
        sys.exit(0)

    print(f"\nLoaded: {len(nodes)} nodes, {len(sources)} sources\n")

    # Validate nodes
    print("--- Node Validation ---")
    node_report = validate_nodes(nodes)
    print(f"  BaseNode valid:    {node_report['valid_base']}/{node_report['total']}")
    print(f"  Subclass valid:    {node_report['valid_subclass']}/{node_report['total']}")
    print(f"  Domain issues:     {len(node_report['domain_issues'])}")
    print(f"  Missing fields:    {len(node_report['missing_fields'])}")
    print(f"\n  Type distribution:")
    for t, count in node_report["type_distribution"].most_common():
        print(f"    {t}: {count}")

    if node_report["base_errors"]:
        print(f"\n  BaseNode errors (first 10):")
        for err in node_report["base_errors"][:10]:
            print(f"    {err['id']}: {err['errors'][0][:100]}")

    if node_report["domain_issues"]:
        print(f"\n  Domain issues (SCHEMA-002 violations):")
        for issue in node_report["domain_issues"][:10]:
            print(f"    {issue['id']}: '{issue['domain']}' -> suggest '{issue['suggestion']}'")

    # Validate sources
    if sources:
        print(f"\n--- Source Validation ---")
        source_report = validate_sources(sources)
        print(f"  Valid:              {source_report['valid']}/{source_report['total']}")
        print(f"  Missing type:       {len(source_report['missing_type'])}")
        print(f"  Tier migration:     {len(source_report['tier_migration_needed'])} (SCHEMA-009)")
        print(f"\n  Type distribution:")
        for t, count in source_report["type_distribution"].most_common():
            print(f"    {t}: {count}")
    else:
        print("\nNo source data found. Skipping source validation.")
        source_report = None

    # Write full report
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    full_report = {
        "nodes": node_report,
        "sources": source_report,
        "summary": {
            "nodes_valid_base": node_report["valid_base"],
            "nodes_valid_subclass": node_report["valid_subclass"],
            "nodes_total": node_report["total"],
            "sources_valid": source_report["valid"] if source_report else 0,
            "sources_total": source_report["total"] if source_report else 0,
            "tier_migration_count": len(source_report["tier_migration_needed"]) if source_report else 0,
            "domain_issues_count": len(node_report["domain_issues"]),
            "action_items": [],
        },
    }

    # Generate action items
    actions = full_report["summary"]["action_items"]
    if node_report["base_errors"]:
        actions.append(f"Fix {len(node_report['base_errors'])} BaseNode validation errors")
    if node_report["domain_issues"]:
        actions.append(f"Normalise {len(node_report['domain_issues'])} domain values to DomainEnum")
    if node_report["missing_fields"]:
        actions.append(f"Add {len(node_report['missing_fields'])} missing subclass fields")
    if source_report and source_report["tier_migration_needed"]:
        actions.append(f"Migrate {len(source_report['tier_migration_needed'])} sources: tier -> citation edge (SCHEMA-009)")
    if source_report and source_report["missing_type"]:
        actions.append(f"Assign source_type to {len(source_report['missing_type'])} sources")

    # Serialise Counter objects
    full_report["nodes"]["type_distribution"] = dict(node_report["type_distribution"])
    if source_report:
        full_report["sources"]["type_distribution"] = dict(source_report["type_distribution"])

    with open(reports_dir / "migration_report.json", "w") as f:
        json.dump(full_report, f, indent=2, default=str)

    print(f"\n--- Action Items ---")
    for i, action in enumerate(actions, 1):
        print(f"  {i}. {action}")

    print(f"\nFull report: reports/migration_report.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
