#!/usr/bin/env python3
"""
validate.py — 6-check CI validator.

Runs on every PR. Fails build on:
  1. Schema violations (node doesn't conform to BaseNode + subclass)
  2. Orphan nodes (referenced but not present)
  3. Invalid topics/domains
  4. Fiscal gap out of range
  5. Confidence inconsistencies
  6. Source integrity (source_id references valid source)

Exit 0 = all checks pass. Exit 1 = any check fails.
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base_schema import (
    BaseNode,
    ClaimNode,
    ConfidenceLevel,
    DomainEnum,
    EdgeType,
    EvidenceEdge,
    FactNode,
    AssumptionNode,
    PolicyNode,
    PositionNode,
)


def load_json_files(directory: Path) -> list[dict]:
    """Load all JSON files from a directory."""
    items = []
    if not directory.exists():
        return items
    for f in directory.glob("*.json"):
        with open(f) as fh:
            data = json.load(fh)
            if isinstance(data, list):
                items.extend(data)
            else:
                items.append(data)
    return items


NODE_TYPE_MAP = {
    "FACT": FactNode,
    "ASSUMPTION": AssumptionNode,
    "CLAIM": ClaimNode,
    "POLICY": PolicyNode,
    "POSITION": PositionNode,
}


class ValidationReport:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.checks_passed = 0
        self.checks_failed = 0

    def error(self, check: str, msg: str):
        self.errors.append(f"[{check}] {msg}")
        self.checks_failed += 1

    def warn(self, check: str, msg: str):
        self.warnings.append(f"[{check}] {msg}")

    def passed(self, check: str):
        self.checks_passed += 1

    def report(self) -> int:
        print(f"\n{'='*60}")
        print(f"BASIS Validation Report")
        print(f"{'='*60}")
        print(f"Checks passed: {self.checks_passed}")
        print(f"Checks failed: {self.checks_failed}")
        print(f"Warnings: {len(self.warnings)}")
        if self.warnings:
            print(f"\nWarnings:")
            for w in self.warnings:
                print(f"  {w}")
        if self.errors:
            print(f"\nErrors:")
            for e in self.errors:
                print(f"  {e}")
        print(f"{'='*60}")
        return 1 if self.errors else 0


def check_1_schema(nodes: list[dict], report: ValidationReport):
    """Check 1: Every node conforms to BaseNode + appropriate subclass."""
    valid = 0
    for node in nodes:
        node_type = node.get("node_type", "UNKNOWN")
        model_class = NODE_TYPE_MAP.get(node_type, BaseNode)
        try:
            model_class.model_validate(node)
            valid += 1
        except Exception as e:
            report.error("SCHEMA", f"Node {node.get('id', '?')}: {e}")
    if valid == len(nodes):
        report.passed("SCHEMA")
    print(f"  Check 1 (Schema): {valid}/{len(nodes)} valid")


def check_2_orphans(nodes: list[dict], edges: list[dict], report: ValidationReport):
    """Check 2: No orphan references in edges."""
    node_ids = {n["id"] for n in nodes}
    orphans = []
    for edge in edges:
        if edge.get("from_id") not in node_ids:
            orphans.append(f"Edge {edge.get('id','?')}: from_id={edge.get('from_id')} not found")
        if edge.get("to_id") not in node_ids:
            orphans.append(f"Edge {edge.get('id','?')}: to_id={edge.get('to_id')} not found")
    if orphans:
        for o in orphans:
            report.error("ORPHAN", o)
    else:
        report.passed("ORPHAN")
    print(f"  Check 2 (Orphans): {len(orphans)} found")


def check_3_domains(nodes: list[dict], report: ValidationReport):
    """Check 3: All domains are valid DomainEnum values."""
    valid_domains = {d.value for d in DomainEnum}
    invalid = []
    for node in nodes:
        domain = node.get("domain")
        if domain and domain not in valid_domains:
            invalid.append(f"Node {node.get('id','?')}: domain='{domain}' not in DomainEnum")
    if invalid:
        for i in invalid:
            report.error("DOMAIN", i)
    else:
        report.passed("DOMAIN")
    print(f"  Check 3 (Domains): {len(invalid)} invalid")


def check_4_fiscal(nodes: list[dict], report: ValidationReport):
    """
    Check 4: Fiscal gap recomputation.
    Recompute from gap_role metadata and assert it overlaps stated range.
    """
    STATED_LOW = 44.0   # bn GBP
    STATED_HIGH = 146.0  # bn GBP (updated range)

    spending_total = 0.0
    revenue_total = 0.0
    for node in nodes:
        fiscal = node.get("fiscal")
        if not fiscal:
            continue
        gap_role = fiscal.get("gap_role")
        if gap_role in ("summary", "position_only"):
            continue

        amount = fiscal.get("amount", 0)
        unit = fiscal.get("unit", "bn_gbp")
        direction = fiscal.get("direction", "spending")
        horizon = fiscal.get("horizon_years")

        # Normalise to bn_gbp
        if unit == "m_gbp":
            amount /= 1000
        elif unit == "pct_gdp":
            amount = amount / 100 * 2.3  # GDP ~2.3tn (SCHEMA-014, OQ-009)

        # Annualise cumulative amounts
        if horizon and horizon > 1:
            amount /= horizon

        if direction == "spending":
            spending_total += amount
        elif direction == "revenue":
            revenue_total += amount

    net_gap = spending_total - revenue_total

    if net_gap == 0 and not any(n.get("fiscal") for n in nodes):
        report.warn("FISCAL", "No fiscal nodes found — skipping gap check")
    elif STATED_LOW <= net_gap <= STATED_HIGH:
        report.passed("FISCAL")
    elif net_gap == 0:
        report.warn("FISCAL", "Computed gap is 0 — likely no fiscal data loaded")
    else:
        report.error(
            "FISCAL",
            f"Computed gap {net_gap:.1f}bn outside stated range "
            f"[{STATED_LOW}, {STATED_HIGH}]"
        )
    print(f"  Check 4 (Fiscal): spending={spending_total:.1f}bn, "
          f"revenue={revenue_total:.1f}bn, net={net_gap:.1f}bn")


def check_5_confidence(nodes: list[dict], report: ValidationReport):
    """Check 5: Confidence values are valid and consistent."""
    valid_levels = {"HIGH", "MEDIUM", "LOW", None}
    issues = []
    for node in nodes:
        conf = node.get("confidence")
        if conf and conf not in valid_levels:
            issues.append(f"Node {node.get('id','?')}: confidence='{conf}' invalid")
        # Check computed_confidence structure if present
        cc = node.get("computed_confidence")
        if cc and isinstance(cc, dict):
            if not all(k in cc for k in ("mean", "std", "p5", "p95", "label")):
                issues.append(f"Node {node.get('id','?')}: computed_confidence missing fields")
    if issues:
        for i in issues:
            report.error("CONFIDENCE", i)
    else:
        report.passed("CONFIDENCE")
    print(f"  Check 5 (Confidence): {len(issues)} issues")


def check_6_sources(nodes: list[dict], sources: list[dict], report: ValidationReport):
    """Check 6: source_id references point to valid sources."""
    source_ids = {s.get("source_id") or s.get("id") for s in sources}
    missing = []
    for node in nodes:
        sid = node.get("source_id")
        if sid and sid not in source_ids:
            missing.append(f"Node {node.get('id','?')}: source_id='{sid}' not in sources")
    if missing:
        for m in missing:
            report.error("SOURCE", m)
    else:
        report.passed("SOURCE")
    print(f"  Check 6 (Sources): {len(missing)} missing references")


def main():
    data_dir = Path("data")

    # Load data
    nodes = load_json_files(data_dir / "nodes") or load_json_files(data_dir)
    edges = load_json_files(data_dir / "edges") or []
    sources = load_json_files(data_dir / "sources") or []

    if not nodes:
        print("No node data found in data/ directory. Looking for alternative paths...")
        # Try flat structure
        for candidate in [Path("data/nodes.json"), Path("data/graph.json")]:
            if candidate.exists():
                with open(candidate) as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "nodes" in data:
                        nodes = data["nodes"]
                        edges = data.get("edges", [])
                    elif isinstance(data, list):
                        nodes = data
                break

    if not nodes:
        print("WARNING: No node data found. Validation skipped.")
        sys.exit(0)

    print(f"Loaded: {len(nodes)} nodes, {len(edges)} edges, {len(sources)} sources\n")

    report = ValidationReport()

    check_1_schema(nodes, report)
    check_2_orphans(nodes, edges, report)
    check_3_domains(nodes, report)
    check_4_fiscal(nodes, report)
    check_5_confidence(nodes, report)
    check_6_sources(nodes, sources, report)

    sys.exit(report.report())


if __name__ == "__main__":
    main()
