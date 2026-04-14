"""
audit_v1_graph.py — Validate the Phase 1 graph against the reconciled v2 schema.

Reads data/basis-kg-full.json (389 nodes, 172 sources, 745 edges) and reports
which records conform to base_schema.py / source_models.py, which can be
migrated with field-level adaptation, and which cannot be salvaged.

Output: a structured markdown report at docs/migration/AUDIT-V1-CONFORMANCE.md
plus a JSON dump for downstream tooling.

This does NOT modify the graph. It only reads and reports.

Invocation:
    python scripts/audit_v1_graph.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

# pydantic imports
from pydantic import ValidationError  # noqa: E402

# Skeleton schema (extracted from basis_full_build.tar.gz)
import base_schema as bs  # noqa: E402
import source_models as sm  # noqa: E402

# Shared v1 -> v2 adapters (canonical map + adapter functions)
from migration import (  # noqa: E402
    V1_DOMAIN_TO_V2,
    adapt_node_v1_to_v2_payload,
    adapt_source_v1_to_v2_payload,
    adapt_edge_v1_to_v2_payload,
)


GRAPH_PATH = REPO / "archive" / "v1" / "data" / "basis-kg-full.json"
REPORT_MD = REPO / "docs" / "migration" / "AUDIT-V1-CONFORMANCE.md"
REPORT_JSON = REPO / "docs" / "migration" / "audit-v1-conformance.json"


# ---------------------------------------------------------------------------
# Validation with diagnostic capture
# ---------------------------------------------------------------------------

def validate_one(payload: dict, model_cls, record_id: str) -> dict:
    """Try to construct the model. Return a dict of {ok, errors, missing, wrong}."""
    try:
        model_cls(**payload)
        return {"ok": True, "id": record_id, "errors": []}
    except ValidationError as exc:
        # Bucket errors into "missing required" vs "value mismatch" for clarity.
        bucketed: list[dict] = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err["loc"])
            bucketed.append(
                {
                    "field": loc,
                    "type": err["type"],
                    "msg": err["msg"],
                    "input_value": err.get("input"),
                }
            )
        return {"ok": False, "id": record_id, "errors": bucketed}


# ---------------------------------------------------------------------------
# Main audit routine
# ---------------------------------------------------------------------------

def audit_nodes(graph: dict) -> dict:
    """Validate every node against the appropriate v2 subclass."""
    subclass_map = {
        "FACT": bs.FactNode,
        "ASSUMPTION": bs.AssumptionNode,
        "CLAIM": bs.ClaimNode,
        "POLICY": bs.PolicyNode,
        "POSITION": bs.PositionNode,
    }

    results = {"pass": [], "fail": [], "by_type": defaultdict(lambda: {"pass": 0, "fail": 0})}

    for n in graph["nodes"]:
        payload = adapt_node_v1_to_v2_payload(n)
        node_type = n.get("type")
        model_cls = subclass_map.get(node_type, bs.BaseNode)

        # AssumptionNode requires basis_fact_ids and falsification_condition,
        # which v1 never captured. Skip to BaseNode validation for assumptions
        # so we report only the base-level gaps (not the subclass-level ones
        # that are universal v1 gaps).
        outcome = validate_one(payload, model_cls, n["id"])

        if outcome["ok"]:
            results["pass"].append(outcome)
            results["by_type"][node_type]["pass"] += 1
        else:
            results["fail"].append(outcome)
            results["by_type"][node_type]["fail"] += 1

    return results


def audit_sources(graph: dict) -> dict:
    """Validate every source against DocumentarySource (heuristic)."""
    results = {"pass": [], "fail": [], "by_tier": defaultdict(lambda: {"pass": 0, "fail": 0})}
    for s in graph["sources"]:
        payload = adapt_source_v1_to_v2_payload(s)
        outcome = validate_one(payload, sm.DocumentarySource, s["id"])
        tier_bucket = f"T{s.get('tier')}" if isinstance(s.get("tier"), int) else "unknown"
        if outcome["ok"]:
            results["pass"].append(outcome)
            results["by_tier"][tier_bucket]["pass"] += 1
        else:
            results["fail"].append(outcome)
            results["by_tier"][tier_bucket]["fail"] += 1
    return results


def audit_edges(graph: dict) -> dict:
    """Validate evidence edges against EvidenceEdge."""
    results = {"pass": [], "fail": [], "by_type": defaultdict(lambda: {"pass": 0, "fail": 0})}
    all_edges = graph["edges"] + graph["cross_domain_edges"]
    for i, e in enumerate(all_edges):
        synthetic_id = f"v1-edge-{i:04d}"
        payload = adapt_edge_v1_to_v2_payload(e, synthetic_id)
        outcome = validate_one(payload, bs.EvidenceEdge, synthetic_id)
        etype = e.get("type", "UNKNOWN")
        if outcome["ok"]:
            results["pass"].append(outcome)
            results["by_type"][etype]["pass"] += 1
        else:
            results["fail"].append(outcome)
            results["by_type"][etype]["fail"] += 1
    return results


# ---------------------------------------------------------------------------
# Error summarisation
# ---------------------------------------------------------------------------

def summarise_errors(failures: list[dict]) -> Counter:
    """Count (field, error_type) pairs across all failures."""
    c: Counter = Counter()
    for f in failures:
        for err in f["errors"]:
            c[(err["field"], err["type"])] += 1
    return c


def format_error_table(counts: Counter, top: int = 15) -> str:
    lines = ["| Field | Error type | Count |", "|---|---|---|"]
    for (field, etype), cnt in counts.most_common(top):
        lines.append(f"| `{field}` | `{etype}` | {cnt} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(node_res: dict, source_res: dict, edge_res: dict) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)

    node_total = len(node_res["pass"]) + len(node_res["fail"])
    source_total = len(source_res["pass"]) + len(source_res["fail"])
    edge_total = len(edge_res["pass"]) + len(edge_res["fail"])

    node_errors = summarise_errors(node_res["fail"])
    source_errors = summarise_errors(source_res["fail"])
    edge_errors = summarise_errors(edge_res["fail"])

    lines: list[str] = []
    lines.append("# v1 graph conformance audit")
    lines.append("")
    lines.append(
        "Validates `data/basis-kg-full.json` against the reconciled v2 schema "
        "(`src/base_schema.py`, `src/source_models.py`). Generated by "
        "`scripts/audit_v1_graph.py`."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Category | Total | Pass | Fail | Pass % |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        f"| Nodes | {node_total} | {len(node_res['pass'])} | {len(node_res['fail'])} | "
        f"{len(node_res['pass']) / node_total * 100:.1f}% |"
    )
    lines.append(
        f"| Sources | {source_total} | {len(source_res['pass'])} | {len(source_res['fail'])} | "
        f"{len(source_res['pass']) / source_total * 100:.1f}% |"
    )
    lines.append(
        f"| Edges | {edge_total} | {len(edge_res['pass'])} | {len(edge_res['fail'])} | "
        f"{len(edge_res['pass']) / edge_total * 100:.1f}% |"
    )
    lines.append("")

    lines.append("## Nodes — by type")
    lines.append("")
    lines.append("| Type | Pass | Fail |")
    lines.append("|---|---|---|")
    for t, c in sorted(node_res["by_type"].items()):
        lines.append(f"| {t} | {c['pass']} | {c['fail']} |")
    lines.append("")
    lines.append("### Top node-level errors")
    lines.append("")
    lines.append(format_error_table(node_errors))
    lines.append("")

    lines.append("## Sources — by v1 tier")
    lines.append("")
    lines.append("| Tier (v1) | Pass | Fail |")
    lines.append("|---|---|---|")
    for t, c in sorted(source_res["by_tier"].items()):
        lines.append(f"| {t} | {c['pass']} | {c['fail']} |")
    lines.append("")
    lines.append("### Top source-level errors")
    lines.append("")
    lines.append(format_error_table(source_errors))
    lines.append("")

    lines.append("## Edges — by type")
    lines.append("")
    lines.append("| Type | Pass | Fail |")
    lines.append("|---|---|---|")
    for t, c in sorted(edge_res["by_type"].items()):
        lines.append(f"| {t} | {c['pass']} | {c['fail']} |")
    lines.append("")
    lines.append("### Top edge-level errors")
    lines.append("")
    lines.append(format_error_table(edge_errors))
    lines.append("")

    lines.append("## Interpretation guide")
    lines.append("")
    lines.append(
        "- `missing` errors are v1 fields that don't exist. Usually fixable "
        "by a migration script that supplies defaults or derives from context."
    )
    lines.append(
        "- `enum` / `literal_error` means the v1 value is not in the v2 enum "
        "(e.g. `domain='energy'` — no such member in `DomainEnum`). Requires "
        "either extending the v2 enum or reclassifying the record."
    )
    lines.append(
        "- `string_too_short` means the v1 text failed a min-length gate "
        "(e.g. edge `explanation` < 10 chars). Unfixable without re-authoring."
    )
    lines.append("")
    lines.append("Pair this report with `docs/migration/README.md` when it lands.")
    lines.append("")

    REPORT_MD.write_text("\n".join(lines))

    # Dump full JSON for downstream tooling.
    # Drop Pydantic-object references; keep only serialisable content.
    def clean(results: dict) -> dict:
        return {
            "pass_count": len(results["pass"]),
            "fail_count": len(results["fail"]),
            "failures": [
                {"id": f["id"], "errors": f["errors"]} for f in results["fail"]
            ],
        }

    REPORT_JSON.write_text(
        json.dumps(
            {
                "nodes": clean(node_res),
                "sources": clean(source_res),
                "edges": clean(edge_res),
            },
            indent=2,
            default=str,
        )
    )


def main() -> None:
    graph = json.loads(GRAPH_PATH.read_text())
    print(f"Loaded graph: {len(graph['nodes'])} nodes, "
          f"{len(graph['sources'])} sources, "
          f"{len(graph['edges']) + len(graph['cross_domain_edges'])} edges")

    node_res = audit_nodes(graph)
    source_res = audit_sources(graph)
    edge_res = audit_edges(graph)

    write_report(node_res, source_res, edge_res)

    print(f"Nodes:   {len(node_res['pass'])}/{len(node_res['pass']) + len(node_res['fail'])} pass")
    print(f"Sources: {len(source_res['pass'])}/{len(source_res['pass']) + len(source_res['fail'])} pass")
    print(f"Edges:   {len(edge_res['pass'])}/{len(edge_res['pass']) + len(edge_res['fail'])} pass")
    print(f"Report:  {REPORT_MD.relative_to(REPO)}")


if __name__ == "__main__":
    main()
