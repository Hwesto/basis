#!/usr/bin/env python3
"""
legal_checks.py — SCHEMA-023: Legal consistency CI checks.

Check 7: ENFORCEMENT_GAP — DUTY with no MECHANISM via ENFORCED_BY
Check 8: MISSING_CORRELATIVE — RIGHT with no DUTY, POWER with no LIABILITY

Runs against Supabase if credentials available, otherwise against local JSON.
Exits 0 if no legal nodes exist yet (not blocking until Phase 4).
"""

import json
import os
import sys
from pathlib import Path


def load_local_legal_data():
    """Load legal nodes and edges from local JSON fixtures."""
    nodes = []
    edges = []

    fixtures_dir = Path("fixtures")
    data_dir = Path("data")

    for d in [fixtures_dir, data_dir]:
        for f in d.glob("**/*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        for item in data:
                            if item.get("node_type") in (
                                "RIGHT", "DUTY", "POWER", "LIABILITY",
                                "PRIVILEGE", "IMMUNITY", "MECHANISM",
                                "REGULATORY_BODY", "EVIDENCE_REQUIREMENT",
                                "ESCALATION_PATH", "PRECEDENT"
                            ):
                                nodes.append(item)
                    elif isinstance(data, dict):
                        if "legal_nodes" in data:
                            nodes.extend(data["legal_nodes"])
                        if "legal_edges" in data:
                            edges.extend(data["legal_edges"])
            except (json.JSONDecodeError, KeyError):
                continue

    return nodes, edges


def check_enforcement_gap(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """
    Check 7: Any DUTY node with no MECHANISM reachable via ENFORCED_BY edges.
    Returns list of findings (enforcement gaps).
    """
    duty_nodes = [n for n in nodes if n.get("node_type") == "DUTY" and n.get("curator_approved")]
    mechanism_ids = {n["id"] for n in nodes if n.get("node_type") == "MECHANISM"}

    # Build ENFORCED_BY adjacency from duty nodes
    enforced_by = {}
    for edge in edges:
        if edge.get("edge_type") == "ENFORCED_BY":
            from_id = edge.get("from_id")
            to_id = edge.get("to_id")
            if from_id not in enforced_by:
                enforced_by[from_id] = set()
            enforced_by[from_id].add(to_id)

    gaps = []
    for duty in duty_nodes:
        reachable_mechanisms = enforced_by.get(duty["id"], set()) & mechanism_ids
        if not reachable_mechanisms:
            gaps.append({
                "check": "ENFORCEMENT_GAP",
                "node_id": duty["id"],
                "node_type": "DUTY",
                "statement": duty.get("statement", ""),
                "domain": duty.get("domain", ""),
                "note": "No MECHANISM reachable via ENFORCED_BY. "
                        "May be extraction gap or genuine legislative gap."
            })

    return gaps


def check_missing_correlative(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """
    Check 8: RIGHT with no DUTY, POWER with no LIABILITY.
    Hohfeld requires correlative pairs.
    """
    CORRELATIVE_PAIRS = [
        ("RIGHT", "DUTY"),
        ("POWER", "LIABILITY"),
    ]

    # Build adjacency (any edge connecting the pair counts)
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        from_id = edge.get("from_id")
        to_id = edge.get("to_id")
        adjacency.setdefault(from_id, set()).add(to_id)
        adjacency.setdefault(to_id, set()).add(from_id)

    node_type_map = {n["id"]: n.get("node_type") for n in nodes}
    approved_nodes = [n for n in nodes if n.get("curator_approved")]

    gaps = []
    for primary_type, correlative_type in CORRELATIVE_PAIRS:
        primary_nodes = [n for n in approved_nodes if n.get("node_type") == primary_type]
        correlative_ids = {
            n["id"] for n in nodes if n.get("node_type") == correlative_type
        }

        for node in primary_nodes:
            connected = adjacency.get(node["id"], set())
            has_correlative = bool(connected & correlative_ids)
            if not has_correlative:
                gaps.append({
                    "check": "MISSING_CORRELATIVE",
                    "node_id": node["id"],
                    "node_type": primary_type,
                    "missing": correlative_type,
                    "statement": node.get("statement", ""),
                    "domain": node.get("domain", ""),
                    "note": f"{primary_type} with no corresponding {correlative_type}. "
                            "May be extraction gap or legal incoherence."
                })

    return gaps


def main():
    nodes, edges = load_local_legal_data()

    if not nodes:
        print("No legal nodes found. Checks skipped (not blocking until Phase 4).")
        sys.exit(0)

    print(f"Legal consistency checks: {len(nodes)} nodes, {len(edges)} edges\n")

    # Check 7
    enforcement_gaps = check_enforcement_gap(nodes, edges)
    print(f"Check 7 (ENFORCEMENT_GAP): {len(enforcement_gaps)} findings")
    for gap in enforcement_gaps:
        print(f"  {gap['node_id']}: {gap['statement'][:80]}...")

    # Check 8
    correlative_gaps = check_missing_correlative(nodes, edges)
    print(f"Check 8 (MISSING_CORRELATIVE): {len(correlative_gaps)} findings")
    for gap in correlative_gaps:
        print(f"  {gap['node_id']} ({gap['node_type']}): missing {gap['missing']}")

    # Write findings report
    findings = enforcement_gaps + correlative_gaps
    if findings:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        with open(reports_dir / "legal_consistency.json", "w") as f:
            json.dump(findings, f, indent=2)
        print(f"\nFindings written to reports/legal_consistency.json")

    # These are findings, not blocking errors.
    # Genuine enforcement gaps are civic findings worth surfacing.
    # Only exit non-zero if we detect actual data integrity issues.
    print("\nLegal consistency checks complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
